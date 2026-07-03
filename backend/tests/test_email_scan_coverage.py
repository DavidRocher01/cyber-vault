"""
Unit tests for send_scan_report in app.services.email_service.scan.

These cover the paths NOT already exercised by test_ssl_email_unit.py and
test_monthly_digest.py (which target send_ssl_expiry_alert / send_monthly_digest).

send_scan_report has two transport branches selected by settings.RESEND_API_KEY:
  - Resend  → resend.Emails.send(params), with/without PDF attachment
  - SMTP    → smtplib.SMTP_SSL(...), with/without PDF attachment
plus the status_emoji mapping (OK / WARNING / CRITICAL / unknown → default).

Nothing here performs real network/SMTP/Resend I/O — every transport is mocked.
"""

import base64
import smtplib
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import scan as scan_mod
from app.services.email_service import send_scan_report

# ── helpers ────────────────────────────────────────────────────────────────────


def _make_pdf(tmp_path, name="report.pdf", content=b"%PDF-1.4 fake pdf bytes"):
    p = tmp_path / name
    p.write_bytes(content)
    return str(p)


def _smtp_setting_patches(stack):
    """Enter the SMTP branch (empty RESEND key) with deterministic SMTP settings."""
    stack.enter_context(patch.object(scan_mod.settings, "RESEND_API_KEY", ""))
    stack.enter_context(patch.object(scan_mod.settings, "SMTP_HOST", "smtp.example.com"))
    stack.enter_context(patch.object(scan_mod.settings, "SMTP_PORT", 465))
    stack.enter_context(patch.object(scan_mod.settings, "SMTP_USER", "user@example.com"))
    stack.enter_context(patch.object(scan_mod.settings, "SMTP_PASSWORD", "pw"))
    stack.enter_context(patch.object(scan_mod.settings, "SMTP_FROM", "from@example.com"))


# ─── Resend transport branch ────────────────────────────────────────────────────


def test_resend_used_when_api_key_set(tmp_path):
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch.object(scan_mod.settings, "RESEND_FROM", "from@rocher.io"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
        patch("app.services.email_service.scan.smtplib.SMTP_SSL") as mock_smtp,
    ):
        send_scan_report("dest@example.com", "https://target.io", "OK", pdf)

    mock_send.assert_called_once()
    mock_smtp.assert_not_called()  # SMTP branch must be short-circuited


def test_resend_params_recipient_from_and_subject(tmp_path):
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch.object(scan_mod.settings, "RESEND_FROM", "sender@rocher.io"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://mysite.fr", "OK", pdf)

    params = mock_send.call_args[0][0]
    assert params["to"] == ["dest@example.com"]
    assert params["from"] == "sender@rocher.io"
    assert "mysite.fr" in params["subject"]
    assert params["subject"].startswith("[Rocher Cybersécurité]")


def test_resend_attaches_existing_pdf_base64(tmp_path):
    pdf = _make_pdf(tmp_path, name="scan_result.pdf", content=b"HELLO-PDF-DATA")
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", "WARNING", pdf)

    params = mock_send.call_args[0][0]
    assert "attachments" in params
    att = params["attachments"][0]
    assert att["filename"] == "scan_result.pdf"
    assert base64.b64decode(att["content"]) == b"HELLO-PDF-DATA"


def test_resend_no_attachment_when_pdf_missing(tmp_path):
    missing = str(tmp_path / "does_not_exist.pdf")
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", "OK", missing)

    params = mock_send.call_args[0][0]
    assert "attachments" not in params
    mock_send.assert_called_once()  # still sends even with no attachment


def test_resend_text_body_contains_site_and_status(tmp_path):
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://body.example", "CRITICAL", pdf)

    params = mock_send.call_args[0][0]
    assert "body.example" in params["text"]
    assert "CRITICAL" in params["text"]


# ─── status_emoji mapping ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "status,emoji",
    [("OK", "✅"), ("WARNING", "⚠️"), ("CRITICAL", "🚨")],
)
def test_known_status_emoji_in_subject(tmp_path, status, emoji):
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", status, pdf)

    subject = mock_send.call_args[0][0]["subject"]
    assert emoji in subject


def test_unknown_status_uses_default_emoji(tmp_path):
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", "MYSTERY", pdf)

    params = mock_send.call_args[0][0]
    # Default clipboard emoji for an unrecognised overall_status.
    assert "📋" in params["subject"]
    # The raw unknown status still appears in the body text.
    assert "MYSTERY" in params["text"]


# ─── SMTP transport branch (RESEND_API_KEY empty) ───────────────────────────────


def test_smtp_used_when_no_resend_key(tmp_path):
    pdf = _make_pdf(tmp_path)
    server = MagicMock()
    with ExitStack() as stack:
        _smtp_setting_patches(stack)
        mock_smtp = stack.enter_context(patch("app.services.email_service.scan.smtplib.SMTP_SSL"))
        mock_resend = stack.enter_context(
            patch("app.services.email_service.scan.resend.Emails.send")
        )
        mock_smtp.return_value.__enter__.return_value = server

        send_scan_report("dest@example.com", "https://x.io", "OK", pdf)

    mock_resend.assert_not_called()
    mock_smtp.assert_called_once()
    server.login.assert_called_once_with("user@example.com", "pw")
    server.sendmail.assert_called_once()


def test_smtp_sendmail_recipient_and_from(tmp_path):
    pdf = _make_pdf(tmp_path)
    server = MagicMock()
    with ExitStack() as stack:
        _smtp_setting_patches(stack)
        mock_smtp = stack.enter_context(patch("app.services.email_service.scan.smtplib.SMTP_SSL"))
        mock_smtp.return_value.__enter__.return_value = server

        send_scan_report("recipient@example.com", "https://x.io", "OK", pdf)

    from_addr, to_addr, raw = server.sendmail.call_args[0]
    assert from_addr == "from@example.com"
    assert to_addr == "recipient@example.com"
    # The attached PDF filename shows up in the MIME payload.
    assert "report.pdf" in raw


def test_smtp_without_pdf_still_sends(tmp_path):
    missing = str(tmp_path / "nope.pdf")
    server = MagicMock()
    with ExitStack() as stack:
        _smtp_setting_patches(stack)
        mock_smtp = stack.enter_context(patch("app.services.email_service.scan.smtplib.SMTP_SSL"))
        mock_smtp.return_value.__enter__.return_value = server

        send_scan_report("dest@example.com", "https://x.io", "WARNING", missing)

    server.sendmail.assert_called_once()
    from_addr, to_addr, raw = server.sendmail.call_args[0]
    assert to_addr == "dest@example.com"
    assert from_addr == "from@example.com"
    # Parse the MIME message: with a missing PDF there must be no attachment part,
    # only the single text/plain body.
    import email as email_lib

    msg = email_lib.message_from_string(raw)
    parts = [p.get_content_type() for p in msg.walk() if not p.is_multipart()]
    assert parts == ["text/plain"]
    # No application/* attachment part was added.
    assert not any(ct.startswith("application/") for ct in parts)


# ─── failure handling: transport error propagates (caller is responsible) ───────


def test_resend_send_failure_propagates(tmp_path):
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch(
            "app.services.email_service.scan.resend.Emails.send",
            side_effect=RuntimeError("resend down"),
        ),
    ):
        with pytest.raises(RuntimeError, match="resend down"):
            send_scan_report("dest@example.com", "https://x.io", "OK", pdf)


def test_smtp_login_failure_propagates(tmp_path):
    pdf = _make_pdf(tmp_path)
    server = MagicMock()
    server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad creds")
    with ExitStack() as stack:
        _smtp_setting_patches(stack)
        mock_smtp = stack.enter_context(patch("app.services.email_service.scan.smtplib.SMTP_SSL"))
        mock_smtp.return_value.__enter__.return_value = server

        with pytest.raises(smtplib.SMTPAuthenticationError):
            send_scan_report("dest@example.com", "https://x.io", "OK", pdf)
