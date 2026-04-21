"""
Email service — sends transactional emails via Resend.
Falls back to SMTP if RESEND_API_KEY is not set (local dev).
"""

import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import resend

from app.core.config import settings


def _send_via_resend(to_email: str, subject: str, html: str, plain: str) -> None:
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.RESEND_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": plain,
    })


def _send_via_smtp(to_email: str, subject: str, html: str, plain: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from_address
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.smtp_from_address, to_email, msg.as_string())


def _send(to_email: str, subject: str, html: str, plain: str) -> None:
    if settings.RESEND_API_KEY:
        _send_via_resend(to_email, subject, html, plain)
    else:
        _send_via_smtp(to_email, subject, html, plain)


def send_scan_report(
    to_email: str,
    site_url: str,
    overall_status: str,
    pdf_path: str,
) -> None:
    status_emoji = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(overall_status, "📋")
    subject = f"[CyberScan] Rapport de scan — {site_url} {status_emoji}"
    plain = f"""Bonjour,

Votre rapport de sécurité mensuel pour {site_url} est disponible.

Résultat global : {overall_status} {status_emoji}

Retrouvez le rapport détaillé en pièce jointe.

---
CyberScan — Cybersécurité as a Service
"""
    html = f"<p>{plain.replace(chr(10), '<br>')}</p>"

    if settings.RESEND_API_KEY:
        resend.api_key = settings.RESEND_API_KEY
        params: dict = {
            "from": settings.RESEND_FROM,
            "to": [to_email],
            "subject": subject,
            "text": plain,
        }
        pdf_file = Path(pdf_path).resolve()
        if pdf_file.exists():
            with open(pdf_file, "rb") as f:
                import base64
                params["attachments"] = [{
                    "filename": pdf_file.name,
                    "content": base64.b64encode(f.read()).decode(),
                }]
        resend.Emails.send(params)
        return

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from_address
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    pdf_file = Path(pdf_path).resolve()
    if pdf_file.exists() and pdf_file.is_file():
        with open(pdf_file, "rb") as f:  # nosec B open
            part = MIMEApplication(f.read(), Name=pdf_file.name)
            part["Content-Disposition"] = f'attachment; filename="{pdf_file.name}"'
            msg.attach(part)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.smtp_from_address, to_email, msg.as_string())


def send_url_scan_alert(
    to_email: str,
    scanned_url: str,
    verdict: str,
    threat_score: int,
    threat_type: str | None,
    findings: list[dict],
    dashboard_url: str,
) -> None:
    verdict_emoji = {"safe": "✅", "suspicious": "⚠️", "malicious": "🚨"}.get(verdict, "📋")
    verdict_fr = {"safe": "Sûr", "suspicious": "Suspect", "malicious": "Malveillant"}.get(verdict, verdict)
    threat_fr = {
        "phishing": "Phishing",
        "malware": "Malware / Script malveillant",
        "redirect": "Redirection suspecte",
        "tracker": "Tracker / Iframe externe",
        "malicious_domain": "Domaine malveillant",
    }.get(threat_type or "", "Inconnu")

    findings_lines = ""
    for f in findings[:8]:
        sev = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(f.get("severity", ""), "⚪")
        findings_lines += f"  {sev} {f.get('detail', '')}\n"

    plain = f"""Bonjour,

L'analyse de l'URL suivante vient de se terminer :

  URL analysée : {scanned_url}
  Verdict      : {verdict_fr} {verdict_emoji}
  Score        : {threat_score}/100
  Type         : {threat_fr if threat_type else '—'}

━━━ Comportements détectés ━━━
{findings_lines if findings_lines else '  Aucun comportement suspect détecté.'}

━━━ Actions rapides ━━━
  Accéder au rapport complet : {dashboard_url}

---
CyberScan — Cybersécurité as a Service
"""
    subject = f"[ScanURL] {verdict_emoji} {verdict_fr} — Score {threat_score}/100 — {scanned_url[:60]}"
    html = f"<pre>{plain}</pre>"
    _send(to_email, subject, html, plain)


def send_password_reset(to_email: str, reset_url: str) -> None:
    plain = f"""Bonjour,

Vous avez demandé la réinitialisation de votre mot de passe CyberScan.

Cliquez sur le lien ci-dessous pour choisir un nouveau mot de passe (valable 30 minutes) :

{reset_url}

Si vous n'avez pas fait cette demande, ignorez cet email — votre mot de passe reste inchangé.

---
CyberScan — Cybersécurité as a Service
"""
    html = f'<p>Bonjour,</p><p>Cliquez ici pour réinitialiser votre mot de passe (valable 30 minutes) :</p><p><a href="{reset_url}">{reset_url}</a></p>'
    _send(to_email, "[CyberScan] Réinitialisation de votre mot de passe", html, plain)
