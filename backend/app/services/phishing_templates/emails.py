"""Templates emails phishing (_tpl_*) + registre _SCENARIO_TEMPLATES."""

from typing import Any

from .engine import _attachment_badge, _email_wrap


def _tpl_ceo_fraud(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    amount, deadline = ctx["ceo_amount"], ctx["ceo_deadline"]
    body = (
        f'<p style="color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 14px">Bonjour {greeting},</p>'
        f"<p style=\"color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 14px\">Je vous écris depuis mon téléphone personnel — je suis en réunion externe jusqu'en fin de matinée. J'ai besoin de votre aide pour une opération confidentielle.</p>"
        f"<p style=\"color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 14px\">Un virement de <strong>{amount}</strong> doit être exécuté <strong>{deadline}</strong> aujourd'hui. L'opération est urgente et ne doit pas être évoquée en interne pour l'instant.</p>"
        f'<p style="color:#1a1a1a;font-size:15px;line-height:1.6;margin:0 0 24px">Confirmez-moi votre disponibilité et je vous transmets les coordonnées bancaires.</p>'
        f'{_attachment_badge("Mandat_virement.pdf")}<p><a href="{url}" style="display:inline-block;background:#1a73e8;color:#fff;padding:12px 26px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Confirmer ma disponibilité</a></p>'
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
        "</svg>"
    )
    body = (
        f'<p style="color:#323130;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<table width="100%" cellpadding="14" cellspacing="0" style="background:#fff4ce;border-left:4px solid #ffb900;margin:0 0 20px">'
        f'<tr><td><p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#323130">&#9888;&#65039; Connexion inhabituelle détectée</p>'
        f'<p style="margin:0 0 4px;font-size:13px;color:#605e5c"><strong>Appareil&nbsp;:</strong> {device}</p>'
        f'<p style="margin:0 0 4px;font-size:13px;color:#605e5c"><strong>Localisation&nbsp;:</strong> {location}</p>'
        f'<p style="margin:0;font-size:13px;color:#605e5c"><strong>Heure&nbsp;:</strong> Aujourd\'hui, il y a quelques minutes</p>'
        f"</td></tr></table>"
        f"<p style=\"color:#323130;font-size:15px;line-height:1.6;margin:0 0 20px\">Si vous n'êtes pas à l'origine de cette connexion, votre compte sera <strong>restreint dans 24&nbsp;heures</strong>.</p>"
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
        f"</table>"
        f'{_attachment_badge(f"Facture_{ref}.pdf")}<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#e53935;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Accéder au portail de paiement</a></p>'
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
        f"</td></tr></table>"
        f'<table width="100%" cellpadding="10" cellspacing="0" style="border:1px solid #e0e0e0;border-radius:4px;margin:0 0 24px">'
        f'<tr style="background:#fafafa"><td colspan="2" style="padding:10px 14px;font-size:12px;color:#888;border-bottom:1px solid #eee;font-weight:700">TRANSACTION DÉTECTÉE</td></tr>'
        f'<tr><td style="padding:10px 14px;font-size:14px;color:#555">Montant</td><td style="padding:10px 14px;font-size:14px;color:#e53935;font-weight:700">{amount}</td></tr>'
        f'<tr style="background:#fafafa"><td style="padding:10px 14px;font-size:14px;color:#555">Statut</td><td style="padding:10px 14px;font-size:14px;color:#e53935">En attente de validation</td></tr>'
        f"</table>"
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
    carrier_colors = {
        "Chronopost": "#ff6600",
        "Colissimo": "#003189",
        "DPD France": "#dc0032",
    }
    color = carrier_colors.get(carrier, "#e65100")
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour,</p>'
        f"<p style=\"color:#333;font-size:15px;line-height:1.6;margin:0 0 16px\">Nous avons tenté de livrer votre colis aujourd'hui mais la livraison a échoué en raison d'une <strong>adresse incomplète</strong>.</p>"
        f'<table width="100%" cellpadding="10" cellspacing="0" style="border:1px solid #e0e0e0;border-radius:4px;margin:0 0 24px;background:#f9f9f9">'
        f'<tr><td style="padding:12px 16px;font-size:14px;color:#555">Référence colis</td><td style="padding:12px 16px;font-size:14px;color:#333;font-weight:700">{ref}</td></tr>'
        f'<tr style="background:#fff"><td style="padding:12px 16px;font-size:14px;color:#555">Statut</td><td style="padding:12px 16px;font-size:14px;color:#e65100;font-weight:600">Livraison échouée</td></tr>'
        f'<tr><td style="padding:12px 16px;font-size:14px;color:#555">Frais de réexpédition</td><td style="padding:12px 16px;font-size:15px;font-weight:700">{fee}</td></tr>'
        f"</table>"
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
        f"</td></tr></table>"
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
        f"</div>"
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
        f"</td></tr></table>"
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Ce document requiert votre signature. Merci de le signer via notre plateforme sécurisée avant la date limite.</p>'
        f'{_attachment_badge(f"{ref}_document.pdf")}<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#f5a81c;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:700">&#9998; Signer le document</a></p>'
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
        f"</td></tr></table>"
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Une faille critique a été découverte dans votre version du client VPN. Des attaquants exploitent activement cette vulnérabilité pour accéder aux réseaux d\'entreprise.</p>'
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px"><strong>Vous devez installer la mise à jour avant ce soir</strong> pour conserver votre accès aux ressources internes.</p>'
        f'{_attachment_badge(f"VPN_patch_{cve}.exe", "EXE")}<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#b71c1c;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:700">&#128274; Télécharger la mise à jour</a></p>'
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
        f"</td></tr></table>"
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 20px">Ce document est <strong>strictement confidentiel</strong>. Accédez-y via le portail RH sécurisé — il expire dans 72&nbsp;h.</p>'
        f'{_attachment_badge("Grille_rémunération_2025.xlsx", "XLSX")}<p style="margin:0 0 20px"><a href="{url}" style="display:inline-block;background:#37474f;color:#fff;padding:13px 28px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">&#128194; Accéder au document</a></p>'
        f'<p style="color:#555;font-size:14px;margin:0;line-height:1.5">Direction des Ressources Humaines</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"Grille des salaires +{pct} disponible — accès confidentiel 72h",
        brand_bg="#37474f",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128101; Direction des Ressources Humaines</span>',
        body_html=body,
    )


def _tpl_teams(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    sender = ctx["teams_sender"]
    initial = ctx["teams_initial"]
    channel = ctx["teams_channel"]
    preview = ctx["teams_preview"]
    dept = ctx.get("dept", "")
    dept_tag = f" &bull; {dept}" if dept else ""
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<p style="color:#555;font-size:14px;margin:0 0 16px">Vous avez reçu un'
        f' <strong style="color:#6264a7">message non lu</strong> dans Microsoft Teams{dept_tag}.</p>'
        f'<table width="100%" cellpadding="0" cellspacing="0"'
        f' style="background:#f9f9f9;border:1px solid #e0e0e0;border-radius:6px;margin:0 0 20px">'
        f'<tr><td style="padding:14px">'
        f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="width:40px;vertical-align:top;padding-right:12px">'
        f'<div style="width:36px;height:36px;background:#6264a7;border-radius:50%;text-align:center;line-height:36px;color:#fff;font-size:14px;font-weight:700">{initial}</div>'
        f'</td><td style="vertical-align:top">'
        f'<p style="margin:0 0 2px;font-size:13px;font-weight:700;color:#333">{sender}</p>'
        f'<p style="margin:0 0 4px;font-size:12px;color:#888">Canal : <strong>#{channel}</strong></p>'
        f'<p style="margin:0;font-size:13px;color:#555;font-style:italic">&laquo; {preview} &raquo;</p>'
        f"</td></tr></table></td></tr>"
        f'<tr><td style="padding:0 14px 14px">'
        f'<span style="background:#fef3c7;color:#d97706;font-size:12px;font-weight:600;padding:2px 8px;border-radius:10px">&#128206; 1 pièce jointe</span>'
        f"</td></tr></table>"
        f'<p style="margin:0 0 20px"><a href="{url}"'
        f' style="display:inline-block;background:#6264a7;color:#fff;padding:12px 26px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">Voir dans Teams</a></p>'
        f'<p style="color:#888;font-size:12px;margin:0">Vous recevez cet e-mail car les notifications Teams sont activées.</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"{sender} vous a envoyé un message dans #{channel}",
        brand_bg="#6264a7",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128172; Microsoft Teams</span>',
        body_html=body,
        footer_html='<p style="color:#aaa;font-size:11px;margin:0">© Microsoft Corporation · <a href="#" style="color:#aaa">Se désabonner des notifications</a></p>',
    )


def _tpl_sharepoint(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    sender = ctx["sp_sender"]
    sp_file = ctx["sp_file"]
    sp_size = ctx["sp_size"]
    dept = ctx.get("dept", "")
    dept_tag = f" ({dept})" if dept else ""
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<p style="color:#555;font-size:14px;margin:0 0 16px"><strong>{sender}</strong> a partagé un document'
        f" avec vous via Microsoft SharePoint{dept_tag}.</p>"
        f'<table width="100%" cellpadding="16" cellspacing="0"'
        f' style="background:#f0f4ff;border-radius:6px;border:1px solid #c7d2fe;margin:0 0 20px">'
        f'<tr><td style="width:48px;vertical-align:middle;padding-right:16px">'
        f'<div style="width:42px;height:42px;background:#0078d4;border-radius:8px;text-align:center;line-height:42px;color:#fff;font-size:22px">&#128196;</div>'
        f'</td><td style="vertical-align:middle">'
        f'<p style="margin:0 0 4px;font-size:14px;font-weight:700;color:#333">{sp_file}</p>'
        f'<p style="margin:0;font-size:12px;color:#888">{sp_size} · Partagé par <strong>{sender}</strong></p>'
        f"</td></tr></table>"
        f'<p style="color:#333;font-size:14px;line-height:1.5;margin:0 0 20px">Cliquez ci-dessous pour ouvrir'
        f" le document. Vous devrez vous connecter avec votre compte Microsoft.</p>"
        f'<p style="margin:0 0 20px"><a href="{url}"'
        f' style="display:inline-block;background:#0078d4;color:#fff;padding:12px 26px;border-radius:2px;text-decoration:none;font-size:15px;font-weight:600">Ouvrir dans SharePoint</a></p>'
        f'<p style="color:#888;font-size:12px;margin:0">Ce document a été partagé via Microsoft SharePoint Online.</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"{sender} a partagé « {sp_file} » avec vous",
        brand_bg="#0078d4",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128193; Microsoft SharePoint</span>',
        body_html=body,
        footer_html='<p style="color:#aaa;font-size:11px;margin:0">© Microsoft Corporation · <a href="#" style="color:#aaa">Confidentialité</a></p>',
    )


def _tpl_it_ticket(greeting: str, url: str, pixel: str, ctx: dict) -> str:
    ticket_num = ctx["ticket_num"]
    ticket_subject = ctx["ticket_subject"]
    dept = ctx.get("dept", "")
    dept_row = (
        (
            f'<tr><td style="padding:10px 16px;font-size:13px;color:#888;border-bottom:1px solid #f0f0f0">Service</td>'
            f'<td style="padding:10px 16px;font-size:13px;color:#333;border-bottom:1px solid #f0f0f0">{dept}</td></tr>'
        )
        if dept
        else ""
    )
    body = (
        f'<p style="color:#333;font-size:15px;line-height:1.6;margin:0 0 16px">Bonjour {greeting},</p>'
        f'<p style="color:#555;font-size:14px;margin:0 0 16px">Un ticket d’assistance vous a été assigné et nécessite votre action immédiate.</p>'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0e0e0;border-radius:4px;margin:0 0 20px;overflow:hidden">'
        f'<tr style="background:#f5f5f5"><td colspan="2" style="padding:10px 16px;border-bottom:1px solid #e0e0e0">'
        f'<span style="font-size:12px;font-weight:700;color:#555;letter-spacing:.5px">TICKET D’ASSISTANCE IT</span></td></tr>'
        f'<tr><td style="padding:10px 16px;font-size:13px;color:#888;width:35%;border-bottom:1px solid #f0f0f0">Numéro</td>'
        f'<td style="padding:10px 16px;font-size:13px;color:#333;font-weight:700;border-bottom:1px solid #f0f0f0">{ticket_num}</td></tr>'
        f'<tr style="background:#fafafa"><td style="padding:10px 16px;font-size:13px;color:#888;border-bottom:1px solid #f0f0f0">Sujet</td>'
        f'<td style="padding:10px 16px;font-size:13px;color:#333;border-bottom:1px solid #f0f0f0">{ticket_subject}</td></tr>'
        + dept_row
        + f'<tr><td style="padding:10px 16px;font-size:13px;color:#888;border-bottom:1px solid #f0f0f0">Priorité</td>'
        f'<td style="padding:10px 16px;border-bottom:1px solid #f0f0f0">'
        f'<span style="background:#fdecea;color:#c62828;font-size:12px;font-weight:700;padding:2px 8px;border-radius:2px">HAUTE</span></td></tr>'
        f'<tr style="background:#fafafa"><td style="padding:10px 16px;font-size:13px;color:#888">Délai</td>'
        f'<td style="padding:10px 16px;font-size:13px;color:#e65100;font-weight:600">Avant fin de journée</td></tr>'
        f"</table>"
        f'<p style="margin:0 0 20px"><a href="{url}"'
        f' style="display:inline-block;background:#1565c0;color:#fff;padding:12px 26px;border-radius:4px;text-decoration:none;font-size:15px;font-weight:600">&#128187; Traiter le ticket</a></p>'
        f'<p style="color:#555;font-size:13px;margin:0">Portail IT — Helpdesk DSI · Ne répondez pas à cet e-mail.</p>'
        f'<img src="{pixel}" width="1" height="1" style="display:none">'
    )
    return _email_wrap(
        preheader=f"[{ticket_num}] {ticket_subject} — action requise avant fin de journée",
        brand_bg="#1565c0",
        brand_html='<span style="color:#fff;font-size:17px;font-weight:700">&#128187; Helpdesk DSI — Ticket</span>',
        body_html=body,
    )


_SCENARIO_TEMPLATES: dict[str, dict[str, Any]] = {
    "ceo-fraud": {
        "from_name": "Direction Générale",
        "internal": True,
        "subject": lambda ctx: (
            f"Action requise — virement urgent {ctx['ceo_amount']}"
            if ctx["ab_variant"] == 0
            else f"Confidentiel — transfert {ctx['ceo_amount']} {ctx['ceo_deadline']}"
        ),
        "html": _tpl_ceo_fraud,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, virement urgent {ctx['ceo_amount']} requis {ctx['ceo_deadline']}. Confirmez : {url}"
        ),
    },
    "o365-credentials": {
        "from_name": "Microsoft 365",
        "internal": False,
        "subject": lambda ctx: (
            f"⚠️ Connexion suspecte depuis {ctx['o365_location']} — sécurisez votre compte"
            if ctx["ab_variant"] == 0
            else f"Alerte sécurité : accès non autorisé depuis {ctx['o365_device']}"
        ),
        "html": _tpl_o365,
        "text": lambda g, url, ctx: (
            f"Connexion suspecte depuis {ctx['o365_location']}. Sécurisez votre compte Microsoft 365 : {url}"
        ),
    },
    "fake-invoice": {
        "from_name": "Service Comptabilité",
        "internal": True,
        "subject": lambda ctx: (
            f"Facture impayée {ctx['invoice_ref']} — {ctx['invoice_amount']} TTC — relance"
        ),
        "html": _tpl_fake_invoice,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, facture {ctx['invoice_ref']} ({ctx['invoice_amount']}) impayée. Portail de paiement : {url}"
        ),
    },
    "bank-phishing": {
        "from_name": "Sécurité Bancaire",
        "internal": False,
        "subject": lambda ctx: (
            f"⚠️ [{ctx['bank_name']}] Transaction suspecte de {ctx['bank_amount']} détectée"
        ),
        "html": _tpl_bank,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, transaction suspecte {ctx['bank_amount']} sur ••••{ctx['bank_last4']}. Bloquez maintenant : {url}"
        ),
    },
    "parcel-tracking": {
        "from_name": "Service Livraison",
        "internal": False,
        "subject": lambda ctx: (
            f"[{ctx['parcel_carrier']}] Colis {ctx['parcel_ref']} non livré — action requise"
        ),
        "html": _tpl_parcel,
        "text": lambda g, url, ctx: (
            f"Colis {ctx['parcel_ref']} non livré. Frais {ctx['parcel_fee']}. Reprogrammez : {url}"
        ),
    },
    "it-password": {
        "from_name": "Équipe DSI",
        "internal": True,
        "subject": lambda ctx: (
            f"[DSI{{company_suffix}}] Mot de passe expire dans {ctx['pw_days']} — renouvellement obligatoire"
        ),
        "html": _tpl_it_password,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, votre mot de passe expire dans {ctx['pw_days']}. Renouveler : {url}"
        ),
    },
    "prize": {
        "from_name": "Service Ressources Humaines",
        "internal": True,
        "subject": lambda ctx: (
            f"\U0001f381 Félicitations — vous avez gagné une carte cadeau {ctx['prize_amount']} € !"
        ),
        "html": _tpl_prize,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, vous avez gagné une carte cadeau Amazon de {ctx['prize_amount']}€. Réclamez-la : {url}"
        ),
    },
    "invoice-pdf": {
        "from_name": "Service Administratif",
        "internal": True,
        "subject": lambda ctx: (
            f"Document {ctx['doc_ref']} — signature requise avant {ctx['doc_deadline']}"
        ),
        "html": _tpl_invoice_pdf,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, document {ctx['doc_ref']} à signer avant {ctx['doc_deadline']} : {url}"
        ),
    },
    "vpn-update": {
        "from_name": "Équipe Sécurité IT",
        "internal": True,
        "subject": lambda ctx: (
            f"[URGENT{{company_suffix}}] {ctx['cve_id']} — mise à jour VPN critique (CVSS {ctx['cvss']}/10)"
        ),
        "html": _tpl_vpn_update,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, vulnérabilité critique {ctx['cve_id']} (CVSS {ctx['cvss']}). Mettez à jour votre VPN : {url}"
        ),
    },
    "hr-document": {
        "from_name": "Ressources Humaines",
        "internal": True,
        "subject": lambda ctx: (
            f"[CONFIDENTIEL{{company_suffix}}] Grille des salaires — revalorisation {ctx['salary_pct']}"
            if ctx["ab_variant"] == 0
            else f"[RH{{company_suffix}}] Votre augmentation {ctx['salary_pct']} — document disponible"
        ),
        "html": _tpl_hr_document,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, nouvelle grille des salaires ({ctx['salary_pct']}) disponible : {url}"
        ),
    },
    "teams-message": {
        "from_name": "Microsoft Teams",
        "internal": False,
        "subject": lambda ctx: (
            f"[Teams] {ctx['teams_sender']} vous a envoyé un message dans #{ctx['teams_channel']}"
            if ctx["ab_variant"] == 0
            else f"💬 Nouveau message Teams de {ctx['teams_sender']} — 1 pièce jointe"
        ),
        "html": _tpl_teams,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, {ctx['teams_sender']} vous a envoyé un message dans #{ctx['teams_channel']}. Voir : {url}"
        ),
    },
    "sharepoint-share": {
        "from_name": "Microsoft SharePoint",
        "internal": False,
        "subject": lambda ctx: (
            f"{ctx['sp_sender']} a partagé « {ctx['sp_file']} » avec vous"
            if ctx["ab_variant"] == 0
            else f"[SharePoint] Document partagé : {ctx['sp_file']} ({ctx['sp_size']})"
        ),
        "html": _tpl_sharepoint,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, {ctx['sp_sender']} a partagé {ctx['sp_file']} avec vous. Ouvrir : {url}"
        ),
    },
    "it-ticket": {
        "from_name": "Équipe DSI",
        "internal": True,
        "subject": lambda ctx: (
            f"[{ctx['ticket_num']}] {ctx['ticket_subject']} — action requise"
            if ctx["ab_variant"] == 0
            else f"Ticket HAUTE priorité : {ctx['ticket_subject']} ({ctx['ticket_num']})"
        ),
        "html": _tpl_it_ticket,
        "text": lambda g, url, ctx: (
            f"Bonjour {g}, ticket {ctx['ticket_num']} : {ctx['ticket_subject']}. Traiter : {url}"
        ),
    },
}
