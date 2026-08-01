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
    # Le code brut « CRITICAL » est du jargon interne : le corps porte
    # desormais le libelle lisible. Un statut NON reconnu, lui, reste affiche
    # tel quel — cf. test_statut_inconnu_reste_affiche.
    assert "Action immédiate requise" in params["text"]


# ─── objet de l'e-mail : lisible, sans emoji ───────────────────────────────────
#
# Ces tests verifiaient auparavant la PRESENCE d'un emoji dans l'objet. Ils ont
# ete inverses le 2026-08-01 : le rapport de scan arrivait en indesirable, et
# l'emoji dans l'objet est un signal negatif connu des filtres. Le statut est
# desormais dit par un libelle, qui informe mieux qu'un pictogramme.


@pytest.mark.parametrize(
    "status,libelle",
    [
        ("OK", "Aucune vulnérabilité critique"),
        ("WARNING", "Vulnérabilités à corriger"),
        ("CRITICAL", "Action immédiate requise"),
    ],
)
def test_statut_dit_en_toutes_lettres(tmp_path, status, libelle):
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", status, pdf)

    params = mock_send.call_args[0][0]
    assert libelle in params["text"]
    assert libelle in params["html"]


@pytest.mark.parametrize("status", ["OK", "WARNING", "CRITICAL", "MYSTERY"])
def test_aucun_emoji_dans_l_objet(tmp_path, status):
    """Un emoji dans l'objet pese sur la delivrabilite — aucun ne doit y entrer."""
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", status, pdf)

    subject = mock_send.call_args[0][0]["subject"]
    # Le tiret cadratin de l'objet est legitime : on ne regarde que les plages
    # de pictogrammes et emoji.
    emoji = [c for c in subject if ord(c) >= 0x2190 and c != "—"]
    assert emoji == [], f"emoji dans l'objet : {emoji}"


def test_statut_inconnu_reste_affiche(tmp_path):
    """Un statut non reconnu doit rester lisible plutot que disparaitre."""
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", "MYSTERY", pdf)

    params = mock_send.call_args[0][0]
    assert "MYSTERY" in params["text"]


def test_le_html_est_reellement_envoye(tmp_path):
    """Le HTML etait construit puis JETE : ce message partait en texte seul."""
    pdf = _make_pdf(tmp_path)
    with (
        patch.object(scan_mod.settings, "RESEND_API_KEY", "re_test_key"),
        patch("app.services.email_service.scan.resend.Emails.send") as mock_send,
    ):
        send_scan_report("dest@example.com", "https://x.io", "WARNING", pdf)

    params = mock_send.call_args[0][0]
    assert params["html"].startswith("<!DOCTYPE html>")
    assert "Rocher Cybersécurité" in params["html"]


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
    # text/html en plus du texte depuis le 2026-08-01 : ce message partait en
    # texte seul, ce qui pesait sur sa delivrabilite.
    assert parts == ["text/plain", "text/html"]
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
