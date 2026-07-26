"""
Public scan service — runs a fast subset of scanner modules (no auth required).

Modules run: SSL, headers, email, cookies, CORS, IP reputation, DNS, CMS, WAF.
Skipped: ports (slow), breach (API key), tech/TLS/takeover/threat_intel (tier 3+).
No PDF or remediation scripts generated.
"""

import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ssrf import assert_no_ssrf
from app.models.public_scan import PublicScan

SCANNER_DIR = Path(__file__).resolve().parents[3] / "cyber-scanner"
sys.path.insert(0, str(SCANNER_DIR))

# Plafond de domaines distincts débloquables par une même adresse email (gate lead).
# Une PME multi-sites peut débloquer jusqu'à 3 domaines gratuitement ; au-delà on
# renvoie vers la création de compte.
MAX_DOMAINS_PER_EMAIL = 3


class ScanNotReadyError(Exception):
    """Le scan n'est pas encore terminé : déblocage impossible."""


class QuotaExceededError(Exception):
    """L'email a déjà atteint le plafond de domaines gratuits."""


def hash_ip(ip: str) -> str:
    """Hash SHA-256 salé de l'IP (RGPD : jamais d'IP en clair en base)."""
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()


def _domain_of(url: str) -> str:
    """Extrait le domaine (hostname en minuscules) d'une URL, sinon l'URL brute."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return (urlparse(url).hostname or url).lower()


def compute_severity_counts(scan: PublicScan) -> dict[str, int] | None:
    """Teaser agrégé : nombre de modules par sévérité, sans exposer le moindre détail.

    Renvoie None tant que le scan n'a pas produit de résultats.
    """
    if not scan.results_json:
        return None
    try:
        results = json.loads(scan.results_json)
    except (ValueError, TypeError):
        return None
    counts = {"CRITICAL": 0, "WARNING": 0, "OK": 0}
    for key, module in results.items():
        if key == "_meta" or not isinstance(module, dict):
            continue
        status = module.get("status")
        if status in counts:
            counts[status] += 1
    return counts


def _run_demo_scan_sync(url: str) -> dict:
    from urllib.parse import urlparse

    from scanner.cms_detector import detect_cms
    from scanner.cookie_checker import check_cookies
    from scanner.cors_checker import check_cors
    from scanner.dns_scanner import scan_subdomains
    from scanner.email_checker import check_email_security
    from scanner.headers_checker import check_headers
    from scanner.ip_reputation import check_ip_reputation
    from scanner.ssl_checker import check_ssl
    from scanner.waf_detector import detect_waf

    hostname = urlparse(url).hostname or url

    ssl_result = check_ssl(hostname)
    headers_result = check_headers(url)
    email_result = check_email_security(hostname)
    cookie_result = check_cookies(url)
    cors_result = check_cors(url)
    ip_result = check_ip_reputation(hostname)
    dns_result = scan_subdomains(hostname)
    cms_result = detect_cms(url)
    waf_result = detect_waf(url)

    all_statuses = [
        ssl_result.get("status"),
        headers_result.get("status"),
        email_result.get("status"),
        cookie_result.get("status"),
        cors_result.get("status"),
        ip_result.get("status"),
        dns_result.get("status"),
        cms_result.get("status"),
        waf_result.get("status"),
    ]

    if "CRITICAL" in all_statuses:
        overall = "CRITICAL"
    elif "WARNING" in all_statuses:
        overall = "WARNING"
    else:
        overall = "OK"

    results = {
        "ssl": ssl_result,
        "headers": headers_result,
        "email": email_result,
        "cookies": cookie_result,
        "cors": cors_result,
        "ip": ip_result,
        "dns": dns_result,
        "cms": cms_result,
        "waf": waf_result,
        "_meta": {"tier": 2, "url": url},
    }

    return {"results": results, "overall": overall}


async def run_public_scan(public_scan_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(PublicScan).where(PublicScan.id == public_scan_id))
    scan: PublicScan | None = result.scalar_one_or_none()
    if not scan:
        return

    scan.status = "running"
    scan.started_at = datetime.now(UTC)
    await db.commit()

    url = scan.target_url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Re-validation SSRF a l'EXECUTION (defense anti DNS-rebinding / TOCTOU).
    # assert_no_ssrf a deja ete appele a la creation de l'endpoint, mais le DNS a
    # pu basculer vers une IP interne entre-temps. Les sondes HTTP passent par
    # scanner.safe_http (revalide chaque hop + re-resout), mais les sondes
    # non-HTTP (check_ssl socket TLS, check_ip_reputation, DNS) re-resolvent sans
    # garde -> on revalide ici, comme url_scan_service._validate_url.
    try:
        assert_no_ssrf(url)
    except HTTPException:
        scan.status = "failed"
        scan.error_message = (
            "URL refusee : l'hote resout vers une adresse interne au moment du scan"
        )
        scan.finished_at = datetime.now(UTC)
        await db.commit()
        return

    try:
        loop = asyncio.get_running_loop()
        outcome = await loop.run_in_executor(None, _run_demo_scan_sync, url)
        scan.status = "done"
        scan.overall_status = outcome["overall"]
        scan.results_json = json.dumps(outcome["results"], default=str)
        scan.finished_at = datetime.now(UTC)
    except Exception as exc:
        logger.error(f"Public scan {public_scan_id} failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:512]
        scan.finished_at = datetime.now(UTC)

    await db.commit()


async def list_recent_public_scans(db: AsyncSession, limit: int = 50) -> list[PublicScan]:
    """Retourne les scans publics les plus recents (ordre anti-chronologique)."""
    result = await db.execute(
        select(PublicScan).order_by(PublicScan.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def create_public_scan(db: AsyncSession, target_url: str) -> PublicScan:
    """Cree un scan public en attente et le renvoie (rafraichi)."""
    scan = PublicScan(target_url=target_url, status="pending")
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


async def get_public_scan_by_token(db: AsyncSession, token: str) -> PublicScan | None:
    """Retourne le scan public correspondant au token de session, ou None."""
    result = await db.execute(select(PublicScan).where(PublicScan.session_token == token))
    return result.scalar_one_or_none()


async def _unlocked_domains_for_email(db: AsyncSession, email: str) -> set[str]:
    """Domaines distincts déjà débloqués (consentement posé) par cette adresse email."""
    result = await db.execute(
        select(PublicScan.domain)
        .where(
            PublicScan.email == email,
            PublicScan.email_consent_at.is_not(None),
            PublicScan.domain.is_not(None),
        )
        .distinct()
    )
    return {d for (d,) in result.all() if d}


async def unlock_public_scan(
    db: AsyncSession, *, token: str, email: str, ip_hash: str
) -> PublicScan | None:
    """Débloque le rapport complet d'un scan public après capture du lead (email).

    Quota : 1 rapport par email + domaine, plafond MAX_DOMAINS_PER_EMAIL domaines par
    email. Débloquer à nouveau un domaine déjà débloqué par le même email est idempotent
    (ne consomme pas de quota).

    Retourne le scan débloqué, None si le token est inconnu. Lève ScanNotReadyError si le scan
    n'est pas terminé, QuotaExceededError si le plafond de domaines est atteint.
    """
    scan = await get_public_scan_by_token(db, token)
    if scan is None:
        return None
    if scan.status != "done":
        raise ScanNotReadyError

    email = email.strip().lower()
    domain = _domain_of(scan.target_url)

    # Déjà débloqué par le même email → idempotent (on ne repose rien, on re-sert).
    if scan.email_consent_at is not None and scan.email == email:
        return scan

    unlocked_domains = await _unlocked_domains_for_email(db, email)
    if domain not in unlocked_domains and len(unlocked_domains) >= MAX_DOMAINS_PER_EMAIL:
        raise QuotaExceededError

    scan.email = email
    scan.email_consent_at = datetime.now(UTC)
    scan.ip_hash = ip_hash
    scan.domain = domain
    await db.commit()
    await db.refresh(scan)
    return scan
