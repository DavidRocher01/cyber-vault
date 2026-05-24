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


def send_booking_confirmation(
    to_email: str,
    name: str,
    date_label: str,
    time_label: str,
    duration_minutes: int,
    slot_label: str,
    need_type: str,
    cancel_url: str,
) -> None:
    need_labels = {
        "audit-flash": "Audit Flash",
        "audit-app": "Audit App-Check",
        "pentest": "Pentest léger",
        "abonnement": "Abonnement surveillance",
        "autre": "Autre / Devis",
    }
    need_label = need_labels.get(need_type, need_type)
    subject = f"[CyberScan] Réservation confirmée — {date_label} à {time_label}"
    plain = f"""Bonjour {name},

Votre rendez-vous est confirmé :

  Date     : {date_label}
  Heure    : {time_label} ({duration_minutes} min)
  Objet    : {slot_label}
  Prestation : {need_label}

Pour annuler votre réservation :
{cancel_url}

À bientôt,
David Rocher — CyberScan
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,#065f46,#0369a1);padding:28px 40px;border-radius:12px 12px 0 0;text-align:center;">
<p style="margin:0 0 4px;color:#6ee7b7;font-size:12px;font-weight:700;letter-spacing:2px;">RÉSERVATION CONFIRMÉE ✓</p>
<h1 style="margin:0;color:#fff;font-size:22px;">{slot_label}</h1>
</td></tr>
<tr><td style="padding:32px 40px;">
<p style="color:#94a3b8;font-size:15px;margin:0 0 24px;">Bonjour <strong style="color:#f8fafc;">{name}</strong>,</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;padding:20px;margin-bottom:24px;">
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">DATE</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:16px;font-weight:700;">{date_label}</p>
</td></tr>
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">HEURE</p>
  <p style="margin:4px 0 0;color:#22d3ee;font-size:16px;font-weight:700;">{time_label} ({duration_minutes} min)</p>
</td></tr>
<tr><td style="padding:8px 0;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">PRESTATION</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{need_label}</p>
</td></tr>
</table>
<p style="color:#64748b;font-size:13px;line-height:1.7;margin:0 0 24px;">
Pour annuler votre réservation, cliquez ci-dessous (jusqu'à 24h avant le rendez-vous).
</p>
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<a href="{cancel_url}" style="display:inline-block;background:#475569;color:#fff;text-decoration:none;
padding:11px 24px;border-radius:8px;font-size:13px;">Annuler ma réservation</a>
</td></tr></table>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
<p style="margin:0;color:#475569;font-size:12px;">David Rocher — CyberScan · Trévoux (01)</p>
</td></tr>
</table></td></tr></table></body></html>"""
    _send(to_email, subject, html, plain)


def send_booking_admin_notification(
    admin_email: str,
    name: str,
    email: str,
    phone: str | None,
    date_label: str,
    time_label: str,
    need_type: str,
    message: str | None,
) -> None:
    need_labels = {
        "audit-flash": "Audit Flash (245 €)",
        "audit-app": "Audit App-Check (725 €)",
        "pentest": "Pentest léger (1 900 €)",
        "abonnement": "Abonnement surveillance",
        "autre": "Autre / Devis",
    }
    need_label = need_labels.get(need_type, need_type)
    subject = f"[CyberScan] Nouvelle réservation — {name} le {date_label} à {time_label}"
    plain = f"""Nouvelle réservation

  Nom      : {name}
  Email    : {email}
  Tél.     : {phone or '—'}
  Date     : {date_label} à {time_label}
  Prestation : {need_label}
  Message  : {message or '—'}

Répondre à : {email}
"""
    html = f"""<p>Nouvelle réservation de <strong>{name}</strong> ({email})<br>
Le <strong>{date_label} à {time_label}</strong> — {need_label}</p>
<p>Message : {message or '—'}</p>
<p><a href="mailto:{email}">Répondre</a></p>"""
    _send(admin_email, subject, html, plain)


def send_contact_email(
    name: str,
    email: str,
    phone: str | None,
    need_type: str,
    site_url: str | None,
    message: str,
    contact_email: str,
) -> None:
    need_labels = {
        "audit-flash": "Audit Flash (245 € HT)",
        "audit-app": "Audit App-Check (725 € HT)",
        "pentest": "Pentest léger (1 900 € HT)",
        "abonnement": "Abonnement surveillance continue",
        "autre": "Autre / Demande de devis",
    }
    need_label = need_labels.get(need_type, need_type)

    subject = f"[CyberScan Contact] {need_label} — {name} <{email}>"

    plain_owner = f"""Nouvelle demande de contact via CyberScan

Nom     : {name}
Email   : {email}
Tél.    : {phone or '—'}
Besoin  : {need_label}
Site    : {site_url or '—'}

Message :
{message}

---
Répondre à : {email}
"""
    html_owner = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,#0e7490,#0369a1);padding:28px 40px;border-radius:12px 12px 0 0;">
<h1 style="margin:0;color:#fff;font-size:20px;">Nouvelle demande de contact</h1>
<p style="margin:6px 0 0;color:#bae6fd;font-size:13px;">{need_label}</p>
</td></tr>
<tr><td style="padding:32px 40px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;padding:20px;margin-bottom:24px;">
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">NOM</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{name}</p>
</td></tr>
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">EMAIL</p>
  <p style="margin:4px 0 0;color:#22d3ee;font-size:15px;"><a href="mailto:{email}" style="color:#22d3ee;">{email}</a></p>
</td></tr>
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">TÉLÉPHONE</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{phone or '—'}</p>
</td></tr>
<tr><td style="padding:8px 0;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">SITE / URL</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{site_url or '—'}</p>
</td></tr>
</table>
<p style="color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;margin:0 0 8px;">MESSAGE</p>
<div style="background:#0f172a;border-radius:8px;padding:16px;color:#cbd5e1;font-size:14px;line-height:1.7;white-space:pre-wrap;">{message}</div>
<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:28px;"><tr><td>
<a href="mailto:{email}" style="display:inline-block;background:#0e7490;color:#fff;text-decoration:none;
padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px;">Répondre à {name} →</a>
</td></tr></table>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
<p style="margin:0;color:#475569;font-size:12px;">CyberScan — Formulaire de contact</p>
</td></tr>
</table></td></tr></table></body></html>"""

    _send(contact_email, subject, html_owner, plain_owner)

    # Confirmation to sender
    plain_confirm = f"""Bonjour {name},

Votre message a bien été reçu. Je reviendrai vers vous sous 4 h (jours ouvrés 9h–18h).

Récapitulatif de votre demande :
  Type : {need_label}
  Site : {site_url or '—'}

---
CyberScan
contact@cyberscanapp.com
"""
    html_confirm = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,#0e7490,#0369a1);padding:28px 40px;border-radius:12px 12px 0 0;text-align:center;">
<h1 style="margin:0;color:#fff;font-size:22px;">Message bien reçu ✓</h1>
</td></tr>
<tr><td style="padding:32px 40px;">
<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 20px;">
Bonjour <strong style="color:#f8fafc;">{name}</strong>,
</p>
<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 20px;">
Votre demande concernant <strong style="color:#22d3ee;">{need_label}</strong> a bien été reçue.
Je vous répondrai sous <strong style="color:#f8fafc;">4 heures</strong> (jours ouvrés, 9h–18h).
</p>
<p style="color:#475569;font-size:13px;line-height:1.7;margin:0;">
CyberScan<br>
<a href="mailto:contact@cyberscanapp.com" style="color:#22d3ee;">contact@cyberscanapp.com</a>
</p>
</td></tr>
</table></td></tr></table></body></html>"""

    try:
        _send(email, "[CyberScan] Votre message a bien été reçu", html_confirm, plain_confirm)
    except Exception:
        pass  # Ne pas bloquer si la confirmation échoue


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
