"""Endpoints CRUD pour les organisations, bulk enroll et CSV import (Sprint 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization
from app.models.user import User
from app.schemas.awareness import (
    AwarenessOrganizationCreate,
    AwarenessOrganizationOut,
    AwarenessOrganizationStats,
    AwarenessOrganizationUpdate,
    CsvImportResult,
)
from app.services.awareness_csv_import import import_learners_from_csv
from app.services.awareness_magic_link import issue_magic_link
from app.services.email_service import send_awareness_magic_link

from .helpers import _get_org_or_404

router = APIRouter()


# ── Organizations ──────────────────────────────────────────────────────────────


@router.post("/organizations", response_model=AwarenessOrganizationOut, status_code=201)
async def create_organization(
    payload: AwarenessOrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessOrganizationOut:
    org = AwarenessOrganization(
        owner_user_id=current_user.id,
        name=payload.name,
        siret=payload.siret,
        sector=payload.sector,
        max_learners=payload.max_learners,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return AwarenessOrganizationOut.model_validate(org)


@router.get("/organizations", response_model=list[AwarenessOrganizationStats])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessOrganizationStats]:
    rows = (
        await db.execute(
            select(
                AwarenessOrganization,
                func.count(AwarenessLearner.id).label("learner_count"),
            )
            .outerjoin(
                AwarenessLearner,
                (AwarenessLearner.organization_id == AwarenessOrganization.id)
                & (AwarenessLearner.is_active == True),
            )
            .where(AwarenessOrganization.owner_user_id == current_user.id)
            .group_by(AwarenessOrganization.id)
        )
    ).all()

    out = []
    for org, learner_count in rows:
        stats = AwarenessOrganizationStats.model_validate(org)
        stats.learner_count = learner_count
        out.append(stats)
    return out


@router.get("/organizations/{org_id}", response_model=AwarenessOrganizationStats)
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessOrganizationStats:
    row = (
        await db.execute(
            select(
                AwarenessOrganization,
                func.count(AwarenessLearner.id).label("learner_count"),
            )
            .outerjoin(
                AwarenessLearner,
                (AwarenessLearner.organization_id == AwarenessOrganization.id)
                & (AwarenessLearner.is_active == True),
            )
            .where(
                AwarenessOrganization.id == org_id,
                AwarenessOrganization.owner_user_id == current_user.id,
            )
            .group_by(AwarenessOrganization.id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Organisation introuvable.")
    org, learner_count = row
    stats = AwarenessOrganizationStats.model_validate(org)
    stats.learner_count = learner_count
    return stats


@router.patch("/organizations/{org_id}", response_model=AwarenessOrganizationOut)
async def update_organization(
    org_id: int,
    payload: AwarenessOrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessOrganizationOut:
    org = await _get_org_or_404(org_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    await db.commit()
    await db.refresh(org)
    return AwarenessOrganizationOut.model_validate(org)


# ── Bulk enrollment ────────────────────────────────────────────────────────────


@router.post("/organizations/{org_id}/enroll-all", status_code=200)
async def enroll_all_learners(
    org_id: int,
    program_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Inscrit tous les learners actifs de l'organisation à un programme.
    Ignore les learners déjà inscrits. Envoie un email magic-link à chaque nouveau inscrit.
    """
    org = await _get_org_or_404(org_id, current_user, db)

    learners_result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.organization_id == org_id,
            AwarenessLearner.is_active == True,
        )
    )
    learners = learners_result.scalars().all()

    enrolled = 0
    skipped = 0
    for learner in learners:
        existing = (
            await db.execute(
                select(AwarenessEnrollment).where(
                    AwarenessEnrollment.learner_id == learner.id,
                    AwarenessEnrollment.program_id == program_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            skipped += 1
            continue
        enrollment = AwarenessEnrollment(
            learner_id=learner.id,
            program_id=program_id,
            organization_id=org_id,
            status="pending",
        )
        db.add(enrollment)
        enrolled += 1

        # Send magic-link invitation
        try:
            magic_result = await issue_magic_link(db, str(learner.email), org_id)
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
            logger.warning(f"Envoi email magic-link échoué pour {learner.email}: {e}")

    await db.commit()
    return {"enrolled": enrolled, "skipped": skipped, "total": len(learners)}


# ── CSV Import ─────────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/learners/import-csv",
    response_model=CsvImportResult,
)
async def import_learners_csv(
    org_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CsvImportResult:
    await _get_org_or_404(org_id, current_user, db)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Fichier CSV requis.")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:  # 2 MB max
        raise HTTPException(status_code=422, detail="Fichier trop volumineux (max 2 MB).")

    return await import_learners_from_csv(db, org_id, content)
