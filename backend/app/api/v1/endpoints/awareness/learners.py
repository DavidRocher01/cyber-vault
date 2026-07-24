"""Endpoints gestion des learners et auth magic-link (Sprint 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.utils import mask_email
from app.models.user import User
from app.schemas.awareness import (
    AwarenessLearnerCreate,
    AwarenessLearnerOut,
    AwarenessLearnerUpdate,
    LearnerSession,
    MagicLinkRequest,
)
from app.services import awareness_access_service, awareness_learner_service
from app.services.awareness_magic_link import (
    create_learner_jwt,
    issue_magic_link,
    verify_magic_link,
)
from app.services.email_service import send_awareness_magic_link

from .helpers import _get_learner_or_404, _get_org_or_404

router = APIRouter()


# ── Learner CRUD ───────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/learners",
    response_model=AwarenessLearnerOut,
    status_code=201,
)
async def create_learner(
    org_id: int,
    payload: AwarenessLearnerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessLearnerOut:
    org = await _get_org_or_404(org_id, current_user, db)

    # Check quota
    count = await awareness_learner_service.count_active_learners(db, org.id)
    if count >= org.max_learners:
        raise HTTPException(
            status_code=422,
            detail=f"Quota atteint ({org.max_learners} learners max).",
        )

    # Check duplicate
    existing = await awareness_learner_service.get_learner_by_email(db, org_id, str(payload.email))
    if existing:
        raise HTTPException(
            status_code=409, detail="Email déjà enregistré dans cette organisation."
        )

    learner = await awareness_learner_service.create_learner(
        db,
        org_id=org_id,
        email=str(payload.email),
        first_name=payload.first_name,
        last_name=payload.last_name,
        department=payload.department,
        job_title=payload.job_title,
        preferred_language=payload.preferred_language,
    )

    # Auto-send welcome email with magic-link
    try:
        magic_result = await issue_magic_link(db, str(payload.email), org_id)
        if magic_result:
            _, raw_token = magic_result
            login_url = f"{settings.FRONTEND_URL}/awareness/login?token={raw_token}"
            send_awareness_magic_link(
                to_email=str(learner.email),
                first_name=learner.first_name,
                org_name=org.name,
                login_url=login_url,
            )
    except Exception as e:
        logger.warning(f"Envoi email magic-link échoué pour {mask_email(payload.email)}: {e}")

    return AwarenessLearnerOut.model_validate(learner)


@router.get("/organizations/{org_id}/learners", response_model=list[AwarenessLearnerOut])
async def list_learners(
    org_id: int,
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessLearnerOut]:
    await _get_org_or_404(org_id, current_user, db)
    learners = await awareness_learner_service.list_org_learners(
        db, org_id, active_only=active_only
    )
    return [AwarenessLearnerOut.model_validate(row) for row in learners]


@router.patch(
    "/organizations/{org_id}/learners/{learner_id}",
    response_model=AwarenessLearnerOut,
)
async def update_learner(
    org_id: int,
    learner_id: int,
    payload: AwarenessLearnerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessLearnerOut:
    await _get_org_or_404(org_id, current_user, db)
    learner = await _get_learner_or_404(learner_id, org_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(learner, field, value)
    await awareness_learner_service.save_learner(db, learner)
    return AwarenessLearnerOut.model_validate(learner)


# ── Magic-link auth ────────────────────────────────────────────────────────────


@router.post("/auth/magic-link", status_code=202)
async def request_magic_link(
    payload: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate a magic link for a learner. Always returns 202 to avoid email enumeration.
    In production the raw token is sent by email; here it's returned for dev convenience.
    """
    result = await issue_magic_link(db, str(payload.email), payload.organization_id)
    if result is None:
        return {"message": "Si l'email existe, un lien de connexion vous a été envoyé."}

    learner, raw_token = result

    org = await awareness_access_service.get_organization_by_id(db, learner.organization_id)
    org_name = org.name if org else "votre organisation"

    login_url = f"{settings.FRONTEND_URL}/awareness/login?token={raw_token}"
    try:
        send_awareness_magic_link(
            to_email=str(learner.email),
            first_name=learner.first_name,
            org_name=org_name,
            login_url=login_url,
        )
    except Exception as e:
        logger.warning(f"Envoi magic-link échoué pour {mask_email(learner.email)}: {e}")

    return {"message": "Si l'email existe, un lien de connexion vous a été envoyé."}


@router.get("/auth/verify", response_model=LearnerSession)
async def verify_magic_link_token(
    token: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
) -> LearnerSession:
    learner = await verify_magic_link(db, token)
    if learner is None:
        raise HTTPException(
            status_code=401,
            detail="Lien invalide ou expiré. Demandez un nouveau lien.",
        )
    jwt_token = create_learner_jwt(learner)
    return LearnerSession(
        learner_id=learner.id,
        organization_id=learner.organization_id,
        email=learner.email,
        first_name=learner.first_name,
        last_name=learner.last_name,
        access_token=jwt_token,
    )
