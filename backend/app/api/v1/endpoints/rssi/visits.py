from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.rssi_visit import RssiVisit
from app.models.user import User
from ._shared import _get_client_or_404

router = APIRouter()

_VALID_VISIT_TYPES = {"monthly", "quarterly", "annual", "urgent"}
_VALID_VISIT_LOCATIONS = {"onsite", "remote"}
_VALID_VISIT_STATUSES = {"planned", "completed", "cancelled", "postponed"}


class RssiVisitCreate(BaseModel):
    scheduled_date: date
    visit_type: str = "monthly"
    location: str = "onsite"
    notes: str | None = None


class RssiVisitUpdate(BaseModel):
    scheduled_date: date | None = None
    visit_type: str | None = None
    location: str | None = None
    status: str | None = None
    notes: str | None = None
    actual_date: date | None = None
    duration_hours: float | None = None


class RssiVisitOut(BaseModel):
    id: int
    client_id: int
    scheduled_date: date
    visit_type: str
    location: str
    status: str
    notes: str | None
    actual_date: date | None
    duration_hours: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/clients/{client_id}/visits", response_model=list[RssiVisitOut])
async def list_visits(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    result = await db.execute(
        select(RssiVisit)
        .where(RssiVisit.client_id == client_id)
        .order_by(RssiVisit.scheduled_date.desc())
    )
    return result.scalars().all()


@router.post("/clients/{client_id}/visits", response_model=RssiVisitOut, status_code=201)
async def create_visit(
    client_id: int,
    payload: RssiVisitCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)

    if payload.visit_type not in _VALID_VISIT_TYPES:
        raise HTTPException(status_code=422, detail=f"Type de visite invalide. Valeurs: {_VALID_VISIT_TYPES}")
    if payload.location not in _VALID_VISIT_LOCATIONS:
        raise HTTPException(status_code=422, detail=f"Lieu invalide. Valeurs: {_VALID_VISIT_LOCATIONS}")

    visit = RssiVisit(
        client_id=client_id,
        scheduled_date=payload.scheduled_date,
        visit_type=payload.visit_type,
        location=payload.location,
        notes=payload.notes,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


@router.put("/clients/{client_id}/visits/{visit_id}", response_model=RssiVisitOut)
async def update_visit(
    client_id: int,
    visit_id: int,
    payload: RssiVisitUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    result = await db.execute(
        select(RssiVisit).where(RssiVisit.id == visit_id, RssiVisit.client_id == client_id)
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Visite non trouvée")

    if payload.status is not None and payload.status not in _VALID_VISIT_STATUSES:
        raise HTTPException(status_code=422, detail=f"Statut invalide. Valeurs: {_VALID_VISIT_STATUSES}")
    if payload.visit_type is not None and payload.visit_type not in _VALID_VISIT_TYPES:
        raise HTTPException(status_code=422, detail=f"Type de visite invalide. Valeurs: {_VALID_VISIT_TYPES}")

    if payload.scheduled_date is not None:
        visit.scheduled_date = payload.scheduled_date
    if payload.visit_type is not None:
        visit.visit_type = payload.visit_type
    if payload.location is not None:
        visit.location = payload.location
    if payload.status is not None:
        visit.status = payload.status
    if payload.notes is not None:
        visit.notes = payload.notes
    if payload.actual_date is not None:
        visit.actual_date = payload.actual_date
    if payload.duration_hours is not None:
        visit.duration_hours = payload.duration_hours

    visit.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(visit)
    return visit


@router.delete("/clients/{client_id}/visits/{visit_id}", status_code=204)
async def delete_visit(
    client_id: int,
    visit_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    result = await db.execute(
        select(RssiVisit).where(RssiVisit.id == visit_id, RssiVisit.client_id == client_id)
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Visite non trouvée")
    await db.delete(visit)
    await db.commit()
