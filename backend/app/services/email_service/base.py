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


def gabarit_html(titre: str, corps: str, cta_libelle: str = "", cta_url: str = "") -> str:
    """Enveloppe `corps` dans la mise en page HTML commune des e-mails.

    Reprend la structure deja utilisee par les alertes (table de 600 px, carte
    sombre, bouton ancre) pour que tous les envois se ressemblent.

    Existe parce que deux e-mails de scan fabriquaient leur « HTML » ainsi :

        html = f"<p>{plain.replace(chr(10), '<br>')}</p>"

    C'est-a-dire le texte brut enveloppe dans un paragraphe. Le message n'avait
    donc ni structure, ni lien ancre : les URL y figuraient en clair, dont une
    longue avec un jeton opaque — exactement la forme d'un lien d'hameconnage.
    C'est l'un des signaux qui ont envoye le rapport de scan en indesirable.
    """
    bouton = ""
    if cta_libelle and cta_url:
        bouton = (
            f'<div style="text-align:center;margin:28px 0 4px;">'
            f'<a href="{cta_url}" style="display:inline-block;background:#0891b2;'
            f"color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;"
            f'font-weight:700;font-size:15px;">{cta_libelle}</a></div>'
        )
    return f"""<!DOCTYPE html><html lang="fr"><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:32px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
  <tr><td style="background:#0f0a28;padding:24px 40px;border-bottom:2px solid #0891b2;border-radius:12px 12px 0 0;">
    <span style="color:#ffffff;font-size:19px;font-weight:700;">Rocher Cybersécurité</span>
  </td></tr>
  <tr><td style="padding:32px 40px;color:#e2e8f0;font-size:15px;line-height:1.6;">
    <h1 style="margin:0 0 20px;color:#ffffff;font-size:20px;">{titre}</h1>
    {corps}
    {bouton}
  </td></tr>
  <tr><td style="padding:18px 40px 28px;border-top:1px solid #334155;color:#94a3b8;font-size:12px;line-height:1.5;">
    Rocher Cybersécurité — Cybersécurité as a Service<br>
    <a href="{settings.FRONTEND_URL}" style="color:#22d3ee;text-decoration:none;">{settings.FRONTEND_URL}</a>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def _send_via_resend(
    to_email: str, subject: str, html: str, plain: str, desinscription: str = ""
) -> None:
    resend.api_key = settings.RESEND_API_KEY
    params: dict = {
        "from": settings.RESEND_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": plain,
    }
    if desinscription:
        # Gmail et Yahoo attendent cet en-tete depuis 2024 et penalisent son
        # absence, y compris sur des messages transactionnels qui comportent une
        # part promotionnelle — ce qui est le cas du rapport de scan gratuit.
        params["headers"] = {
            "List-Unsubscribe": f"<{desinscription}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    resend.Emails.send(params)


def _send_via_smtp(
    to_email: str, subject: str, html: str, plain: str, desinscription: str = ""
) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from_address
    msg["To"] = to_email
    msg["Subject"] = subject
    if desinscription:
        msg["List-Unsubscribe"] = f"<{desinscription}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.smtp_from_address, to_email, msg.as_string())


def _send(to_email: str, subject: str, html: str, plain: str, desinscription: str = "") -> None:
    if settings.RESEND_API_KEY:
        _send_via_resend(to_email, subject, html, plain, desinscription)
    else:
        _send_via_smtp(to_email, subject, html, plain, desinscription)
