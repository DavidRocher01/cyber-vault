"""Routes phishing — launch."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.phishing import (
    CampaignLaunchOut,
)
from app.services.phishing import base, launch, sending

from ._shared import (
    _EDITABLE_CAMPAIGN_STATUSES,
    _PHISHING_MIN_TIER,
    _background_tasks,
    _get_owned,
    _require_status,
)

router = APIRouter()


@router.post(
    "/campaigns/{campaign_id}/launch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CampaignLaunchOut,
)
async def launch_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    _require_status(
        campaign,
        _EDITABLE_CAMPAIGN_STATUSES,
        "Une campagne active ou terminée ne peut pas être relancée.",
    )
    if campaign.targets_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune cible uploadée pour cette campagne.",
        )
    if not campaign.scenario_keys or campaign.scenario_keys == "[]":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun scénario sélectionné.",
        )
    if not campaign.cgu_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous devez accepter les conditions générales avant de lancer la campagne.",
        )

    # Le domaine d'expédition est vérifié ICI, avant le premier envoi : une fois
    # la campagne lancée, le batch part sans repasser par un contrôle humain.
    try:
        sending.verifier_domaine_expedition()
    except sending.DomaineExpeditionInvalideError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # Gating par plan AU LANCEMENT (l'envoi réel) et seulement en mode entreprise
    # directe : le consultant lance via sa prestation (campagne rattachée à un client).
    if campaign.rssi_client_id is None:
        from app.services.subscription_service import get_active_tier

        if await get_active_tier(db, current_user.id) < _PHISHING_MIN_TIER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La simulation de phishing nécessite un abonnement Pro ou supérieur.",
            )

    try:
        await launch.launch_campaign(campaign, db)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        # Ne pas exposer l'exception brute au client (fuite d'info) — on la journalise.
        logger.exception(f"Échec lancement campagne phishing id={campaign_id}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur lors du lancement de la campagne.",
        )

    await base.commit(db)
    # Trigger first batch immediately — APScheduler fires every 15 min but users expect prompt starts.
    # On garde une référence forte à la tâche (sinon GC possible avant la fin).
    task = asyncio.create_task(sending.send_pending_batch())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "sending", "campaign_id": campaign_id}
