"""
Email service — sends scan report PDF by email.
Uses SMTP settings from .env
"""

import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.core.config import settings


def send_scan_report(
    to_email: str,
    site_url: str,
    overall_status: str,
    pdf_path: str,
) -> None:
    """
    Send the PDF scan report to the client by email.

    Args:
        to_email:       Recipient email address.
        site_url:       The scanned URL (for subject/body).
        overall_status: OK | WARNING | CRITICAL
        pdf_path:       Absolute path to the generated PDF.
    """
    status_emoji = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(overall_status, "📋")

    msg = MIMEMultipart()
    msg["From"]    = settings.SMTP_FROM
    msg["To"]      = to_email
    msg["Subject"] = f"[CyberScan] Rapport de scan — {site_url} {status_emoji}"

    body = f"""Bonjour,

Votre rapport de sécurité mensuel pour {site_url} est disponible.

Résultat global : {overall_status} {status_emoji}

Retrouvez le rapport détaillé en pièce jointe.

---
CyberScan — Cybersécurité as a Service
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach PDF — resolve to prevent any path traversal (pdf_path comes from internal scan service)
    pdf_file = Path(pdf_path).resolve()
    if pdf_file.exists() and pdf_file.is_file():
        with open(pdf_file, "rb") as f:  # nosec B open
            part = MIMEApplication(f.read(), Name=pdf_file.name)
            part["Content-Disposition"] = f'attachment; filename="{pdf_file.name}"'
            msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())


def send_url_scan_alert(
    to_email: str,
    scanned_url: str,
    verdict: str,
    threat_score: int,
    threat_type: str | None,
    findings: list[dict],
    dashboard_url: str,
) -> None:
    """Send an alert email after a suspicious URL scan completes."""
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

    body = f"""Bonjour,

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

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = f"[ScanURL] {verdict_emoji} {verdict_fr} — Score {threat_score}/100 — {scanned_url[:60]}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())


def send_password_reset(to_email: str, reset_url: str) -> None:
    """Send a password-reset link to the user."""
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = "[CyberScan] Réinitialisation de votre mot de passe"

    body = f"""Bonjour,

Vous avez demandé la réinitialisation de votre mot de passe CyberScan.

Cliquez sur le lien ci-dessous pour choisir un nouveau mot de passe (valable 30 minutes) :

{reset_url}

Si vous n'avez pas fait cette demande, ignorez cet email — votre mot de passe reste inchangé.

---
CyberScan — Cybersécurité as a Service
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
