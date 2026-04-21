"""
Unit tests for send_ssl_expiry_alert in app.services.email_service.

Covers: urgency level selection, subject content, HTML content, _send dispatch.
"""

from unittest.mock import patch, MagicMock

import pytest

from app.services.email_service import send_ssl_expiry_alert


def _call_alert(days: int, site_url: str = "https://example.com", expiry_date: str = "2026-05-01"):
    """Call send_ssl_expiry_alert with a patched _send and return (subject, html, plain, mock)."""
    with patch("app.services.email_service._send") as mock_send:
        send_ssl_expiry_alert(
            to_email="user@example.com",
            site_url=site_url,
            days_remaining=days,
            expiry_date=expiry_date,
            dashboard_url="https://cyberscanapp.com/cyberscan/dashboard",
        )
    assert mock_send.called
    _, subject, html, plain = mock_send.call_args[0]
    return subject, html, plain, mock_send


# ─── urgency level ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("days", [1, 5, 7])
def test_critique_level_at_7_days_or_less(days):
    subject, html, plain, _ = _call_alert(days)
    assert "CRITIQUE" in html
    assert "#ef4444" in html
    assert "🚨" in subject


@pytest.mark.parametrize("days", [8, 10, 14])
def test_urgent_level_at_8_to_14_days(days):
    subject, html, plain, _ = _call_alert(days)
    assert "URGENT" in html
    assert "#f97316" in html


@pytest.mark.parametrize("days", [15, 20, 30])
def test_attention_level_at_15_to_30_days(days):
    subject, html, plain, _ = _call_alert(days)
    assert "ATTENTION" in html
    assert "#eab308" in html


# ─── subject ─────────────────────────────────────────────────────────────────

def test_subject_contains_site_url():
    subject, *_ = _call_alert(10, site_url="https://mysite.fr")
    assert "mysite.fr" in subject


def test_subject_contains_days_remaining():
    subject, *_ = _call_alert(10)
    assert "10" in subject


def test_subject_prefixed_with_cyberscan_tag():
    subject, *_ = _call_alert(5)
    assert subject.startswith("[CyberScan]")


# ─── email content ────────────────────────────────────────────────────────────

def test_html_contains_site_url():
    _, html, _, _ = _call_alert(5, site_url="https://target.io")
    assert "target.io" in html


def test_html_contains_expiry_date():
    _, html, _, _ = _call_alert(5, expiry_date="2026-04-28")
    assert "2026-04-28" in html


def test_html_contains_days_remaining():
    _, html, _, _ = _call_alert(5)
    assert "5" in html


def test_plain_contains_site_url():
    _, _, plain, _ = _call_alert(5, site_url="https://target.io")
    assert "target.io" in plain


def test_plain_contains_dashboard_url():
    _, _, plain, _ = _call_alert(5)
    assert "cyberscanapp.com/cyberscan/dashboard" in plain


# ─── dispatch ────────────────────────────────────────────────────────────────

def test_send_called_once():
    *_, mock_send = _call_alert(10)
    mock_send.assert_called_once()


def test_send_receives_correct_recipient():
    with patch("app.services.email_service._send") as mock_send:
        send_ssl_expiry_alert(
            to_email="recipient@example.com",
            site_url="https://example.com",
            days_remaining=10,
            expiry_date="2026-05-01",
            dashboard_url="https://cyberscanapp.com/cyberscan/dashboard",
        )
    to_email = mock_send.call_args[0][0]
    assert to_email == "recipient@example.com"
