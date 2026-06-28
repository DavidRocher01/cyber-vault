"""
Phishing simulation endpoints.

Authenticated routes:
  GET    /phishing/campaigns                 — list user campaigns
  POST   /phishing/campaigns                 — create campaign (draft)
  GET    /phishing/campaigns/{id}            — get campaign + targets
  PATCH  /phishing/campaigns/{id}            — update (name, domain, lookalike_domain, scenarios, cgu, schedule)
  POST   /phishing/campaigns/{id}/targets    — upload CSV targets
  GET    /phishing/campaigns/{id}/targets    — list targets
  POST   /phishing/campaigns/{id}/launch     — validate & launch
  GET    /phishing/campaigns/{id}/pdf        — download PDF report
  POST   /phishing/domain-verify             — request domain TXT verification
  POST   /phishing/domain-verify/check       — check DNS TXT record
  GET    /phishing/lookalike-domains         — suggest look-alike domains for a target domain

Public tracking routes (no auth — called by email clients / browsers):
  GET    /phishing/t/{tracking_id}/px        — 1×1 pixel GIF (open tracking)
  GET    /phishing/t/{tracking_id}/c         — click redirect → landing page
  GET    /phishing/t/{tracking_id}/l         — serve fake landing page HTML
  POST   /phishing/t/{tracking_id}/s         — record credential submit → awareness page
"""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.core.utils import safe_json_load
from app.models.phishing import (
    PhishingCampaign,
    PhishingDomainVerification,
    PhishingTarget,
)
from app.models.user import User
from app.services import phishing_service
from app.services.domain_lookalike import generate_lookalikes
from app.services.phishing_report_pdf import generate_phishing_report

router = APIRouter(prefix="/phishing", tags=["phishing"])

# Conserve une référence forte aux tâches détachées : sans cela, asyncio peut
# les garbage-collecter avant la fin (la tâche serait annulée silencieusement).
_background_tasks: set = set()

_MAX_TARGETS = {
    "express": 50,
    "standard": 200,
    "premium": 500,
    "quarterly": 100,
    "monthly": 300,
}

_VALID_TIERS = set(_MAX_TARGETS.keys())


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    plan_tier: str = Field(..., pattern="^(express|standard|premium|quarterly|monthly)$")


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    domain: str | None = Field(None, max_length=255)
    lookalike_domain: str | None = Field(None, max_length=255)
    scenario_keys: list[str] | None = None
    cgu_accepted: bool | None = None
    scheduled_at: datetime | None = None


class DomainVerifyRequest(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)


class DomainCheckRequest(BaseModel):
    domain: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_campaign(c: PhishingCampaign) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "status": c.status,
        "plan_tier": c.plan_tier,
        "domain": c.domain,
        "domain_verified": c.domain_verified,
        "lookalike_domain": c.lookalike_domain,
        "scenario_keys": safe_json_load(c.scenario_keys, []),
        "targets_count": c.targets_count,
        "emails_sent": c.emails_sent,
        "opened_count": c.opened_count,
        "clicked_count": c.clicked_count,
        "submitted_count": c.submitted_count,
        "click_rate": round(c.clicked_count / c.targets_count, 4) if c.targets_count else 0,
        "cgu_accepted": c.cgu_accepted,
        "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "finished_at": c.finished_at.isoformat() if c.finished_at else None,
        "created_at": c.created_at.isoformat(),
    }


def _serialize_target(t: PhishingTarget) -> dict:
    def _iso(dt: object) -> str | None:
        return dt.isoformat() if dt else None  # type: ignore[union-attr]

    return {
        "id": t.id,
        "email": t.email,
        "first_name": t.first_name,
        "last_name": t.last_name,
        "department": t.department,
        "scenario_key": t.scenario_key,
        "status": t.status,
        "email_sent_at": _iso(t.email_sent_at),
        "opened_at": _iso(t.opened_at),
        "clicked_at": _iso(t.clicked_at),
        "submitted_at": _iso(t.submitted_at),
    }


async def _get_owned(campaign_id: int, user_id: int, db: AsyncSession) -> PhishingCampaign:
    campaign = await phishing_service.get_campaign(campaign_id, user_id, db)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campagne introuvable")
    return campaign


# ---------------------------------------------------------------------------
# Campaign endpoints
# ---------------------------------------------------------------------------


@router.get("/campaigns")
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaigns = await phishing_service.get_campaigns(current_user.id, db)
    return [_serialize_campaign(c) for c in campaigns]


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await phishing_service.create_campaign(
        current_user.id, payload.name, payload.plan_tier, db
    )
    await db.commit()
    return _serialize_campaign(campaign)


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)
    targets_result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.campaign_id == campaign_id)
    )
    targets = list(targets_result.scalars().all())
    return {
        **_serialize_campaign(campaign),
        "targets": [_serialize_target(t) for t in targets],
    }


@router.patch("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    if campaign.status not in ("draft", "pending_verification", "ready", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une campagne active ou terminée ne peut pas être modifiée.",
        )

    # Check domain verification if domain changed
    domain_verified: bool | None = None
    if payload.domain and payload.domain != campaign.domain:
        result = await db.execute(
            select(PhishingDomainVerification).where(
                PhishingDomainVerification.user_id == current_user.id,
                PhishingDomainVerification.domain == payload.domain.lower().strip(),
                PhishingDomainVerification.verified == True,  # noqa: E712
            )
        )
        already_verified = result.scalar_one_or_none()
        domain_verified = already_verified is not None

    updated = await phishing_service.update_campaign(
        campaign,
        name=payload.name,
        domain=payload.domain,
        domain_verified=domain_verified,
        lookalike_domain=payload.lookalike_domain,
        scenario_keys=payload.scenario_keys,
        cgu_accepted=payload.cgu_accepted,
        scheduled_at=payload.scheduled_at,
        db=db,
    )
    await db.commit()
    return _serialize_campaign(updated)


@router.post("/campaigns/{campaign_id}/targets")
async def upload_targets(
    campaign_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    if campaign.status not in ("draft", "pending_verification", "ready"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de modifier les cibles d'une campagne active ou terminée.",
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers CSV sont acceptés.",
        )

    content_bytes = await file.read()
    try:
        csv_content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_content = content_bytes.decode("latin-1")

    max_targets = _MAX_TARGETS.get(campaign.plan_tier, 50)
    # Quick count check before full parse
    rough_count = csv_content.count("\n")
    if rough_count > max_targets + 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le plan {campaign.plan_tier} est limité à {max_targets} cibles.",
        )

    count = await phishing_service.upload_targets_csv(campaign, csv_content, db)

    if count > max_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le plan {campaign.plan_tier} est limité à {max_targets} cibles ({count} trouvées).",
        )
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune adresse email valide trouvée dans le fichier.",
        )

    await db.commit()
    return {"targets_added": count}


@router.get("/campaigns/{campaign_id}/targets")
async def list_targets(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned(campaign_id, current_user.id, db)
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.campaign_id == campaign_id)
    )
    return [_serialize_target(t) for t in result.scalars().all()]


@router.post("/campaigns/{campaign_id}/launch", status_code=status.HTTP_202_ACCEPTED)
async def launch_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    if campaign.status not in ("draft", "pending_verification", "ready", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une campagne active ou terminée ne peut pas être relancée.",
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

    try:
        await phishing_service.launch_campaign(campaign, db)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        # Ne pas exposer l'exception brute au client (fuite d'info) — on la journalise.
        logger.exception(f"Échec lancement campagne phishing id={campaign_id}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur lors du lancement de la campagne.",
        )

    await db.commit()
    # Trigger first batch immediately — APScheduler fires every 15 min but users expect prompt starts.
    # On garde une référence forte à la tâche (sinon GC possible avant la fin).
    task = asyncio.create_task(phishing_service.send_pending_batch())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "sending", "campaign_id": campaign_id}


@router.get("/campaigns/{campaign_id}/pdf")
async def download_report_pdf(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    if campaign.status not in ("completed", "active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le rapport PDF n'est disponible que pour les campagnes actives ou terminées.",
        )

    targets_result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.campaign_id == campaign_id)
    )
    targets = list(targets_result.scalars().all())

    pdf_bytes = generate_phishing_report(campaign, targets)
    filename = f"rapport-phishing-{campaign_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Domain verification endpoints
# ---------------------------------------------------------------------------


@router.post("/domain-verify", status_code=status.HTTP_201_CREATED)
async def request_domain_verification(
    payload: DomainVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await phishing_service.request_domain_verification(
        current_user.id, payload.domain.lower().strip(), db
    )
    await db.commit()
    return {
        "domain": record.domain,
        "verified": record.verified,
        "verification_token": record.verification_token,
        "dns_record_name": f"_cyberscan-verify.{record.domain}",
        "dns_record_type": "TXT",
        "dns_record_value": record.verification_token,
        "instructions": (
            f"Ajoutez un enregistrement DNS TXT sur votre domaine :\n"
            f"  Nom : _cyberscan-verify.{record.domain}\n"
            f"  Type : TXT\n"
            f"  Valeur : {record.verification_token}\n"
            "Puis cliquez sur 'Vérifier' une fois propagé (peut prendre jusqu'à 10 min)."
        ),
    }


@router.post("/domain-verify/check")
async def check_domain_verification(
    payload: DomainCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    domain = payload.domain.lower().strip()
    result = await db.execute(
        select(PhishingDomainVerification).where(
            PhishingDomainVerification.user_id == current_user.id,
            PhishingDomainVerification.domain == domain,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune demande de vérification trouvée pour ce domaine. "
            "Lancez d'abord une demande via POST /phishing/domain-verify.",
        )

    verified = await phishing_service.check_domain_verification(record, db)
    if verified:
        await db.commit()
    return {
        "domain": domain,
        "verified": verified,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
    }


# ---------------------------------------------------------------------------
# Look-alike domain suggestions (authenticated)
# ---------------------------------------------------------------------------


@router.get("/lookalike-domains")
async def get_lookalike_domains(
    domain: str = Query(
        ...,
        min_length=3,
        max_length=255,
        description="Target domain, e.g. monentreprise.com",
    ),
    _current_user: User = Depends(get_current_user),
):
    """Return a list of look-alike domain suggestions for the given target domain."""
    suggestions = generate_lookalikes(domain.lower().strip(), max_results=30)
    return {"domain": domain, "suggestions": suggestions}


# ---------------------------------------------------------------------------
# Public tracking routes — no authentication (called by email clients / browsers)
# ---------------------------------------------------------------------------


@router.get("/t/{tracking_id}/px", include_in_schema=False)
@limiter.limit("30/minute")
async def tracking_pixel(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Serve 1×1 transparent GIF and record email open."""
    await phishing_service.record_open(tracking_id, db)
    return Response(
        content=phishing_service.get_pixel_gif(),
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/t/{tracking_id}/c", include_in_schema=False)
@limiter.limit("10/minute")
async def tracking_click(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Record link click and redirect to the landing page (or expiry page if campaign has ended)."""
    active = await phishing_service.record_click(tracking_id, db)
    if not active:
        return HTMLResponse(content=phishing_service.get_expired_html())
    return RedirectResponse(url=f"/phishing/t/{tracking_id}/l", status_code=302)


@router.get("/t/{tracking_id}/l", response_class=HTMLResponse, include_in_schema=False)
@limiter.limit("15/minute")
async def tracking_landing(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Serve the scenario-specific credential-harvesting landing page, or expiry page."""
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    scenario_key = phishing_service._DEFAULT_SCENARIO_KEY
    if target:
        campaign_result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.id == target.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            if phishing_service._is_campaign_expired(campaign):
                return HTMLResponse(content=phishing_service.get_expired_html())
            keys = json.loads(campaign.scenario_keys or "[]")
            if keys:
                scenario_key = keys[0]
    return HTMLResponse(content=phishing_service.get_landing_html(tracking_id, scenario_key))


@router.post("/t/{tracking_id}/s", response_class=HTMLResponse, include_in_schema=False)
@limiter.limit("5/minute")
async def tracking_submit(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Record credential submission and return the awareness / education page."""
    scenario_key = await phishing_service.record_submit(tracking_id, db)
    return HTMLResponse(content=phishing_service.get_awareness_html(scenario_key))
