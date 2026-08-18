"""Routes phishing — targets."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.phishing import (
    PhishingTargetOut,
    TargetsUploadOut,
)
from app.services import phishing_service
from app.services.storage import FichierTropVolumineuxError, lire_borne

from ._shared import (
    _EDITABLE_TARGET_STATUSES,
    _MAX_CSV_BYTES,
    _MAX_TARGETS,
    _TARGETS_LOCKED_DETAIL,
    TargetAdd,
    _get_owned,
    _require_status,
    _serialize_target,
)

router = APIRouter()


@router.post("/campaigns/{campaign_id}/targets", response_model=TargetsUploadOut)
async def upload_targets(
    campaign_id: int,
    file: UploadFile = File(...),
    replace: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    _require_status(campaign, _EDITABLE_TARGET_STATUSES, _TARGETS_LOCKED_DETAIL)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers CSV sont acceptés.",
        )

    # Lecture BORNEE : un `read()` nu chargeait tout en memoire sans le moindre
    # plafond — un abonne authentifie faisait tomber la tache de production.
    try:
        content_bytes = await lire_borne(file, _MAX_CSV_BYTES)
    except FichierTropVolumineuxError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
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

    result = await phishing_service.upload_targets_csv(campaign, csv_content, db, replace=replace)

    if result["total"] > max_targets:
        raise HTTPException(  # non commité -> le flush est annulé par get_db
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le plan {campaign.plan_tier} est limité à {max_targets} cibles "
            f"({result['total']} au total).",
        )
    if result["added"] == 0 and result["skipped"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune adresse email valide trouvée dans le fichier.",
        )

    await phishing_service.commit(db)
    return {
        "targets_added": result["added"],
        "targets_skipped": result["skipped"],
        "targets_total": result["total"],
    }


@router.get("/campaigns/{campaign_id}/targets", response_model=list[PhishingTargetOut])
async def list_targets(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned(campaign_id, current_user.id, db)
    targets = await phishing_service.get_targets(campaign_id, db)
    return [_serialize_target(t) for t in targets]


@router.post(
    "/campaigns/{campaign_id}/targets/single",
    status_code=status.HTTP_201_CREATED,
    response_model=PhishingTargetOut,
)
async def add_single_target(
    campaign_id: int,
    payload: TargetAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)
    _require_status(campaign, _EDITABLE_TARGET_STATUSES, _TARGETS_LOCKED_DETAIL)
    max_targets = _MAX_TARGETS.get(campaign.plan_tier, 50)
    if campaign.targets_count >= max_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le plan {campaign.plan_tier} est limité à {max_targets} cibles.",
        )
    target = await phishing_service.add_target(
        campaign,
        email=str(payload.email),
        first_name=payload.first_name or "",
        last_name=payload.last_name,
        department=payload.department,
        db=db,
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette adresse email est déjà une cible de la campagne.",
        )
    await phishing_service.commit(db)
    return _serialize_target(target)


@router.delete(
    "/campaigns/{campaign_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_single_target(
    campaign_id: int,
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)
    _require_status(campaign, _EDITABLE_TARGET_STATUSES, _TARGETS_LOCKED_DETAIL)
    ok = await phishing_service.delete_target(campaign, target_id, db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cible introuvable.")
    await phishing_service.commit(db)
