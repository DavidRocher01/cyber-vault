"""Lancement d'une campagne."""

import json
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
        logger.info(
            "DEV MODE — RESEND_API_KEY absent, campagne passée en 'sending' sans envoi réel."
        )

    now = datetime.now(UTC)
    if campaign.scheduled_at and campaign.scheduled_at > now:
        campaign.status = CampaignStatus.SCHEDULED
        campaign.updated_at = now
        logger.info(f"Campaign {campaign.id} scheduled for {campaign.scheduled_at.isoformat()}")
    else:
        campaign.status = CampaignStatus.SENDING
        campaign.started_at = now
        campaign.updated_at = now
    await db.flush()
