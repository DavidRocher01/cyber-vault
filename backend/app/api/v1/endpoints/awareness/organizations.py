"""Endpoints CRUD pour les organisations, bulk enroll et CSV import (Sprint 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.awareness import (
    AwarenessOrganizationCreate,
    AwarenessOrganizationOut,
    AwarenessOrganizationStats,
    AwarenessOrganizationUpdate,
    CsvImportResult,
)
from app.schemas.divers import EnrollmentBatchOut
from app.services import awareness_organization_service
from app.services.awareness_csv_import import import_learners_from_csv
from app.services.storage import FichierTropVolumineuxError, lire_borne

from .helpers import _get_org_or_404

router = APIRouter()

# Plafond de lecture, aligne sur le dossier Dark Web (remediation S4).
_MAX_CSV_BYTES = 2 * 1024 * 1024


# ── Organizations ──────────────────────────────────────────────────────────────


@router.post("/organizations", response_model=AwarenessOrganizationOut, status_code=201)
async def create_organization(
    payload: AwarenessOrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessOrganizationOut:
    org = await awareness_organization_service.create_organization(
        db,
        owner_user_id=current_user.id,
        name=payload.name,
        siret=payload.siret,
        sector=payload.sector,
        max_learners=payload.max_learners,
    )
    return AwarenessOrganizationOut.model_validate(org)


@router.get("/organizations", response_model=list[AwarenessOrganizationStats])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessOrganizationStats]:
    rows = await awareness_organization_service.list_organizations_with_counts(db, current_user.id)
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
    row = await awareness_organization_service.get_organization_with_count(
        db, org_id, current_user.id
    )
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
    org = await awareness_organization_service.save_organization(db, org)
    return AwarenessOrganizationOut.model_validate(org)


# ── Bulk enrollment ────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/enroll-all", status_code=200, response_model=EnrollmentBatchOut
)
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
    return await awareness_organization_service.enroll_all_learners(db, org, program_id)


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

    # Lecture BORNEE : le plafond etait verifie APRES un `read()` complet, donc
    # la memoire etait deja consommee — un message d'erreur, pas un rempart.
    try:
        content = await lire_borne(file, _MAX_CSV_BYTES)
    except FichierTropVolumineuxError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    return await import_learners_from_csv(db, org_id, content)
