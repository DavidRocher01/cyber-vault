"""
Unit tests for the _check_ssl_alerts scheduler job.

Covers: threshold selection, deduplication, cert-renewed reset,
notif_ssl_expiry preference, missing scan/json, email dispatch.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scheduler import _check_ssl_alerts
from app.models.plan import Plan
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User


# ─── helpers ─────────────────────────────────────────────────────────────────

def _user(user_id: int = 1, notif_ssl_expiry: bool = True) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    u.email = f"user{user_id}@example.com"
    u.notif_ssl_expiry = notif_ssl_expiry
    return u


def _site(site_id: int = 1, user_id: int = 1, ssl_alert_threshold=None) -> MagicMock:
    s = MagicMock(spec=Site)
    s.id = site_id
    s.user_id = user_id
    s.url = "https://example.com"
    s.ssl_alert_threshold = ssl_alert_threshold
    s.ssl_alert_sent_at = None
    return s


def _scan(site_id: int = 1, days_remaining=None, expiry_date: str = "2026-05-21") -> MagicMock:
    sc = MagicMock(spec=Scan)
    sc.site_id = site_id
    sc.results_json = (
        json.dumps({"ssl": {"days_remaining": days_remaining, "expiry_date": expiry_date}})
        if days_remaining is not None
        else None
    )
    return sc


def _plan() -> MagicMock:
    return MagicMock(spec=Plan)


def _build_db(rows, last_scans, users):
    """Mock AsyncSession with sequential execute() results."""
    db = AsyncMock()
    db.commit = AsyncMock()
    calls = {"n": 0}

    async def _execute(*args, **kwargs):
        i = calls["n"]
        calls["n"] += 1
        r = MagicMock()
        if i == 0:
            r.all.return_value = rows
        elif i == 1:
            r.scalars.return_value.all.return_value = last_scans
        elif i == 2:
            r.scalars.return_value.all.return_value = users
        return r

    db.execute = _execute
    return db


def _patch_session(db):
    """Patch AsyncSessionLocal to use the provided mock db."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.scheduler.AsyncSessionLocal", MagicMock(return_value=cm))


# ─── tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_active_sites_returns_early():
    """No rows → function returns immediately without touching anything."""
    db = _build_db(rows=[], last_scans=[], users=[])
    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()
    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_notif_ssl_expiry_false_skips_email():
    """User has opted out of SSL alerts → no email sent."""
    site = _site()
    user = _user(notif_ssl_expiry=False)
    scan = _scan(days_remaining=5)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_no_last_scan_skips_email():
    """Site has no completed scan → no email sent."""
    site = _site()
    user = _user()
    db = _build_db(rows=[(site, _plan())], last_scans=[], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_results_json_none_skips_email():
    """Last scan has no results_json → no email sent."""
    site = _site()
    user = _user()
    scan = _scan(days_remaining=None)  # produces results_json=None
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_days_remaining_missing_in_json_skips_email():
    """results_json present but ssl.days_remaining is absent → no email."""
    site = _site()
    user = _user()
    scan = MagicMock(spec=Scan)
    scan.site_id = 1
    scan.results_json = json.dumps({"ssl": {"expiry_date": "2026-06-01"}})
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_cert_renewed_resets_threshold():
    """days > 30 and threshold was set → reset threshold to None, no email."""
    site = _site(ssl_alert_threshold=14)
    user = _user()
    scan = _scan(days_remaining=45)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    assert site.ssl_alert_threshold is None
    assert site.ssl_alert_sent_at is None
    db.commit.assert_called()
    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_cert_above_30_no_threshold_no_action():
    """days > 30 but threshold was already None → nothing changes, no email."""
    site = _site(ssl_alert_threshold=None)
    user = _user()
    scan = _scan(days_remaining=45)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    assert site.ssl_alert_threshold is None
    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_sends_alert_at_30_day_threshold():
    """days=25 → matches 30-day threshold, email sent and threshold updated."""
    site = _site(ssl_alert_threshold=None)
    user = _user()
    scan = _scan(days_remaining=25)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_called_once()
    assert site.ssl_alert_threshold == 30
    assert site.ssl_alert_sent_at is not None
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_sends_alert_at_14_day_threshold():
    """days=10 → matches 14-day threshold, email sent."""
    site = _site(ssl_alert_threshold=None)
    user = _user()
    scan = _scan(days_remaining=10)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_called_once()
    assert site.ssl_alert_threshold == 14


@pytest.mark.asyncio
async def test_sends_alert_at_7_day_threshold():
    """days=5 → matches 7-day threshold, email sent."""
    site = _site(ssl_alert_threshold=None)
    user = _user()
    scan = _scan(days_remaining=5)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_called_once()
    assert site.ssl_alert_threshold == 7


@pytest.mark.asyncio
async def test_skip_if_same_threshold_already_sent():
    """days=10 → threshold=14, but ssl_alert_threshold=14 already → skip."""
    site = _site(ssl_alert_threshold=14)
    user = _user()
    scan = _scan(days_remaining=10)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_skip_if_more_urgent_already_sent():
    """days=10 → threshold=14, but ssl_alert_threshold=7 (more urgent) → skip."""
    site = _site(ssl_alert_threshold=7)
    user = _user()
    scan = _scan(days_remaining=10)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_not_called()


@pytest.mark.asyncio
async def test_escalates_from_30_to_14_threshold():
    """days=10, ssl_alert_threshold=30 (only 30-day sent) → send 14-day alert."""
    site = _site(ssl_alert_threshold=30)
    user = _user()
    scan = _scan(days_remaining=10)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    mock_thread.assert_called_once()
    assert site.ssl_alert_threshold == 14


@pytest.mark.asyncio
async def test_email_called_with_correct_args():
    """Verify send_ssl_expiry_alert is passed the right site_url, days, email."""
    site = _site()
    user = _user()
    scan = _scan(days_remaining=5, expiry_date="2026-04-28")
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        await _check_ssl_alerts()

    args, kwargs = mock_thread.call_args
    # args[0] is the callable, remaining are positional kwargs
    assert kwargs.get("to_email") == user.email or args[1] == user.email or "user1@example.com" in str(mock_thread.call_args)
    call_kwargs = mock_thread.call_args.kwargs
    assert call_kwargs["to_email"] == "user1@example.com"
    assert call_kwargs["site_url"] == "https://example.com"
    assert call_kwargs["days_remaining"] == 5
    assert call_kwargs["expiry_date"] == "2026-04-28"


@pytest.mark.asyncio
async def test_email_failure_does_not_raise():
    """If email send raises, the job should swallow the error silently."""
    site = _site()
    user = _user()
    scan = _scan(days_remaining=5)
    db = _build_db(rows=[(site, _plan())], last_scans=[scan], users=[user])

    with _patch_session(db), patch("asyncio.to_thread", AsyncMock(side_effect=Exception("SMTP error"))):
        await _check_ssl_alerts()  # must not raise


@pytest.mark.asyncio
async def test_multiple_sites_independent():
    """Two sites with different days: each gets the correct threshold."""
    site1 = _site(site_id=1, user_id=1)
    site2 = _site(site_id=2, user_id=2)
    user1 = _user(user_id=1)
    user2 = _user(user_id=2)
    scan1 = _scan(site_id=1, days_remaining=5)
    scan2 = _scan(site_id=2, days_remaining=20)

    db = AsyncMock()
    db.commit = AsyncMock()
    calls = {"n": 0}

    async def _execute(*args, **kwargs):
        i = calls["n"]
        calls["n"] += 1
        r = MagicMock()
        if i == 0:
            r.all.return_value = [(site1, _plan()), (site2, _plan())]
        elif i == 1:
            r.scalars.return_value.all.return_value = [scan1, scan2]
        elif i == 2:
            r.scalars.return_value.all.return_value = [user1, user2]
        return r

    db.execute = _execute

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.scheduler.AsyncSessionLocal", MagicMock(return_value=cm)):
        with patch("asyncio.to_thread", new_callable=AsyncMock):
            await _check_ssl_alerts()

    assert site1.ssl_alert_threshold == 7
    assert site2.ssl_alert_threshold == 30
