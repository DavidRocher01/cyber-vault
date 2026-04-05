"""
Newsletter email service — welcome email + bi-weekly issue template.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def _send(to_email: str, subject: str, html: str, plain: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())


def send_newsletter_welcome(to_email: str, unsubscribe_url: str) -> None:
    """Welcome email sent on subscription."""
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#0e7490,#164e63);padding:32px 40px;text-align:center;">
          <p style="margin:0 0 8px;color:#67e8f9;font-size:13px;letter-spacing:2px;font-weight:bold;">🛰️ LE RADAR CYBER</p>
          <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:800;">Bienvenue à bord !</h1>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:40px;">
          <p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 20px;">
            Bonjour,<br><br>
            Vous êtes maintenant abonné(e) au <strong style="color:#22d3ee;">Radar Cyber</strong>, votre brief cybersécurité toutes les deux semaines.
          </p>

          <!-- What to expect -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
            <tr>
              <td width="33%" style="padding:16px;background:#0f172a;border-radius:8px;text-align:center;vertical-align:top;">
                <p style="margin:0 0 6px;font-size:24px;">🌍</p>
                <p style="margin:0;color:#22d3ee;font-size:12px;font-weight:bold;">FLASH INTERNATIONAL</p>
                <p style="margin:6px 0 0;color:#64748b;font-size:12px;">Une cyberattaque majeure décryptée</p>
              </td>
              <td width="4%"></td>
              <td width="33%" style="padding:16px;background:#0f172a;border-radius:8px;text-align:center;vertical-align:top;">
                <p style="margin:0 0 6px;font-size:24px;">💡</p>
                <p style="margin:0;color:#22d3ee;font-size:12px;font-weight:bold;">LE BON RÉFLEXE</p>
                <p style="margin:6px 0 0;color:#64748b;font-size:12px;">Un conseil pratique en 2 minutes</p>
              </td>
              <td width="4%"></td>
              <td width="33%" style="padding:16px;background:#0f172a;border-radius:8px;text-align:center;vertical-align:top;">
                <p style="margin:0 0 6px;font-size:24px;">⚖️</p>
                <p style="margin:0;color:#22d3ee;font-size:12px;font-weight:bold;">COIN DIRIGEANTS</p>
                <p style="margin:6px 0 0;color:#64748b;font-size:12px;">Réglementation & conformité</p>
              </td>
            </tr>
          </table>

          <p style="color:#94a3b8;font-size:14px;line-height:1.7;margin:20px 0 0;">
            La prochaine édition arrive dans <strong style="color:#f1f5f9;">moins de deux semaines</strong>.
            En attendant, découvrez nos ressources et bonnes pratiques sur
            <a href="{settings.FRONTEND_URL}/cyberscan/ressources" style="color:#22d3ee;text-decoration:none;">cyberscan.io</a>.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:24px 40px;border-top:1px solid #334155;text-align:center;">
          <p style="margin:0;color:#475569;font-size:12px;">
            CyberScan — Cybersécurité as a Service<br>
            <a href="{unsubscribe_url}" style="color:#475569;">Se désabonner</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    plain = f"""Bienvenue au Radar Cyber !

Vous recevrez votre brief cybersécurité toutes les deux semaines.

Au programme :
- Flash International : une cyberattaque majeure décryptée
- Le Bon Réflexe : un conseil pratique en 2 minutes
- Coin Dirigeants : réglementation & conformité

Ressources : {settings.FRONTEND_URL}/cyberscan/ressources

Se désabonner : {unsubscribe_url}
---
CyberScan — Cybersécurité as a Service
"""
    _send(to_email, "🛰️ Bienvenue au Radar Cyber !", html, plain)


def send_newsletter_issue(
    to_email: str,
    unsubscribe_url: str,
    edition: int,
    flash_title: str,
    flash_body: str,
    reflex_title: str,
    reflex_body: str,
    legal_title: str,
    legal_body: str,
) -> None:
    """Send a bi-weekly newsletter issue."""
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#0e7490,#164e63);padding:32px 40px;">
          <p style="margin:0 0 4px;color:#67e8f9;font-size:12px;letter-spacing:2px;">🛰️ LE RADAR CYBER · ÉDITION #{edition:03d}</p>
          <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:800;">Votre brief cybersécurité</h1>
          <p style="margin:8px 0 0;color:#94a3b8;font-size:13px;">Toutes les deux semaines — en 5 minutes chrono</p>
        </td></tr>

        <!-- Flash International -->
        <tr><td style="padding:32px 40px 0;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="4" style="background:#ef4444;border-radius:2px;"></td>
              <td style="padding-left:16px;">
                <p style="margin:0 0 4px;color:#ef4444;font-size:11px;font-weight:bold;letter-spacing:1px;">🌍 FLASH INTERNATIONAL</p>
                <h2 style="margin:0 0 12px;color:#f1f5f9;font-size:18px;">{flash_title}</h2>
                <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;">{flash_body}</p>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Divider -->
        <tr><td style="padding:24px 40px;"><hr style="border:none;border-top:1px solid #334155;"></td></tr>

        <!-- Le Bon Réflexe -->
        <tr><td style="padding:0 40px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="4" style="background:#22d3ee;border-radius:2px;"></td>
              <td style="padding-left:16px;">
                <p style="margin:0 0 4px;color:#22d3ee;font-size:11px;font-weight:bold;letter-spacing:1px;">💡 LE BON RÉFLEXE</p>
                <h2 style="margin:0 0 12px;color:#f1f5f9;font-size:18px;">{reflex_title}</h2>
                <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;">{reflex_body}</p>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Divider -->
        <tr><td style="padding:24px 40px;"><hr style="border:none;border-top:1px solid #334155;"></td></tr>

        <!-- Coin Dirigeants -->
        <tr><td style="padding:0 40px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="4" style="background:#a855f7;border-radius:2px;"></td>
              <td style="padding-left:16px;">
                <p style="margin:0 0 4px;color:#a855f7;font-size:11px;font-weight:bold;letter-spacing:1px;">⚖️ COIN DES DIRIGEANTS</p>
                <h2 style="margin:0 0 12px;color:#f1f5f9;font-size:18px;">{legal_title}</h2>
                <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;">{legal_body}</p>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- CTA -->
        <tr><td style="padding:0 40px 32px;text-align:center;">
          <a href="{settings.FRONTEND_URL}/cyberscan/dashboard"
             style="display:inline-block;background:#0891b2;color:#ffffff;text-decoration:none;padding:12px 32px;border-radius:8px;font-weight:bold;font-size:14px;">
            Accéder à mon dashboard →
          </a>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:24px 40px;border-top:1px solid #334155;text-align:center;">
          <p style="margin:0;color:#475569;font-size:12px;">
            CyberScan — Cybersécurité as a Service<br>
            <a href="{settings.FRONTEND_URL}/cyberscan/ressources" style="color:#475569;">Ressources</a> ·
            <a href="{settings.FRONTEND_URL}/cyberscan/bonnes-pratiques" style="color:#475569;">Bonnes pratiques</a> ·
            <a href="{unsubscribe_url}" style="color:#475569;">Se désabonner</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    plain = f"""🛰️ LE RADAR CYBER · Édition #{edition:03d}

🌍 FLASH INTERNATIONAL
{flash_title}
{flash_body}

💡 LE BON RÉFLEXE
{reflex_title}
{reflex_body}

⚖️ COIN DES DIRIGEANTS
{legal_title}
{legal_body}

→ Dashboard : {settings.FRONTEND_URL}/cyberscan/dashboard

Se désabonner : {unsubscribe_url}
---
CyberScan — Cybersécurité as a Service
"""
    _send(to_email, f"🛰️ Le Radar Cyber #{edition:03d}", html, plain)
