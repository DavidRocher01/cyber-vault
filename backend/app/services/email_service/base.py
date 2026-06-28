"""
Transport layer — _send, _send_via_resend, _send_via_smtp.
All other sub-modules import _send from here; nothing else should call the
transport functions directly.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import resend

from app.core.config import settings


def _send_via_resend(to_email: str, subject: str, html: str, plain: str) -> None:
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(
        {
            "from": settings.RESEND_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": plain,
        }
    )


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
