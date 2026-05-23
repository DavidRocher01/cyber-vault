"""Unit tests — dark web surveillance (personal email check)."""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.darkweb import get_darkweb_status, run_darkweb_check
from app.models.darkweb_scan import DarkwebScan
from app.models.user import User
from app.services.darkweb_service import (
    check_email_breaches,
    check_email_hibp,
    check_email_leakcheck,
    enrich_breaches_from_catalog,
    fetch_hibp_breach_catalog,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _user(uid: int = 1, email: str = "test@example.com") -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uid
    u.email = email
    return u


def _scan(total: int = 2, status: str = "WARNING", hours_ago: int = 1) -> MagicMock:
    s = MagicMock(spec=DarkwebScan)
    s.user_id = 1
    s.email = "test@example.com"
    s.total_breaches = total
    s.status = status
    s.checked_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    s.results_json = json.dumps([{
        "name": "TestBreach", "domain": "test.com",
        "breach_date": "2023-01-01", "pwn_count": 100000,
        "data_classes": ["Email addresses"], "is_sensitive": False,
    }])
    return s


def _db_no_scan():
    db = AsyncMock()
    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        return r
    db.execute = execute
    return db


def _db_with_scan(scan):
    db = AsyncMock()
    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = scan
        return r
    db.execute = execute
    return db


def _leakcheck_response(found: int, sources: list) -> MagicMock:
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"success": True, "found": found, "sources": sources}
    return m


def _hibp_response(status_code: int, data=None) -> MagicMock:
    m = MagicMock()
    m.status_code = status_code
    if data is not None:
        m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


# ── check_email_leakcheck ─────────────────────────────────────────────────────

def test_leakcheck_clean_email():
    with patch("app.services.darkweb_service.requests.get") as mock_get:
        mock_get.return_value = _leakcheck_response(0, [])
        result = check_email_leakcheck("clean@example.com")
    assert result["status"] == "OK"
    assert result["total"] == 0
    assert result["provider"] == "leakcheck"


def test_leakcheck_warning_one_breach():
    sources = [{"name": "LinkedIn", "date": "2021-06-22"}]
    with patch("app.services.darkweb_service.requests.get") as mock_get:
        mock_get.return_value = _leakcheck_response(1, sources)
        result = check_email_leakcheck("user@example.com")
    assert result["status"] == "WARNING"
    assert result["total"] == 1
    assert result["breaches"][0]["name"] == "LinkedIn"


def test_leakcheck_critical_three_breaches():
    sources = [{"name": f"Breach{i}", "date": "2020-01-01"} for i in range(3)]
    with patch("app.services.darkweb_service.requests.get") as mock_get:
        mock_get.return_value = _leakcheck_response(3, sources)
        result = check_email_leakcheck("user@example.com")
    assert result["status"] == "CRITICAL"
    assert result["total"] == 3


def test_leakcheck_rate_limited():
    m = MagicMock()
    m.status_code = 429
    with patch("app.services.darkweb_service.requests.get", return_value=m):
        result = check_email_leakcheck("user@example.com")
    assert result["status"] == "unknown"
    assert "Rate limited" in result["error"]


def test_leakcheck_api_returns_failure():
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"success": False, "error": "Invalid email"}
    with patch("app.services.darkweb_service.requests.get", return_value=m):
        result = check_email_leakcheck("bad@")
    assert result["status"] == "unknown"
    assert result["error"] == "Invalid email"


def test_leakcheck_connection_error():
    import requests as req_lib
    with patch("app.services.darkweb_service.requests.get",
               side_effect=req_lib.exceptions.ConnectionError("unreachable")):
        result = check_email_leakcheck("user@example.com")
    assert result["status"] == "unknown"
    assert result["provider"] == "leakcheck"


# ── check_email_hibp ──────────────────────────────────────────────────────────

def test_hibp_no_key_returns_unknown():
    result = check_email_hibp("test@example.com", "")
    assert result["status"] == "unknown"
    assert "not configured" in result["error"]


def test_hibp_404_returns_ok():
    with patch("app.services.darkweb_service.requests.get",
               return_value=_hibp_response(404)):
        result = check_email_hibp("clean@example.com", "key123")
    assert result["status"] == "OK"
    assert result["total"] == 0


def test_hibp_401_returns_unknown():
    with patch("app.services.darkweb_service.requests.get",
               return_value=_hibp_response(401)):
        result = check_email_hibp("test@example.com", "bad_key")
    assert result["status"] == "unknown"
    assert "Invalid" in result["error"]


def test_hibp_429_returns_unknown():
    with patch("app.services.darkweb_service.requests.get",
               return_value=_hibp_response(429)):
        result = check_email_hibp("test@example.com", "key123")
    assert result["status"] == "unknown"
    assert "Rate limited" in result["error"]


def test_hibp_warning_one_breach():
    data = [{"Name": "Adobe", "Domain": "adobe.com", "BreachDate": "2013-10-04",
             "PwnCount": 153000000, "DataClasses": ["Email addresses", "Passwords"],
             "IsSensitive": False}]
    with patch("app.services.darkweb_service.requests.get",
               return_value=_hibp_response(200, data)):
        result = check_email_hibp("user@example.com", "key123")
    assert result["status"] == "WARNING"
    assert result["total"] == 1
    assert result["breaches"][0]["name"] == "Adobe"
    assert result["breaches"][0]["pwn_count"] == 153000000
    assert "Passwords" in result["breaches"][0]["data_classes"]


def test_hibp_critical_three_breaches():
    data = [{"Name": f"B{i}", "Domain": "x.com", "BreachDate": "2020-01-01",
             "PwnCount": 100, "DataClasses": [], "IsSensitive": False}
            for i in range(3)]
    with patch("app.services.darkweb_service.requests.get",
               return_value=_hibp_response(200, data)):
        result = check_email_hibp("user@example.com", "key123")
    assert result["status"] == "CRITICAL"
    assert result["total"] == 3


# ── check_email_breaches (multi-provider) ─────────────────────────────────────

def test_breaches_uses_leakcheck_when_no_key():
    sources = [{"name": "LinkedIn", "date": "2021-06-22"}]
    with patch("app.services.darkweb_service.requests.get",
               return_value=_leakcheck_response(1, sources)):
        result = check_email_breaches("user@example.com", "")
    assert result["provider"] == "leakcheck"
    assert result["status"] == "WARNING"


def test_breaches_uses_hibp_when_key_provided():
    data = [{"Name": "Adobe", "Domain": "adobe.com", "BreachDate": "2013-10-04",
             "PwnCount": 100, "DataClasses": [], "IsSensitive": False}]
    with patch("app.services.darkweb_service.requests.get",
               return_value=_hibp_response(200, data)):
        result = check_email_breaches("user@example.com", "valid_key")
    assert result["provider"] == "hibp"
    assert result["total"] == 1


def test_breaches_falls_back_to_leakcheck_when_hibp_unknown():
    sources = [{"name": "RockYou", "date": "2021-01-01"}]
    leakcheck_resp = _leakcheck_response(1, sources)

    call_count = {"n": 0}
    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _hibp_response(429)
        return leakcheck_resp

    with patch("app.services.darkweb_service.requests.get", side_effect=side_effect):
        result = check_email_breaches("user@example.com", "valid_key")
    assert result["provider"] == "leakcheck"
    assert result["status"] == "WARNING"


# ── enrich_breaches_from_catalog ──────────────────────────────────────────────

def test_enrich_adds_catalog_data():
    breaches = [{"name": "LinkedIn", "domain": "", "breach_date": "",
                 "pwn_count": 0, "data_classes": [], "is_sensitive": False}]
    catalog = {
        "linkedin": {
            "domain": "linkedin.com",
            "breach_date": "2012-05-05",
            "pwn_count": 164611595,
            "data_classes": ["Email addresses", "Passwords"],
            "is_sensitive": False,
            "is_verified": True,
        }
    }
    enriched = enrich_breaches_from_catalog(breaches, catalog)
    assert enriched[0]["domain"] == "linkedin.com"
    assert enriched[0]["pwn_count"] == 164611595
    assert "Passwords" in enriched[0]["data_classes"]
    assert enriched[0]["is_verified"] is True


def test_enrich_keeps_original_when_not_in_catalog():
    breaches = [{"name": "UnknownBreach", "domain": "unknown.com", "breach_date": "2020-01-01",
                 "pwn_count": 500, "data_classes": ["Emails"], "is_sensitive": False}]
    enriched = enrich_breaches_from_catalog(breaches, {})
    assert enriched[0]["domain"] == "unknown.com"
    assert enriched[0]["pwn_count"] == 500


def test_enrich_empty_list():
    assert enrich_breaches_from_catalog([], {}) == []


# ── fetch_hibp_breach_catalog ─────────────────────────────────────────────────

def test_fetch_catalog_returns_list():
    fake = [{"Name": "Adobe", "Domain": "adobe.com", "BreachDate": "2013-10-04",
             "PwnCount": 153000000, "DataClasses": ["Emails"], "IsVerified": True,
             "IsSensitive": False, "IsFabricated": False, "IsSpamList": False}]
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = fake
    m.raise_for_status = MagicMock()
    with patch("app.services.darkweb_service.requests.get", return_value=m):
        result = fetch_hibp_breach_catalog()
    assert len(result) == 1
    assert result[0]["Name"] == "Adobe"


def test_fetch_catalog_returns_empty_on_error():
    import requests as req_lib
    with patch("app.services.darkweb_service.requests.get",
               side_effect=req_lib.exceptions.ConnectionError()):
        result = fetch_hibp_breach_catalog()
    assert result == []


# ── get_darkweb_status endpoint ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_status_not_checked_when_no_scan():
    result = await get_darkweb_status(_user(), _db_no_scan())
    assert result.status == "not_checked"
    assert result.checked_at is None
    assert not result.fresh


@pytest.mark.asyncio
async def test_status_returns_cached_data():
    scan = _scan(total=2, status="WARNING", hours_ago=1)
    result = await get_darkweb_status(_user(), _db_with_scan(scan))
    assert result.status == "WARNING"
    assert result.total_breaches == 2
    assert result.fresh is True


@pytest.mark.asyncio
async def test_status_stale_when_old_scan():
    scan = _scan(hours_ago=30)
    result = await get_darkweb_status(_user(), _db_with_scan(scan))
    assert result.fresh is False


# ── run_darkweb_check endpoint ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_returns_cached_if_fresh():
    scan = _scan(hours_ago=1)
    result = await run_darkweb_check(_user(), _db_with_scan(scan))
    assert result.fresh is True
    assert result.status == scan.status


@pytest.mark.asyncio
async def test_check_calls_provider_when_stale():
    scan = _scan(hours_ago=30)
    db = _db_with_scan(scan)
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def refresh(obj):
        obj.id = 99
        obj.checked_at = datetime.now(timezone.utc)
    db.refresh = refresh

    mock_result = {"email": "test@example.com", "breaches": [], "total": 0,
                   "status": "OK", "error": None}
    with patch("app.api.v1.endpoints.darkweb.check_email_breaches", return_value=mock_result):
        result = await run_darkweb_check(_user(), db)

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    assert result.status == "OK"
