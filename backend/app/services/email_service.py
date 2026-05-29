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
    _html = f"<p>{plain.replace(chr(10), '<br>')}</p>"

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

                params["attachments"] = [
                    {
                        "filename": pdf_file.name,
                        "content": base64.b64encode(f.read()).decode(),
                    }
                ]
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
    verdict_fr = {
        "safe": "Sûr",
        "suspicious": "Suspect",
        "malicious": "Malveillant",
    }.get(verdict, verdict)
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
    subject = (
        f"[ScanURL] {verdict_emoji} {verdict_fr} — Score {threat_score}/100 — {scanned_url[:60]}"
    )
    html = f"<pre>{plain}</pre>"
    _send(to_email, subject, html, plain)


def send_ssl_expiry_alert(
    to_email: str,
    site_url: str,
    days_remaining: int,
    expiry_date: str,
    dashboard_url: str,
) -> None:
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

    subject = (
        f"[CyberScan] {emoji} Certificat SSL expirant dans {days_remaining} jour(s) — {site_url}"
    )
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
        "audit-flash": "Audit Flash (290 €)",
        "audit-app": "Audit App-Check (725 €)",
        "pentest": "Pentest léger (1 900 €)",
        "simulation-phishing": "Simulation de phishing",
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
        "audit-flash": "Audit Flash (290 € HT)",
        "audit-app": "Audit App-Check (725 € HT)",
        "pentest": "Pentest léger (1 900 € HT)",
        "simulation-phishing": "Simulation de phishing",
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
        _send(
            email,
            "[CyberScan] Votre message a bien été reçu",
            html_confirm,
            plain_confirm,
        )
    except Exception:
        pass  # Ne pas bloquer si la confirmation échoue


def send_monthly_digest(
    to_email: str,
    month_label: str,
    sites: list[dict],
    dashboard_url: str,
) -> None:
    """Send the monthly security digest to a paying user.

    Each dict in *sites* must have: url, overall_status (str|None),
    scans_count, critical_count, warning_count.
    """
    total_scans = sum(s["scans_count"] for s in sites)
    total_critical = sum(s["critical_count"] for s in sites)

    # ── Plain-text version ────────────────────────────────────────────────
    site_lines = ""
    for s in sites:
        status_str = s["overall_status"] or "—"
        site_lines += (
            f"\n  • {s['url']}\n"
            f"    Statut : {status_str}  |  Scans : {s['scans_count']}"
            f"  |  Critiques : {s['critical_count']}  |  Warnings : {s['warning_count']}\n"
        )

    plain = f"""Bonjour,

Voici votre bilan de sécurité CyberScan pour {month_label}.

━━━ Résumé global ━━━
  Sites surveillés : {len(sites)}
  Scans réalisés   : {total_scans}
  Failles critiques: {total_critical}

━━━ Détail par site ━━━{site_lines}
{"⚠️  Des failles critiques ont été détectées ce mois-ci. Consultez votre dashboard." if total_critical > 0 else "✅  Aucune faille critique ce mois-ci. Beau travail !"}

Accéder à votre dashboard : {dashboard_url}

---
CyberScan — Cybersécurité as a Service
Pour ne plus recevoir ce bilan, rendez-vous dans vos préférences de notification.
"""

    # ── HTML version ──────────────────────────────────────────────────────
    site_rows = ""
    for s in sites:
        status = s["overall_status"] or "—"
        status_color = (
            "#22c55e"
            if status == "OK"
            else "#eab308"
            if status == "WARNING"
            else "#ef4444"
            if status == "CRITICAL"
            else "#94a3b8"
        )
        crit_color = "#ef4444" if s["critical_count"] > 0 else "#94a3b8"
        site_rows += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;color:#e2e8f0;font-size:14px;">{s['url']}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;text-align:center;font-weight:700;color:{status_color};">{status}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;text-align:center;color:#94a3b8;">{s['scans_count']}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;text-align:center;font-weight:700;color:{crit_color};">{s['critical_count']}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;text-align:center;color:#eab308;">{s['warning_count']}</td>
        </tr>"""

    summary_color = "#ef4444" if total_critical > 0 else "#22c55e"
    summary_icon = "🚨" if total_critical > 0 else "✅"
    summary_text = (
        f"<strong style='color:#ef4444;'>{total_critical} faille(s) critique(s)</strong> détectée(s) ce mois. Consultez votre dashboard."
        if total_critical > 0
        else "Aucune faille critique ce mois-ci — beau travail !"
    )

    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
  <tr><td style="background:linear-gradient(135deg,#0891b222,#0891b211);padding:32px 40px;border-bottom:2px solid #0891b2;text-align:center;">
    <p style="margin:0 0 6px;color:#22d3ee;font-size:12px;font-weight:800;letter-spacing:2px;">BILAN MENSUEL</p>
    <h1 style="margin:0;color:#f8fafc;font-size:24px;">Votre sécurité en {month_label}</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;margin-bottom:24px;">
      <tr>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Sites</p>
          <p style="margin:4px 0 0;color:#f8fafc;font-size:28px;font-weight:800;">{len(sites)}</p>
        </td>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Scans</p>
          <p style="margin:4px 0 0;color:#f8fafc;font-size:28px;font-weight:800;">{total_scans}</p>
        </td>
        <td style="padding:16px;text-align:center;">
          <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Critiques</p>
          <p style="margin:4px 0 0;font-size:28px;font-weight:800;color:{summary_color};">{total_critical}</p>
        </td>
      </tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;margin-bottom:24px;">
      <thead>
        <tr style="background:#1e293b;">
          <th style="padding:10px 16px;text-align:left;color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;">Site</th>
          <th style="padding:10px 16px;text-align:center;color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;">Statut</th>
          <th style="padding:10px 16px;text-align:center;color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;">Scans</th>
          <th style="padding:10px 16px;text-align:center;color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;">Crit.</th>
          <th style="padding:10px 16px;text-align:center;color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;">Warn.</th>
        </tr>
      </thead>
      <tbody>{site_rows}</tbody>
    </table>
    <div style="background:{summary_color}22;border:1px solid {summary_color}44;border-radius:8px;padding:16px;margin-bottom:24px;text-align:center;">
      <p style="margin:0;color:#e2e8f0;font-size:14px;">{summary_icon} {summary_text}</p>
    </div>
    <div style="text-align:center;">
      <a href="{dashboard_url}" style="display:inline-block;background:#0891b2;color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:15px;">Voir mon dashboard</a>
    </div>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
    <p style="margin:0;color:#475569;font-size:12px;">CyberScan — Cybersécurité as a Service</p>
    <p style="margin:4px 0 0;color:#475569;font-size:11px;">Pour désactiver ce bilan, rendez-vous dans vos préférences de notification.</p>
  </td></tr>
</table></td></tr></table></body></html>"""

    subject = f"[CyberScan] Votre bilan de sécurité — {month_label}"
    _send(to_email, subject, html, plain)


def send_campaign_complete(
    to_email: str,
    campaign_name: str,
    campaign_id: int,
    targets_count: int,
    emails_sent: int,
    opened_count: int,
    clicked_count: int,
    submitted_count: int,
) -> None:
    open_rate = round(opened_count / emails_sent * 100) if emails_sent else 0
    click_rate = round(clicked_count / emails_sent * 100) if emails_sent else 0
    submit_rate = round(submitted_count / emails_sent * 100) if emails_sent else 0

    if click_rate >= 30:
        risk_label, risk_color = "Risque élevé", "#ef4444"
    elif click_rate >= 15:
        risk_label, risk_color = "Risque modéré", "#f59e0b"
    elif click_rate > 0:
        risk_label, risk_color = "Risque faible", "#22c55e"
    else:
        risk_label, risk_color = "Aucun clic", "#22c55e"

    from app.core.config import settings

    detail_url = f"{settings.FRONTEND_URL}/cyberscan/phishing/campaigns/{campaign_id}"

    plain = f"""Bonjour,

Votre campagne de simulation de phishing "{campaign_name}" est terminée.

━━━ Résultats ━━━
  Cibles         : {targets_count}
  Emails envoyés : {emails_sent}
  Taux d'ouverture : {open_rate}% ({opened_count} / {emails_sent})
  Taux de clic   : {click_rate}% ({clicked_count} / {emails_sent})
  Identifiants saisis : {submit_rate}% ({submitted_count} / {emails_sent})
  Niveau de risque : {risk_label}

Voir les résultats détaillés et télécharger le rapport PDF :
{detail_url}

---
CyberScan — Simulation de phishing
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
  <tr><td style="background:linear-gradient(135deg,#1e1b4b,#0f172a);padding:32px 40px;border-bottom:2px solid #4f46e5;text-align:center;border-radius:12px 12px 0 0;">
    <p style="margin:0 0 6px;color:#a5b4fc;font-size:12px;font-weight:800;letter-spacing:2px;">SIMULATION TERMINÉE ✓</p>
    <h1 style="margin:0;color:#f8fafc;font-size:22px;line-height:1.3;">{campaign_name}</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:10px;margin-bottom:24px;">
      <tr>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Cibles</p>
          <p style="margin:6px 0 0;color:#f8fafc;font-size:26px;font-weight:800;">{targets_count}</p>
        </td>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Ouvertures</p>
          <p style="margin:6px 0 0;color:#f8fafc;font-size:26px;font-weight:800;">{open_rate}<span style="font-size:14px;color:#94a3b8;">%</span></p>
        </td>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Clics</p>
          <p style="margin:6px 0 0;font-size:26px;font-weight:800;color:{risk_color};">{click_rate}<span style="font-size:14px;color:#94a3b8;">%</span></p>
        </td>
        <td style="padding:16px;text-align:center;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Identifiants</p>
          <p style="margin:6px 0 0;font-size:26px;font-weight:800;color:{'#ef4444' if submitted_count > 0 else '#22c55e'};">{submit_rate}<span style="font-size:14px;color:#94a3b8;">%</span></p>
        </td>
      </tr>
    </table>
    <div style="background:{risk_color}18;border:1px solid {risk_color}44;border-radius:8px;padding:14px 20px;margin-bottom:28px;display:flex;align-items:center;">
      <p style="margin:0;color:#e2e8f0;font-size:14px;">Niveau de risque : <strong style="color:{risk_color};">{risk_label}</strong> — basé sur {click_rate}% de taux de clic</p>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
      <a href="{detail_url}" style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:14px 36px;border-radius:8px;font-weight:700;font-size:15px;">Voir les résultats détaillés →</a>
    </td></tr></table>
    <p style="color:#475569;font-size:12px;text-align:center;margin:20px 0 0;">Le rapport PDF est disponible depuis la page de résultats.</p>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
    <p style="margin:0;color:#475569;font-size:12px;">CyberScan — Simulation de phishing</p>
  </td></tr>
</table></td></tr></table></body></html>"""

    subject = f"[CyberScan] Campagne terminée — {campaign_name} ({click_rate}% de clic)"
    _send(to_email, subject, html, plain)


def send_awareness_magic_link(
    to_email: str,
    first_name: str | None,
    org_name: str,
    login_url: str,
    token_ttl_minutes: int = 30,
) -> None:
    greeting = f"Bonjour{' ' + first_name if first_name else ''},"
    subject = f"[CyberScan] Votre lien de connexion — {org_name}"
    plain = f"""{greeting}

Vous avez été invité(e) à rejoindre la plateforme de sensibilisation NIS2 de {org_name}.

Cliquez sur le lien ci-dessous pour accéder à votre espace de formation (valable {token_ttl_minutes} minutes) :

{login_url}

Ce lien est personnel et à usage unique. Si vous n'avez pas demandé cet accès, ignorez cet email.

---
CyberScan — Sensibilisation NIS2
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#030712;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#030712;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:12px;border:1px solid #1f2937;">
  <tr><td style="background:linear-gradient(135deg,#0e7490,#1d4ed8);padding:32px 40px;border-radius:12px 12px 0 0;text-align:center;">
    <p style="margin:0 0 6px;color:#a5f3fc;font-size:12px;font-weight:800;letter-spacing:2px;">SENSIBILISATION NIS2</p>
    <h1 style="margin:0;color:#fff;font-size:22px;">Votre lien de connexion</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 8px;">{greeting}</p>
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 24px;">
      Vous avez été invité(e) à rejoindre la plateforme de formation cybersécurité de
      <strong style="color:#f9fafb;">{org_name}</strong>.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr><td align="center">
        <a href="{login_url}" style="display:inline-block;background:#0891b2;color:#fff;text-decoration:none;
        padding:14px 36px;border-radius:8px;font-weight:700;font-size:15px;">
          Accéder à ma formation
        </a>
      </td></tr>
    </table>
    <div style="background:#1f2937;border-radius:8px;padding:14px 18px;margin-bottom:20px;">
      <p style="margin:0;color:#6b7280;font-size:12px;word-break:break-all;">{login_url}</p>
    </div>
    <p style="color:#6b7280;font-size:12px;line-height:1.6;margin:0;">
      Ce lien est personnel, à usage unique et expire dans <strong style="color:#9ca3af;">{token_ttl_minutes} minutes</strong>.<br>
      Si vous n'avez pas demandé cet accès, ignorez cet email.
    </p>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #1f2937;text-align:center;">
    <p style="margin:0;color:#4b5563;font-size:12px;">CyberScan — Sensibilisation NIS2</p>
  </td></tr>
</table></td></tr></table></body></html>"""
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
