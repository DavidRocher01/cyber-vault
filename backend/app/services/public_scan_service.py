"""
Public scan service — runs a fast subset of scanner modules (no auth required).

Modules run: SSL, headers, email, cookies, CORS, IP reputation, DNS, CMS, WAF.
Skipped: ports (slow), breach (API key), tech/TLS/takeover/threat_intel (tier 3+).
No PDF or remediation scripts generated.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.public_scan import PublicScan

SCANNER_DIR = Path(__file__).resolve().parents[3] / "cyber-scanner"
sys.path.insert(0, str(SCANNER_DIR))


def _run_demo_scan_sync(url: str) -> dict:
    from urllib.parse import urlparse
    from scanner.ssl_checker import check_ssl
    from scanner.headers_checker import check_headers
    from scanner.email_checker import check_email_security
    from scanner.cookie_checker import check_cookies
    from scanner.cors_checker import check_cors
    from scanner.ip_reputation import check_ip_reputation
    from scanner.dns_scanner import scan_subdomains
    from scanner.cms_detector import detect_cms
    from scanner.waf_detector import detect_waf

    hostname = urlparse(url).hostname or url

    ssl_result     = check_ssl(hostname)
    headers_result = check_headers(url)
    email_result   = check_email_security(hostname)
    cookie_result  = check_cookies(url)
    cors_result    = check_cors(url)
    ip_result      = check_ip_reputation(hostname)
    dns_result     = scan_subdomains(hostname)
    cms_result     = detect_cms(url)
    waf_result     = detect_waf(url)

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
        "ssl":     ssl_result,
        "headers": headers_result,
        "email":   email_result,
        "cookies": cookie_result,
        "cors":    cors_result,
        "ip":      ip_result,
        "dns":     dns_result,
        "cms":     cms_result,
        "waf":     waf_result,
        "_meta": {"tier": 2, "url": url},
    }

    return {"results": results, "overall": overall}


async def run_public_scan(public_scan_id: int, db: AsyncSession) -> None:
    result = await db.execute(select(PublicScan).where(PublicScan.id == public_scan_id))
    scan: PublicScan | None = result.scalar_one_or_none()
    if not scan:
        return

    scan.status = "running"
    scan.started_at = datetime.now(timezone.utc)
    await db.commit()

    url = scan.target_url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        loop = asyncio.get_running_loop()
        outcome = await loop.run_in_executor(None, _run_demo_scan_sync, url)
        scan.status = "done"
        scan.overall_status = outcome["overall"]
        scan.results_json = json.dumps(outcome["results"], default=str)
        scan.finished_at = datetime.now(timezone.utc)
    except Exception as exc:
        logger.error(f"Public scan {public_scan_id} failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:512]
        scan.finished_at = datetime.now(timezone.utc)

    await db.commit()
