"""
Scan service — runs the cyber-scanner against a site URL,
saves the PDF, and updates the Scan record in DB.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan
from app.models.site import Site

# Resolve cyber-scanner path (sibling of backend/)
SCANNER_DIR = Path(__file__).resolve().parents[3] / "cyber-scanner"
sys.path.insert(0, str(SCANNER_DIR))


async def _get_plan_tier(db: AsyncSession, user_id: int) -> int:
    """Return the tier level of the user's active subscription (default 1 = Gratuit).

    Source de vérité unique : subscription_service.get_active_tier.
    """
    from app.services.subscription_service import get_active_tier

    return await get_active_tier(db, user_id)


def _run_scan_sync(
    url: str, tier: int, scan_id: int, hibp_key: str, allow_active: bool = True
) -> dict:
    """
    All blocking scanner calls, executed in a thread pool executor so the
    asyncio event loop stays free to serve API requests during the scan.
    Returns a dict with keys: results, overall, pdf_path.

    allow_active : si False, on saute le scan de ports nmap (module INTRUSIF).
    Réservé aux domaines dont l'utilisateur a prouvé la propriété (anti-scan de
    tiers non consentants). Les autres modules (GET/DNS/TLS) restent passifs.
    """
    from urllib.parse import urlparse

    from scanner.cms_detector import detect_cms
    from scanner.cookie_checker import check_cookies
    from scanner.cors_checker import check_cors
    from scanner.dns_scanner import scan_subdomains
    from scanner.email_checker import check_email_security
    from scanner.headers_checker import check_headers
    from scanner.ip_reputation import check_ip_reputation
    from scanner.port_scanner import scan_ports
    from scanner.report_generator import generate_report
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
    # Scan de ports nmap = INTRUSIF : uniquement si le domaine est vérifié.
    port_result = scan_ports(hostname) if allow_active else {}

    breach_result: dict = {}
    if hibp_key:
        from scanner.breach_checker import check_breach

        breach_result = check_breach(hostname, api_key=hibp_key, mode="domain")

    tech_result = tls_result = takeover_result = ti_result = methods_result = {}
    if tier >= 3:
        from scanner.http_methods import check_http_methods
        from scanner.subdomain_takeover import check_subdomain_takeover
        from scanner.tech_fingerprint import fingerprint_tech
        from scanner.threat_intel import get_threat_intel
        from scanner.tls_auditor import audit_tls

        tech_result = fingerprint_tech(url)
        tls_result = audit_tls(hostname)
        found_subs = [s["subdomain"] for s in dns_result.get("found", [])]
        takeover_result = check_subdomain_takeover(found_subs)
        ti_result = get_threat_intel(hostname)
        methods_result = check_http_methods(url)

    redirect_result = clickjacking_result = dirlist_result = robots_result = jwt_result = {}
    if tier >= 4:
        from scanner.clickjacking import check_clickjacking
        from scanner.directory_listing import check_directory_listing
        from scanner.jwt_checker import check_jwt
        from scanner.open_redirect import check_open_redirect
        from scanner.robots_sitemap import analyse_robots_sitemap

        redirect_result = check_open_redirect(url)
        clickjacking_result = check_clickjacking(url)
        dirlist_result = check_directory_listing(url)
        robots_result = analyse_robots_sitemap(url)
        jwt_result = check_jwt(url)

    pdf_dir = SCANNER_DIR / "reports" / "clients"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = str(pdf_dir / f"scan_{scan_id}.pdf")

    generate_report(
        target_url=url,
        ssl_result=ssl_result,
        headers_result=headers_result,
        port_result=port_result,
        ports_skipped=not allow_active,
        sca_result={},
        sca_skipped=True,
        email_result=email_result,
        email_skipped=False,
        cookie_result=cookie_result,
        cookie_skipped=False,
        cors_result=cors_result,
        cors_skipped=False,
        ip_result=ip_result,
        ip_skipped=False,
        dns_result=dns_result,
        dns_skipped=False,
        cms_result=cms_result,
        cms_skipped=False,
        waf_result=waf_result,
        waf_skipped=False,
        tech_result=tech_result,
        tech_skipped=(tier < 3),
        tls_result=tls_result,
        tls_skipped=(tier < 3),
        takeover_result=takeover_result,
        takeover_skipped=(tier < 3),
        ti_result=ti_result,
        ti_skipped=(tier < 3),
        methods_result=methods_result,
        methods_skipped=(tier < 3),
        redirect_result=redirect_result,
        redirect_skipped=(tier < 4),
        clickjacking_result=clickjacking_result,
        clickjacking_skipped=(tier < 4),
        dirlist_result=dirlist_result,
        dirlist_skipped=(tier < 4),
        robots_result=robots_result,
        robots_skipped=(tier < 4),
        jwt_result=jwt_result,
        jwt_skipped=(tier < 4),
        output_path=pdf_path,
    )

    # Source unique des résultats par module : le dict `results` ET le calcul du
    # statut global en dérivent, évitant toute divergence (un module présent dans
    # `results` mais oublié dans l'agrégation faussait silencieusement le verdict).
    module_results: dict[str, dict] = {
        "ssl": ssl_result,
        "headers": headers_result,
        "email": email_result,
        "cookies": cookie_result,
        "cors": cors_result,
        "ip": ip_result,
        "dns": dns_result,
        "cms": cms_result,
        "waf": waf_result,
        "ports": port_result,
        "breach": breach_result,
        "tech": tech_result,
        "tls": tls_result,
        "takeover": takeover_result,
        "threat_intel": ti_result,
        "http_methods": methods_result,
        "open_redirect": redirect_result,
        "clickjacking": clickjacking_result,
        "directory_listing": dirlist_result,
        "robots": robots_result,
        "jwt": jwt_result,
    }

    # Modules contribuant au verdict global. `takeover` et `robots` en sont
    # volontairement exclus ; `breach` a sa propre garde d'erreur (ci-dessous).
    # Les modules non joués pour le tier sont un dict vide -> .get("status") =
    # None, sans effet sur le verdict.
    status_keys = {
        "ssl",
        "headers",
        "email",
        "cookies",
        "cors",
        "ip",
        "dns",
        "cms",
        "waf",
        "ports",
        "tech",
        "tls",
        "threat_intel",
        "http_methods",
        "open_redirect",
        "clickjacking",
        "directory_listing",
        "jwt",
    }
    all_statuses = [r.get("status") for k, r in module_results.items() if k in status_keys]
    if breach_result and not breach_result.get("error"):
        all_statuses.append(breach_result.get("status"))

    if "CRITICAL" in all_statuses:
        overall = "CRITICAL"
    elif "WARNING" in all_statuses:
        overall = "WARNING"
    else:
        overall = "OK"

    remediation_dir = str(pdf_dir / f"remediation_{scan_id}")
    try:
        from scanner.remediation import generate_remediation

        remediation_paths = generate_remediation(
            target_url=url,
            port_result=port_result,
            headers_result=headers_result,
            sca_result=None,
            ssl_result=ssl_result,
            cors_result=cors_result,
            cookie_result=cookie_result,
            http_methods_result=methods_result,
            clickjacking_result=clickjacking_result,
            directory_listing_result=dirlist_result,
            open_redirect_result=redirect_result,
            robots_result=robots_result,
            email_result=email_result,
            waf_result=waf_result,
            output_dir=remediation_dir,
        )
    except Exception as exc:
        logger.warning(f"Remediation generation failed: {exc}")
        remediation_paths = {}

    results = {
        **module_results,
        "_meta": {
            "tier": tier,
            "url": url,
            "remediation_scripts": remediation_paths,
        },
    }

    return {"results": results, "overall": overall, "pdf_path": pdf_path}


async def _active_scan_allowed(user_id: int, url: str, db: AsyncSession) -> bool:
    """True si l'utilisateur a prouvé la propriété du domaine (scan nmap autorisé).
    Couvre l'hôte exact et l'apex sans préfixe 'www.' (vérifier l'apex vaut pour www)."""
    from urllib.parse import urlparse

    from app.services import phishing_service

    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    candidates = {host}
    if host.startswith("www."):
        candidates.add(host[4:])
    for domain in candidates:
        if await phishing_service.is_domain_verified(user_id, domain, db):
            return True
    return False


async def run_scan(scan_id: int, db: AsyncSession) -> None:
    """
    Execute a full scan for the given scan_id.
    Updates scan.status, scan.pdf_path, scan.results_json, scan.overall_status.
    """
    # Fetch scan + site
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan: Scan | None = result.scalar_one_or_none()
    if not scan:
        return

    site_result = await db.execute(select(Site).where(Site.id == scan.site_id))
    site: Site | None = site_result.scalar_one_or_none()
    if not site:
        scan.status = "failed"
        scan.error_message = "Site not found"
        await db.commit()
        return

    scan.status = "running"
    scan.started_at = datetime.now(UTC)
    await db.commit()

    tier = await _get_plan_tier(db, site.user_id)

    url = site.url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    from app.core.config import settings

    hibp_key = settings.HIBP_API_KEY

    # Scan de ports nmap (intrusif) uniquement si l'utilisateur a prouvé la
    # propriété du domaine (niveau 2 : passif libre / intrusif vérifié).
    allow_active = await _active_scan_allowed(site.user_id, url, db)

    try:
        # Run all blocking scanner calls in a thread pool so the asyncio event
        # loop stays free to serve other API requests during the scan.
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, _run_scan_sync, url, tier, scan_id, hibp_key, allow_active
        )

        scan.status = "done"
        scan.overall_status = result["overall"]
        scan.pdf_path = result["pdf_path"]
        scan.results_json = json.dumps(result["results"], default=str)
        scan.finished_at = datetime.now(UTC)
        await db.commit()

        # Email alert on CRITICAL (manual scans)
        if result["overall"] == "CRITICAL" and result["pdf_path"]:
            try:
                from app.models.user import User
                from app.services.email_service import send_scan_report

                user_result = await db.execute(select(User).where(User.id == site.user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    send_scan_report(
                        to_email=user.email,
                        site_url=site.url,
                        overall_status="CRITICAL",
                        pdf_path=result["pdf_path"],
                    )
            except Exception as exc:
                logger.warning(f"Scan report email failed: {exc}")

    except Exception as exc:
        # Ne pas avaler l'echec en silence : trace complete -> CloudWatch + Sentry.
        logger.exception(f"Scan {scan.id} failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:500]
        scan.finished_at = datetime.now(UTC)
        await db.commit()
