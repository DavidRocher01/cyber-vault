from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.user import User
from app.services import rssi_deliverable_service

from ._shared import _get_client_or_404

router = APIRouter()

DocType = Literal["compte_rendu", "rapport", "recommandation", "contrat", "autre"]


class RssiDeliverableCreate(BaseModel):
    title: str
    doc_type: DocType = "autre"
    file_url: str | None = None
    notes: str | None = None
    delivered_at: date


class RssiDeliverableUpdate(BaseModel):
    title: str | None = None
    doc_type: DocType | None = None
    file_url: str | None = None
    notes: str | None = None
    delivered_at: date | None = None


class RssiDeliverableOut(BaseModel):
    id: int
    client_id: int
    title: str
    doc_type: str
    file_url: str | None
    notes: str | None
    delivered_at: date
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/clients/{client_id}/deliverables", response_model=list[RssiDeliverableOut])
async def list_deliverables(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    return await rssi_deliverable_service.list_client_deliverables(db, client_id)


@router.post(
    "/clients/{client_id}/deliverables",
    response_model=RssiDeliverableOut,
    status_code=201,
)
async def create_deliverable(
    client_id: int,
    payload: RssiDeliverableCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)

    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="Le titre du livrable est requis")

    return await rssi_deliverable_service.create_deliverable(
        db,
        client_id=client_id,
        title=payload.title.strip(),
        doc_type=payload.doc_type,
        file_url=payload.file_url,
        notes=payload.notes,
        delivered_at=payload.delivered_at,
    )


@router.put(
    "/clients/{client_id}/deliverables/{deliverable_id}",
    response_model=RssiDeliverableOut,
)
async def update_deliverable(
    client_id: int,
    deliverable_id: int,
    payload: RssiDeliverableUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    deliverable = await rssi_deliverable_service.get_client_deliverable(
        db, client_id, deliverable_id
    )
    if not deliverable:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")

    if payload.title is not None:
        deliverable.title = payload.title.strip()
    if payload.doc_type is not None:
        deliverable.doc_type = payload.doc_type
    if payload.file_url is not None:
        deliverable.file_url = payload.file_url
    if payload.notes is not None:
        deliverable.notes = payload.notes
    if payload.delivered_at is not None:
        deliverable.delivered_at = payload.delivered_at

    return await rssi_deliverable_service.save_deliverable(db, deliverable)


@router.delete("/clients/{client_id}/deliverables/{deliverable_id}", status_code=204)
async def delete_deliverable(
    client_id: int,
    deliverable_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    deliverable = await rssi_deliverable_service.get_client_deliverable(
        db, client_id, deliverable_id
    )
    if not deliverable:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")
    await rssi_deliverable_service.delete_deliverable(db, deliverable)


@router.post("/clients/{client_id}/deliverables/upload")
async def upload_deliverable_file(
    client_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file for a client deliverable and return its storage key."""
    from app.services.storage import MAX_UPLOAD_BYTES, upload_file, validate_upload

    await _get_client_or_404(client_id, current_user.id, db)

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        validate_upload(
            filename=file.filename or "upload",
            content_type=file.content_type or "",
            size=len(content),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    key = upload_file(content, file.filename or "upload", current_user.id, client_id)
    return {"key": key, "filename": file.filename}


@router.get("/clients/{client_id}/deliverables/{deliverable_id}/download")
async def download_deliverable_file(
    client_id: int,
    deliverable_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Return a short-lived download URL for a deliverable file."""
    from app.services.storage import get_download_url

    await _get_client_or_404(client_id, current_user.id, db)

    deliverable = await rssi_deliverable_service.get_client_deliverable(
        db, client_id, deliverable_id
    )
    if not deliverable:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")
    if not deliverable.file_url:
        raise HTTPException(status_code=404, detail="Aucun fichier attaché à ce livrable")

    url = get_download_url(deliverable.file_url)
    return {"url": url}
