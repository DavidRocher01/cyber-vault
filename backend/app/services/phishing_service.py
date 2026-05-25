"""
Phishing simulation engine — homemade, no GoPhish required.

Architecture:
  - Emails sent via Resend (already in requirements) with per-target tracking IDs
  - Tracking pixel / click / landing pages served by this FastAPI backend
  - APScheduler sends emails in batches (PHISHING_BATCH_SIZE every 15 min)
  - Results stored directly in phishing_targets rows (no external API polling)

URL scheme for tracking routes (all public, no auth):
  GET  /phishing/t/{tracking_id}/px    → 1×1 transparent GIF, marks "opened"
  GET  /phishing/t/{tracking_id}/c     → redirects to landing page, marks "clicked"
  GET  /phishing/t/{tracking_id}/l     → serves phishing landing page HTML
  POST /phishing/t/{tracking_id}/s     → records form submission, returns awareness page
"""

import csv
import io
import json
import random
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

import resend
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.phishing import PhishingCampaign, PhishingDomainVerification, PhishingTarget

# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------

def _email_wrap(preheader: str, brand_bg: str, brand_html: str, body_html: str, footer_html: str = "") -> str:
    if not footer_html:
        footer_html = '<p style="color:#aaa;font-size:11px;margin:0">Message automatique — ne pas répondre.</p>'
    filler = "&nbsp;&#8203;" * 40
    return (
        '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title></title></head>'
        f'<body style="margin:0;padding:0;background:#f1f3f4;font-family:Arial,Helvetica,sans-serif">'
        f'<span style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#f1f3f4">{preheader}{filler}</span>'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f3f4;padding:24px 0">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:4px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.12)">'
        f'<tr><td style="background:{brand_bg};padding:18px 30px">{brand_html}</td></tr>'
        f'<tr><td style="padding:30px 30px 24px">{body_html}</td></tr>'
        f'<tr><td style="background:#f8f9fa;padding:18px 30px;border-top:1px solid #e8eaed">{footer_html}</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def _dynamic_ctx(target: Any, scenario_key: str) -> dict[str, Any]:
    rng = random.Random(f"{getattr(target, 'id', 0) or 0}-{scenario_key}")
    now = datetime.now(timezone.utc)
    y = now.year
    months = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
    day = rng.randint(5, 25)
    month = months[(now.month) % 12]
    return {
        "invoice_ref":    f"INV-{y}-{rng.randint(1000, 9999)}",
        "invoice_amount": f"{rng.randint(500, 9_999):,}".replace(",", " ") + " €",
        "ceo_amount":     rng.choice(["15 000 €","22 000 €","35 000 €","48 500 €"]),
        "ceo_deadline":   rng.choice(["avant 14h00","avant 16h00","avant 17h30","avant 18h00"]),
        "bank_last4":     str(rng.randint(1000, 9999)),
        "bank_name":      rng.choice(["Société Générale","BNP Paribas","La Banque Postale","Crédit Mutuel","CIC"]),
        "bank_amount":    f"{rng.randint(450, 3_500):,}".replace(",", " ") + " €",
        "parcel_ref":     f"FR{rng.randint(1_000_000_000, 9_999_999_999)}",
        "parcel_fee":     f"{rng.choice([1.80, 2.50, 2.90, 3.20]):.2f} €",
        "parcel_carrier": rng.choice(["Chronopost","Colissimo","DPD France"]),
        "cve_id":         f"CVE-{y}-{rng.randint(10_000, 99_999)}",
        "cvss":           f"{rng.uniform(9.0, 9.9):.1f}",
        "prize_amount":   rng.choice([100, 150, 200, 250]),
        "doc_ref":        f"DOC-{y}-{rng.randint(100, 999)}",
        "doc_deadline":   rng.choice([f"ce vendredi {day} {month}", "lundi prochain", f"le {day} {month}"]),
        "salary_pct":     rng.choice(["2.8 %","3.1 %","3.4 %","4.0 %"]),
        "pw_days":        rng.choice(["2 jours","3 jours","5 jours","ce soir à minuit"]),
        "o365_device":    rng.choice(["iPhone 15","Windows 11 PC","MacBook Pro","Samsung Galaxy S24","iPad Pro"]),
        "o365_location":  rng.choice(["Amsterdam, Pays-Bas","Francfort, Allemagne","Londres, Royaume-Uni","Dublin, Irlande","Zurich, Suisse"]),
    }


# ---------------------------------------------------------------------------
# Email template functions  (greeting, click_url, pixel_url, ctx) → html
# ---------------------------------------------------------------------------

def _tpl_ceo_fraud(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    amount, deadline = ctx["ceo_amount"], ctx["ceo_deadline"]
    body = (
        f'<p style="color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 14px">Bonjour {greeting},</p>'
        f'<p style="color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 14px">Je vous écris depuis mon téléphone personnel — je suis en réunion externe jusqu\'en fin de matinée. J\'ai besoin de votre aide pour une opération confidentielle.</p>'
        f'<p style="color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 14px">Un virement de <strong>{amount}</strong> doit être exécuté <strong>{deadline}</strong> aujourd\'hui. L\'opération est urgente et ne doit pas être évoquée en interne pour l\'instant.</p>'
        f'<p style="color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 24px">Confirmez-moi votre disponibilité et je vous transmets les coordonnées bancaires.</p>'
        f'<p><a href="{url}" style="display:inline-block;background:#1a73e8;color:#fff;padding:12px 26px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Confirmer ma disponibilité</a></p>'
        f'<p style="color:#555;font-size:14px;margin:24px 0 0;line-height:1.5">Merci pour votre réactivité,<br><strong>Direction Générale</strong><br><span style="color:#aaa;font-size:12px">Envoyé depuis iPhone</span></p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Virement {amount} requis {deadline} — confirmez votre disponibilité",
        brand_bg="#ffffff",
        brand_html='<p style="margin:0;font-size:13px;color:#888;font-weight:600">Direction Générale</p>',
        body_html=body,
        footer_html='<p style="color:#ccc;font-size:11px;margin:0">Ce message est confidentiel. Si vous n\'êtes pas le destinataire, merci de le détruire.</p>',
    )


def _tpl_o365(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    device, location = ctx["o365_device"], ctx["o365_location"]
    ms_logo = (
        '<svg width="120" height="24" viewBox="0 0 120 24" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="10.5" height="10.5" fill="#F35325"/><rect x="12" width="10.5" height="10.5" fill="#81BC06"/>'
        '<rect y="12" width="10.5" height="10.5" fill="#05A6F0"/><rect x="12" y="12" width="10.5" height="10.5" fill="#FFBA08"/>'
        '<text x="28" y="17" font-family="Segoe UI,Arial" font-size="16" font-weight="300" fill="#fff">Microsoft 365</text>'
        '</svg>'
    )
    body = (
        f'<p style="color:#323130;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<table width="100%" cellpadding="14" cellspacing="0" style="background:#fff4ce;border-left:4px solid #ffb900;margin:0 0 20px">'
        f'<tr><td><p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#323130">&#9888;&#65039; Connexion inhabituelle détectée</p>'
        f'<p style="margin:0 0 4px;font-size:13px;color:#605e5c"><strong>Appareil&nbsp;:</strong> {device}</p>'
        f'<p style="margin:0 0 4px;font-size:13px;color:#605e5c"><strong>Localisation&nbsp;:</strong> {location}</p>'
        f'<p style="margin:0;font-size:13px;color:#605e5c"><strong>Heure&nbsp;:</strong> Aujourd\'hui, il y a quelques minutes</p>'
        f'</td></tr></table>'
        f'<p style="color:#323130;font-size:15px;line-height:1.6;margin:0 0 20px">Si vous n\'êtes pas à l\'origine de cette connexion, votre compte sera <strong>restreint dans 24&nbsp;heures</strong>.</p>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#0078d4;color:#fff;padding:13px 28px;border-radius:2px;text-decoration:none;font-size:15px;font-weight:600">Sécuriser mon compte</a></p>'
        f'<p style="color:#605e5c;font-size:13px;margin:0">Ce message est envoyé par Microsoft Account Team.</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Connexion depuis {location} sur {device} — sécurisez votre compte",
        brand_bg="#0078d4",
        brand_html=ms_logo,
        body_html=body,
        footer_html='<p style="color:#aaa;font-size:11px;margin:0">© Microsoft Corporation · One Microsoft Way · Redmond, WA 98052 · <a href="#" style="color:#aaa">Confidentialité</a></p>',
    )


def _tpl_fake_invoice(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    ref, amount = ctx["invoice_ref"], ctx["invoice_amount"]
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Malgré nos relances précédentes, la facture ci-dessous reste impayée. Merci de régulariser votre situation sous 48&nbsp;h pour éviter des pénalités de retard.</p>'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0e0e0;border-radius:4px;margin:0 0 24px;overflow:hidden">'
        f'<tr style="background:#f5f5f5"><td style="padding:10px 14px;font-size:12px;font-weight:700;color:#666;border-bottom:1px solid #e0e0e0">RÉFÉRENCE</td>'
        f'<td style="padding:10px 14px;font-size:12px;font-weight:700;color:#666;border-bottom:1px solid #e0e0e0">ÉCHÉANCE</td>'
        f'<td style="padding:10px 14px;font-size:12px;font-weight:700;color:#666;border-bottom:1px solid #e0e0e0">MONTANT TTC</td>'
        f'<td style="padding:10px 14px;font-size:12px;font-weight:700;color:#666;border-bottom:1px solid #e0e0e0">STATUT</td></tr>'
        f'<tr><td style="padding:14px;font-size:14px;color:#333;font-weight:600">{ref}</td>'
        f'<td style="padding:14px;font-size:14px;color:#e53935">Dépassée</td>'
        f'<td style="padding:14px;font-size:14px;font-weight:700">{amount}</td>'
        f'<td style="padding:14px"><span style="background:#fdecea;color:#e53935;font-size:12px;font-weight:700;padding:3px 8px;border-radius:2px">IMPAYÉE</span></td></tr>'
        f'</table>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#e53935;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Accéder au portail de paiement</a></p>'
        f'<p style="color:#777;font-size:13px;margin:0">En cas de litige, contactez-nous par retour de mail en indiquant votre référence.</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Relance : facture {ref} — {amount} impayée, action requise",
        brand_bg="#1565c0",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128202; Service Comptabilité</span>',
        body_html=body,
    )


def _tpl_bank(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    bank, last4, amount = ctx["bank_name"], ctx["bank_last4"], ctx["bank_amount"]
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<table width="100%" cellpadding="14" cellspacing="0" style="background:#fdecea;border-left:4px solid #e53935;margin:0 0 20px">'
        f'<tr><td><p style="margin:0 0 6px;font-size:14px;font-weight:700;color:#c62828">&#128308; Alerte de sécurité — Transaction suspecte</p>'
        f'<p style="margin:0;font-size:13px;color:#555">Une opération non reconnue a été détectée sur votre compte se terminant par <strong>••••{last4}</strong>.</p>'
        f'</td></tr></table>'
        f'<table width="100%" cellpadding="10" cellspacing="0" style="border:1px solid #e0e0e0;border-radius:4px;margin:0 0 24px">'
        f'<tr style="background:#fafafa"><td colspan="2" style="padding:10px 14px;font-size:12px;color:#888;border-bottom:1px solid #eee;font-weight:700">TRANSACTION DÉTECTÉE</td></tr>'
        f'<tr><td style="padding:10px 14px;font-size:14px;color:#555">Montant</td><td style="padding:10px 14px;font-size:14px;color:#e53935;font-weight:700">{amount}</td></tr>'
        f'<tr style="background:#fafafa"><td style="padding:10px 14px;font-size:14px;color:#555">Statut</td><td style="padding:10px 14px;font-size:14px;color:#e53935">En attente de validation</td></tr>'
        f'</table>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Pour <strong>bloquer cette opération</strong>, connectez-vous immédiatement. Sans action dans <strong>2&nbsp;heures</strong>, la transaction sera validée.</p>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#c62828;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Bloquer la transaction</a></p>'
        f'<p style="color:#888;font-size:12px;margin:0">Service Sécurité — {bank} · Ne répondez pas à cet e-mail.</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Transaction suspecte {amount} sur ••••{last4} — bloquez maintenant",
        brand_bg="#1a237e",
        brand_html=f'<span style="color:#fff;font-size:17px;font-weight:700">&#127974; {bank} — Sécurité</span>',
        body_html=body,
    )


def _tpl_parcel(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    carrier, ref, fee = ctx["parcel_carrier"], ctx["parcel_ref"], ctx["parcel_fee"]
    carrier_colors = {"Chronopost": "#ff6600", "Colissimo": "#003189", "DPD France": "#dc0032"}
    color = carrier_colors.get(carrier, "#e65100")
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour,</p>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Nous avons tenté de livrer votre colis aujourd\'hui mais la livraison a échoué en raison d\'une <strong>adresse incomplète</strong>.</p>'
        f'<table width="100%" cellpadding="10" cellspacing="0" style="border:1px solid #e0e0e0;border-radius:4px;margin:0 0 24px;background:#f9f9f9">'
        f'<tr><td style="padding:12px 16px;font-size:14px;color:#555">Référence colis</td><td style="padding:12px 16px;font-size:14px;color:#333;font-weight:700">{ref}</td></tr>'
        f'<tr style="background:#fff"><td style="padding:12px 16px;font-size:14px;color:#555">Statut</td><td style="padding:12px 16px;font-size:14px;color:#e65100;font-weight:600">Livraison échouée</td></tr>'
        f'<tr><td style="padding:12px 16px;font-size:14px;color:#555">Frais de réexpédition</td><td style="padding:12px 16px;font-size:15px;font-weight:700">{fee}</td></tr>'
        f'</table>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Reprogrammez la livraison et réglez les frais de <strong>{fee}</strong> avant 23h59 ce soir. Passé ce délai, le colis sera retourné à l\'expéditeur.</p>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:{color};color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Reprogrammer ma livraison</a></p>'
        f'<p style="color:#888;font-size:12px;margin:0">{carrier} · Service Client · Message automatique</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Colis {ref} non livré — reprogrammez avant ce soir ({fee})",
        brand_bg=color,
        brand_html=f'<span style="color:#fff;font-size:17px;font-weight:700">&#128230; {carrier}</span>',
        body_html=body,
    )


def _tpl_it_password(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    days = ctx["pw_days"]
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Conformément à notre politique de sécurité, votre mot de passe doit être renouvelé. <strong>Il expirera dans {days}.</strong></p>'
        f'<table width="100%" cellpadding="14" cellspacing="0" style="background:#e3f2fd;border-left:4px solid #1565c0;margin:0 0 20px">'
        f'<tr><td><p style="margin:0 0 6px;font-size:14px;font-weight:700;color:#0d47a1">&#8505;&#65039; Systèmes concernés</p>'
        f'<p style="margin:0;font-size:13px;color:#555;line-height:1.7">Active Directory &nbsp;·&nbsp; Messagerie Outlook &nbsp;·&nbsp; Accès VPN &nbsp;·&nbsp; Portail intranet</p>'
        f'</td></tr></table>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Sans action, votre accès à l\'ensemble de ces services sera <strong>suspendu automatiquement</strong>.</p>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#1565c0;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Renouveler mon mot de passe</a></p>'
        f'<p style="color:#555;font-size:14px;margin:0;line-height:1.5">L\'équipe DSI<br><span style="font-size:12px;color:#888">Direction des Systèmes d\'Information</span></p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Votre mot de passe expire dans {days} — renouvellement obligatoire",
        brand_bg="#1565c0",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128187; Direction des Systèmes d\'Information</span>',
        body_html=body,
    )


def _tpl_prize(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    amount = ctx["prize_amount"]
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<div style="text-align:center;padding:24px 16px;background:#fffde7;border-radius:8px;margin:0 0 24px">'
        f'<p style="font-size:48px;margin:0 0 8px">&#127873;</p>'
        f'<p style="font-size:22px;font-weight:700;color:#f9a825;margin:0 0 4px">Félicitations&nbsp;!</p>'
        f'<p style="font-size:36px;font-weight:900;color:#e65100;margin:4px 0 0">{amount}&nbsp;€</p>'
        f'<p style="font-size:14px;color:#555;margin:8px 0 0">Carte cadeau Amazon</p>'
        f'</div>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Votre participation au tirage au sort du comité d\'entreprise vous a désigné(e) gagnant(e). Cliquez ci-dessous pour réclamer votre lot avant expiration.</p>'
        f'<p style="text-align:center;margin:0 0 16px"><a href="{url}" style="display:inline-block;background:#f9a825;color:#fff;padding:14px 32px;border-radius:4px;text-decoration:none;font-size:16px;font-weight:700">&#127881; Réclamer mon lot</a></p>'
        f'<p style="color:#e53935;font-size:13px;text-align:center;margin:0 0 16px;font-weight:600">&#9200; Offre valable 48&nbsp;h uniquement</p>'
        f'<p style="color:#888;font-size:12px;margin:0">Service Ressources Humaines · Comité d\'entreprise</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Vous avez gagné une carte cadeau Amazon de {amount}€ — réclamez dans les 48h",
        brand_bg="#2e7d32",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#127970; Ressources Humaines</span>',
        body_html=body,
    )


def _tpl_invoice_pdf(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    ref, deadline = ctx["doc_ref"], ctx["doc_deadline"]
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px"><strong>Service Administratif</strong> vous a envoyé un document à signer électroniquement.</p>'
        f'<table width="100%" cellpadding="16" cellspacing="0" style="border:1px solid #e0e0e0;border-radius:4px;background:#f9f9f9;margin:0 0 24px">'
        f'<tr><td style="border-right:4px solid #f5a81c;width:64px;padding-right:16px" valign="middle"><div style="font-size:36px;text-align:center">&#128196;</div></td>'
        f'<td valign="middle"><p style="margin:0 0 4px;font-size:15px;font-weight:700;color:#333">Document à signer</p>'
        f'<p style="margin:0 0 2px;font-size:13px;color:#777">Référence&nbsp;: <strong>{ref}</strong></p>'
        f'<p style="margin:0;font-size:13px;color:#e65100;font-weight:600">À signer avant {deadline}</p>'
        f'</td></tr></table>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Ce document requiert votre signature. Merci de le signer via notre plateforme sécurisée avant la date limite.</p>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#f5a81c;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:700">&#9998; Signer le document</a></p>'
        f'<p style="color:#888;font-size:12px;margin:0">Service Administratif · Document confidentiel · Ne pas transférer</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Document {ref} en attente de votre signature — délai : {deadline}",
        brand_bg="#f5a81c",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#9998; Signature électronique</span>',
        body_html=body,
    )


def _tpl_vpn_update(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    cve, cvss = ctx["cve_id"], ctx["cvss"]
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<table width="100%" cellpadding="14" cellspacing="0" style="background:#fdecea;border-left:4px solid #b71c1c;margin:0 0 20px">'
        f'<tr><td><p style="margin:0 0 8px;font-size:14px;font-weight:700;color:#b71c1c">&#128308; VULNÉRABILITÉ CRITIQUE DÉTECTÉE</p>'
        f'<p style="margin:0 0 4px;font-size:14px;color:#333">Identifiant CVE&nbsp;: <strong>{cve}</strong></p>'
        f'<p style="margin:0 0 4px;font-size:14px;color:#333">Score CVSS&nbsp;: <strong style="color:#b71c1c">{cvss}/10 — CRITIQUE</strong></p>'
        f'<p style="margin:0;font-size:13px;color:#555">Exploitation active confirmée dans la nature.</p>'
        f'</td></tr></table>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Une faille critique a été découverte dans votre version du client VPN. Des attaquants exploitent activement cette vulnérabilité pour accéder aux réseaux d\'entreprise.</p>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px"><strong>Vous devez installer la mise à jour avant ce soir</strong> pour conserver votre accès aux ressources internes.</p>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#b71c1c;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:700">&#128274; Télécharger la mise à jour</a></p>'
        f'<p style="color:#555;font-size:14px;margin:0;line-height:1.5">L\'équipe Sécurité IT<br><span style="font-size:12px;color:#888">CSIRT — Centre de Réponse aux Incidents</span></p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"CRITIQUE : {cve} (CVSS {cvss}/10) — mise à jour VPN obligatoire ce soir",
        brand_bg="#b71c1c",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128274; Équipe Sécurité IT — ALERTE</span>',
        body_html=body,
    )


def _tpl_hr_document(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    pct = ctx["salary_pct"]
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Suite aux revues de performance annuelles, la DRH a finalisé la <strong>nouvelle grille de rémunération</strong> incluant les revalorisations individuelles.</p>'
        f'<table width="100%" cellpadding="16" cellspacing="0" style="border:1px solid #cfd8dc;border-radius:4px;background:#f9f9f9;margin:0 0 24px">'
        f'<tr><td><p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#37474f;letter-spacing:1px">&#128274; DOCUMENT CONFIDENTIEL</p>'
        f'<p style="margin:0 0 4px;font-size:14px;color:#333">Contenu&nbsp;: Grille des salaires &amp; revalorisation</p>'
        f'<p style="margin:0;font-size:13px;color:#e65100;font-weight:600">Augmentation moyenne&nbsp;: <strong>{pct}</strong></p>'
        f'</td></tr></table>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Ce document est <strong>strictement confidentiel</strong>. Accédez-y via le portail RH sécurisé — il expire dans 72&nbsp;h.</p>'
        f'<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#37474f;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">&#128194; Accéder au document</a></p>'
        f'<p style="color:#555;font-size:14px;margin:0;line-height:1.5">Direction des Ressources Humaines</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Grille des salaires +{pct} disponible — accès confidentiel 72h",
        brand_bg="#37474f",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128101; Direction des Ressources Humaines</span>',
        body_html=body,
    )


# ---------------------------------------------------------------------------
# Scenario metadata + template dispatch
# ---------------------------------------------------------------------------

_SCENARIO_TEMPLATES: dict[str, dict[str, Any]] = {
    "ceo-fraud": {
        "from_name": "Direction Générale",
        "internal": True,
        "subject": lambda ctx: f"Action requise — virement urgent {ctx['ceo_amount']}",
        "html": _tpl_ceo_fraud,
        "text": lambda g, url, ctx: f"Bonjour {g}, virement urgent {ctx['ceo_amount']} requis {ctx['ceo_deadline']}. Confirmez : {url}",
    },
    "o365-credentials": {
        "from_name": "Microsoft 365",
        "internal": False,
        "subject": lambda ctx: f"⚠️ Connexion suspecte depuis {ctx['o365_location']} — sécurisez votre compte",
        "html": _tpl_o365,
        "text": lambda g, url, ctx: f"Connexion suspecte depuis {ctx['o365_location']}. Sécurisez votre compte Microsoft 365 : {url}",
    },
    "fake-invoice": {
        "from_name": "Service Comptabilité",
        "internal": True,
        "subject": lambda ctx: f"Facture impayée {ctx['invoice_ref']} — {ctx['invoice_amount']} TTC — relance",
        "html": _tpl_fake_invoice,
        "text": lambda g, url, ctx: f"Bonjour {g}, facture {ctx['invoice_ref']} ({ctx['invoice_amount']}) impayée. Portail de paiement : {url}",
    },
    "bank-phishing": {
        "from_name": "Sécurité Bancaire",
        "internal": False,
        "subject": lambda ctx: f"⚠️ [{ctx['bank_name']}] Transaction suspecte de {ctx['bank_amount']} détectée",
        "html": _tpl_bank,
        "text": lambda g, url, ctx: f"Bonjour {g}, transaction suspecte {ctx['bank_amount']} sur ••••{ctx['bank_last4']}. Bloquez maintenant : {url}",
    },
    "parcel-tracking": {
        "from_name": "Service Livraison",
        "internal": False,
        "subject": lambda ctx: f"[{ctx['parcel_carrier']}] Colis {ctx['parcel_ref']} non livré — action requise",
        "html": _tpl_parcel,
        "text": lambda g, url, ctx: f"Colis {ctx['parcel_ref']} non livré. Frais {ctx['parcel_fee']}. Reprogrammez : {url}",
    },
    "it-password": {
        "from_name": "Équipe DSI",
        "internal": True,
        "subject": lambda ctx: f"[DSI{{company_suffix}}] Mot de passe expire dans {ctx['pw_days']} — renouvellement obligatoire",
        "html": _tpl_it_password,
        "text": lambda g, url, ctx: f"Bonjour {g}, votre mot de passe expire dans {ctx['pw_days']}. Renouveler : {url}",
    },
    "prize": {
        "from_name": "Service Ressources Humaines",
        "internal": True,
        "subject": lambda ctx: f"\U0001f381 Félicitations — vous avez gagné une carte cadeau {ctx['prize_amount']} € !",
        "html": _tpl_prize,
        "text": lambda g, url, ctx: f"Bonjour {g}, vous avez gagné une carte cadeau Amazon de {ctx['prize_amount']}€. Réclamez-la : {url}",
    },
    "invoice-pdf": {
        "from_name": "Service Administratif",
        "internal": True,
        "subject": lambda ctx: f"Document {ctx['doc_ref']} — signature requise avant {ctx['doc_deadline']}",
        "html": _tpl_invoice_pdf,
        "text": lambda g, url, ctx: f"Bonjour {g}, document {ctx['doc_ref']} à signer avant {ctx['doc_deadline']} : {url}",
    },
    "vpn-update": {
        "from_name": "Équipe Sécurité IT",
        "internal": True,
        "subject": lambda ctx: f"[URGENT{{company_suffix}}] {ctx['cve_id']} — mise à jour VPN critique (CVSS {ctx['cvss']}/10)",
        "html": _tpl_vpn_update,
        "text": lambda g, url, ctx: f"Bonjour {g}, vulnérabilité critique {ctx['cve_id']} (CVSS {ctx['cvss']}). Mettez à jour votre VPN : {url}",
    },
    "hr-document": {
        "from_name": "Ressources Humaines",
        "internal": True,
        "subject": lambda ctx: f"[CONFIDENTIEL{{company_suffix}}] Grille des salaires — revalorisation {ctx['salary_pct']}",
        "html": _tpl_hr_document,
        "text": lambda g, url, ctx: f"Bonjour {g}, nouvelle grille des salaires ({ctx['salary_pct']}) disponible : {url}",
    },
}

_DEFAULT_SCENARIO_KEY = "o365-credentials"

# ---------------------------------------------------------------------------
# Scenario → landing page mapping
# ---------------------------------------------------------------------------

_SCENARIO_LANDING: dict[str, str] = {
    "o365-credentials": "microsoft",
    "bank-phishing":    "bank",
    "it-password":      "it",
    "vpn-update":       "it",
    "invoice-pdf":      "docusign",
    "parcel-tracking":  "parcel",
    "prize":            "prize",
    "fake-invoice":     "payment",
    "hr-document":      "hr",
    "ceo-fraud":        "ceo",
}

# ---------------------------------------------------------------------------
# Tracking HTML pages — scenario-specific landing pages
# ---------------------------------------------------------------------------

_LANDING_MICROSOFT = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Se connecter — Microsoft</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f2f2f2;font-family:'Segoe UI',Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.w{background:#fff;width:440px;padding:44px;box-shadow:0 2px 8px rgba(0,0,0,.2)}h1{font-size:24px;font-weight:600;color:#1b1b1b;margin:20px 0 16px}input{width:100%;border:1px solid #666;padding:6px 10px;font-size:15px;height:38px;margin-bottom:12px;outline:none;font-family:inherit}input:focus{border-color:#0078d4;box-shadow:0 0 0 1px #0078d4}.btn{width:100%;background:#0078d4;color:#fff;border:none;height:38px;font-size:15px;cursor:pointer}.btn:hover{background:#106ebe}.lnk{margin-top:12px;font-size:13px}.lnk a{color:#0078d4;text-decoration:none}.ft{margin-top:32px;font-size:11px;color:#666;display:flex;gap:16px}.ft a{color:#666;text-decoration:none}</style></head>
<body><div class="w">
<svg width="108" height="24" viewBox="0 0 120 24" xmlns="http://www.w3.org/2000/svg"><rect width="10.5" height="10.5" fill="#F35325"/><rect x="12" width="10.5" height="10.5" fill="#81BC06"/><rect y="12" width="10.5" height="10.5" fill="#05A6F0"/><rect x="12" y="12" width="10.5" height="10.5" fill="#FFBA08"/><text x="28" y="18" font-family="Segoe UI,Arial" font-size="18" font-weight="300" fill="#1b1b1b">Microsoft</text></svg>
<h1>Se connecter</h1>
<form method="POST" action="ACTION_URL">
<input type="email" name="username" placeholder="Adresse e-mail, téléphone ou Skype" autocomplete="email">
<input type="password" name="password" placeholder="Mot de passe" autocomplete="current-password">
<button type="submit" class="btn">Se connecter</button></form>
<div class="lnk"><a href="#">Mot de passe oublié ?</a></div>
<div class="ft"><a href="#">Conditions d'utilisation</a><a href="#">Confidentialité</a></div>
</div></body></html>"""

_LANDING_BANK = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Espace Client Sécurisé</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#0d1b3e;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:400px;border-radius:4px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.4)}.hd{background:#0d1b3e;padding:24px;text-align:center;border-bottom:4px solid #c9a227}.hd p{color:#c9a227;font-size:18px;font-weight:700;letter-spacing:1px}.hd span{color:#fff;font-size:12px}.bd{padding:32px 28px}.ico{text-align:center;font-size:40px;margin-bottom:16px}h2{font-size:16px;color:#0d1b3e;text-align:center;margin-bottom:24px}label{display:block;font-size:12px;font-weight:700;color:#555;letter-spacing:.5px;margin-bottom:4px}input{width:100%;border:1px solid #ccc;padding:10px 12px;font-size:14px;margin-bottom:16px;border-radius:2px;outline:none}input:focus{border-color:#0d1b3e}.btn{width:100%;background:#0d1b3e;color:#fff;border:none;padding:12px;font-size:14px;font-weight:700;cursor:pointer;letter-spacing:.5px}.ft{padding:14px 28px;background:#f5f5f5;text-align:center;font-size:11px;color:#888;border-top:1px solid #eee}</style></head>
<body><div class="card"><div class="hd"><p>&#127974; ESPACE CLIENT</p><span>Connexion sécurisée — Authentification forte</span></div>
<div class="bd"><div class="ico">&#128274;</div><h2>Identifiez-vous pour sécuriser votre compte</h2>
<form method="POST" action="ACTION_URL">
<label>IDENTIFIANT CLIENT</label><input type="text" name="username" placeholder="N° client ou adresse e-mail" autocomplete="username">
<label>MOT DE PASSE</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">ACCÉDER À MON ESPACE</button></form></div>
<div class="ft">&#128274; Connexion chiffrée SSL/TLS — Données sécurisées</div></div></body></html>"""

_LANDING_IT = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portail de Sécurité IT</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#1e2a3a;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:420px;border-radius:6px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.4)}.hd{background:#1565c0;padding:18px 24px}.hd span{color:#fff;font-size:16px;font-weight:700}.alert{background:#fff3e0;border-left:4px solid #f57c00;padding:12px 16px;margin:20px 20px 0;font-size:13px;color:#e65100}.bd{padding:20px 24px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#1565c0;box-shadow:0 0 0 2px rgba(21,101,192,.2)}.btn{width:100%;background:#1565c0;color:#fff;border:none;padding:12px;font-size:14px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:20px}.ft{background:#f5f5f5;padding:12px 24px;font-size:11px;color:#888;border-top:1px solid #eee}</style></head>
<body><div class="card"><div class="hd"><span>&#128187; Portail SSO — Direction des Systèmes d'Information</span></div>
<div class="alert">&#9888;&#65039; Votre session a expiré. Veuillez vous reconnecter pour continuer.</div>
<div class="bd"><form method="POST" action="ACTION_URL">
<label>IDENTIFIANT RÉSEAU</label><input type="text" name="username" placeholder="prenom.nom" autocomplete="username">
<label>MOT DE PASSE ACTUEL</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">Se connecter</button></form></div>
<div class="ft">Portail DSI — Connexion sécurisée LDAP/AD · v3.4.1</div></div></body></html>"""

_LANDING_DOCUSIGN = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DocuSign — Signer le document</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f2f2f2;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:4px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden}.hd{background:#f5a81c;padding:16px 28px}.logo{font-size:22px;font-weight:900;color:#fff;letter-spacing:-.5px}.doc{background:#fafafa;border:1px solid #e0e0e0;margin:20px 28px 0;padding:14px;border-radius:4px;font-size:13px}.doc .from{color:#555;margin-bottom:4px}.doc .name{font-weight:700;color:#333;font-size:14px}.bd{padding:20px 28px 28px}h2{font-size:15px;color:#333;margin-bottom:16px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#f5a81c}.btn{width:100%;background:#f5a81c;color:#fff;border:none;padding:12px;font-size:15px;font-weight:700;cursor:pointer;border-radius:3px;margin-top:20px}.ft{padding:12px 28px;border-top:1px solid #eee;font-size:11px;color:#999;text-align:center}</style></head>
<body><div class="card"><div class="hd"><div class="logo">DocuSign</div></div>
<div class="doc"><p class="from">Document envoyé par : Service Administratif</p><p class="name">&#128196; Document en attente de signature</p></div>
<div class="bd"><h2>Connectez-vous pour accéder au document</h2>
<form method="POST" action="ACTION_URL">
<label>E-MAIL</label><input type="email" name="username" placeholder="prenom.nom@entreprise.com" autocomplete="email">
<label>MOT DE PASSE</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">&#9998; Accéder au document</button></form></div>
<div class="ft">DocuSign — Signature électronique sécurisée · eIDAS conforme</div></div></body></html>"""

_LANDING_PARCEL = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reprogrammer la livraison</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f5f5f5;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden}.hd{background:#e65100;padding:16px 28px}.hd h1{color:#fff;font-size:18px;font-weight:700}.st{background:#fff3e0;padding:12px 28px;border-bottom:1px solid #ffe0b2;font-size:13px;color:#e65100}.bd{padding:24px 28px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:14px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#e65100}.row{display:flex;gap:12px}.row>div{flex:1}.amt{background:#e65100;color:#fff;text-align:center;padding:10px;border-radius:3px;font-size:16px;font-weight:700;margin:20px 0}.btn{width:100%;background:#e65100;color:#fff;border:none;padding:12px;font-size:15px;font-weight:700;cursor:pointer;border-radius:3px}.ft{padding:12px 28px;background:#f9f9f9;border-top:1px solid #eee;font-size:11px;color:#888;text-align:center}</style></head>
<body><div class="card"><div class="hd"><h1>&#128230; Reprogrammer la livraison</h1></div>
<div class="st">&#9888;&#65039; Votre colis est en attente — frais de réexpédition à régler</div>
<div class="bd"><form method="POST" action="ACTION_URL">
<label>NOM SUR LA CARTE</label><input type="text" name="cardholder" placeholder="JEAN DUPONT">
<label>NUMÉRO DE CARTE</label><input type="text" name="card_number" placeholder="•••• •••• •••• ••••" maxlength="19">
<div class="row"><div><label>EXPIRATION</label><input type="text" name="expiry" placeholder="MM/AA" maxlength="5"></div><div><label>CVV</label><input type="text" name="cvv" placeholder="•••" maxlength="3"></div></div>
<div class="amt">&#128179; À payer : 2,50 €</div>
<button type="submit" class="btn">Confirmer le paiement</button></form></div>
<div class="ft">&#128274; Paiement sécurisé 3D Secure · SSL/TLS</div></div></body></html>"""

_LANDING_PRIZE = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Réclamer mon lot</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:linear-gradient(135deg,#1b5e20,#2e7d32);font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.3);overflow:hidden}.hd{background:#f9a825;padding:24px;text-align:center}.hd h1{font-size:22px;color:#fff;font-weight:700}.hd .prize{font-size:36px;font-weight:900;color:#fff;margin-top:8px}.bd{padding:28px}p{font-size:14px;color:#555;margin-bottom:20px;line-height:1.5}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#f9a825}.btn{width:100%;background:#f9a825;color:#fff;border:none;padding:13px;font-size:15px;font-weight:700;cursor:pointer;border-radius:4px;margin-top:20px}.exp{font-size:12px;color:#e65100;text-align:center;margin-top:12px;font-weight:600}</style></head>
<body><div class="card"><div class="hd"><h1>&#127873; Félicitations !</h1><div class="prize">Carte cadeau Amazon</div></div>
<div class="bd"><p>Pour recevoir votre lot, confirmez vos coordonnées afin que nous puissions vous envoyer votre carte cadeau.</p>
<form method="POST" action="ACTION_URL">
<label>NOM COMPLET</label><input type="text" name="full_name" placeholder="Jean Dupont" autocomplete="name">
<label>ADRESSE E-MAIL</label><input type="email" name="username" placeholder="jean.dupont@entreprise.com" autocomplete="email">
<label>MOT DE PASSE (vérification d'identité)</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">&#127881; Réclamer mon lot</button></form>
<p class="exp">&#9200; Offre expire dans : 47h 23min</p></div></div></body></html>"""

_LANDING_PAYMENT = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portail de paiement</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f5f5f5;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:440px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.15);overflow:hidden}.hd{background:#1565c0;padding:16px 28px}.hd h1{color:#fff;font-size:17px;font-weight:700}.inv{margin:20px 28px 0;padding:16px;background:#e3f2fd;border-radius:4px;border:1px solid #bbdefb}.inv .ref{font-size:12px;color:#555;margin-bottom:4px}.inv .amt{font-size:28px;font-weight:700;color:#1565c0}.inv .st{font-size:12px;color:#e53935;font-weight:600;margin-top:4px}.bd{padding:20px 28px}h2{font-size:14px;color:#333;margin-bottom:14px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#1565c0}.row{display:flex;gap:12px}.row>div{flex:1}.btn{width:100%;background:#1565c0;color:#fff;border:none;padding:12px;font-size:15px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:20px}.ft{padding:12px 28px;border-top:1px solid #eee;font-size:11px;color:#888;text-align:center}</style></head>
<body><div class="card"><div class="hd"><h1>&#128179; Portail de Paiement Sécurisé</h1></div>
<div class="inv"><div class="ref">Facture en attente de règlement</div><div class="amt">En attente</div><div class="st">&#9888;&#65039; IMPAYÉE — Pénalités de retard en cours</div></div>
<div class="bd"><h2>Règlement par carte bancaire</h2>
<form method="POST" action="ACTION_URL">
<label>NOM SUR LA CARTE</label><input type="text" name="cardholder" placeholder="NOM PRÉNOM">
<label>NUMÉRO DE CARTE</label><input type="text" name="card_number" placeholder="•••• •••• •••• ••••" maxlength="19">
<div class="row"><div><label>EXPIRATION</label><input type="text" name="expiry" placeholder="MM/AA" maxlength="5"></div><div><label>CVV</label><input type="text" name="cvv" placeholder="•••" maxlength="3"></div></div>
<button type="submit" class="btn">Payer maintenant</button></form></div>
<div class="ft">&#128274; Paiement 3D Secure — Données chiffrées SSL/TLS</div></div></body></html>"""

_LANDING_HR = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Portail RH — Document confidentiel</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#eceff1;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:420px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.12);overflow:hidden}.hd{background:#37474f;padding:18px 28px}.hd h1{color:#fff;font-size:16px;font-weight:700}.prev{margin:20px 28px 0;border:1px solid #e0e0e0;border-radius:4px;overflow:hidden}.prev-hd{background:#37474f;padding:10px 14px;color:#fff;font-size:12px;font-weight:700;letter-spacing:1px}.prev-bd{padding:16px;background:#fafafa;font-size:13px;color:#777;text-align:center;position:relative}.blur{filter:blur(4px);user-select:none;line-height:1.8}.ov{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:13px;color:#37474f;font-weight:700;background:rgba(255,255,255,.7)}.bd{padding:20px 28px}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:12px}input{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#37474f}.btn{width:100%;background:#37474f;color:#fff;border:none;padding:12px;font-size:14px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:20px}.ft{padding:12px 28px;background:#f5f5f5;border-top:1px solid #eee;font-size:11px;color:#888;text-align:center}</style></head>
<body><div class="card"><div class="hd"><h1>&#128101; Portail RH — Document Confidentiel</h1></div>
<div class="prev"><div class="prev-hd">&#128274; GRILLE DE RÉMUNÉRATION — CONFIDENTIEL</div>
<div class="prev-bd"><div class="blur">Niveau 1 — 28 000 € — 31 000 €<br>Niveau 2 — 34 000 € — 38 000 €<br>Niveau 3 — 42 000 € — 48 000 €<br>Augmentation moyenne : +3.4%</div>
<div class="ov">&#128274; Authentification requise</div></div></div>
<div class="bd"><form method="POST" action="ACTION_URL">
<label>IDENTIFIANT</label><input type="text" name="username" placeholder="prenom.nom" autocomplete="username">
<label>MOT DE PASSE</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<button type="submit" class="btn">&#128275; Accéder au document</button></form></div>
<div class="ft">Document confidentiel — accès restreint au personnel autorisé</div></div></body></html>"""

_LANDING_CEO = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Confirmation de disponibilité</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#f5f5f5;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}.card{background:#fff;width:420px;border-radius:6px;box-shadow:0 2px 12px rgba(0,0,0,.12);overflow:hidden}.hd{background:#1a73e8;padding:18px 28px}.hd h1{color:#fff;font-size:16px;font-weight:600}.bd{padding:28px}.ctx{background:#e8f0fe;border-radius:4px;padding:14px 16px;font-size:13px;color:#1a73e8;margin-bottom:20px;line-height:1.5}label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:4px;margin-top:14px}input[type=text],input[type=password]{width:100%;border:1px solid #ccc;padding:9px 12px;font-size:14px;border-radius:3px;outline:none}input:focus{border-color:#1a73e8}.rg{display:flex;gap:16px;margin-top:6px}.rg label{display:flex;align-items:center;gap:6px;font-size:14px;font-weight:400;cursor:pointer;margin-top:0}.btn{width:100%;background:#1a73e8;color:#fff;border:none;padding:12px;font-size:14px;font-weight:600;cursor:pointer;border-radius:3px;margin-top:24px}.ft{padding:12px 28px;border-top:1px solid #eee;font-size:11px;color:#888}</style></head>
<body><div class="card"><div class="hd"><h1>&#128203; Confirmation de disponibilité</h1></div>
<div class="bd"><div class="ctx">&#128204; Message de la Direction Générale — Opération confidentielle. Votre confirmation est requise avant 17h.</div>
<form method="POST" action="ACTION_URL">
<label>VOTRE NOM</label><input type="text" name="full_name" placeholder="Prénom Nom" autocomplete="name">
<label>MOT DE PASSE (authentification)</label><input type="password" name="password" placeholder="••••••••" autocomplete="current-password">
<label>DISPONIBILITÉ</label><div class="rg"><label><input type="radio" name="available" value="yes"> Disponible</label><label><input type="radio" name="available" value="no"> Non disponible</label></div>
<button type="submit" class="btn">Confirmer</button></form></div>
<div class="ft">Communication interne confidentielle — ne pas transférer</div></div></body></html>"""

_LANDING_TEMPLATES: dict[str, str] = {
    "microsoft": _LANDING_MICROSOFT,
    "bank":      _LANDING_BANK,
    "it":        _LANDING_IT,
    "docusign":  _LANDING_DOCUSIGN,
    "parcel":    _LANDING_PARCEL,
    "prize":     _LANDING_PRIZE,
    "payment":   _LANDING_PAYMENT,
    "hr":        _LANDING_HR,
    "ceo":       _LANDING_CEO,
}

_AWARENESS_HTML = """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Exercice de cybersécurité — CyberScan</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f172a;color:#fff;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}
.card{background:#1e293b;border:1px solid #334155;padding:40px;border-radius:12px;max-width:600px;width:100%;text-align:center}
.icon{font-size:56px;margin-bottom:16px}
h1{font-size:24px;color:#f59e0b;margin-bottom:12px}
p{color:#94a3b8;line-height:1.6;margin-bottom:16px}
.tips{background:#0f172a;border-radius:8px;padding:24px;text-align:left;margin-top:24px}
.tips h3{color:#38bdf8;margin-bottom:12px;font-size:15px}
ol{color:#94a3b8;padding-left:20px;line-height:2}
.badge{display:inline-block;background:#0e7490;color:#fff;padding:4px 12px;border-radius:999px;font-size:12px;margin-top:24px}
</style></head>
<body>
<div class="card">
  <div class="icon">⚠️</div>
  <h1>Exercice de cybersécurité</h1>
  <p>Vous venez de cliquer sur un <strong style="color:#fbbf24">lien de phishing simulé</strong>
  dans le cadre d'un exercice de sensibilisation organisé par votre entreprise.</p>
  <p>Aucune donnée réelle n'a été capturée. Votre vigilance contribue à la sécurité collective.</p>
  <div class="tips">
    <h3>3 réflexes anti-phishing à retenir</h3>
    <ol>
      <li>Vérifiez toujours l'adresse de l'expéditeur (pas seulement le nom affiché)</li>
      <li>Survolez les liens pour voir l'URL réelle avant de cliquer</li>
      <li>En cas de doute, appelez directement la personne concernée</li>
    </ol>
  </div>
  <span class="badge">CyberScan — Simulation de phishing</span>
</div>
</body></html>"""

_PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


# ---------------------------------------------------------------------------
# Domain verification (DNS TXT)
# ---------------------------------------------------------------------------

async def request_domain_verification(
    user_id: int, domain: str, db: AsyncSession
) -> PhishingDomainVerification:
    result = await db.execute(
        select(PhishingDomainVerification).where(
            PhishingDomainVerification.user_id == user_id,
            PhishingDomainVerification.domain == domain,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.verified:
        return existing

    token = f"cyberscan-verify-{secrets.token_urlsafe(16)}"
    if existing:
        existing.verification_token = token
        existing.verified = False
        existing.verified_at = None
    else:
        existing = PhishingDomainVerification(
            user_id=user_id,
            domain=domain,
            verification_token=token,
        )
        db.add(existing)
    await db.flush()
    await db.refresh(existing)
    return existing


async def check_domain_verification(
    record: PhishingDomainVerification, db: AsyncSession
) -> bool:
    if record.verified:
        return True
    from app.core.config import settings
    if settings.APP_ENV == "development":
        record.verified = True
        record.verified_at = datetime.now(timezone.utc)
        await db.flush()
        return True
    try:
        import dns.resolver
        answers = dns.resolver.resolve(
            f"_cyberscan-verify.{record.domain}", "TXT", lifetime=5.0
        )
        for rdata in answers:
            for txt_string in rdata.strings:
                if txt_string.decode("utf-8") == record.verification_token:
                    record.verified = True
                    record.verified_at = datetime.now(timezone.utc)
                    await db.flush()
                    return True
    except Exception as exc:
        logger.debug(f"DNS TXT check failed for {record.domain}: {exc}")
    return False


# ---------------------------------------------------------------------------
# Campaign CRUD
# ---------------------------------------------------------------------------

async def get_campaigns(user_id: int, db: AsyncSession) -> list[PhishingCampaign]:
    result = await db.execute(
        select(PhishingCampaign)
        .where(PhishingCampaign.user_id == user_id)
        .order_by(PhishingCampaign.created_at.desc())
    )
    return list(result.scalars().all())


async def get_campaign(campaign_id: int, user_id: int, db: AsyncSession) -> PhishingCampaign | None:
    result = await db.execute(
        select(PhishingCampaign).where(
            PhishingCampaign.id == campaign_id,
            PhishingCampaign.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_campaign(user_id: int, name: str, plan_tier: str, db: AsyncSession) -> PhishingCampaign:
    campaign = PhishingCampaign(user_id=user_id, name=name, plan_tier=plan_tier, status="draft")
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


async def update_campaign(
    campaign: PhishingCampaign,
    *,
    name: str | None = None,
    domain: str | None = None,
    domain_verified: bool | None = None,
    lookalike_domain: str | None = None,
    scenario_keys: list[str] | None = None,
    cgu_accepted: bool | None = None,
    scheduled_at: datetime | None = None,
    status: str | None = None,
    db: AsyncSession,
) -> PhishingCampaign:
    if name is not None:
        campaign.name = name
    if domain is not None:
        campaign.domain = domain
    if domain_verified is not None:
        campaign.domain_verified = domain_verified
    if lookalike_domain is not None:
        campaign.lookalike_domain = lookalike_domain
    if scenario_keys is not None:
        campaign.scenario_keys = json.dumps(scenario_keys)
    if cgu_accepted is not None:
        campaign.cgu_accepted = cgu_accepted
    if scheduled_at is not None:
        campaign.scheduled_at = scheduled_at
    if status is not None:
        campaign.status = status
    campaign.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return campaign


async def upload_targets_csv(
    campaign: PhishingCampaign, csv_content: str, db: AsyncSession
) -> int:
    existing = await db.execute(
        select(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
    )
    for t in existing.scalars().all():
        await db.delete(t)

    reader = csv.DictReader(io.StringIO(csv_content))
    count = 0
    for row in reader:
        email = (row.get("email") or row.get("Email") or "").strip()
        if not email or "@" not in email:
            continue
        target = PhishingTarget(
            campaign_id=campaign.id,
            email=email,
            first_name=(row.get("first_name") or row.get("prenom") or row.get("Prénom") or "").strip(),
            last_name=(row.get("last_name") or row.get("nom") or row.get("Nom") or "").strip() or None,
            department=(row.get("department") or row.get("departement") or row.get("Département") or "").strip() or None,
        )
        db.add(target)
        count += 1

    campaign.targets_count = count
    campaign.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return count


# ---------------------------------------------------------------------------
# Email sending engine
# ---------------------------------------------------------------------------

def _tracking_base(campaign: PhishingCampaign) -> str:
    """Determine the base URL for tracking links (look-alike or default)."""
    if campaign.lookalike_domain:
        domain = campaign.lookalike_domain.rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        return domain
    return settings.PHISHING_BASE_URL.rstrip("/")


def _extract_company_name(domain: str | None) -> str:
    """Extract a display-ready company name from a domain. "acme-corp.com" → "Acme Corp"."""
    if not domain:
        return ""
    name = domain.split(".")[0]
    return " ".join(w.capitalize() for w in name.replace("-", " ").replace("_", " ").split())


def _build_email(
    campaign: PhishingCampaign,
    target: PhishingTarget,
    tracking_id: str,
    scenario_key: str,
) -> tuple[str, str, str, str]:
    """Return (from_addr, subject, html, text)."""
    base = _tracking_base(campaign)
    pixel_url = f"{base}/phishing/t/{tracking_id}/px"
    click_url = f"{base}/phishing/t/{tracking_id}/c"

    tpl = _SCENARIO_TEMPLATES.get(scenario_key, _SCENARIO_TEMPLATES[_DEFAULT_SCENARIO_KEY])
    ctx = _dynamic_ctx(target, scenario_key)

    first_name = target.first_name or ""
    last_name = target.last_name or ""
    greeting = f"{first_name} {last_name}".strip() or "Madame/Monsieur"

    company = _extract_company_name(campaign.domain)
    from_name = tpl["from_name"]
    if tpl.get("internal") and company:
        from_name = f"{from_name} — {company}"

    company_suffix = f" — {company}" if company else ""
    raw_subject = tpl["subject"](ctx) if callable(tpl["subject"]) else tpl["subject"]
    subject: str = raw_subject.replace("{company_suffix}", company_suffix)

    html: str = tpl["html"](greeting, click_url, pixel_url, ctx)
    text: str = tpl["text"](greeting, click_url, ctx)

    from_email = settings.PHISHING_FROM_EMAIL or settings.RESEND_FROM
    from_addr = f"{from_name} <{from_email}>"
    return from_addr, subject, html, text


def _send_phishing_email(
    to_email: str,
    from_addr: str,
    subject: str,
    html: str,
    text: str,
) -> None:
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
    })


async def send_pending_batch() -> None:
    """
    Called by APScheduler every 15 min.
    Sends up to PHISHING_BATCH_SIZE pending emails for active campaigns.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Find active campaigns that still have pending targets
        campaigns_result = await db.execute(
            select(PhishingCampaign).where(
                PhishingCampaign.status.in_(["active", "sending"])
            )
        )
        campaigns = list(campaigns_result.scalars().all())

        for campaign in campaigns:
            scenario_keys: list[str] = json.loads(campaign.scenario_keys or "[]")
            scenario_key = scenario_keys[0] if scenario_keys else _DEFAULT_SCENARIO_KEY

            pending_result = await db.execute(
                select(PhishingTarget).where(
                    PhishingTarget.campaign_id == campaign.id,
                    PhishingTarget.status == "pending",
                ).limit(settings.PHISHING_BATCH_SIZE)
            )
            pending = list(pending_result.scalars().all())

            if not pending:
                # All emails sent — move to 'active' results phase
                if campaign.status == "sending":
                    campaign.status = "active"
                    campaign.updated_at = datetime.now(timezone.utc)
                continue

            sent_count = 0
            for target in pending:
                tracking_id = str(uuid.uuid4())
                from_addr, subject, html, text = _build_email(
                    campaign, target, tracking_id, scenario_key
                )
                try:
                    _send_phishing_email(target.email, from_addr, subject, html, text)
                    target.tracking_id = tracking_id
                    target.status = "email_sent"
                    campaign.emails_sent += 1
                    sent_count += 1
                except Exception as exc:
                    logger.warning(f"Failed to send phishing email (target_id={target.id}): {exc}")

            campaign.updated_at = datetime.now(timezone.utc)
            logger.info(f"Phishing batch: sent {sent_count} emails for campaign {campaign.id}")

        await db.commit()


# ---------------------------------------------------------------------------
# Campaign launch
# ---------------------------------------------------------------------------

async def launch_campaign(campaign: PhishingCampaign, db: AsyncSession) -> None:
    """Transition campaign to 'sending' — actual emails sent by APScheduler batch."""
    targets_result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
    )
    if not list(targets_result.scalars().all()):
        raise ValueError("Aucune cible uploadée pour cette campagne.")

    scenario_keys: list[str] = json.loads(campaign.scenario_keys or "[]")
    if not scenario_keys:
        raise ValueError("Aucun scénario sélectionné.")

    if not settings.RESEND_API_KEY:
        if settings.APP_ENV != "development":
            raise RuntimeError("Resend n'est pas configuré (RESEND_API_KEY manquant).")
        logger.info("DEV MODE — RESEND_API_KEY absent, campagne passée en 'sending' sans envoi réel.")

    campaign.status = "sending"
    campaign.started_at = datetime.now(timezone.utc)
    campaign.updated_at = datetime.now(timezone.utc)
    await db.flush()


# ---------------------------------------------------------------------------
# Tracking event handlers (called from public endpoints)
# ---------------------------------------------------------------------------

async def record_open(tracking_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    if target and target.status == "email_sent":
        target.status = "opened"
        campaign_result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.id == target.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.opened_count += 1
            campaign.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def record_click(tracking_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    if target and target.status in ("email_sent", "opened"):
        target.status = "clicked"
        campaign_result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.id == target.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.clicked_count += 1
            campaign.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def record_submit(tracking_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    if target and target.status != "submitted":
        target.status = "submitted"
        campaign_result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.id == target.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.submitted_count += 1
            campaign.updated_at = datetime.now(timezone.utc)
        await db.commit()


# ---------------------------------------------------------------------------
# Tracking page content
# ---------------------------------------------------------------------------

def get_pixel_gif() -> bytes:
    return _PIXEL_GIF


def get_landing_html(tracking_id: str, scenario_key: str = _DEFAULT_SCENARIO_KEY) -> str:
    base = settings.PHISHING_BASE_URL.rstrip("/")
    action = f"{base}/phishing/t/{tracking_id}/s"
    template_name = _SCENARIO_LANDING.get(scenario_key, "microsoft")
    html = _LANDING_TEMPLATES.get(template_name, _LANDING_MICROSOFT)
    return html.replace("ACTION_URL", action)


def get_awareness_html() -> str:
    return _AWARENESS_HTML
