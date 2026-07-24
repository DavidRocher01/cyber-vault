from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.user import User
from app.services import rssi_visit_service

from ._shared import _get_client_or_404

router = APIRouter()

VisitType = Literal["monthly", "quarterly", "annual", "urgent"]
VisitLocation = Literal["onsite", "remote"]
VisitStatus = Literal["planned", "completed", "cancelled", "postponed"]


class RssiVisitCreate(BaseModel):
    scheduled_date: date
    visit_type: VisitType = "monthly"
    location: VisitLocation = "onsite"
    notes: str | None = None


class RssiVisitUpdate(BaseModel):
    scheduled_date: date | None = None
    visit_type: VisitType | None = None
    location: VisitLocation | None = None
    status: VisitStatus | None = None
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
    return await rssi_visit_service.list_client_visits(db, client_id)


@router.post("/clients/{client_id}/visits", response_model=RssiVisitOut, status_code=201)
async def create_visit(
    client_id: int,
    payload: RssiVisitCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    return await rssi_visit_service.create_visit(
        db,
        client_id=client_id,
        scheduled_date=payload.scheduled_date,
        visit_type=payload.visit_type,
        location=payload.location,
        notes=payload.notes,
    )


@router.put("/clients/{client_id}/visits/{visit_id}", response_model=RssiVisitOut)
async def update_visit(
    client_id: int,
    visit_id: int,
    payload: RssiVisitUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    visit = await rssi_visit_service.get_client_visit(db, client_id, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visite non trouvée")

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

    return await rssi_visit_service.save_visit(db, visit)


@router.delete("/clients/{client_id}/visits/{visit_id}", status_code=204)
async def delete_visit(
    client_id: int,
    visit_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    visit = await rssi_visit_service.get_client_visit(db, client_id, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visite non trouvée")
    await rssi_visit_service.delete_visit(db, visit)
