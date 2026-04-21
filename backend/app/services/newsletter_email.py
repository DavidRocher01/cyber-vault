"""
Newsletter email service — confirmation, welcome, unsubscribe, bi-weekly issue.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import resend

from app.core.config import settings

_HEADER_STYLE = "background:linear-gradient(135deg,#0e7490,#0c4a6e);padding:32px 40px;"
_CARD_BG = "background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155;"


def _footer(frontend: str, unsubscribe_url: str = "") -> str:
    unsub = (
        f' | <a href="{unsubscribe_url}" style="color:#475569;">Se desabonner</a>'
        if unsubscribe_url else ""
    )
    return (
        f'<tr><td style="padding:24px 40px;border-top:1px solid #334155;text-align:center;">'
        f'<p style="margin:0 0 4px;color:#475569;font-size:12px;">CyberScan — Cybersecurite as a Service</p>'
        f'<p style="margin:0;font-size:11px;">'
        f'<a href="{frontend}/cyberscan/ressources" style="color:#475569;">Ressources</a>{unsub}'
        f'</p></td></tr>'
    )


def _wrap(rows: str) -> str:
    return (
        '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">'
        '<tr><td align="center" style="padding:40px 20px;">'
        f'<table width="600" cellpadding="0" cellspacing="0" style="{_CARD_BG}">'
        f'{rows}'
        '</table></td></tr></table></body></html>'
    )


def _send(to_email: str, subject: str, html: str, plain: str) -> None:
    if settings.RESEND_API_KEY:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.RESEND_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": plain,
        })
        return
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


# ── 1. Confirmation email (double opt-in) ─────────────────────────────────────

def send_confirmation_email(to_email: str, confirm_url: str) -> None:
    rows = (
        f'<tr><td style="{_HEADER_STYLE}text-align:center;">'
        '<p style="margin:0 0 6px;color:#67e8f9;font-size:12px;letter-spacing:2px;">LE RADAR CYBER</p>'
        '<h1 style="margin:0;color:#fff;font-size:26px;">Confirmez votre inscription</h1>'
        '<p style="margin:8px 0 0;color:#94a3b8;font-size:13px;">Une derniere etape avant de rejoindre la communaute</p>'
        '</td></tr>'
        '<tr><td style="padding:40px;text-align:center;">'
        '<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 32px;">'
        'Bonjour,<br><br>'
        'Vous avez demande a vous inscrire au <strong style="color:#22d3ee;">Radar Cyber</strong>,'
        ' le brief bimensuel qui decrypte les cybermenaces mondiales en 5 minutes.<br><br>'
        'Cliquez sur le bouton ci-dessous pour confirmer votre adresse et activer votre abonnement.'
        '</p>'
        f'<a href="{confirm_url}"'
        ' style="display:inline-block;background:#0891b2;color:#fff;text-decoration:none;'
        'padding:14px 36px;border-radius:10px;font-weight:bold;font-size:15px;">'
        'Confirmer mon inscription'
        '</a>'
        '<p style="color:#475569;font-size:12px;margin:24px 0 0;">'
        "Lien valable 7 jours. Ignorez cet email si vous n'etes pas a l'origine de cette inscription."
        '</p>'
        '</td></tr>'
        + _footer(settings.FRONTEND_URL)
    )
    html = _wrap(rows)
    plain = "\n".join([
        "Confirmez votre inscription au Radar Cyber",
        "",
        f"Lien de confirmation : {confirm_url}",
        "",
        "Lien valable 7 jours.",
        "---",
        "CyberScan",
    ])
    _send(to_email, "Confirmez votre inscription au Radar Cyber", html, plain)


# ── 2. Welcome email (apres confirmation) ─────────────────────────────────────

def send_newsletter_welcome(to_email: str, unsubscribe_url: str) -> None:
    rows = (
        f'<tr><td style="{_HEADER_STYLE}text-align:center;">'
        '<p style="margin:0 0 6px;color:#67e8f9;font-size:12px;letter-spacing:2px;">LE RADAR CYBER</p>'
        '<h1 style="margin:0;color:#fff;font-size:28px;">Bienvenue a bord !</h1>'
        '<p style="margin:8px 0 0;color:#94a3b8;font-size:13px;">Votre inscription est confirmee</p>'
        '</td></tr>'
        '<tr><td style="padding:40px;">'
        '<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 24px;">'
        'Vous etes desormais abonne(e) au <strong style="color:#22d3ee;">Radar Cyber</strong>.'
        ' Toutes les deux semaines, un brief concis pour rester a la pointe des cybermenaces.'
        '</p>'
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">'
        '<tr>'
        '<td width="32%" style="padding:14px;background:#0f172a;border-radius:10px;text-align:center;vertical-align:top;">'
        '<p style="margin:0 0 6px;font-size:20px;">🌍</p>'
        '<p style="margin:0;color:#22d3ee;font-size:11px;font-weight:bold;">FLASH INTERNATIONAL</p>'
        '<p style="margin:4px 0 0;color:#64748b;font-size:12px;">Une attaque mondiale decryptee</p>'
        '</td>'
        '<td width="2%"></td>'
        '<td width="32%" style="padding:14px;background:#0f172a;border-radius:10px;text-align:center;vertical-align:top;">'
        '<p style="margin:0 0 6px;font-size:20px;">💡</p>'
        '<p style="margin:0;color:#22d3ee;font-size:11px;font-weight:bold;">LE BON REFLEXE</p>'
        '<p style="margin:4px 0 0;color:#64748b;font-size:12px;">Un conseil en 2 minutes</p>'
        '</td>'
        '<td width="2%"></td>'
        '<td width="32%" style="padding:14px;background:#0f172a;border-radius:10px;text-align:center;vertical-align:top;">'
        '<p style="margin:0 0 6px;font-size:20px;">⚖️</p>'
        '<p style="margin:0;color:#22d3ee;font-size:11px;font-weight:bold;">COIN DIRIGEANTS</p>'
        '<p style="margin:4px 0 0;color:#64748b;font-size:12px;">Reglementation et conformite</p>'
        '</td>'
        '</tr></table>'
        '<p style="color:#94a3b8;font-size:14px;line-height:1.7;">'
        'Prochaine edition dans <strong style="color:#f1f5f9;">moins de deux semaines</strong>.'
        f' Consultez nos <a href="{settings.FRONTEND_URL}/cyberscan/ressources" style="color:#22d3ee;">ressources</a> en attendant.'
        '</p>'
        '</td></tr>'
        + _footer(settings.FRONTEND_URL, unsubscribe_url)
    )
    html = _wrap(rows)
    plain = (
        "Bienvenue au Radar Cyber — Inscription confirmee !\n\n"
        "Vous recevrez votre brief cybersecurite toutes les deux semaines.\n\n"
        f"Se desabonner : {unsubscribe_url}\n---\nCyberScan"
    )
    _send(to_email, "Bienvenue au Radar Cyber — Inscription confirmee !", html, plain)


# ── 3. Unsubscribe confirmation ────────────────────────────────────────────────

def send_unsubscribe_confirmation(to_email: str) -> None:
    resubscribe_url = f"{settings.FRONTEND_URL}/cyberscan"
    rows = (
        f'<tr><td style="{_HEADER_STYLE}text-align:center;">'
        '<p style="margin:0 0 6px;color:#67e8f9;font-size:12px;letter-spacing:2px;">LE RADAR CYBER</p>'
        '<h1 style="margin:0;color:#fff;font-size:26px;">Desabonnement effectue</h1>'
        '</td></tr>'
        '<tr><td style="padding:40px;text-align:center;">'
        '<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 20px;">'
        'Votre desabonnement a bien ete pris en compte.<br>'
        'Vous ne recevrez plus les prochaines editions du Radar Cyber.'
        '</p>'
        '<p style="color:#64748b;font-size:13px;margin:0 0 24px;">'
        "Vous avez change d'avis ? Reabonnez-vous a tout moment."
        '</p>'
        f'<a href="{resubscribe_url}"'
        ' style="display:inline-block;background:#1e293b;color:#22d3ee;text-decoration:none;'
        'padding:12px 28px;border-radius:10px;font-size:14px;border:1px solid #0e7490;">'
        'Retourner sur CyberScan'
        '</a>'
        '</td></tr>'
        + _footer(settings.FRONTEND_URL)
    )
    html = _wrap(rows)
    plain = (
        "Desabonnement confirme.\n\n"
        "Vous avez ete desabonne(e) du Radar Cyber.\n"
        f"Reabonnez-vous sur : {resubscribe_url}\n---\nCyberScan"
    )
    _send(to_email, "Desabonnement confirme — Radar Cyber", html, plain)


# ── 4. Newsletter issue (articles) ────────────────────────────────────────────

def send_newsletter_articles(
    to_email: str,
    unsubscribe_url: str,
    edition: int,
    articles: list[dict],
) -> None:
    """articles: list of {actu_title, actu_url, actu_source, reflex}"""
    edition_str = f"{edition:03d}"
    article_rows = ""
    plain_articles = ""
    accent_colors = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6", "#a855f7"]
    for i, a in enumerate(articles, 1):
        color = accent_colors[(i - 1) % len(accent_colors)]
        image_block = (
            f'<a href="{a["actu_url"]}" style="display:block;">'
            f'<img src="{a["image_url"]}" alt="" width="556" style="display:block;width:100%;max-width:556px;height:200px;object-fit:cover;border-radius:0;">'
            f'</a>'
        ) if a.get("image_url") else ""
        article_rows += (
            f'<tr><td style="padding:0 28px 14px;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" style="border-radius:12px;overflow:hidden;border:1px solid #1e293b;">'
            # image optionnelle
            + (f'<tr><td style="padding:0;line-height:0;">{image_block}</td></tr>' if image_block else "")
            + f'<tr><td style="background:linear-gradient(135deg,#0f172a 0%,#0d1b2a 100%);padding:18px 22px 18px;">'
            # source + numéro
            f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td><span style="background:{color}22;color:{color};font-size:10px;font-weight:800;letter-spacing:2px;padding:4px 10px;border-radius:20px;">{a["actu_source"].upper()}</span></td>'
            f'<td align="right"><span style="color:#334155;font-size:12px;font-weight:700;">0{i}</span></td>'
            f'</tr></table>'
            # titre cliquable
            f'<a href="{a["actu_url"]}" style="display:block;margin:12px 0 8px;color:#f8fafc;font-size:16px;font-weight:800;text-decoration:none;line-height:1.45;letter-spacing:-0.2px;">'
            f'{a["actu_title"]}'
            f'</a>'
            # note
            f'<p style="margin:0 0 16px;color:#94a3b8;font-size:13px;line-height:1.65;">{a["reflex"]}</p>'
            # CTA
            f'<a href="{a["actu_url"]}" style="display:inline-block;background:{color};color:#fff;font-size:12px;font-weight:700;text-decoration:none;padding:8px 18px;border-radius:6px;letter-spacing:0.5px;">'
            f'Lire l\'article &rarr;'
            f'</a>'
            f'</td></tr>'
            f'</table>'
            f'</td></tr>'
        )
        plain_articles += f'{i}. [{a["actu_source"]}] {a["actu_title"]}\n   {a["reflex"]}\n   {a["actu_url"]}\n\n'

    rows = (
        f'<tr><td style="{_HEADER_STYLE}">'
        f'<p style="margin:0 0 6px;color:#67e8f9;font-size:11px;font-weight:700;letter-spacing:3px;">LE RADAR CYBER &middot; #{edition_str}</p>'
        '<h1 style="margin:0 0 8px;color:#fff;font-size:26px;font-weight:900;letter-spacing:-0.5px;">Votre brief cybersecurite</h1>'
        '<p style="margin:0;color:#94a3b8;font-size:13px;">Les actus qui comptent &mdash; en 5 minutes chrono</p>'
        '</td></tr>'
        '<tr><td style="padding:24px 28px 10px;">'
        '<p style="margin:0;color:#475569;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Au programme cette semaine</p>'
        '</td></tr>'
        + article_rows +
        '<tr><td style="padding:10px 28px 32px;text-align:center;">'
        f'<a href="{settings.FRONTEND_URL}/cyberscan/dashboard"'
        ' style="display:inline-block;background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;text-decoration:none;'
        'padding:13px 36px;border-radius:8px;font-weight:700;font-size:14px;letter-spacing:0.3px;">'
        'Acceder a mon tableau de bord &rarr;'
        '</a>'
        '</td></tr>'
        + _footer(settings.FRONTEND_URL, unsubscribe_url)
    )
    html = _wrap(rows)
    plain = (
        f"RADAR CYBER · Edition #{edition_str}\n\n"
        f"{plain_articles}"
        f"Dashboard : {settings.FRONTEND_URL}/cyberscan/dashboard\n"
        f"Se desabonner : {unsubscribe_url}\n---\nCyberScan"
    )
    _send(to_email, f"Le Radar Cyber #{edition_str}", html, plain)


# ── 5. Newsletter issue (legacy editorial) ────────────────────────────────────

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
    edition_str = f"{edition:03d}"
    rows = (
        f'<tr><td style="{_HEADER_STYLE}">'
        f'<p style="margin:0 0 4px;color:#67e8f9;font-size:12px;letter-spacing:2px;">LE RADAR CYBER · EDITION #{edition_str}</p>'
        '<h1 style="margin:0;color:#fff;font-size:24px;">Votre brief cybersecurite</h1>'
        '<p style="margin:8px 0 0;color:#94a3b8;font-size:13px;">Toutes les deux semaines — 5 minutes chrono</p>'
        '</td></tr>'
        '<tr><td style="padding:28px 40px 0;">'
        '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
        '<td width="4" style="background:#ef4444;border-radius:2px;"></td>'
        '<td style="padding-left:16px;">'
        '<p style="margin:0 0 4px;color:#ef4444;font-size:11px;font-weight:bold;letter-spacing:1px;">🌍 FLASH INTERNATIONAL</p>'
        f'<h2 style="margin:0 0 10px;color:#f1f5f9;font-size:17px;">{flash_title}</h2>'
        f'<p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;">{flash_body}</p>'
        '</td></tr></table>'
        '</td></tr>'
        '<tr><td style="padding:18px 40px;"><hr style="border:none;border-top:1px solid #334155;"></td></tr>'
        '<tr><td style="padding:0 40px;">'
        '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
        '<td width="4" style="background:#22d3ee;border-radius:2px;"></td>'
        '<td style="padding-left:16px;">'
        '<p style="margin:0 0 4px;color:#22d3ee;font-size:11px;font-weight:bold;letter-spacing:1px;">💡 LE BON REFLEXE</p>'
        f'<h2 style="margin:0 0 10px;color:#f1f5f9;font-size:17px;">{reflex_title}</h2>'
        f'<p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;">{reflex_body}</p>'
        '</td></tr></table>'
        '</td></tr>'
        '<tr><td style="padding:18px 40px;"><hr style="border:none;border-top:1px solid #334155;"></td></tr>'
        '<tr><td style="padding:0 40px;">'
        '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
        '<td width="4" style="background:#a855f7;border-radius:2px;"></td>'
        '<td style="padding-left:16px;">'
        '<p style="margin:0 0 4px;color:#a855f7;font-size:11px;font-weight:bold;letter-spacing:1px;">⚖️ COIN DES DIRIGEANTS</p>'
        f'<h2 style="margin:0 0 10px;color:#f1f5f9;font-size:17px;">{legal_title}</h2>'
        f'<p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;">{legal_body}</p>'
        '</td></tr></table>'
        '</td></tr>'
        '<tr><td style="padding:28px 40px;text-align:center;">'
        f'<a href="{settings.FRONTEND_URL}/cyberscan/dashboard"'
        ' style="display:inline-block;background:#0891b2;color:#fff;text-decoration:none;'
        'padding:12px 32px;border-radius:8px;font-weight:bold;font-size:14px;">'
        'Acceder a mon dashboard'
        '</a>'
        '</td></tr>'
        + _footer(settings.FRONTEND_URL, unsubscribe_url)
    )
    html = _wrap(rows)
    plain = (
        f"RADAR CYBER · Edition #{edition_str}\n\n"
        f"FLASH: {flash_title}\n{flash_body}\n\n"
        f"REFLEXE: {reflex_title}\n{reflex_body}\n\n"
        f"DIRIGEANTS: {legal_title}\n{legal_body}\n\n"
        f"Dashboard : {settings.FRONTEND_URL}/cyberscan/dashboard\n"
        f"Se desabonner : {unsubscribe_url}\n---\nCyberScan"
    )
    _send(to_email, f"Le Radar Cyber #{edition_str}", html, plain)
