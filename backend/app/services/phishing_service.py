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
# Email templates per scenario
# ---------------------------------------------------------------------------

_SCENARIO_TEMPLATES: dict[str, dict[str, Any]] = {
    "ceo-fraud": {
        "from_name": "Direction Générale",
        "internal": True,
        "subject": "Action requise — virement urgent",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Je vous contacte depuis mon téléphone personnel. J'ai besoin que vous confirmiez
votre disponibilité pour effectuer un virement urgent avant 17 h aujourd'hui.</p>
<p><a href="{url}" style="background:#0078d4;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Confirmer ma disponibilité</a></p>
<p>Merci de votre réactivité.</p><p>Direction Générale</p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Bonjour {first}, virement urgent requis. Confirmez : {url}",
    },
    "o365-credentials": {
        "from_name": "Microsoft 365",
        "internal": False,
        "subject": "⚠️ Votre session Microsoft 365 a expiré",
        "html": lambda first, url, pixel: f"""<div style="font-family:Arial,sans-serif;max-width:600px">
<div style="background:#0078d4;padding:20px;text-align:center">
  <span style="color:white;font-size:20px;font-weight:bold">Microsoft 365</span>
</div>
<div style="padding:30px">
<p>Bonjour {first},</p>
<p>Votre session Microsoft 365 a expiré. Pour continuer à accéder à vos emails
et fichiers, veuillez vous reconnecter immédiatement.</p>
<p><a href="{url}" style="background:#0078d4;color:white;padding:12px 24px;border-radius:4px;text-decoration:none;display:inline-block">
Se reconnecter à Microsoft 365</a></p>
<p style="color:#666;font-size:12px">Si vous ne vous reconnectez pas dans les 24 h, votre compte sera suspendu.</p>
</div></div>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Session Microsoft 365 expirée. Reconnectez-vous : {url}",
    },
    "fake-invoice": {
        "from_name": "Service Comptabilité",
        "internal": True,
        "subject": "Facture impayée #INV-2024-0847 — relance",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Nous vous contactons concernant la facture <strong>#INV-2024-0847</strong>
d'un montant de <strong>2 340 € TTC</strong> qui reste impayée à ce jour.</p>
<p><a href="{url}" style="background:#e53935;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Accéder au portail de paiement</a></p>
<p>En cas de litige, veuillez nous contacter par retour de mail.</p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Facture impayée #INV-2024-0847. Réglez sur : {url}",
    },
    "bank-phishing": {
        "from_name": "Sécurité Bancaire",
        "internal": False,
        "subject": "⚠️ Alerte de sécurité — activité suspecte détectée",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Une activité inhabituelle a été détectée sur votre compte professionnel.
Pour sécuriser votre compte, veuillez confirmer votre identité immédiatement.</p>
<p><a href="{url}" style="background:#c62828;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Sécuriser mon compte maintenant</a></p>
<p style="color:#888;font-size:12px">Si vous ne prenez pas cette mesure dans les 2 heures, votre compte sera bloqué temporairement.</p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Activité suspecte. Sécurisez votre compte : {url}",
    },
    "parcel-tracking": {
        "from_name": "Chronopost Livraison",
        "internal": False,
        "subject": "Votre colis n'a pas pu être livré — action requise",
        "html": lambda first, url, pixel: f"""<p>Bonjour,</p>
<p>Votre colis (réf. : <strong>FR7823649201</strong>) n'a pas pu être livré
en raison d'une adresse incomplète. Frais de réexpédition : <strong>2,50 €</strong>.</p>
<p><a href="{url}" style="background:#f57f17;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Reprogrammer la livraison</a></p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Colis non livré. Reprogrammer : {url}",
    },
    "it-password": {
        "from_name": "Équipe DSI",
        "internal": True,
        "subject": "[DSI{company_suffix}] Mise à jour obligatoire de votre mot de passe",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Dans le cadre de notre politique de sécurité, tous les mots de passe doivent être
renouvelés avant le 30 du mois. Merci d'agir avant expiration de votre accès.</p>
<p><a href="{url}" style="background:#1565c0;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Mettre à jour mon mot de passe</a></p>
<p>L'équipe DSI</p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Mise à jour mot de passe obligatoire : {url}",
    },
    "prize": {
        "from_name": "Service Ressources Humaines",
        "internal": True,
        "subject": "🎁 Félicitations — vous avez gagné !",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Votre participation au tirage au sort de fin d'année vous a permis de remporter
une <strong>carte cadeau Amazon de 150 €</strong>. Pour réclamer votre lot, cliquez ci-dessous.</p>
<p><a href="{url}" style="background:#2e7d32;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Réclamer mon lot</a></p>
<p style="color:#888;font-size:12px">Offre valable 48 h.</p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Vous avez gagné un lot ! Réclamez-le : {url}",
    },
    "invoice-pdf": {
        "from_name": "Service Administratif",
        "internal": True,
        "subject": "Facture PDF en pièce jointe — signature requise",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Veuillez trouver ci-joint la facture pour validation. Merci de la signer
électroniquement via notre plateforme sécurisée avant vendredi.</p>
<p><a href="{url}" style="background:#6a1b9a;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Signer la facture en ligne</a></p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Facture à signer : {url}",
    },
    "vpn-update": {
        "from_name": "Équipe Sécurité IT",
        "internal": True,
        "subject": "[URGENT{company_suffix}] Mise à jour critique du client VPN — action immédiate requise",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Une vulnérabilité critique (<strong>CVE-2024-8871</strong>) a été découverte
dans votre version du client VPN. Vous devez installer la mise à jour avant
ce soir pour continuer à accéder au réseau de l'entreprise.</p>
<p><a href="{url}" style="background:#b71c1c;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Télécharger la mise à jour VPN</a></p>
<p>L'équipe Sécurité</p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Mise à jour VPN critique : {url}",
    },
    "hr-document": {
        "from_name": "Ressources Humaines",
        "internal": True,
        "subject": "[CONFIDENTIEL{company_suffix}] Document RH — grille des salaires 2024",
        "html": lambda first, url, pixel: f"""<p>Bonjour {first},</p>
<p>Suite à la réunion de direction, la nouvelle grille des salaires 2024 est disponible.
Ce document est <strong>strictement confidentiel</strong>. Accédez-y via le portail RH sécurisé.</p>
<p><a href="{url}" style="background:#37474f;color:white;padding:10px 20px;border-radius:4px;text-decoration:none;">
Accéder au document confidentiel</a></p>
<img src="{pixel}" width="1" height="1" style="display:none" />""",
        "text": lambda first, url: f"Document RH confidentiel disponible : {url}",
    },
}

_DEFAULT_SCENARIO_KEY = "o365-credentials"

# ---------------------------------------------------------------------------
# Tracking HTML pages
# ---------------------------------------------------------------------------

_LANDING_HTML = """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Authentification requise</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#f0f2f5;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{background:#fff;padding:40px;border-radius:8px;box-shadow:0 2px 16px rgba(0,0,0,.15);width:100%;max-width:400px}
h2{font-size:20px;margin-bottom:4px;color:#1a1a2e}
p{color:#666;font-size:13px;margin-bottom:20px}
label{display:block;font-size:13px;font-weight:600;color:#333;margin-bottom:4px}
input{width:100%;padding:10px 12px;border:1px solid #ccc;border-radius:4px;font-size:14px;margin-bottom:14px}
input:focus{outline:none;border-color:#0078d4}
button{width:100%;padding:12px;background:#0078d4;color:#fff;border:none;border-radius:4px;font-size:15px;font-weight:600;cursor:pointer}
button:hover{background:#005fa3}
</style></head>
<body>
<div class="card">
  <h2>Connexion sécurisée</h2>
  <p>Veuillez vous identifier pour accéder au document.</p>
  <form method="POST" action="">
    <label>Identifiant ou adresse e-mail</label>
    <input type="text" name="username" autocomplete="username" placeholder="prenom.nom@entreprise.com" />
    <label>Mot de passe</label>
    <input type="password" name="password" autocomplete="current-password" />
    <button type="submit">Se connecter</button>
  </form>
</div>
</body></html>"""

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

    # Levier 3: full name greeting ("David Rocher" instead of just "David")
    first_name = target.first_name or ""
    last_name = target.last_name or ""
    greeting = f"{first_name} {last_name}".strip() or "Madame/Monsieur"

    # Levier 2: contextualize from_name with company for internal scenarios
    company = _extract_company_name(campaign.domain)
    from_name = tpl["from_name"]
    if tpl.get("internal") and company:
        from_name = f"{from_name} — {company}"

    # Inject {company_suffix} placeholder in subject (" — Acme" or "" when no domain)
    company_suffix = f" — {company}" if company else ""
    subject: str = tpl["subject"].replace("{company_suffix}", company_suffix)

    html: str = tpl["html"](greeting, click_url, pixel_url)
    text: str = tpl["text"](greeting, click_url)

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
                    logger.warning(f"Failed to send phishing email to {target.email}: {exc}")

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
        raise RuntimeError("Resend n'est pas configuré (RESEND_API_KEY manquant).")

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


def get_landing_html(tracking_id: str) -> str:
    base = settings.PHISHING_BASE_URL.rstrip("/")
    action = f"{base}/phishing/t/{tracking_id}/s"
    return _LANDING_HTML.replace('action=""', f'action="{action}"')


def get_awareness_html() -> str:
    return _AWARENESS_HTML
