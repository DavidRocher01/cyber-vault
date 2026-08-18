"""Routes phishing — campaigns."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.rssi._shared import _get_client_or_404
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.phishing import (
    PhishingCampaignDetailOut,
    PhishingCampaignOut,
)
from app.services import phishing_service

from ._shared import (
    _CANCELLABLE_STATUSES,
    _EDITABLE_CAMPAIGN_STATUSES,
    CampaignCreate,
    CampaignUpdate,
    _get_owned,
    _require_status,
    _serialize_campaign,
    _serialize_target,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Campaign endpoints
# ---------------------------------------------------------------------------


async def _resolve_client_attribution(
    rssi_client_id: int | None, current_user: User, db: AsyncSession
) -> int | None:
    """Valide l'attribution d'une campagne à un client RSSI (mode consultant).

    Le gating par PLAN se fait au LANCEMENT (cf. launch_campaign), PAS ici : on peut
    créer et configurer un brouillon librement. Ici on ne valide que le contexte
    consultant : exige is_rssi_consultant + ownership du client (404 sinon, pour ne
    pas révéler son existence). Mode entreprise directe (NULL) : rien à valider.
    """
    if rssi_client_id is None:
        return None
    if not current_user.is_rssi_consultant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux consultants RSSI.",
        )
    await _get_client_or_404(rssi_client_id, current_user.id, db)
    return rssi_client_id


@router.get("/campaigns", response_model=list[PhishingCampaignOut])
async def list_campaigns(
    rssi_client_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if rssi_client_id is not None:
        # Mode consultant : campagnes d'un client (ownership vérifié).
        if not current_user.is_rssi_consultant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès réservé aux consultants RSSI.",
            )
        await _get_client_or_404(rssi_client_id, current_user.id, db)
        campaigns = await phishing_service.get_campaigns(
            current_user.id, db, rssi_client_id=rssi_client_id
        )
    else:
        # Mode entreprise directe : campagnes sans client rattaché.
        campaigns = await phishing_service.get_campaigns(current_user.id, db, company_only=True)
    return [_serialize_campaign(c) for c in campaigns]


@router.post("/campaigns", status_code=status.HTTP_201_CREATED, response_model=PhishingCampaignOut)
async def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rssi_client_id = await _resolve_client_attribution(payload.rssi_client_id, current_user, db)
    campaign = await phishing_service.create_campaign(
        current_user.id, payload.name, payload.plan_tier, db, rssi_client_id=rssi_client_id
    )
    await phishing_service.commit(db)
    return _serialize_campaign(campaign)


@router.get("/campaigns/{campaign_id}", response_model=PhishingCampaignDetailOut)
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)
    targets = await phishing_service.get_targets(campaign_id, db)
    return {
        **_serialize_campaign(campaign),
        "targets": [_serialize_target(t) for t in targets],
    }


@router.patch("/campaigns/{campaign_id}", response_model=PhishingCampaignOut)
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    _require_status(
        campaign,
        _EDITABLE_CAMPAIGN_STATUSES,
        "Une campagne active ou terminée ne peut pas être modifiée.",
    )

    # Check domain verification if domain changed
    domain_verified: bool | None = None
    if payload.domain and payload.domain != campaign.domain:
        domain_verified = await phishing_service.is_domain_verified(
            current_user.id, payload.domain.lower().strip(), db
        )

    updated = await phishing_service.update_campaign(
        campaign,
        name=payload.name,
        domain=payload.domain,
        domain_verified=domain_verified,
        lookalike_domain=payload.lookalike_domain,
        scenario_keys=payload.scenario_keys,
        cgu_accepted=payload.cgu_accepted,
        scheduled_at=payload.scheduled_at,
        training_on_fail=payload.training_on_fail,
        training_trigger=payload.training_trigger,
        batch_size=payload.batch_size,
        db=db,
    )
    await phishing_service.commit(db)
    return _serialize_campaign(updated)


@router.post("/campaigns/{campaign_id}/cancel", response_model=PhishingCampaignOut)
async def cancel_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)
    _require_status(
        campaign,
        _CANCELLABLE_STATUSES,
        "Seule une campagne en préparation ou en cours d'envoi peut être annulée.",
    )
    updated = await phishing_service.cancel_campaign(campaign, db)
    await phishing_service.commit(db)
    return _serialize_campaign(updated)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Supprime définitivement une campagne du propriétaire (cibles en cascade)."""
    campaign = await _get_owned(campaign_id, current_user.id, db)
    await phishing_service.delete_campaign(campaign, db)
    await phishing_service.commit(db)
