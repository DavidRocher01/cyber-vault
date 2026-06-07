"""
Unit tests for app.api.v1.endpoints.scans — direct function calls.

These bypass the HTTP layer entirely so coverage.py properly tracks
all lines inside the async endpoint functions.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.v1.endpoints.scans import (
    download_pdf,
    download_remediation_script,
    export_scans_csv,
    get_scan,
    list_scans,
    trigger_scan,
)
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User

# ─── helpers ──────────────────────────────────────────────────────────────────


def _mock_user(user_id: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    return u


def _mock_site(site_id: int = 1, url: str = "https://example.com") -> MagicMock:
    s = MagicMock(spec=Site)
    s.id = site_id
    s.url = url
    s.is_active = True
    return s


def _mock_scan(scan_id: int = 1, site_id: int = 1, status: str = "done") -> MagicMock:
    s = MagicMock(spec=Scan)
    s.id = scan_id
    s.site_id = site_id
    s.status = status
    s.overall_status = "safe"
    s.pdf_path = "/tmp/report.pdf"
    s.results_json = json.dumps({"_meta": {"url": "https://example.com"}, "ports": {}})
    s.created_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    s.started_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    s.finished_at = datetime(2024, 1, 1, 12, 5, tzinfo=UTC)
    return s


def _scalar_result(val):
    """Return a MagicMock execute result with scalar_one_or_none = val."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    r.scalar_one.return_value = val
    r.scalar.return_value = val if isinstance(val, int) else 0
    r.scalars.return_value.all.return_value = val if isinstance(val, list) else []
    return r


def _make_db(*results):
    """Return an AsyncMock db that returns successive scalar_one_or_none results."""
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        if n < len(results):
            val = results[n]
        else:
            val = None
        r.scalar_one_or_none.return_value = val
        r.scalar_one.return_value = val if isinstance(val, int) else 0
        r.scalars.return_value.all.return_value = val if isinstance(val, list) else []
        call_count["n"] += 1
        return r

    db.execute = execute
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ─── trigger_scan ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_scan_unknown_site_raises_404():
    db = _make_db(None)  # site query returns None
    user = _mock_user()
    bg = MagicMock(spec=BackgroundTasks)

    with pytest.raises(HTTPException) as exc:
        await trigger_scan(site_id=99, background_tasks=bg, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_trigger_scan_success_returns_scan_id():
    site = _mock_site()

    db = _make_db(site)
    db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", 42))

    user = _mock_user()
    bg = MagicMock(spec=BackgroundTasks)

    # get_active_plan returns None (no subscription) → interval=30, max_scans=1
    # scalar() for count of recent scans returns 0 → scan allowed
    with (
        patch(
            "app.api.v1.endpoints.scans.get_active_plan",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("app.api.v1.endpoints.scans.assert_no_ssrf"),
    ):
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(site),  # site query
                MagicMock(),  # verrou FOR UPDATE (resultat non utilise)
                count_result,  # recent scans count
            ]
        )
        result = await trigger_scan(site_id=1, background_tasks=bg, current_user=user, db=db)

    assert "scan_id" in result or hasattr(result, "scan_id")
    bg.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_scan_recent_scan_raises_429():
    site = _mock_site()
    user = _mock_user()
    bg = MagicMock(spec=BackgroundTasks)

    # Plan with interval=30, max_sites=1. Count of recent scans = 1 → 429.
    mock_plan = MagicMock()
    mock_plan.scan_interval_days = 30
    mock_plan.max_sites = 1
    mock_plan.price_eur = 10

    count_result = MagicMock()
    count_result.scalar.return_value = 1  # >= max_sites → blocked

    with (
        patch(
            "app.api.v1.endpoints.scans.get_active_plan",
            new_callable=AsyncMock,
            return_value=mock_plan,
        ),
        patch("app.api.v1.endpoints.scans.assert_no_ssrf"),
    ):
        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(site),
                MagicMock(),  # verrou FOR UPDATE (resultat non utilise)
                count_result,
            ]
        )
        with pytest.raises(HTTPException) as exc:
            await trigger_scan(site_id=1, background_tasks=bg, current_user=user, db=db)

    assert exc.value.status_code == 429
    assert "Limite de scans atteinte" in exc.value.detail


@pytest.mark.asyncio
async def test_trigger_scan_free_plan_blocks_after_one_scan():
    """Free plan (price_eur=0) allows only 1 scan total ever."""
    site = _mock_site()
    user = _mock_user()
    bg = MagicMock(spec=BackgroundTasks)

    mock_plan = MagicMock()
    mock_plan.scan_interval_days = 30
    mock_plan.max_sites = 1
    mock_plan.price_eur = 0  # free plan

    count_result = MagicMock()
    count_result.scalar.return_value = 1  # already has 1 scan

    with (
        patch(
            "app.api.v1.endpoints.scans.get_active_plan",
            new_callable=AsyncMock,
            return_value=mock_plan,
        ),
        patch("app.api.v1.endpoints.scans.assert_no_ssrf"),
    ):
        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(site),
                MagicMock(),  # verrou FOR UPDATE (resultat non utilise)
                count_result,
            ]
        )
        with pytest.raises(HTTPException) as exc:
            await trigger_scan(site_id=1, background_tasks=bg, current_user=user, db=db)

    assert exc.value.status_code == 403


# ─── list_scans ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_scans_unknown_site_raises_404():
    db = _make_db(None)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await list_scans(site_id=99, page=1, per_page=10, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_scans_empty():
    site = _mock_site()
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:  # site query
            r.scalar_one_or_none.return_value = site
        elif n == 1:  # count query
            r.scalar_one.return_value = 0
        else:  # items query
            r.scalars.return_value.all.return_value = []
        return r

    db.execute = execute
    user = _mock_user()

    result = await list_scans(site_id=1, page=1, per_page=10, current_user=user, db=db)
    assert result["total"] == 0
    assert result["items"] == []
    assert result["page"] == 1


@pytest.mark.asyncio
async def test_list_scans_pagination():
    site = _mock_site()
    scan = _mock_scan()
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = site
        elif n == 1:
            r.scalar_one.return_value = 5  # total = 5
        else:
            r.scalars.return_value.all.return_value = [scan]
        return r

    db.execute = execute
    user = _mock_user()

    result = await list_scans(site_id=1, page=2, per_page=2, current_user=user, db=db)
    assert result["total"] == 5
    assert result["page"] == 2
    assert result["per_page"] == 2
    assert result["pages"] == 3  # ceil(5/2)


# ─── export_scans_csv ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_csv_unknown_site_raises_404():
    db = _make_db(None)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await export_scans_csv(site_id=99, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_export_csv_success():
    site = _mock_site()
    scan = _mock_scan()
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = site
        else:
            r.scalars.return_value.all.return_value = [scan]
        return r

    db.execute = execute
    user = _mock_user()

    response = await export_scans_csv(site_id=1, current_user=user, db=db)
    # StreamingResponse
    assert response.media_type == "text/csv"
    assert "cyberscan_site_1.csv" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_csv_no_duration_when_missing_timestamps():
    site = _mock_site()
    scan = _mock_scan()
    scan.started_at = None  # no duration
    scan.finished_at = None
    scan.created_at = None
    scan.overall_status = None

    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = site
        else:
            r.scalars.return_value.all.return_value = [scan]
        return r

    db.execute = execute
    user = _mock_user()

    response = await export_scans_csv(site_id=1, current_user=user, db=db)
    assert response.media_type == "text/csv"


# ─── get_scan ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_scan_returns_scan():
    scan = _mock_scan(scan_id=5)
    db = _make_db(scan)
    user = _mock_user()

    result = await get_scan(scan_id=5, current_user=user, db=db)
    assert result.id == 5


@pytest.mark.asyncio
async def test_get_scan_not_found_raises_404():
    db = _make_db(None)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await get_scan(scan_id=999, current_user=user, db=db)
    assert exc.value.status_code == 404


# ─── download_pdf ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_download_pdf_scan_not_found_raises_404():
    db = _make_db(None)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await download_pdf(scan_id=1, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_download_pdf_not_done_raises_404():
    scan = _mock_scan()
    scan.status = "running"
    db = _make_db(scan)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await download_pdf(scan_id=1, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_download_pdf_no_path_raises_404():
    scan = _mock_scan()
    scan.status = "done"
    scan.pdf_path = None
    db = _make_db(scan)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await download_pdf(scan_id=1, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_download_pdf_success_returns_file_response():
    import os
    import tempfile

    scan = _mock_scan()
    scan.status = "done"

    # Create a real temp file for FileResponse
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-test")
        tmp_path = f.name

    scan.pdf_path = tmp_path
    db = _make_db(scan)
    user = _mock_user()

    try:
        from fastapi.responses import FileResponse

        response = await download_pdf(scan_id=1, current_user=user, db=db)
        assert isinstance(response, FileResponse)
        assert response.media_type == "application/pdf"
    finally:
        os.unlink(tmp_path)


# ─── download_remediation_script ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remediation_unknown_key_raises_404():
    db = _make_db(None)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await download_remediation_script(
            scan_id=1, script_key="nonexistent", current_user=user, db=db
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_remediation_scan_not_found_raises_404():
    db = _make_db(None)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await download_remediation_script(scan_id=999, script_key="ufw", current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_remediation_scan_not_done_raises_404():
    scan = _mock_scan()
    scan.status = "running"
    scan.results_json = None
    db = _make_db(scan)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await download_remediation_script(scan_id=1, script_key="ufw", current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_remediation_file_served_when_exists():
    import os
    import tempfile

    scan = _mock_scan()
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as f:
        f.write(b"#!/bin/bash")
        script_path = f.name

    scan.results_json = json.dumps(
        {
            "_meta": {
                "remediation_scripts": {"ufw": script_path},
                "url": "https://example.com",
            },
            "ports": {},
        }
    )
    db = _make_db(scan)
    user = _mock_user()

    try:
        from fastapi.responses import FileResponse

        response = await download_remediation_script(
            scan_id=1, script_key="ufw", current_user=user, db=db
        )
        assert isinstance(response, FileResponse)
    finally:
        os.unlink(script_path)


@pytest.mark.asyncio
async def test_remediation_import_error_raises_404():
    """When /cyber-scanner module not available and no cached script file."""
    scan = _mock_scan()
    scan.results_json = json.dumps(
        {
            "_meta": {"remediation_scripts": {}, "url": "https://example.com"},
            "ports": {},
        }
    )
    db = _make_db(scan)
    user = _mock_user()

    with patch("builtins.__import__", side_effect=ImportError("no cyber-scanner")):
        with pytest.raises(HTTPException) as exc:
            await download_remediation_script(scan_id=1, script_key="ufw", current_user=user, db=db)
    # Either ImportError caught → 404, or the normal import error path
    assert exc.value.status_code == 404


# ─── _REMEDIATION_META completeness ───────────────────────────────────────────


def test_remediation_meta_contains_all_expected_keys():
    """_REMEDIATION_META must cover every key generate_remediation can return."""
    from app.api.v1.endpoints.scans import _REMEDIATION_META

    expected_keys = {
        "ufw",
        "ssh",
        "robots",
        "nginx_waf",
        "fastapi",
        "upgrade",
        "nginx_ssl",
        "fastapi_cors",
        "nginx_cors",
        "fastapi_cookie",
        "nginx_methods",
        "nginx_clickjacking",
        "fastapi_clickjacking",
        "nginx_dirlist",
        "fastapi_open_redirect",
        "dns_email",
    }
    missing = expected_keys - set(_REMEDIATION_META.keys())
    assert not missing, f"Keys missing from _REMEDIATION_META: {missing}"


def test_remediation_meta_values_have_filename_and_mimetype():
    from app.api.v1.endpoints.scans import _REMEDIATION_META

    for key, (filename, mimetype) in _REMEDIATION_META.items():
        assert filename, f"Empty filename for key '{key}'"
        assert mimetype, f"Empty mimetype for key '{key}'"
        assert "/" in mimetype, f"Invalid mimetype '{mimetype}' for key '{key}'"


@pytest.mark.parametrize(
    "script_key",
    [
        "ufw",
        "ssh",
        "robots",
        "nginx_waf",
        "fastapi",
        "upgrade",
        "nginx_ssl",
        "fastapi_cors",
        "nginx_cors",
        "fastapi_cookie",
        "nginx_methods",
        "nginx_clickjacking",
        "fastapi_clickjacking",
        "nginx_dirlist",
        "fastapi_open_redirect",
        "dns_email",
    ],
)
@pytest.mark.asyncio
async def test_remediation_all_keys_not_rejected(script_key):
    """All valid script keys must pass the _REMEDIATION_META guard (not return 404 'Script inconnu')."""
    import os
    import tempfile

    scan = _mock_scan()
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as f:
        f.write(b"#!/bin/bash\necho ok")
        path = f.name
    scan.results_json = json.dumps(
        {
            "_meta": {
                "remediation_scripts": {script_key: path},
                "url": "https://example.com",
            },
        }
    )
    db = _make_db(scan)
    user = _mock_user()
    try:
        response = await download_remediation_script(
            scan_id=1, script_key=script_key, current_user=user, db=db
        )
        assert response is not None
    finally:
        os.unlink(path)


# ─── on-the-fly regeneration ──────────────────────────────────────────────────


def _scan_with_results(extra_results: dict | None = None) -> MagicMock:
    """Scan with full results_json but no on-disk remediation files."""
    base = {
        "_meta": {"remediation_scripts": {}, "url": "https://example.com"},
        "ssl": {"status": "CRITICAL", "tls_ok": False, "error": None},
        "headers": {
            "status": "CRITICAL",
            "headers_missing": ["Content-Security-Policy"],
            "error": None,
        },
        "email": {
            "status": "CRITICAL",
            "spf": False,
            "dkim": False,
            "dmarc": False,
            "domain": "example.com",
            "issues": [],
            "error": None,
        },
        "cookies": {
            "status": "WARNING",
            "issues": [{"name": "session", "missing_flags": ["HttpOnly"]}],
            "error": None,
        },
        "cors": {"status": "CRITICAL", "issues": ["Wildcard origin"], "error": None},
        "http_methods": {
            "status": "CRITICAL",
            "dangerous_methods": ["DELETE", "TRACE"],
            "error": None,
        },
        "clickjacking": {"status": "CRITICAL", "error": None},
        "directory_listing": {
            "status": "CRITICAL",
            "exposed_paths": ["/backup/"],
            "error": None,
        },
        "open_redirect": {"status": "CRITICAL", "error": None},
        "robots": {"status": "WARNING", "error": None},
        "waf": {"status": "WARNING", "error": None},
        "ports": {"status": "OK", "critical_ports": [], "error": None},
    }
    if extra_results:
        base.update(extra_results)
    scan = _mock_scan()
    scan.results_json = json.dumps(base)
    return scan


@pytest.mark.parametrize(
    "script_key",
    [
        "ufw",
        "ssh",
        "robots",
        "nginx_waf",
        "fastapi",
        "nginx_ssl",
        "fastapi_cors",
        "nginx_cors",
        "fastapi_cookie",
        "nginx_methods",
        "nginx_clickjacking",
        "fastapi_clickjacking",
        "nginx_dirlist",
        "fastapi_open_redirect",
        "dns_email",
    ],
)
@pytest.mark.asyncio
async def test_remediation_regenerated_on_the_fly(script_key):
    """When file is absent from disk, the script is regenerated from DB data and served."""
    import sys
    from pathlib import Path

    scanner_dir = str(Path(__file__).resolve().parents[2] / "cyber-scanner")
    if scanner_dir not in sys.path:
        sys.path.insert(0, scanner_dir)

    scan = _scan_with_results()
    db = _make_db(scan)
    user = _mock_user()

    from fastapi.responses import StreamingResponse

    response = await download_remediation_script(
        scan_id=1, script_key=script_key, current_user=user, db=db
    )
    assert response is not None
    assert isinstance(response, StreamingResponse)


@pytest.mark.asyncio
async def test_remediation_regeneration_unavailable_script_raises_404():
    """Script not generated (condition not met) → 404, not a 500."""
    import sys
    from pathlib import Path

    scanner_dir = str(Path(__file__).resolve().parents[2] / "cyber-scanner")
    if scanner_dir not in sys.path:
        sys.path.insert(0, scanner_dir)

    scan = _mock_scan()
    # All OK results → no conditional scripts generated
    scan.results_json = json.dumps(
        {
            "_meta": {"remediation_scripts": {}, "url": "https://example.com"},
            "ssl": {"status": "OK"},
            "headers": {"status": "OK", "headers_missing": []},
            "email": {"status": "OK"},
            "cookies": {"status": "OK", "issues": []},
            "cors": {"status": "OK"},
            "http_methods": {"status": "OK"},
            "clickjacking": {"status": "OK"},
            "directory_listing": {"status": "OK"},
            "open_redirect": {"status": "OK"},
            "waf": {"status": "OK"},
            "robots": {"status": "OK"},
            "ports": {"status": "OK", "critical_ports": []},
        }
    )
    db = _make_db(scan)
    user = _mock_user()

    # nginx_ssl requires ssl CRITICAL — should return 404 since ssl is OK
    with pytest.raises(HTTPException) as exc:
        await download_remediation_script(
            scan_id=1, script_key="nginx_ssl", current_user=user, db=db
        )
    assert exc.value.status_code == 404


# ─── scan_service passes all parameters ───────────────────────────────────────


def test_scan_service_passes_all_remediation_params():
    """generate_remediation must be called with all scan result parameters."""
    import ast
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "app" / "services" / "scan_service.py").read_text()
    tree = ast.parse(src)

    required_params = {
        "ssl_result",
        "cors_result",
        "cookie_result",
        "http_methods_result",
        "clickjacking_result",
        "directory_listing_result",
        "open_redirect_result",
        "robots_result",
        "email_result",
        "waf_result",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "generate_remediation":
                passed = {kw.arg for kw in node.keywords}
                missing = required_params - passed
                assert not missing, f"scan_service missing params: {missing}"
                return

    raise AssertionError("generate_remediation call not found in scan_service.py")
