"""
GoPhish integration service.

Responsibilities:
  - CRUD helpers for PhishingCampaign / PhishingTarget / PhishingDomainVerification
  - GoPhish REST API client (create groups, templates, pages, campaigns)
  - Domain ownership verification via DNS TXT record
  - Results polling (called by APScheduler)
"""

import csv
import io
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.phishing import PhishingCampaign, PhishingDomainVerification, PhishingTarget

# ---------------------------------------------------------------------------
# GoPhish HTTP client helpers
# ---------------------------------------------------------------------------

_GOPHISH_TIMEOUT = 15.0

# Phishing email templates per scenario key.
# Each entry has "subject", "html", "text".
_SCENARIO_TEMPLATES: dict[str, dict[str, str]] = {
    "ceo-fraud": {
        "subject": "Action requise — virement urgent",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Je vous contacte depuis mon téléphone personnel. J'ai besoin que vous effectuiez "
            "un virement urgent de 8 500 € avant 17 h aujourd'hui. Merci de confirmer votre disponibilité "
            "via le lien sécurisé ci-dessous.</p>"
            "<p><a href='{{.URL}}'>Confirmer ma disponibilité</a></p>"
            "<p>Merci de votre réactivité.</p>"
            "<p>David Martin<br>Directeur Général</p>"
        ),
        "text": "Bonjour {{.FirstName}}, virement urgent requis. Confirmez : {{.URL}}",
    },
    "o365-credentials": {
        "subject": "⚠️ Votre session Microsoft 365 a expiré",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Votre session Microsoft 365 a expiré. Pour continuer à accéder à vos emails "
            "et fichiers, veuillez vous reconnecter immédiatement.</p>"
            "<p><a href='{{.URL}}'>Se reconnecter à Microsoft 365</a></p>"
            "<p>Si vous ne vous reconnectez pas dans les 24 h, votre compte sera suspendu.</p>"
            "<p>L'équipe IT</p>"
        ),
        "text": "Session Microsoft 365 expirée. Reconnectez-vous : {{.URL}}",
    },
    "fake-invoice": {
        "subject": "Facture impayée #INV-2024-0847 — relance",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Nous vous contactons concernant la facture #INV-2024-0847 d'un montant de 2 340 € TTC "
            "qui reste impayée à ce jour. Merci de procéder au règlement via notre portail sécurisé.</p>"
            "<p><a href='{{.URL}}'>Accéder au portail de paiement</a></p>"
            "<p>En cas de litige, veuillez nous contacter.</p>"
        ),
        "text": "Facture impayée #INV-2024-0847. Réglez sur : {{.URL}}",
    },
    "bank-phishing": {
        "subject": "Alerte de sécurité — activité suspecte détectée",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Une activité inhabituelle a été détectée sur votre compte professionnel. "
            "Pour sécuriser votre compte, veuillez confirmer votre identité immédiatement.</p>"
            "<p><a href='{{.URL}}'>Sécuriser mon compte</a></p>"
            "<p>Si vous ne prenez pas cette mesure dans les 2 heures, votre compte sera temporairement bloqué.</p>"
        ),
        "text": "Activité suspecte sur votre compte. Sécurisez-le : {{.URL}}",
    },
    "parcel-tracking": {
        "subject": "Votre colis n'a pas pu être livré — action requise",
        "html": (
            "<p>Bonjour,</p>"
            "<p>Votre colis (référence: FR7823649201) n'a pas pu être livré en raison d'une adresse incomplète. "
            "Pour programmer une nouvelle livraison, veuillez vérifier et compléter vos informations.</p>"
            "<p><a href='{{.URL}}'>Reprogrammer la livraison</a></p>"
            "<p>Frais de réexpédition : 2,50 €</p>"
        ),
        "text": "Colis non livré. Reprogrammer : {{.URL}}",
    },
    "it-password": {
        "subject": "[IT] Mise à jour obligatoire de votre mot de passe",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Dans le cadre de notre politique de sécurité, tous les mots de passe doivent être "
            "renouvelés avant le 30 du mois. Merci de mettre à jour votre mot de passe via le "
            "portail RH interne.</p>"
            "<p><a href='{{.URL}}'>Mettre à jour mon mot de passe</a></p>"
            "<p>L'équipe DSI</p>"
        ),
        "text": "Mise à jour mot de passe obligatoire : {{.URL}}",
    },
    "prize": {
        "subject": "Félicitations ! Vous avez gagné un lot",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Votre participation au tirage au sort de fin d'année vous a permis de gagner "
            "une carte cadeau Amazon de 150 €. Pour réclamer votre lot, cliquez ci-dessous.</p>"
            "<p><a href='{{.URL}}'>Réclamer mon lot</a></p>"
            "<p>Offre valable 48 h.</p>"
        ),
        "text": "Vous avez gagné un lot ! Réclamez-le : {{.URL}}",
    },
    "invoice-pdf": {
        "subject": "Facture PDF en pièce jointe — à valider",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Veuillez trouver ci-joint la facture pour validation. "
            "Merci de la signer électroniquement via notre plateforme sécurisée.</p>"
            "<p><a href='{{.URL}}'>Signer la facture</a></p>"
        ),
        "text": "Facture à signer : {{.URL}}",
    },
    "vpn-update": {
        "subject": "[URGENT] Mise à jour critique du client VPN — action immédiate requise",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Une vulnérabilité critique (CVE-2024-8871) a été découverte dans votre version "
            "du client VPN. Vous devez installer la mise à jour immédiatement pour continuer "
            "à accéder au réseau de l'entreprise.</p>"
            "<p><a href='{{.URL}}'>Télécharger la mise à jour</a></p>"
            "<p>L'équipe Sécurité</p>"
        ),
        "text": "Mise à jour VPN critique : {{.URL}}",
    },
    "hr-document": {
        "subject": "Document RH confidentiel — grille des salaires 2024",
        "html": (
            "<p>Bonjour {{.FirstName}},</p>"
            "<p>Suite à la réunion de direction, la nouvelle grille des salaires 2024 est disponible. "
            "Ce document est strictement confidentiel. Merci d'y accéder via le portail RH sécurisé.</p>"
            "<p><a href='{{.URL}}'>Accéder au document confidentiel</a></p>"
        ),
        "text": "Document RH confidentiel disponible : {{.URL}}",
    },
}

_LANDING_PAGE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Authentification requise</title>
<style>
  body{font-family:Arial,sans-serif;max-width:400px;margin:60px auto;padding:20px;background:#f5f5f5;}
  .card{background:#fff;padding:30px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}
  input{width:100%;padding:10px;margin:8px 0;border:1px solid #ddd;border-radius:4px;box-sizing:border-box;}
  button{width:100%;padding:12px;background:#0078d4;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:16px;}
</style>
</head>
<body>
<div class="card">
  <h2>Connexion sécurisée</h2>
  <form method="POST" action="">
    {{.Form}}
    <input type="text" name="username" placeholder="Identifiant ou e-mail" />
    <input type="password" name="password" placeholder="Mot de passe" />
    <button type="submit">Se connecter</button>
  </form>
</div>
</body>
</html>"""

_REDIRECT_PAGE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Exercice de cybersécurité</title>
<style>
  body{font-family:Arial,sans-serif;max-width:600px;margin:60px auto;padding:20px;background:#f5f5f5;text-align:center;}
  .card{background:#fff;padding:40px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}
  .icon{font-size:64px;}
  h1{color:#d32f2f;}
  .tips{text-align:left;background:#f9f9f9;padding:20px;border-radius:6px;margin-top:20px;}
</style>
</head>
<body>
<div class="card">
  <div class="icon">⚠️</div>
  <h1>Exercice de cybersécurité</h1>
  <p>Vous venez de cliquer sur un <strong>lien de phishing simulé</strong> dans le cadre d'un
  exercice de sensibilisation organisé par votre entreprise.</p>
  <p>Aucune donnée réelle n'a été capturée. Votre vigilance contribue à la sécurité collective.</p>
  <div class="tips">
    <strong>3 réflexes anti-phishing :</strong>
    <ol>
      <li>Vérifiez toujours l'adresse de l'expéditeur avant de cliquer</li>
      <li>Survolez les liens pour voir l'URL réelle avant de cliquer</li>
      <li>En cas de doute, contactez directement la personne par téléphone</li>
    </ol>
  </div>
</div>
</body>
</html>"""


def _gophish_headers() -> dict[str, str]:
    return {"Authorization": settings.GOPHISH_API_KEY, "Content-Type": "application/json"}


def _gophish_available() -> bool:
    return bool(settings.GOPHISH_API_URL and settings.GOPHISH_API_KEY)


async def _gophish_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(verify=False, timeout=_GOPHISH_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.GOPHISH_API_URL.rstrip('/')}{path}",
            json=payload,
            headers=_gophish_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def _gophish_get(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(verify=False, timeout=_GOPHISH_TIMEOUT) as client:
        resp = await client.get(
            f"{settings.GOPHISH_API_URL.rstrip('/')}{path}",
            headers=_gophish_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def _gophish_delete(path: str) -> None:
    async with httpx.AsyncClient(verify=False, timeout=_GOPHISH_TIMEOUT) as client:
        resp = await client.delete(
            f"{settings.GOPHISH_API_URL.rstrip('/')}{path}",
            headers=_gophish_headers(),
        )
        resp.raise_for_status()


# ---------------------------------------------------------------------------
# Domain verification
# ---------------------------------------------------------------------------

async def request_domain_verification(
    user_id: int, domain: str, db: AsyncSession
) -> PhishingDomainVerification:
    """Create or reuse a verification record for (user_id, domain)."""
    result = await db.execute(
        select(PhishingDomainVerification)
        .where(
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
    """Check the DNS TXT record and update the verification status."""
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


async def create_campaign(
    user_id: int,
    name: str,
    plan_tier: str,
    db: AsyncSession,
) -> PhishingCampaign:
    campaign = PhishingCampaign(
        user_id=user_id,
        name=name,
        plan_tier=plan_tier,
        status="draft",
    )
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
    campaign: PhishingCampaign,
    csv_content: str,
    db: AsyncSession,
) -> int:
    """Parse CSV and replace all targets for this campaign. Returns number of targets added."""
    # Delete existing targets
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
# GoPhish campaign launch
# ---------------------------------------------------------------------------

async def launch_campaign(campaign: PhishingCampaign, db: AsyncSession) -> None:
    """Create all GoPhish objects and launch the campaign."""
    if not _gophish_available():
        raise RuntimeError("GoPhish n'est pas configuré sur ce serveur.")

    targets_result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
    )
    targets = list(targets_result.scalars().all())
    if not targets:
        raise ValueError("Aucune cible uploadée pour cette campagne.")

    scenario_keys: list[str] = json.loads(campaign.scenario_keys or "[]")
    if not scenario_keys:
        raise ValueError("Aucun scénario sélectionné.")
    scenario_key = scenario_keys[0]
    template_data = _SCENARIO_TEMPLATES.get(scenario_key, _SCENARIO_TEMPLATES["o365-credentials"])

    unique_suffix = secrets.token_hex(4)
    group_name = f"CyberScan-{campaign.id}-{unique_suffix}"
    template_name = f"CyberScan-TPL-{campaign.id}-{unique_suffix}"
    page_name = f"CyberScan-PAGE-{campaign.id}-{unique_suffix}"

    # 1 — Create target group
    group_payload = {
        "name": group_name,
        "targets": [
            {
                "email": t.email,
                "first_name": t.first_name or "",
                "last_name": t.last_name or "",
                "position": t.department or "",
            }
            for t in targets
        ],
    }
    group_resp = await _gophish_post("/api/groups/", group_payload)
    gophish_group_id = group_resp["id"]

    # 2 — Create email template
    template_payload = {
        "name": template_name,
        "subject": template_data["subject"],
        "html": template_data["html"],
        "text": template_data["text"],
    }
    template_resp = await _gophish_post("/api/templates/", template_payload)
    gophish_template_id = template_resp["id"]

    # 3 — Create landing page
    page_payload = {
        "name": page_name,
        "html": _LANDING_PAGE_HTML,
        "capture_credentials": True,
        "capture_passwords": False,
        "redirect_url": "",
    }
    # Embed the redirect awareness page as custom HTML response
    page_payload["html"] = _LANDING_PAGE_HTML
    page_resp = await _gophish_post("/api/pages/", page_payload)
    gophish_page_id = page_resp["id"]

    # 4 — Create campaign
    launch_time = campaign.scheduled_at or datetime.now(timezone.utc)
    campaign_payload = {
        "name": f"CyberScan #{campaign.id} — {campaign.name}",
        "template": {"name": template_name},
        "page": {"name": page_name},
        "url": settings.GOPHISH_PHISHING_URL or "https://cyberscan-sim.com",
        "smtp": {"name": settings.GOPHISH_SMTP_PROFILE},
        "launch_date": launch_time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "send_by_date": None,
        "groups": [{"name": group_name}],
    }
    campaign_resp = await _gophish_post("/api/campaigns/", campaign_payload)
    gophish_campaign_id = campaign_resp["id"]

    # Update local DB
    campaign.gophish_campaign_id = gophish_campaign_id
    campaign.gophish_group_id = gophish_group_id
    campaign.gophish_template_id = gophish_template_id
    campaign.gophish_page_id = gophish_page_id
    campaign.status = "active"
    campaign.started_at = datetime.now(timezone.utc)
    campaign.updated_at = datetime.now(timezone.utc)
    await db.flush()


# ---------------------------------------------------------------------------
# Results polling (called by APScheduler)
# ---------------------------------------------------------------------------

async def sync_active_campaigns() -> None:
    """Fetch GoPhish results for all active campaigns and update the DB."""
    if not _gophish_available():
        return

    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.status == "active")
        )
        campaigns = list(result.scalars().all())

        for campaign in campaigns:
            if not campaign.gophish_campaign_id:
                continue
            try:
                data = await _gophish_get(f"/api/campaigns/{campaign.gophish_campaign_id}")
                stats = data.get("stats", {})
                campaign.emails_sent = stats.get("sent", 0)
                campaign.opened_count = stats.get("opened", 0)
                campaign.clicked_count = stats.get("clicked", 0)
                campaign.submitted_count = stats.get("submitted_data", 0)
                campaign.updated_at = datetime.now(timezone.utc)

                # Mark completed if GoPhish status is "Completed"
                if data.get("status") == "Completed":
                    campaign.status = "completed"
                    campaign.finished_at = datetime.now(timezone.utc)

                # Sync individual target statuses
                results_list = data.get("results", [])
                target_map: dict[str, PhishingTarget] = {}
                t_result = await db.execute(
                    select(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
                )
                for t in t_result.scalars().all():
                    target_map[t.email.lower()] = t

                for r in results_list:
                    email = r.get("email", "").lower()
                    if email in target_map:
                        gp_status = r.get("status", "")
                        target_map[email].status = _map_gophish_status(gp_status)

            except Exception as exc:
                logger.warning(f"GoPhish sync failed for campaign {campaign.id}: {exc}")

        await db.commit()


def _map_gophish_status(gp_status: str) -> str:
    mapping = {
        "Email Sent": "email_sent",
        "Email Opened": "opened",
        "Clicked Link": "clicked",
        "Submitted Data": "submitted",
        "Email Reported": "reported",
    }
    return mapping.get(gp_status, "pending")
