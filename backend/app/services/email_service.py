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


def send_ssl_expiry_alert(to_email: str, site_url: str, days_remaining: int, expiry_date: str, dashboard_url: str) -> None:
    if days_remaining <= 7:
        urgency = "CRITIQUE"
        color = "#ef4444"
        emoji = "🚨"
    elif days_remaining <= 14:
        urgency = "URGENT"
        color = "#f97316"
        emoji = "⚠️"
    else:
        urgency = "ATTENTION"
        color = "#eab308"
        emoji = "⚠️"

    subject = f"[CyberScan] {emoji} Certificat SSL expirant dans {days_remaining} jour(s) — {site_url}"
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,{color}22,{color}11);padding:32px 40px;border-bottom:2px solid {color};text-align:center;">
<p style="margin:0 0 6px;color:{color};font-size:12px;font-weight:800;letter-spacing:2px;">{urgency} — CERTIFICAT SSL</p>
<h1 style="margin:0;color:#f8fafc;font-size:24px;">Votre certificat expire bientôt</h1>
</td></tr>
<tr><td style="padding:32px 40px;">
<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 24px;">
Le certificat SSL de <strong style="color:#f8fafc;">{site_url}</strong> expire dans
<strong style="color:{color};font-size:18px;"> {days_remaining} jour(s)</strong> (le {expiry_date}).
</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;padding:20px;margin-bottom:24px;">
<tr><td>
<p style="margin:0 0 8px;color:#475569;font-size:11px;font-weight:700;letter-spacing:2px;">SITE CONCERNÉ</p>
<p style="margin:0;color:#22d3ee;font-size:15px;font-weight:700;">{site_url}</p>
</td></tr>
<tr><td style="padding-top:12px;">
<p style="margin:0 0 8px;color:#475569;font-size:11px;font-weight:700;letter-spacing:2px;">DATE D'EXPIRATION</p>
<p style="margin:0;color:{color};font-size:15px;font-weight:700;">{expiry_date}</p>
</td></tr>
</table>
<p style="color:#64748b;font-size:13px;line-height:1.7;margin:0 0 28px;">
Renouvelez votre certificat auprès de votre hébergeur ou via Let's Encrypt avant cette date pour éviter
une interruption de service et des alertes de sécurité chez vos visiteurs.
</p>
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<a href="{dashboard_url}" style="display:inline-block;background:{color};color:#fff;text-decoration:none;
padding:13px 36px;border-radius:8px;font-weight:700;font-size:14px;">
Voir le rapport SSL →
</a>
</td></tr></table>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
<p style="margin:0;color:#475569;font-size:12px;">CyberScan — Cybersécurité as a Service</p>
</td></tr>
</table></td></tr></table></body></html>"""

    plain = f"""{emoji} Certificat SSL expirant dans {days_remaining} jour(s)

Site : {site_url}
Expiration : {expiry_date}

Renouvelez votre certificat avant cette date.
Tableau de bord : {dashboard_url}

---
CyberScan
"""
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
