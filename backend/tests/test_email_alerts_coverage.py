"""
Unit tests for app.services.email_service.alerts.

Covers the alert/notification builders directly (not through the endpoints,
which existing tests mock out): send_url_scan_alert, send_campaign_complete,
send_contact_email, send_booking_confirmation, send_booking_admin_notification.

Focus: branches NOT exercised elsewhere — verdict/threat mappings, severity
icons, findings truncation, empty findings, campaign risk tiers, the
emails_sent==0 division guard, None recipients/fields, unknown enum labels,
the two-email contact flow, and the swallowed confirmation-send failure.

The transport (_send) is patched at the alerts module level so nothing is sent.
"""

from unittest.mock import patch

from app.services.email_service import (
    send_booking_admin_notification,
    send_booking_confirmation,
    send_campaign_complete,
    send_contact_email,
    send_url_scan_alert,
)

SEND = "app.services.email_service.alerts._send"


# ─── send_url_scan_alert ──────────────────────────────────────────────────────


def _call_url_scan(
    verdict="malicious",
    threat_score=88,
    threat_type="phishing",
    findings=None,
    scanned_url="https://evil.example.com",
):
    if findings is None:
        findings = [{"severity": "critical", "detail": "Formulaire de login détecté"}]
    with patch(SEND) as mock_send:
        send_url_scan_alert(
            to_email="user@example.com",
            scanned_url=scanned_url,
            verdict=verdict,
            threat_score=threat_score,
            threat_type=threat_type,
            findings=findings,
            dashboard_url="https://rochercybersecurite.com/dashboard",
        )
    assert mock_send.called
    to_email, subject, html, plain = mock_send.call_args[0]
    return to_email, subject, html, plain, mock_send


def test_url_scan_malicious_verdict_emoji_and_label():
    _, subject, _, plain, _ = _call_url_scan(verdict="malicious")
    assert "🚨" in subject
    assert "Malveillant" in plain


def test_url_scan_suspicious_verdict():
    _, subject, _, plain, _ = _call_url_scan(verdict="suspicious")
    assert "⚠️" in subject
    assert "Suspect" in plain


def test_url_scan_safe_verdict():
    _, subject, _, plain, _ = _call_url_scan(verdict="safe", threat_type=None)
    assert "✅" in subject
    assert "Sûr" in plain


def test_url_scan_unknown_verdict_falls_back_to_default_emoji_and_raw_label():
    _, subject, _, plain, _ = _call_url_scan(verdict="weird", threat_type=None)
    # default emoji from .get fallback
    assert "📋" in subject
    # verdict_fr falls back to the raw verdict string
    assert "weird" in plain


def test_url_scan_threat_type_mappings():
    for threat_type, label in [
        ("phishing", "Phishing"),
        ("malware", "Malware / Script malveillant"),
        ("redirect", "Redirection suspecte"),
        ("tracker", "Tracker / Iframe externe"),
        ("malicious_domain", "Domaine malveillant"),
    ]:
        _, _, _, plain, _ = _call_url_scan(threat_type=threat_type)
        assert label in plain


def test_url_scan_unknown_threat_type_maps_to_inconnu():
    _, _, _, plain, _ = _call_url_scan(threat_type="something-else")
    assert "Inconnu" in plain


def test_url_scan_none_threat_type_renders_dash_in_type_line():
    # When threat_type is None the Type line shows '—' (ternary in the f-string).
    _, _, _, plain, _ = _call_url_scan(threat_type=None)
    assert "Type         : —" in plain


def test_url_scan_findings_severity_icons_rendered():
    findings = [
        {"severity": "critical", "detail": "crit-item"},
        {"severity": "high", "detail": "high-item"},
        {"severity": "medium", "detail": "medium-item"},
        {"severity": "unknown", "detail": "other-item"},
    ]
    _, _, _, plain, _ = _call_url_scan(findings=findings)
    assert "🔴 crit-item" in plain
    assert "🟠 high-item" in plain
    assert "🟡 medium-item" in plain
    # unknown severity -> white circle fallback
    assert "⚪ other-item" in plain


def test_url_scan_findings_truncated_to_eight():
    findings = [{"severity": "medium", "detail": f"item-{i}"} for i in range(12)]
    _, _, _, plain, _ = _call_url_scan(findings=findings)
    assert "item-7" in plain  # 8th (index 7) included
    assert "item-8" not in plain  # 9th and beyond dropped


def test_url_scan_empty_findings_shows_no_suspicious_behavior_message():
    _, _, _, plain, _ = _call_url_scan(findings=[])
    assert "Aucun comportement suspect détecté." in plain


def test_url_scan_finding_missing_keys_uses_defaults():
    # finding without severity/detail keys -> ⚪ icon and empty detail, no crash
    _, _, _, plain, _ = _call_url_scan(findings=[{}])
    assert "⚪" in plain


def test_url_scan_subject_contains_score_and_truncated_url():
    long_url = "https://example.com/" + "a" * 100
    _, subject, _, _, _ = _call_url_scan(threat_score=42, scanned_url=long_url)
    assert "Score 42/100" in subject
    # URL truncated to 60 chars in subject (full URL is longer than that)
    assert long_url[:60] in subject
    assert long_url not in subject


def test_url_scan_recipient_and_html_wrapping():
    to_email, _, html, plain, _ = _call_url_scan()
    assert to_email == "user@example.com"
    assert html == f"<pre>{plain}</pre>"


# ─── send_campaign_complete ───────────────────────────────────────────────────


def _call_campaign(
    emails_sent=100,
    opened_count=50,
    clicked_count=20,
    submitted_count=5,
    campaign_name="Ma campagne",
):
    with patch(SEND) as mock_send:
        send_campaign_complete(
            to_email="owner@example.com",
            campaign_name=campaign_name,
            campaign_id=7,
            targets_count=120,
            emails_sent=emails_sent,
            opened_count=opened_count,
            clicked_count=clicked_count,
            submitted_count=submitted_count,
        )
    assert mock_send.called
    to_email, subject, html, plain = mock_send.call_args[0]
    return to_email, subject, html, plain, mock_send


def test_campaign_risk_high_at_30pct_click():
    # 40/100 = 40% click -> risque élevé + red
    _, _, html, plain, _ = _call_campaign(clicked_count=40)
    assert "Risque élevé" in html
    assert "#ef4444" in html


def test_campaign_risk_moderate_between_15_and_30():
    # 20/100 = 20% -> risque modéré + amber
    _, _, html, _, _ = _call_campaign(clicked_count=20)
    assert "Risque modéré" in html
    assert "#f59e0b" in html


def test_campaign_risk_low_when_some_clicks_below_15():
    # 5/100 = 5% -> risque faible + green
    _, _, html, _, _ = _call_campaign(clicked_count=5)
    assert "Risque faible" in html
    assert "#22c55e" in html


def test_campaign_no_click_label():
    _, _, html, _, _ = _call_campaign(clicked_count=0, submitted_count=0)
    assert "Aucun clic" in html


def test_campaign_zero_emails_sent_avoids_division_by_zero():
    # emails_sent == 0 -> all rates fall back to 0, no ZeroDivisionError
    _, subject, html, plain, _ = _call_campaign(
        emails_sent=0, opened_count=0, clicked_count=0, submitted_count=0
    )
    assert "0% de clic" in subject
    assert "Aucun clic" in html


def test_campaign_submitted_positive_uses_red_credential_color():
    _, _, html, _, _ = _call_campaign(submitted_count=3)
    # submitted_count > 0 -> red credential stat color
    assert "#ef4444" in html


def test_campaign_submitted_zero_uses_green_credential_color():
    # No clicks/submits -> credential color green (#22c55e also used by risk here)
    _, _, html, _, _ = _call_campaign(clicked_count=0, submitted_count=0)
    assert "#22c55e" in html


def test_campaign_subject_and_recipient():
    to_email, subject, _, _, _ = _call_campaign(campaign_name="Phish-Q1")
    assert to_email == "owner@example.com"
    assert "Phish-Q1" in subject
    assert subject.startswith("[Rocher Cybersécurité]")


def test_campaign_detail_url_contains_campaign_id():
    _, _, html, plain, _ = _call_campaign()
    assert "/phishing/campaigns/7" in html
    assert "/phishing/campaigns/7" in plain


# ─── send_contact_email ───────────────────────────────────────────────────────


def _call_contact(
    need_type="audit-flash",
    phone="0600000000",
    site_url="https://site.example",
    name="Alice",
    email="alice@example.com",
):
    with patch(SEND) as mock_send:
        send_contact_email(
            name=name,
            email=email,
            phone=phone,
            need_type=need_type,
            site_url=site_url,
            message="Bonjour, je souhaite un audit.",
            contact_email="owner@rocher.com",
        )
    return mock_send


def test_contact_sends_two_emails_owner_then_confirmation():
    mock_send = _call_contact()
    assert mock_send.call_count == 2
    # First call = owner notification (to contact_email)
    owner_call = mock_send.call_args_list[0][0]
    assert owner_call[0] == "owner@rocher.com"
    # Second call = confirmation to the sender
    confirm_call = mock_send.call_args_list[1][0]
    assert confirm_call[0] == "alice@example.com"
    assert "bien été reçu" in confirm_call[1]


def test_contact_need_type_label_mapping():
    for need_type, label in [
        ("audit-flash", "Audit Flash (290 € HT)"),
        ("audit-app", "Audit App-Check (725 € HT)"),
        ("pentest", "Pentest léger (1 900 € HT)"),
        ("simulation-phishing", "Simulation de phishing"),
        ("abonnement", "Abonnement surveillance continue"),
        ("autre", "Autre / Demande de devis"),
    ]:
        mock_send = _call_contact(need_type=need_type)
        owner_subject = mock_send.call_args_list[0][0][1]
        assert label in owner_subject


def test_contact_unknown_need_type_uses_raw_value():
    mock_send = _call_contact(need_type="mystere")
    owner_subject = mock_send.call_args_list[0][0][1]
    assert "mystere" in owner_subject


def test_contact_none_phone_and_site_render_dash():
    mock_send = _call_contact(phone=None, site_url=None)
    owner_plain = mock_send.call_args_list[0][0][3]
    assert "Tél.    : —" in owner_plain
    assert "Site    : —" in owner_plain


def test_contact_confirmation_failure_is_swallowed():
    # The owner email succeeds; the confirmation email raises -> caught and logged.
    def side_effect(to_email, *args, **kwargs):
        if to_email == "alice@example.com":
            raise RuntimeError("SMTP down")

    with patch(SEND, side_effect=side_effect) as mock_send:
        with patch("app.services.email_service.alerts.logger.warning") as mock_warn:
            # Must NOT raise despite the confirmation send failing.
            send_contact_email(
                name="Alice",
                email="alice@example.com",
                phone="0600000000",
                need_type="audit-flash",
                site_url="https://site.example",
                message="msg",
                contact_email="owner@rocher.com",
            )
    assert mock_send.call_count == 2
    assert mock_warn.called


def test_contact_owner_email_failure_propagates():
    # The owner email is sent outside the try/except -> a failure there propagates.
    with patch(SEND, side_effect=RuntimeError("boom")):
        raised = False
        try:
            send_contact_email(
                name="Alice",
                email="alice@example.com",
                phone=None,
                need_type="autre",
                site_url=None,
                message="msg",
                contact_email="owner@rocher.com",
            )
        except RuntimeError:
            raised = True
    assert raised


# ─── send_booking_confirmation ────────────────────────────────────────────────


def _call_booking_confirm(need_type="audit-flash"):
    with patch(SEND) as mock_send:
        send_booking_confirmation(
            to_email="client@example.com",
            name="Bob",
            date_label="lundi 5 mai",
            time_label="14h00",
            duration_minutes=45,
            slot_label="Créneau audit",
            need_type=need_type,
            cancel_url="https://rocher.com/cancel/abc",
        )
    assert mock_send.called
    to_email, subject, html, plain = mock_send.call_args[0]
    return to_email, subject, html, plain


def test_booking_confirmation_recipient_and_subject():
    to_email, subject, _, _ = _call_booking_confirm()
    assert to_email == "client@example.com"
    assert "Réservation confirmée" in subject
    assert "lundi 5 mai" in subject


def test_booking_confirmation_need_label_mapping():
    for need_type, label in [
        ("audit-flash", "Audit Flash"),
        ("audit-app", "Audit App-Check"),
        ("pentest", "Pentest léger"),
        ("abonnement", "Abonnement surveillance"),
        ("autre", "Autre / Devis"),
    ]:
        _, _, _, plain = _call_booking_confirm(need_type=need_type)
        assert label in plain


def test_booking_confirmation_unknown_need_type_uses_raw():
    _, _, _, plain = _call_booking_confirm(need_type="xyz")
    assert "xyz" in plain


def test_booking_confirmation_content_has_cancel_url_and_duration():
    _, _, html, plain = _call_booking_confirm()
    assert "https://rocher.com/cancel/abc" in html
    assert "45 min" in plain


# ─── send_booking_admin_notification ──────────────────────────────────────────


def _call_booking_admin(need_type="audit-flash", phone="0600000000", message="Merci"):
    with patch(SEND) as mock_send:
        send_booking_admin_notification(
            admin_email="admin@rocher.com",
            name="Carol",
            email="carol@example.com",
            phone=phone,
            date_label="mardi 6 mai",
            time_label="10h00",
            need_type=need_type,
            message=message,
        )
    assert mock_send.called
    to_email, subject, html, plain = mock_send.call_args[0]
    return to_email, subject, html, plain


def test_booking_admin_recipient_and_subject():
    to_email, subject, _, _ = _call_booking_admin()
    assert to_email == "admin@rocher.com"
    assert "Nouvelle réservation" in subject
    assert "Carol" in subject


def test_booking_admin_need_label_mapping():
    for need_type, label in [
        ("audit-flash", "Audit Flash (290 €)"),
        ("audit-app", "Audit App-Check (725 €)"),
        ("pentest", "Pentest léger (1 900 €)"),
        ("simulation-phishing", "Simulation de phishing"),
        ("abonnement", "Abonnement surveillance"),
        ("autre", "Autre / Devis"),
    ]:
        _, _, _, plain = _call_booking_admin(need_type=need_type)
        assert label in plain


def test_booking_admin_unknown_need_type_uses_raw():
    _, _, _, plain = _call_booking_admin(need_type="zzz")
    assert "zzz" in plain


def test_booking_admin_none_phone_and_message_render_dash():
    _, _, html, plain = _call_booking_admin(phone=None, message=None)
    assert "Tél.     : —" in plain
    assert "Message  : —" in plain
    assert "Message : —" in html
