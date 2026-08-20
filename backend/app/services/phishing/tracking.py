"""Ouvertures, clics, soumissions — appele par les routes publiques."""

import json
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.enums import CampaignStatus, TargetStatus
from app.models.phishing import (
    PhishingCampaign,
    PhishingTarget,
)
from app.services.phishing import sending
from app.services.phishing.templates import (
    _DEFAULT_SCENARIO_KEY,
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
# Tracking event handlers (called from public endpoints)
# ---------------------------------------------------------------------------


async def _enroll_target_in_remediation(
    campaign: PhishingCampaign, target: PhishingTarget, db: AsyncSession
) -> None:
    """Training-on-fail : inscrit la cible piégée dans un module de remédiation
    awareness. BEST-EFFORT — ne doit JAMAIS casser le flux de tracking.

    Périmètre Lot 4 : mode consultant uniquement (l'org awareness vient du client
    RSSI) et learner DÉJÀ existant dans l'org (pas d'auto-création -> pas d'email).
    Company directe (pas d'org) et auto-création de learner = follow-up.
    """
    if not campaign.training_on_fail or campaign.rssi_client_id is None:
        return
    try:
        from app.models.awareness_learner import AwarenessLearner
        from app.models.awareness_program import AwarenessProgram
        from app.models.rssi_client import RssiClient
        from app.services.awareness.progression import enroll_learner

        client = (
            await db.execute(select(RssiClient).where(RssiClient.id == campaign.rssi_client_id))
        ).scalar_one_or_none()
        if client is None or client.awareness_organization_id is None:
            return

        learner = (
            await db.execute(
                select(AwarenessLearner).where(
                    AwarenessLearner.email == target.email,
                    AwarenessLearner.organization_id == client.awareness_organization_id,
                    AwarenessLearner.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if learner is None:
            return

        # Programme de remédiation dédié si présent (slug ~ "remediation"), sinon
        # 1er programme actif en repli (ex. nis2-essentiel) pour rester fonctionnel
        # tant qu'aucun contenu de remédiation dédié n'est seedé.
        program = (
            await db.execute(
                select(AwarenessProgram)
                .where(
                    AwarenessProgram.is_active.is_(True),
                    AwarenessProgram.slug.contains("remediation"),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if program is None:
            program = (
                await db.execute(
                    select(AwarenessProgram).where(AwarenessProgram.is_active.is_(True)).limit(1)
                )
            ).scalar_one_or_none()
        if program is None:
            return

        await enroll_learner(db, learner, program.id)
        await db.commit()
        logger.info(
            f"training-on-fail: learner {learner.id} enrolled in program {program.id} "
            f"(campaign {campaign.id}, target {target.id})"
        )
    except Exception as exc:  # best-effort : on n'interrompt jamais le tracking
        logger.warning(f"training-on-fail enrollment skipped (campaign {campaign.id}): {exc}")


async def _resolve_target_and_campaign(
    tracking_id: str, db: AsyncSession
) -> tuple[PhishingTarget | None, PhishingCampaign | None]:
    """Charge la cible (par tracking_id) ET sa campagne en UNE requête (joinedload).
    Remplace le double SELECT dupliqué dans les handlers de tracking."""
    result = await db.execute(
        select(PhishingTarget)
        .options(joinedload(PhishingTarget.campaign))
        .where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    return target, (target.campaign if target else None)


async def record_open(tracking_id: str, db: AsyncSession) -> None:
    target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    if (
        target
        and campaign
        and target.status == TargetStatus.EMAIL_SENT
        and not _is_campaign_expired(campaign)
    ):
        target.status = TargetStatus.OPENED
        target.opened_at = datetime.now(UTC)
        campaign.opened_count += 1
        campaign.updated_at = datetime.now(UTC)
        await db.commit()


async def record_click(tracking_id: str, db: AsyncSession) -> bool:
    """Record link click. Returns False if campaign has expired (endpoint should serve expiry page)."""
    target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    if target and campaign and target.status in (TargetStatus.EMAIL_SENT, TargetStatus.OPENED):
        if _is_campaign_expired(campaign):
            return False
        target.status = TargetStatus.CLICKED
        target.clicked_at = datetime.now(UTC)
        campaign.clicked_count += 1
        campaign.updated_at = datetime.now(UTC)
        await db.commit()
        if campaign.training_trigger == "click":
            await _enroll_target_in_remediation(campaign, target, db)
    return True


async def record_submit(tracking_id: str, db: AsyncSession) -> str:
    """Records submission and returns the scenario_key for the awareness page.
    Always returns a scenario_key so the awareness page is shown even after expiry."""
    target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    scenario_key = _DEFAULT_SCENARIO_KEY
    if target and campaign:
        keys = json.loads(campaign.scenario_keys or "[]")
        if target.scenario_key:
            scenario_key = target.scenario_key
        elif keys:
            scenario_key = keys[0]
        if not _is_campaign_expired(campaign) and target.status != TargetStatus.SUBMITTED:
            target.status = TargetStatus.SUBMITTED
            target.submitted_at = datetime.now(UTC)
            campaign.submitted_count += 1
            campaign.updated_at = datetime.now(UTC)
            await db.commit()
            if campaign.training_trigger == "submit":
                await _enroll_target_in_remediation(campaign, target, db)
    elif target and target.status != TargetStatus.SUBMITTED:
        target.status = TargetStatus.SUBMITTED
        await db.commit()
    return scenario_key


async def get_landing_context(tracking_id: str, db: AsyncSession) -> tuple[str, str | None, bool]:
    """Contexte pour servir la landing page : (scenario_key, landing_base, expired).
    landing_base = host de la campagne (le formulaire doit poster sur le même host)."""
    _target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    if not campaign:
        return _DEFAULT_SCENARIO_KEY, None, False
    if _is_campaign_expired(campaign):
        return _DEFAULT_SCENARIO_KEY, None, True
    keys = json.loads(campaign.scenario_keys or "[]")
    scenario_key = keys[0] if keys else _DEFAULT_SCENARIO_KEY
    return scenario_key, sending._tracking_base(campaign), False


def _is_campaign_expired(campaign: PhishingCampaign) -> bool:
    """Return True when tracking events should no longer be recorded."""
    if campaign.status == CampaignStatus.COMPLETED:
        return True
    if campaign.started_at is not None:
        age = datetime.now(UTC) - campaign.started_at
        if age.days >= settings.PHISHING_TRACKING_TTL_DAYS:
            return True
    return False
