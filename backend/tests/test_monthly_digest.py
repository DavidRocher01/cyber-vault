"""
Tests for the monthly digest — email function + scheduler job.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email_service import send_monthly_digest

# ── send_monthly_digest ────────────────────────────────────────────────────────


def _sites(n=1, critical=0, warning=0, status="OK"):
    return [
        {
            "url": f"https://site{i}.example.com",
            "overall_status": status,
            "scans_count": 3,
            "critical_count": critical,
            "warning_count": warning,
        }
        for i in range(n)
    ]


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_calls_send(mock_send):
    send_monthly_digest(
        to_email="user@example.com",
        month_label="Janvier 2026",
        sites=_sites(1),
        dashboard_url="https://app.example.com/dashboard",
    )
    mock_send.assert_called_once()
    subject, html, plain = (
        mock_send.call_args[0][1],
        mock_send.call_args[0][2],
        mock_send.call_args[0][3],
    )
    assert "Janvier 2026" in subject


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_subject_contains_month(mock_send):
    send_monthly_digest("u@e.com", "Mars 2025", _sites(), "http://x")
    subject = mock_send.call_args[0][1]
    assert "Mars 2025" in subject
    assert "bilan" in subject.lower()


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_html_contains_site_url(mock_send):
    send_monthly_digest("u@e.com", "Avril 2026", _sites(1), "http://dash")
    html = mock_send.call_args[0][2]
    assert "https://site0.example.com" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_html_shows_critical_count(mock_send):
    send_monthly_digest("u@e.com", "Avril 2026", _sites(1, critical=3), "http://dash")
    html = mock_send.call_args[0][2]
    assert "3" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_ok_status_green_color(mock_send):
    send_monthly_digest("u@e.com", "Avril 2026", _sites(1, status="OK"), "http://dash")
    html = mock_send.call_args[0][2]
    assert "#22c55e" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_critical_status_red_color(mock_send):
    send_monthly_digest("u@e.com", "Avril 2026", _sites(1, status="CRITICAL"), "http://dash")
    html = mock_send.call_args[0][2]
    assert "#ef4444" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_dashboard_link_in_html(mock_send):
    send_monthly_digest(
        "u@e.com", "Mai 2026", _sites(), "https://app.example.com/cyberscan/dashboard"
    )
    html = mock_send.call_args[0][2]
    assert "https://app.example.com/cyberscan/dashboard" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_plain_text_contains_site(mock_send):
    send_monthly_digest("u@e.com", "Mai 2026", _sites(1), "http://dash")
    plain = mock_send.call_args[0][3]
    assert "https://site0.example.com" in plain


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_multiple_sites(mock_send):
    send_monthly_digest("u@e.com", "Juin 2026", _sites(3), "http://dash")
    html = mock_send.call_args[0][2]
    assert "site0" in html
    assert "site1" in html
    assert "site2" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_zero_scans_handled(mock_send):
    sites = [
        {
            "url": "https://s.com",
            "overall_status": None,
            "scans_count": 0,
            "critical_count": 0,
            "warning_count": 0,
        }
    ]
    send_monthly_digest("u@e.com", "Juillet 2026", sites, "http://dash")
    mock_send.assert_called_once()
    html = mock_send.call_args[0][2]
    assert "https://s.com" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_no_criticals_green_summary(mock_send):
    send_monthly_digest("u@e.com", "Août 2026", _sites(2, critical=0), "http://dash")
    html = mock_send.call_args[0][2]
    assert "Aucune faille critique" in html


@patch("app.services.email_service.scan._send")
def test_send_monthly_digest_with_criticals_warning_summary(mock_send):
    send_monthly_digest("u@e.com", "Août 2026", _sites(1, critical=2), "http://dash")
    plain = mock_send.call_args[0][3]
    assert "faille" in plain.lower()


# ── _send_monthly_digest_job (scheduler) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_monthly_digest_job_no_active_subscriptions():
    """Job returns immediately without sending emails when no active subs."""
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    with patch("app.services.scheduler.AsyncSessionLocal") as mock_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_ctx

        with patch("app.services.scheduler.send_monthly_digest") as mock_send:
            from app.services.scheduler import _send_monthly_digest_job

            await _send_monthly_digest_job()
            mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_monthly_digest_job_sends_to_each_user():
    """One email per distinct user even if they have multiple sites."""
    user1 = MagicMock(id=1, email="u1@ex.com")
    site1a = MagicMock(id=10, user_id=1, url="https://a.com", is_active=True)
    site1b = MagicMock(id=11, user_id=1, url="https://b.com", is_active=True)

    db = AsyncMock()
    call_count = {"n": 0}

    async def execute_side(query):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.all.return_value = [(user1, site1a), (user1, site1b)]
        else:
            r.scalars.return_value.all.return_value = []
        return r

    db.execute = execute_side

    with patch("app.services.scheduler.AsyncSessionLocal") as mock_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_ctx

        with patch(
            "app.services.scheduler.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_thread:
            from app.services.scheduler import _send_monthly_digest_job

            await _send_monthly_digest_job()
            assert mock_thread.call_count == 1


@pytest.mark.asyncio
async def test_monthly_digest_job_counts_scans_per_site():
    """Job correctly counts scans for each site."""
    user1 = MagicMock(id=1, email="u@ex.com")
    site1 = MagicMock(id=10, user_id=1, url="https://a.com", is_active=True)

    scan1 = MagicMock(
        site_id=10,
        overall_status="OK",
        results_json=json.dumps({"ssl": {"status": "OK"}}),
    )
    scan2 = MagicMock(
        site_id=10,
        overall_status="WARNING",
        results_json=json.dumps({"headers": {"status": "WARNING"}}),
    )

    db = AsyncMock()
    call_count = {"n": 0}

    async def execute_side(query):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.all.return_value = [(user1, site1)]
        else:
            r.scalars.return_value.all.return_value = [scan1, scan2]
        return r

    db.execute = execute_side

    captured = {}

    async def capture_thread(fn, **kwargs):
        captured.update(kwargs)
        # Call the function to validate it works
        return fn(**kwargs)

    with patch("app.services.scheduler.AsyncSessionLocal") as mock_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=db)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_ctx

        with patch("app.services.scheduler.asyncio.to_thread") as mock_thread:
            mock_thread.return_value = None

            async def fake_to_thread(fn, **kw):
                return fn(**kw)

            mock_thread.side_effect = fake_to_thread

            with patch("app.services.scheduler.send_monthly_digest") as mock_send:
                from app.services.scheduler import _send_monthly_digest_job

                await _send_monthly_digest_job()

                assert mock_send.called
                call_kwargs = mock_send.call_args[1]
                sites = call_kwargs["sites"]
                assert len(sites) == 1
                assert sites[0]["scans_count"] == 2
