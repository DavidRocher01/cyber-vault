"""Emails liés aux scans : rapport scan, alerte SSL, digest mensuel."""

import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import resend

from app.core.config import settings

from .base import _send


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
