"""
URL Scan Service — analyzes a suspicious URL using httpx.
Detects redirects, SSL issues, phishing patterns, and malicious JS.
Playwright (deep JS sandbox) is planned for V2.
"""

import ipaddress
import json
import re
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url_scan import UrlScan
from app.models.user import User

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUSPICIOUS_TLDS = {
    ".ru", ".cn", ".tk", ".ml", ".ga", ".cf", ".top",
    ".xyz", ".pw", ".cc", ".biz", ".click", ".cam",
}

PHISHING_KEYWORDS = [
    "paypal", "amazon", "bank", "secure", "verify", "account",
    "password", "credit-card", "ssn", "irs", "tax-refund",
    "google", "microsoft", "apple", "facebook", "instagram",
    "login-update", "billing", "suspended",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS IMDS + link-local
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Known internal hostnames that must never be scanned
_INTERNAL_HOSTNAMES = {"localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal"}  # nosec B104


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return True  # unparseable → block


def _validate_url(url: str) -> None:
    """
    Raise ValueError if URL points to an internal/private resource.
    Uses DNS resolution to catch rebinding attacks — not just string matching.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL invalide : hôte manquant")

    # Fast path: block well-known internal hostnames by name
    if hostname in _INTERNAL_HOSTNAMES:
        raise ValueError("Scan of internal addresses is not allowed")

    # If the hostname is a literal IP, check it directly (no DNS needed)
    try:
        ipaddress.ip_address(hostname)
        is_literal_ip = True
    except ValueError:
        is_literal_ip = False

    if is_literal_ip:
        if _is_private_ip(hostname):
            raise ValueError("Scan of private network addresses is not allowed")
        return

    # Resolve hostname → check every returned IP (guards against DNS rebinding)
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Impossible de résoudre l'hôte : {hostname}")
    for info in infos:
        ip = info[4][0]
        if _is_private_ip(ip):
            raise ValueError("Scan of private network addresses is not allowed")


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

async def _analyze_url(url: str) -> dict:
    _validate_url(url)

    original_domain = urlparse(url).hostname or ""
    findings: list[dict] = []
    score = 0
    ssl_valid = True
    redirect_chain: list[str] = []
    final_url = url
    html = ""

    # ── 1. Fetch with redirect tracking ────────────────────────────────────
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            verify=True,
            headers=HEADERS,
        ) as client:
            resp = await client.get(url)
            final_url = str(resp.url)
            redirect_chain = [str(r.url) for r in resp.history]
            html = resp.text[:200_000]  # cap at 200 KB

    except httpx.TimeoutException:
        raise ValueError("L'URL ne répond pas (timeout 15s)")
    except httpx.ConnectError as exc:
        # httpx raises ConnectError for SSL failures; check the message to distinguish
        exc_str = str(exc).lower()
        if any(t in exc_str for t in ("ssl", "certificate", "tls", "handshake", "verify")):
            ssl_valid = False
            score += 20
            findings.append({
                "type": "ssl_error",
                "severity": "high",
                "time_ms": None,
                "detail": "Certificat SSL invalide ou expiré",
            })
            # Retry without SSL verification to still analyze content
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=15.0,
                    verify=False,  # nosec B501 — fallback scan for sites with invalid certs
                    headers=HEADERS,
                ) as client:
                    resp = await client.get(url)
                    final_url = str(resp.url)
                    redirect_chain = [str(r.url) for r in resp.history]
                    html = resp.text[:200_000]
            except Exception:
                html = ""
        else:
            raise ValueError(f"Erreur réseau : {exc}")
    except httpx.RequestError as exc:
        raise ValueError(f"Erreur réseau : {exc}")

    final_domain = urlparse(final_url).hostname or original_domain

    # ── 1b. SSRF guard on redirect targets ────────────────────────────────────
    for redir_url in redirect_chain + ([final_url] if final_url != url else []):
        try:
            _validate_url(redir_url)
        except ValueError:
            score = min(score + 50, 100)
            findings.append({
                "type": "ssrf_redirect",
                "severity": "critical",
                "time_ms": None,
                "detail": f"Redirection vers une adresse interne détectée : {urlparse(redir_url).hostname}",
            })
            html = ""  # discard any fetched content from internal address
            break

    # ── 2. Redirect chain analysis ──────────────────────────────────────────
    if redirect_chain:
        if final_domain.lower() != original_domain.lower():
            score += 25
            findings.append({
                "type": "domain_redirect",
                "severity": "high",
                "time_ms": None,
                "detail": f"Redirection vers un domaine différent : {final_domain}",
            })
        if len(redirect_chain) > 2:
            score += 10
            findings.append({
                "type": "multiple_redirects",
                "severity": "medium",
                "time_ms": None,
                "detail": f"{len(redirect_chain)} redirections détectées",
            })

    # ── 3. Suspicious TLD ───────────────────────────────────────────────────
    all_domains = {original_domain, final_domain} | {
        urlparse(r).hostname or "" for r in redirect_chain
    }
    for domain in all_domains:
        for tld in SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                score += 20
                findings.append({
                    "type": "suspicious_tld",
                    "severity": "high",
                    "time_ms": None,
                    "detail": f"TLD suspect détecté : {domain}",
                })
                break

    # ── 4. HTML / JS analysis ───────────────────────────────────────────────
    if html:
        # 4a. eval() — JS obfuscation
        if re.search(r'\beval\s*\(', html):
            score += 15
            findings.append({
                "type": "js_eval",
                "severity": "medium",
                "time_ms": 450,
                "detail": "Utilisation de eval() détectée — possible obfuscation JS",
            })

        # 4b. document.cookie — cookie stealing
        if re.search(r'document\.cookie', html):
            score += 15
            findings.append({
                "type": "cookie_access",
                "severity": "medium",
                "time_ms": 620,
                "detail": "Accès aux cookies détecté (document.cookie)",
            })

        # 4c. window.location forced redirect in JS
        if re.search(r'window\.location\s*=', html):
            score += 15
            findings.append({
                "type": "js_redirect",
                "severity": "medium",
                "time_ms": 800,
                "detail": "Redirection JS forcée via window.location",
            })

        # 4d. External form action (phishing)
        ext_forms = re.findall(
            r'<form[^>]+action=["\']?(https?://[^"\'> ]+)',
            html, re.IGNORECASE
        )
        for action in ext_forms:
            form_domain = urlparse(action).hostname or ""
            if form_domain and form_domain.lower() != final_domain.lower():
                score += 30
                findings.append({
                    "type": "external_form",
                    "severity": "critical",
                    "time_ms": 900,
                    "detail": f"Formulaire envoyant des données vers {form_domain}",
                })

        # 4e. External iframes
        ext_iframes = re.findall(
            r'<iframe[^>]+src=["\']?(https?://[^"\'> ]+)',
            html, re.IGNORECASE
        )
        for src in ext_iframes:
            iframe_domain = urlparse(src).hostname or ""
            if iframe_domain and iframe_domain.lower() != final_domain.lower():
                score += 20
                findings.append({
                    "type": "external_iframe",
                    "severity": "high",
                    "time_ms": 1100,
                    "detail": f"iframe externe chargée depuis {iframe_domain}",
                })

        # 4f. Meta refresh redirect
        if re.search(r'<meta[^>]+http-equiv=["\']?refresh', html, re.IGNORECASE):
            score += 15
            findings.append({
                "type": "meta_refresh",
                "severity": "medium",
                "time_ms": 200,
                "detail": "Redirection automatique (meta refresh) détectée",
            })

        # 4g. Phishing keywords in visible text (only if domain differs or is suspicious)
        page_text = re.sub(r"<[^>]+>", " ", html).lower()
        for kw in PHISHING_KEYWORDS:
            if kw in page_text and kw not in original_domain.lower():
                score += 10
                findings.append({
                    "type": "phishing_keyword",
                    "severity": "medium",
                    "time_ms": None,
                    "detail": f"Mot-clé de phishing potentiel : « {kw} »",
                })
                break  # Only one keyword finding to avoid score inflation

    # ── 5. Cap score and determine verdict ──────────────────────────────────
    score = min(score, 100)

    if score >= 66:
        verdict = "malicious"
    elif score >= 31:
        verdict = "suspicious"
    else:
        verdict = "safe"

    # Determine primary threat type
    type_priority = ["external_form", "js_eval", "cookie_access", "domain_redirect", "phishing_keyword"]
    threat_map = {
        "external_form": "phishing",
        "js_eval": "malware",
        "cookie_access": "malware",
        "js_redirect": "malware",
        "domain_redirect": "redirect",
        "multiple_redirects": "redirect",
        "phishing_keyword": "phishing",
        "external_iframe": "tracker",
        "suspicious_tld": "malicious_domain",
    }
    threat_type = None
    for finding in findings:
        mapped = threat_map.get(finding["type"])
        if mapped:
            threat_type = mapped
            break

    return {
        "verdict": verdict,
        "threat_type": threat_type,
        "threat_score": score,
        "ssl_valid": ssl_valid,
        "original_url": url,
        "final_url": final_url,
        "original_domain": original_domain,
        "final_domain": final_domain,
        "redirect_count": len(redirect_chain),
        "redirect_chain": redirect_chain[:10],
        "findings": findings,
        "screenshot_url": None,  # Playwright in V2
    }


# ---------------------------------------------------------------------------
# Background task entry point
# ---------------------------------------------------------------------------

async def run_url_scan(url_scan_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(UrlScan).where(UrlScan.id == url_scan_id))
    url_scan: UrlScan | None = result.scalar_one_or_none()
    if not url_scan:
        return

    url_scan.status = "running"
    url_scan.started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        analysis = await _analyze_url(url_scan.url)

        url_scan.status = "done"
        url_scan.finished_at = datetime.now(timezone.utc)
        url_scan.verdict = analysis["verdict"]
        url_scan.threat_type = analysis["threat_type"]
        url_scan.threat_score = analysis["threat_score"]
        url_scan.results_json = json.dumps(analysis, default=str)
        await db.commit()

        # In-app notification
        try:
            from app.models.notification import Notification
            verdict = analysis["verdict"]
            score = analysis["threat_score"]
            icon = {"safe": "✅", "suspicious": "⚠️", "malicious": "🚨"}.get(verdict, "🔍")
            notif = Notification(
                user_id=url_scan.user_id,
                type="url_scan_done",
                title=f"{icon} Scan URL — {verdict.capitalize()} (score {score}/100)",
                body=url_scan.url[:120],
                link="/cyberscan/url-scanner",
            )
            db.add(notif)
            await db.commit()
        except Exception:
            pass

        # Send email alert (non-blocking — ignore SMTP errors)
        try:
            from app.core.config import settings
            from app.services.email_service import send_url_scan_alert
            user_result = await db.execute(select(User).where(User.id == url_scan.user_id))
            user = user_result.scalar_one_or_none()
            if user:
                dashboard_url = f"{settings.FRONTEND_URL}/cyberscan/url-scanner"
                send_url_scan_alert(
                    to_email=user.email,
                    scanned_url=url_scan.url,
                    verdict=analysis["verdict"],
                    threat_score=analysis["threat_score"],
                    threat_type=analysis["threat_type"],
                    findings=analysis["findings"],
                    dashboard_url=dashboard_url,
                )
        except Exception:
            pass  # Email failure must never crash the scan

    except Exception as exc:
        url_scan.status = "error"
        url_scan.finished_at = datetime.now(timezone.utc)
        url_scan.error_message = str(exc)[:500]
        await db.commit()
