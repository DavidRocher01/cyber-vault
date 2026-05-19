"""
Unit tests for dark web surveillance module.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.darkweb import get_darkweb_status, run_darkweb_check
from app.services.darkweb_service import check_email_breaches
from app.models.darkweb_scan import DarkwebScan
from app.models.user import User


# ── helpers ────────────────────────────────────────────────────────────────────

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
    s.results_json = json.dumps([{"name": "TestBreach", "domain": "test.com",
                                   "breach_date": "2023-01-01", "pwn_count": 100000,
                                   "data_classes": ["Email addresses"], "is_sensitive": False}])
    return s


def _db_no_scan():
    db = AsyncMock()
    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        return r
    db.execute = execute
    return db


def _db_with_scan(scan, fresh=True):
    db = AsyncMock()
    call_count = {"n": 0}
    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = scan
        return r
    db.execute = execute
    return db


# ── darkweb_service ────────────────────────────────────────────────────────────

def test_check_email_no_api_key_returns_unknown():
    result = check_email_breaches("test@example.com", "")
    assert result["status"] == "unknown"
    assert "not configured" in result["error"]


def test_check_email_status_ok_when_no_breaches():
    with patch("app.services.darkweb_service.requests.get") as mock_get:
        mock_get.return_value.status_code = 404
        result = check_email_breaches("clean@example.com", "test_key")
    assert result["status"] == "OK"
    assert result["total"] == 0


def test_check_email_status_warning_one_breach():
    breach_data = [{"Name": "Test", "Domain": "test.com", "BreachDate": "2023-01-01",
                    "PwnCount": 100, "DataClasses": ["Emails"], "IsSensitive": False}]
    with patch("app.services.darkweb_service.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = breach_data
        result = check_email_breaches("warn@example.com", "test_key")
    assert result["status"] == "WARNING"
    assert result["total"] == 1


def test_check_email_status_critical_three_breaches():
    breach_data = [
        {"Name": f"B{i}", "Domain": "x.com", "BreachDate": "2023-01-01",
         "PwnCount": 100, "DataClasses": [], "IsSensitive": False}
        for i in range(3)
    ]
    with patch("app.services.darkweb_service.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = breach_data
        result = check_email_breaches("crit@example.com", "test_key")
    assert result["status"] == "CRITICAL"
    assert result["total"] == 3


def test_check_email_rate_limited():
    with patch("app.services.darkweb_service.requests.get") as mock_get:
        mock_get.return_value.status_code = 429
        result = check_email_breaches("test@example.com", "test_key")
    assert result["status"] == "unknown"
    assert "Rate limited" in result["error"]


# ── get_darkweb_status ────────────────────────────────────────────────────────

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


# ── run_darkweb_check ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_returns_cached_if_fresh():
    scan = _scan(hours_ago=1)
    result = await run_darkweb_check(_user(), _db_with_scan(scan))
    assert result.fresh is True
    assert result.status == scan.status


@pytest.mark.asyncio
async def test_check_calls_hibp_when_stale():
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
