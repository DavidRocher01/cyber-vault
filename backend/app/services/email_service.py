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

    # Attach PDF
    pdf_file = Path(pdf_path)
    if pdf_file.exists():
        with open(pdf_file, "rb") as f:
            part = MIMEApplication(f.read(), Name=pdf_file.name)
            part["Content-Disposition"] = f'attachment; filename="{pdf_file.name}"'
            msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
