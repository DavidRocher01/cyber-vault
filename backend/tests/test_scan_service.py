"""
Unit tests — scan_service internals.
Les modules scanner externes (SSL, headers, etc.) sont mockés pour éviter
des appels réseau réels et des dépendances système.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan_service import _get_plan_tier, run_scan


# ── Helpers ────────────────────────────────────────────────────────────────────

def _mock_db(scalars_results: list) -> AsyncMock:
    """Return a minimal AsyncSession mock that yields items from scalars_results in order."""
    db = AsyncMock(spec=AsyncSession)
    execute_results = []
    for item in scalars_results:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = item
        result_mock.scalars.return_value.all.return_value = [item] if item else []
        execute_results.append(result_mock)
    db.execute = AsyncMock(side_effect=execute_results)
    return db


# ── _get_plan_tier ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_plan_tier_returns_plan_tier_level():
    plan_mock = MagicMock()
    plan_mock.tier_level = 3
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = plan_mock
    db.execute = AsyncMock(return_value=result_mock)

    tier = await _get_plan_tier(db, user_id=1)
    assert tier == 3


@pytest.mark.asyncio
async def test_get_plan_tier_defaults_to_2_when_no_subscription():
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    tier = await _get_plan_tier(db, user_id=99)
    assert tier == 2


# ── run_scan ───────────────────────────────────────────────────────────────────

def _scanner_ok(status: str = "OK") -> dict:
    return {"status": status}


SCANNER_MOCKS = {
    "scanner.ssl_checker.check_ssl": MagicMock(return_value=_scanner_ok()),
    "scanner.headers_checker.check_headers": MagicMock(return_value=_scanner_ok()),
    "scanner.email_checker.check_email_security": MagicMock(return_value=_scanner_ok()),
    "scanner.cookie_checker.check_cookies": MagicMock(return_value=_scanner_ok()),
    "scanner.cors_checker.check_cors": MagicMock(return_value=_scanner_ok()),
    "scanner.ip_reputation.check_ip_reputation": MagicMock(return_value=_scanner_ok()),
    "scanner.dns_scanner.scan_subdomains": MagicMock(return_value={"status": "OK", "found": []}),
    "scanner.cms_detector.detect_cms": MagicMock(return_value=_scanner_ok()),
    "scanner.waf_detector.detect_waf": MagicMock(return_value=_scanner_ok()),
    "scanner.port_scanner.scan_ports": MagicMock(return_value=_scanner_ok()),
    "scanner.report_generator.generate_report": MagicMock(),
    "scanner.remediation.generate_remediation": MagicMock(return_value={}),
}


@pytest.mark.asyncio
async def test_run_scan_missing_scan_returns_early():
    """Si le scan_id n'existe pas en DB, run_scan doit sortir sans erreur."""
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    await run_scan(scan_id=9999, db=db)
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_scan_missing_site_marks_scan_failed():
    """Si le site n'existe plus, le scan doit passer en 'failed'."""
    from app.models.scan import Scan

    scan = MagicMock(spec=Scan)
    scan.id = 1
    scan.site_id = 10
    scan.status = "pending"

    db = AsyncMock(spec=AsyncSession)
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = scan   # scan found
    results[1].scalar_one_or_none.return_value = None   # site not found
    db.execute = AsyncMock(side_effect=results)

    await run_scan(scan_id=1, db=db)

    assert scan.status == "failed"
    assert "not found" in (scan.error_message or "").lower()
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_run_scan_sets_started_at_on_site_found():
    """Quand scan et site existent, started_at est défini (scan passe en 'running' avant de crash sur les scanners)."""
    from app.models.scan import Scan
    from app.models.site import Site
    import sys

    scan = MagicMock(spec=Scan)
    scan.id = 2
    scan.site_id = 5
    scan.status = "pending"
    scan.started_at = None
    scan.finished_at = None
    scan.error_message = None

    site = MagicMock(spec=Site)
    site.id = 5
    site.url = "https://example.com"
    site.user_id = 1

    plan_mock = MagicMock()
    plan_mock.tier_level = 2

    db = AsyncMock(spec=AsyncSession)
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=scan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=site)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan_mock)),
    ]
    db.execute = AsyncMock(side_effect=results)

    # Make ssl_checker crash immediately → scan will fail, but started_at must have been set
    crashing_ssl = MagicMock()
    crashing_ssl.check_ssl = MagicMock(side_effect=RuntimeError("crash"))
    original = sys.modules.get("scanner.ssl_checker")
    sys.modules["scanner.ssl_checker"] = crashing_ssl

    try:
        await run_scan(scan_id=2, db=db)
    finally:
        if original is None:
            sys.modules.pop("scanner.ssl_checker", None)
        else:
            sys.modules["scanner.ssl_checker"] = original

    # started_at was set before entering the scanner block
    assert scan.started_at is not None
    assert scan.status == "failed"


@pytest.mark.asyncio
async def test_run_scan_exception_marks_scan_failed():
    """Si un scanner lève une exception, le scan passe en 'failed'."""
    from app.models.scan import Scan
    from app.models.site import Site
    import sys

    scan = MagicMock(spec=Scan)
    scan.id = 3
    scan.site_id = 6
    scan.status = "pending"
    scan.started_at = None
    scan.finished_at = None
    scan.error_message = None

    site = MagicMock(spec=Site)
    site.id = 6
    site.url = "https://crash.com"
    site.user_id = 1

    plan_mock = MagicMock()
    plan_mock.tier_level = 2

    db = AsyncMock(spec=AsyncSession)
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=scan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=site)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan_mock)),
    ]
    db.execute = AsyncMock(side_effect=results)

    # Patch ssl_checker to raise an exception
    crashing_ssl = MagicMock()
    crashing_ssl.check_ssl = MagicMock(side_effect=RuntimeError("SSL check failed"))

    original = sys.modules.get("scanner.ssl_checker")
    sys.modules["scanner.ssl_checker"] = crashing_ssl

    try:
        await run_scan(scan_id=3, db=db)
    finally:
        if original is None:
            sys.modules.pop("scanner.ssl_checker", None)
        else:
            sys.modules["scanner.ssl_checker"] = original

    assert scan.status == "failed"
    assert scan.error_message is not None
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_run_scan_overall_status_critical_when_any_critical():
    """overall_status doit être CRITICAL si au moins un module est CRITICAL."""
    from app.models.scan import Scan
    from app.models.site import Site
    import sys

    scan = MagicMock(spec=Scan)
    scan.id = 4
    scan.site_id = 7
    scan.status = "pending"
    scan.started_at = None
    scan.finished_at = None
    scan.pdf_path = None
    scan.results_json = None
    scan.overall_status = None

    site = MagicMock(spec=Site)
    site.id = 7
    site.url = "https://critical.com"
    site.user_id = 1

    plan_mock = MagicMock()
    plan_mock.tier_level = 2

    db = AsyncMock(spec=AsyncSession)
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=scan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=site)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan_mock)),
    ]
    db.execute = AsyncMock(side_effect=results)

    # One scanner returns CRITICAL
    def _make_module(fn_name, return_val):
        m = MagicMock()
        setattr(m, fn_name, MagicMock(return_value=return_val))
        return m

    scanner_setup = [
        ("scanner.ssl_checker", "check_ssl", {"status": "CRITICAL"}),
        ("scanner.headers_checker", "check_headers", _scanner_ok()),
        ("scanner.email_checker", "check_email_security", _scanner_ok()),
        ("scanner.cookie_checker", "check_cookies", _scanner_ok()),
        ("scanner.cors_checker", "check_cors", _scanner_ok()),
        ("scanner.ip_reputation", "check_ip_reputation", _scanner_ok()),
        ("scanner.dns_scanner", "scan_subdomains", {"status": "OK", "found": []}),
        ("scanner.cms_detector", "detect_cms", _scanner_ok()),
        ("scanner.waf_detector", "detect_waf", _scanner_ok()),
        ("scanner.port_scanner", "scan_ports", _scanner_ok()),
        ("scanner.report_generator", "generate_report", None),
        ("scanner.remediation", "generate_remediation", {}),
    ]

    originals = {}
    for mod_path, fn_name, retval in scanner_setup:
        originals[mod_path] = sys.modules.get(mod_path)
        m = MagicMock()
        setattr(m, fn_name, MagicMock(return_value=retval))
        sys.modules[mod_path] = m

    try:
        await run_scan(scan_id=4, db=db)
    finally:
        for mod_path, original in originals.items():
            if original is None:
                sys.modules.pop(mod_path, None)
            else:
                sys.modules[mod_path] = original

    assert scan.overall_status == "CRITICAL"


@pytest.mark.asyncio
async def test_run_scan_overall_status_ok_when_all_ok():
    """overall_status doit être OK si tous les modules sont OK."""
    from app.models.scan import Scan
    from app.models.site import Site
    import sys

    scan = MagicMock(spec=Scan)
    scan.id = 5
    scan.site_id = 8
    scan.status = "pending"
    scan.started_at = None
    scan.finished_at = None
    scan.pdf_path = None
    scan.results_json = None
    scan.overall_status = None

    site = MagicMock(spec=Site)
    site.id = 8
    site.url = "https://allok.com"
    site.user_id = 1

    plan_mock = MagicMock()
    plan_mock.tier_level = 2

    db = AsyncMock(spec=AsyncSession)
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=scan)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=site)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=plan_mock)),
    ]
    db.execute = AsyncMock(side_effect=results)

    scanner_setup = [
        ("scanner.ssl_checker", "check_ssl"),
        ("scanner.headers_checker", "check_headers"),
        ("scanner.email_checker", "check_email_security"),
        ("scanner.cookie_checker", "check_cookies"),
        ("scanner.cors_checker", "check_cors"),
        ("scanner.ip_reputation", "check_ip_reputation"),
        ("scanner.dns_scanner", "scan_subdomains"),
        ("scanner.cms_detector", "detect_cms"),
        ("scanner.waf_detector", "detect_waf"),
        ("scanner.port_scanner", "scan_ports"),
        ("scanner.report_generator", "generate_report"),
        ("scanner.remediation", "generate_remediation"),
    ]

    originals = {}
    for mod_path, fn_name in scanner_setup:
        originals[mod_path] = sys.modules.get(mod_path)
        m = MagicMock()
        rv = {"status": "OK", "found": []} if fn_name == "scan_subdomains" else (
            {} if fn_name == "generate_remediation" else (None if fn_name == "generate_report" else _scanner_ok())
        )
        setattr(m, fn_name, MagicMock(return_value=rv))
        sys.modules[mod_path] = m

    try:
        await run_scan(scan_id=5, db=db)
    finally:
        for mod_path, original in originals.items():
            if original is None:
                sys.modules.pop(mod_path, None)
            else:
                sys.modules[mod_path] = original

    assert scan.overall_status == "OK"
