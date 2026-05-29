"""
Unit tests for GET /users/me/badges endpoint.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.users import get_my_badges
from app.models.nis2_assessment import Nis2Assessment
from app.models.scan import Scan
from app.models.user import User

# ── helpers ────────────────────────────────────────────────────────────────────


def _user(uid: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uid
    return u


def _scan(site_id=1, overall="OK", days_ago=5) -> MagicMock:
    s = MagicMock(spec=Scan)
    s.site_id = site_id
    s.status = "done"
    s.overall_status = overall
    s.finished_at = datetime.now(UTC) - timedelta(days=days_ago)
    return s


def _nis2(score=75) -> MagicMock:
    n = MagicMock(spec=Nis2Assessment)
    n.score = score
    n.updated_at = datetime.now(UTC)
    return n


def _db(scans: list, nis2=None):
    db = AsyncMock()
    call_count = {"n": 0}

    async def execute(query):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalars.return_value.all.return_value = scans
        else:
            r.scalar_one_or_none.return_value = nis2
        return r

    db.execute = execute
    return db


# ── always returns 5 badges ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_returns_exactly_five_badges():
    result = await get_my_badges(_user(), _db([]))
    assert len(result) == 5


@pytest.mark.asyncio
async def test_badge_ids_are_correct():
    result = await get_my_badges(_user(), _db([]))
    ids = {b["id"] for b in result}
    assert ids == {
        "first_scan",
        "power_user",
        "site_secured",
        "no_critical_30d",
        "nis2_complete",
    }


# ── first_scan ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_scan_not_earned_without_scans():
    result = await get_my_badges(_user(), _db([]))
    badge = next(b for b in result if b["id"] == "first_scan")
    assert badge["earned"] is False
    assert badge["earned_at"] is None


@pytest.mark.asyncio
async def test_first_scan_earned_with_one_scan():
    result = await get_my_badges(_user(), _db([_scan()]))
    badge = next(b for b in result if b["id"] == "first_scan")
    assert badge["earned"] is True
    assert badge["earned_at"] is not None


# ── power_user ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_power_user_not_earned_with_four_scans():
    result = await get_my_badges(_user(), _db([_scan() for _ in range(4)]))
    badge = next(b for b in result if b["id"] == "power_user")
    assert badge["earned"] is False


@pytest.mark.asyncio
async def test_power_user_earned_with_five_scans():
    result = await get_my_badges(_user(), _db([_scan() for _ in range(5)]))
    badge = next(b for b in result if b["id"] == "power_user")
    assert badge["earned"] is True
    assert badge["earned_at"] is not None


# ── site_secured ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_site_secured_not_earned_with_only_critical_scans():
    result = await get_my_badges(_user(), _db([_scan(overall="CRITICAL")]))
    badge = next(b for b in result if b["id"] == "site_secured")
    assert badge["earned"] is False


@pytest.mark.asyncio
async def test_site_secured_earned_with_ok_scan():
    result = await get_my_badges(_user(), _db([_scan(overall="OK")]))
    badge = next(b for b in result if b["id"] == "site_secured")
    assert badge["earned"] is True


# ── no_critical_30d ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_critical_30d_not_earned_without_recent_scans():
    old_scan = _scan(overall="OK", days_ago=60)
    result = await get_my_badges(_user(), _db([old_scan]))
    badge = next(b for b in result if b["id"] == "no_critical_30d")
    assert badge["earned"] is False


@pytest.mark.asyncio
async def test_no_critical_30d_earned_with_clean_recent_scans():
    result = await get_my_badges(_user(), _db([_scan(overall="OK", days_ago=3)]))
    badge = next(b for b in result if b["id"] == "no_critical_30d")
    assert badge["earned"] is True


@pytest.mark.asyncio
async def test_no_critical_30d_not_earned_if_critical_in_period():
    result = await get_my_badges(_user(), _db([_scan(overall="CRITICAL", days_ago=3)]))
    badge = next(b for b in result if b["id"] == "no_critical_30d")
    assert badge["earned"] is False


# ── nis2_complete ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nis2_not_earned_without_assessment():
    result = await get_my_badges(_user(), _db([], nis2=None))
    badge = next(b for b in result if b["id"] == "nis2_complete")
    assert badge["earned"] is False


@pytest.mark.asyncio
async def test_nis2_not_earned_with_zero_score():
    result = await get_my_badges(_user(), _db([], nis2=_nis2(score=0)))
    badge = next(b for b in result if b["id"] == "nis2_complete")
    assert badge["earned"] is False


@pytest.mark.asyncio
async def test_nis2_earned_with_positive_score():
    result = await get_my_badges(_user(), _db([], nis2=_nis2(score=60)))
    badge = next(b for b in result if b["id"] == "nis2_complete")
    assert badge["earned"] is True
    assert badge["earned_at"] is not None


# ── structure validation ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_each_badge_has_required_fields():
    result = await get_my_badges(_user(), _db([]))
    for b in result:
        assert "id" in b
        assert "label" in b
        assert "description" in b
        assert "icon" in b
        assert "earned" in b
        assert "earned_at" in b
