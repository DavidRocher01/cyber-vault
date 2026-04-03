"""
Scan service — runs the cyber-scanner against a site URL,
saves the PDF, and updates the Scan record in DB.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription
from app.models.plan import Plan

# Resolve cyber-scanner path (sibling of backend/)
SCANNER_DIR = Path(__file__).resolve().parents[3] / "cyber-scanner"
sys.path.insert(0, str(SCANNER_DIR))


async def _get_plan_tier(db: AsyncSession, user_id: int) -> int:
    """Return the tier level of the user's active subscription (default 2)."""
    result = await db.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    plan = result.scalar_one_or_none()
    return plan.tier_level if plan else 2


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
    scan.started_at = datetime.utcnow()
    await db.commit()

    tier = await _get_plan_tier(db, site.user_id)

    try:
        from scanner.ssl_checker import check_ssl
        from scanner.headers_checker import check_headers
        from scanner.email_checker import check_email_security
        from scanner.cookie_checker import check_cookies
        from scanner.cors_checker import check_cors
        from scanner.ip_reputation import check_ip_reputation
        from scanner.dns_scanner import scan_subdomains
        from scanner.cms_detector import detect_cms
        from scanner.waf_detector import detect_waf
        from scanner.report_generator import generate_report

        url = site.url
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or url

        ssl_result      = check_ssl(hostname)
        headers_result  = check_headers(url)
        email_result    = check_email_security(hostname)
        cookie_result   = check_cookies(url)
        cors_result     = check_cors(url)
        ip_result       = check_ip_reputation(hostname)
        dns_result      = scan_subdomains(hostname)
        cms_result      = detect_cms(url)
        waf_result      = detect_waf(url)

        # Tier 3+ modules
        tech_result = tls_result = takeover_result = ti_result = methods_result = {}
        if tier >= 3:
            from scanner.tech_fingerprint import fingerprint_tech
            from scanner.tls_auditor import audit_tls
            from scanner.subdomain_takeover import check_subdomain_takeover
            from scanner.threat_intel import get_threat_intel
            from scanner.http_methods import check_http_methods
            tech_result     = fingerprint_tech(url)
            tls_result      = audit_tls(hostname)
            found_subs      = [s["subdomain"] for s in dns_result.get("found", [])]
            takeover_result = check_subdomain_takeover(found_subs)
            ti_result       = get_threat_intel(hostname)
            methods_result  = check_http_methods(url)

        # Tier 4 modules
        redirect_result = clickjacking_result = dirlist_result = robots_result = jwt_result = {}
        if tier >= 4:
            from scanner.open_redirect import check_open_redirect
            from scanner.clickjacking import check_clickjacking
            from scanner.directory_listing import check_directory_listing
            from scanner.robots_sitemap import analyse_robots_sitemap
            from scanner.jwt_checker import check_jwt
            redirect_result     = check_open_redirect(url)
            clickjacking_result = check_clickjacking(url)
            dirlist_result      = check_directory_listing(url)
            robots_result       = analyse_robots_sitemap(url)
            jwt_result          = check_jwt(url)

        # PDF output path
        pdf_dir = SCANNER_DIR / "reports" / "clients"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = str(pdf_dir / f"scan_{scan_id}.pdf")

        generate_report(
            target_url=url,
            ssl_result=ssl_result,
            headers_result=headers_result,
            port_result={}, ports_skipped=True,
            sca_result={},  sca_skipped=True,
            email_result=email_result,    email_skipped=False,
            cookie_result=cookie_result,  cookie_skipped=False,
            cors_result=cors_result,      cors_skipped=False,
            ip_result=ip_result,          ip_skipped=False,
            dns_result=dns_result,        dns_skipped=False,
            cms_result=cms_result,        cms_skipped=False,
            waf_result=waf_result,        waf_skipped=False,
            tech_result=tech_result,      tech_skipped=(tier < 3),
            tls_result=tls_result,        tls_skipped=(tier < 3),
            takeover_result=takeover_result, takeover_skipped=(tier < 3),
            ti_result=ti_result,          ti_skipped=(tier < 3),
            methods_result=methods_result, methods_skipped=(tier < 3),
            redirect_result=redirect_result,       redirect_skipped=(tier < 4),
            clickjacking_result=clickjacking_result, clickjacking_skipped=(tier < 4),
            dirlist_result=dirlist_result,         dirlist_skipped=(tier < 4),
            robots_result=robots_result,           robots_skipped=(tier < 4),
            jwt_result=jwt_result,                 jwt_skipped=(tier < 4),
            output_path=pdf_path,
        )

        # Collect statuses for overall
        all_statuses = [
            ssl_result.get("status"), headers_result.get("status"),
            email_result.get("status"), cookie_result.get("status"),
            cors_result.get("status"), ip_result.get("status"),
            dns_result.get("status"), cms_result.get("status"), waf_result.get("status"),
        ]
        if tier >= 3:
            all_statuses += [tech_result.get("status"), tls_result.get("status"), ti_result.get("status"), methods_result.get("status")]
        if tier >= 4:
            all_statuses += [redirect_result.get("status"), clickjacking_result.get("status"), dirlist_result.get("status"), jwt_result.get("status")]

        if "CRITICAL" in all_statuses:
            overall = "CRITICAL"
        elif "WARNING" in all_statuses:
            overall = "WARNING"
        else:
            overall = "OK"

        scan.status         = "done"
        scan.overall_status = overall
        scan.pdf_path       = pdf_path
        scan.results_json   = json.dumps({"ssl": ssl_result, "headers": headers_result})
        scan.finished_at    = datetime.utcnow()
        await db.commit()

        # Email alert on CRITICAL (manual scans)
        if overall == "CRITICAL" and pdf_path:
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
                        pdf_path=pdf_path,
                    )
            except Exception:
                pass  # Ne pas bloquer si l'email échoue

    except Exception as exc:
        scan.status        = "failed"
        scan.error_message = str(exc)[:500]
        scan.finished_at   = datetime.utcnow()
        await db.commit()
