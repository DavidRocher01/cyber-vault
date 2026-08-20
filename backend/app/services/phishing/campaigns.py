"""Campagnes et cibles — creation, mise a jour, import CSV."""

import csv
import io
import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CampaignStatus
from app.models.phishing import (
    PhishingCampaign,
    PhishingTarget,
)
from app.services.phishing.templates import (
    get_awareness_html as get_awareness_html,  # re-export (facade service)
)
from app.services.phishing.templates import (
    get_expired_html as get_expired_html,
)
from app.services.phishing.templates import (
    get_landing_html as get_landing_html,
)
from app.services.phishing.templates import (
    get_pixel_gif as get_pixel_gif,
)

# ---------------------------------------------------------------------------
# Campaign CRUD
# ---------------------------------------------------------------------------


async def get_campaigns(
    user_id: int,
    db: AsyncSession,
    *,
    rssi_client_id: int | None = None,
    company_only: bool = False,
) -> list[PhishingCampaign]:
    """Campagnes du propriétaire, filtrées par mode :
    - rssi_client_id renseigné → campagnes de ce client (mode consultant) ;
    - company_only=True → campagnes sans client (mode entreprise directe) ;
    - sinon → toutes celles du propriétaire.
    """
    query = select(PhishingCampaign).where(PhishingCampaign.user_id == user_id)
    if rssi_client_id is not None:
        query = query.where(PhishingCampaign.rssi_client_id == rssi_client_id)
    elif company_only:
        query = query.where(PhishingCampaign.rssi_client_id.is_(None))
    result = await db.execute(query.order_by(PhishingCampaign.created_at.desc()))
    return list(result.scalars().all())


async def get_campaign(campaign_id: int, user_id: int, db: AsyncSession) -> PhishingCampaign | None:
    result = await db.execute(
        select(PhishingCampaign).where(
            PhishingCampaign.id == campaign_id,
            PhishingCampaign.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_targets(campaign_id: int, db: AsyncSession) -> list[PhishingTarget]:
    """Cibles d'une campagne (ordre d'insertion)."""
    result = await db.execute(
        select(PhishingTarget)
        .where(PhishingTarget.campaign_id == campaign_id)
        .order_by(PhishingTarget.id)
    )
    return list(result.scalars().all())


async def delete_campaign(campaign: PhishingCampaign, db: AsyncSession) -> None:
    """Supprime la campagne (cibles supprimées en cascade via la relation ORM)."""
    await db.delete(campaign)


async def create_campaign(
    user_id: int,
    name: str,
    plan_tier: str,
    db: AsyncSession,
    *,
    rssi_client_id: int | None = None,
) -> PhishingCampaign:
    campaign = PhishingCampaign(
        user_id=user_id,
        name=name,
        plan_tier=plan_tier,
        status=CampaignStatus.DRAFT,
        rssi_client_id=rssi_client_id,
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
    lookalike_domain: str | None = None,
    scenario_keys: list[str] | None = None,
    cgu_accepted: bool | None = None,
    scheduled_at: datetime | None = None,
    status: str | None = None,
    training_on_fail: bool | None = None,
    training_trigger: str | None = None,
    batch_size: int | None = None,
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
    if training_on_fail is not None:
        campaign.training_on_fail = training_on_fail
    if training_trigger is not None:
        campaign.training_trigger = training_trigger
    if batch_size is not None:
        campaign.batch_size = batch_size
    if scheduled_at is not None:
        campaign.scheduled_at = scheduled_at
    if status is not None:
        campaign.status = status
    campaign.updated_at = datetime.now(UTC)
    await db.flush()
    return campaign


async def cancel_campaign(campaign: PhishingCampaign, db: AsyncSession) -> PhishingCampaign:
    """Annule une campagne : le statut "cancelled" l'exclut du batch (qui ne
    traite que scheduled/active/sending) — plus aucun email ne partira."""
    campaign.status = CampaignStatus.CANCELLED
    campaign.finished_at = datetime.now(UTC)
    campaign.updated_at = datetime.now(UTC)
    await db.flush()
    return campaign


async def _recount_targets(campaign: PhishingCampaign, db: AsyncSession) -> int:
    """Resynchronise campaign.targets_count avec le nombre réel de cibles."""
    total = (
        await db.execute(
            select(func.count(PhishingTarget.id)).where(PhishingTarget.campaign_id == campaign.id)
        )
    ).scalar() or 0
    campaign.targets_count = total
    campaign.updated_at = datetime.now(UTC)
    await db.flush()
    return total


async def upload_targets_csv(
    campaign: PhishingCampaign, csv_content: str, db: AsyncSession, *, replace: bool = False
) -> dict:
    """Importe des cibles depuis un CSV.

    - replace=False (défaut) : MERGE — ajoute les nouvelles cibles sans écraser
      les existantes, en ignorant les doublons d'email (dédup insensible à la casse).
    - replace=True : remplace toutes les cibles (ancien comportement, sur demande explicite).

    Retourne {"added", "skipped", "total"}.
    """
    if replace:
        existing = await db.execute(
            select(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
        )
        for t in existing.scalars().all():
            await db.delete(t)
        await db.flush()
        seen: set[str] = set()
    else:
        rows = (
            (
                await db.execute(
                    select(PhishingTarget.email).where(PhishingTarget.campaign_id == campaign.id)
                )
            )
            .scalars()
            .all()
        )
        seen = {e.lower() for e in rows}

    reader = csv.DictReader(io.StringIO(csv_content))
    added = 0
    skipped = 0
    for row in reader:
        email = (row.get("email") or row.get("Email") or "").strip()
        if not email or "@" not in email:
            continue
        if email.lower() in seen:
            skipped += 1
            continue
        seen.add(email.lower())
        db.add(
            PhishingTarget(
                campaign_id=campaign.id,
                email=email,
                first_name=(
                    row.get("first_name") or row.get("prenom") or row.get("Prénom") or ""
                ).strip(),
                last_name=(row.get("last_name") or row.get("nom") or row.get("Nom") or "").strip()
                or None,
                department=(
                    row.get("department") or row.get("departement") or row.get("Département") or ""
                ).strip()
                or None,
            )
        )
        added += 1

    await db.flush()
    total = await _recount_targets(campaign, db)
    return {"added": added, "skipped": skipped, "total": total}


async def add_target(
    campaign: PhishingCampaign,
    *,
    email: str,
    first_name: str = "",
    last_name: str | None = None,
    department: str | None = None,
    db: AsyncSession,
) -> PhishingTarget | None:
    """Ajoute une cible unique. Retourne None si l'email existe déjà (dédup)."""
    exists = (
        await db.execute(
            select(PhishingTarget).where(
                PhishingTarget.campaign_id == campaign.id,
                func.lower(PhishingTarget.email) == email.lower(),
            )
        )
    ).scalar_one_or_none()
    if exists:
        return None
    target = PhishingTarget(
        campaign_id=campaign.id,
        email=email,
        first_name=first_name or "",
        last_name=last_name or None,
        department=department or None,
    )
    db.add(target)
    await db.flush()
    await _recount_targets(campaign, db)
    await db.refresh(target)
    return target


async def delete_target(campaign: PhishingCampaign, target_id: int, db: AsyncSession) -> bool:
    """Supprime une cible. Retourne False si introuvable pour cette campagne."""
    target = (
        await db.execute(
            select(PhishingTarget).where(
                PhishingTarget.id == target_id,
                PhishingTarget.campaign_id == campaign.id,
            )
        )
    ).scalar_one_or_none()
    if target is None:
        return False
    await db.delete(target)
    await db.flush()
    await _recount_targets(campaign, db)
    return True
