import csv
import io
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.rssi_action import RssiAction
from app.models.user import User
from ._shared import _get_client_or_404

router = APIRouter()

_VALID_PRIORITIES = {"critical", "high", "medium", "low"}
_VALID_ACTION_STATUSES = {"open", "in_progress", "done", "cancelled", "postponed"}


class RssiActionCreate(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    priority: str = "medium"
    assigned_to: str | None = None
    due_date: date | None = None
    source_visit_id: int | None = None


class RssiActionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    due_date: date | None = None
    completed_at: datetime | None = None


class RssiActionOut(BaseModel):
    id: int
    client_id: int
    title: str
    description: str | None
    category: str | None
    priority: str
    status: str
    assigned_to: str | None
    due_date: date | None
    completed_at: datetime | None
    source_visit_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/clients/{client_id}/actions", response_model=list[RssiActionOut])
async def list_actions(
    client_id: int,
    status_filter: str | None = None,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    query = select(RssiAction).where(RssiAction.client_id == client_id)
    if status_filter:
        query = query.where(RssiAction.status == status_filter)
    query = query.order_by(RssiAction.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/clients/{client_id}/actions", response_model=RssiActionOut, status_code=201)
async def create_action(
    client_id: int,
    payload: RssiActionCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)

    if payload.priority not in _VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"Priorité invalide. Valeurs: {_VALID_PRIORITIES}")
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="Le titre de l'action est requis")

    action = RssiAction(
        client_id=client_id,
        title=payload.title.strip(),
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        assigned_to=payload.assigned_to,
        due_date=payload.due_date,
        source_visit_id=payload.source_visit_id,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


@router.put("/clients/{client_id}/actions/{action_id}", response_model=RssiActionOut)
async def update_action(
    client_id: int,
    action_id: int,
    payload: RssiActionUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    result = await db.execute(
        select(RssiAction).where(RssiAction.id == action_id, RssiAction.client_id == client_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvée")

    if payload.priority is not None and payload.priority not in _VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"Priorité invalide. Valeurs: {_VALID_PRIORITIES}")
    if payload.status is not None and payload.status not in _VALID_ACTION_STATUSES:
        raise HTTPException(status_code=422, detail=f"Statut invalide. Valeurs: {_VALID_ACTION_STATUSES}")

    if payload.title is not None:
        action.title = payload.title.strip()
    if payload.description is not None:
        action.description = payload.description
    if payload.category is not None:
        action.category = payload.category
    if payload.priority is not None:
        action.priority = payload.priority
    if payload.status is not None:
        action.status = payload.status
        if payload.status == "done" and action.completed_at is None:
            action.completed_at = datetime.now(timezone.utc)
    if payload.assigned_to is not None:
        action.assigned_to = payload.assigned_to
    if payload.due_date is not None:
        action.due_date = payload.due_date
    if payload.completed_at is not None:
        action.completed_at = payload.completed_at

    action.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(action)
    return action


@router.delete("/clients/{client_id}/actions/{action_id}", status_code=204)
async def delete_action(
    client_id: int,
    action_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    result = await db.execute(
        select(RssiAction).where(RssiAction.id == action_id, RssiAction.client_id == client_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvée")
    await db.delete(action)
    await db.commit()


@router.get("/clients/{client_id}/actions/export")
async def export_actions_csv(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Export all actions for a client as a CSV file."""
    await _get_client_or_404(client_id, current_user.id, db)

    result = await db.execute(
        select(RssiAction)
        .where(RssiAction.client_id == client_id)
        .order_by(RssiAction.created_at.desc())
    )
    actions = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writerow(["Titre", "Catégorie", "Priorité", "Statut", "Responsable", "Échéance", "Terminée le", "Créée le"])

    _priority_fr = {"critical": "Critique", "high": "Haute", "medium": "Moyenne", "low": "Basse"}
    _status_fr   = {"open": "Ouverte", "in_progress": "En cours", "done": "Terminée",
                    "cancelled": "Annulée", "postponed": "Reportée"}
    _category_fr = {"governance": "Gouvernance", "technical": "Technique",
                    "training": "Formation", "compliance": "Conformité"}

    for a in actions:
        writer.writerow([
            a.title,
            _category_fr.get(a.category or "", a.category or ""),
            _priority_fr.get(a.priority, a.priority),
            _status_fr.get(a.status, a.status),
            a.assigned_to or "",
            str(a.due_date) if a.due_date else "",
            str(a.completed_at.date()) if a.completed_at else "",
            str(a.created_at.date()) if a.created_at else "",
        ])

    csv_bytes = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=actions_client_{client_id}.csv"},
    )
