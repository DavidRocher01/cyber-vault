import csv
import io
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.user import User
from app.services import rssi_action_service

from ._shared import _get_client_or_404

router = APIRouter()

ActionPriority = Literal["critical", "high", "medium", "low"]
ActionStatus = Literal["open", "in_progress", "done", "cancelled", "postponed"]
ActionCategory = Literal["governance", "technical", "training", "compliance"]


class RssiActionCreate(BaseModel):
    title: str
    description: str | None = None
    category: ActionCategory | None = None
    priority: ActionPriority = "medium"
    assigned_to: str | None = None
    due_date: date | None = None
    source_visit_id: int | None = None


class RssiActionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: ActionCategory | None = None
    priority: ActionPriority | None = None
    status: ActionStatus | None = None
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
    return await rssi_action_service.list_actions(db, client_id, status_filter)


@router.post("/clients/{client_id}/actions", response_model=RssiActionOut, status_code=201)
async def create_action(
    client_id: int,
    payload: RssiActionCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)

    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="Le titre de l'action est requis")

    # Isolation : une visite source référencée doit appartenir à CE client (sinon un
    # consultant pourrait lier l'action à la visite d'un autre client).
    if payload.source_visit_id is not None:
        visit = await rssi_action_service.get_visit_for_client(
            db, payload.source_visit_id, client_id
        )
        if visit is None:
            raise HTTPException(status_code=422, detail="Visite source introuvable pour ce client")

    return await rssi_action_service.create_action(
        db,
        client_id=client_id,
        values={
            "title": payload.title.strip(),
            "description": payload.description,
            "category": payload.category,
            "priority": payload.priority,
            "assigned_to": payload.assigned_to,
            "due_date": payload.due_date,
            "source_visit_id": payload.source_visit_id,
        },
    )


@router.put("/clients/{client_id}/actions/{action_id}", response_model=RssiActionOut)
async def update_action(
    client_id: int,
    action_id: int,
    payload: RssiActionUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    action = await rssi_action_service.get_action(db, action_id, client_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvée")

    # Patch partiel : seuls les champs fournis non-nuls sont appliqués (mêmes
    # sémantiques que l'ancienne cascade de `if payload.x is not None`).
    values: dict = {}
    if payload.title is not None:
        values["title"] = payload.title.strip()
    if payload.description is not None:
        values["description"] = payload.description
    if payload.category is not None:
        values["category"] = payload.category
    if payload.priority is not None:
        values["priority"] = payload.priority
    if payload.status is not None:
        values["status"] = payload.status
        if payload.status == "done" and action.completed_at is None:
            values["completed_at"] = datetime.now(UTC)
    if payload.assigned_to is not None:
        values["assigned_to"] = payload.assigned_to
    if payload.due_date is not None:
        values["due_date"] = payload.due_date
    if payload.completed_at is not None:
        values["completed_at"] = payload.completed_at

    return await rssi_action_service.update_action(db, action, values)


@router.delete("/clients/{client_id}/actions/{action_id}", status_code=204)
async def delete_action(
    client_id: int,
    action_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    action = await rssi_action_service.get_action(db, action_id, client_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvée")
    await rssi_action_service.delete_action(db, action)


@router.get("/clients/{client_id}/actions/export")
async def export_actions_csv(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Export all actions for a client as a CSV file."""
    await _get_client_or_404(client_id, current_user.id, db)

    actions = await rssi_action_service.list_actions(db, client_id)

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writerow(
        [
            "Titre",
            "Catégorie",
            "Priorité",
            "Statut",
            "Responsable",
            "Échéance",
            "Terminée le",
            "Créée le",
        ]
    )

    _priority_fr = {
        "critical": "Critique",
        "high": "Haute",
        "medium": "Moyenne",
        "low": "Basse",
    }
    _status_fr = {
        "open": "Ouverte",
        "in_progress": "En cours",
        "done": "Terminée",
        "cancelled": "Annulée",
        "postponed": "Reportée",
    }
    _category_fr = {
        "governance": "Gouvernance",
        "technical": "Technique",
        "training": "Formation",
        "compliance": "Conformité",
    }

    for a in actions:
        writer.writerow(
            [
                a.title,
                _category_fr.get(a.category or "", a.category or ""),
                _priority_fr.get(a.priority, a.priority),
                _status_fr.get(a.status, a.status),
                a.assigned_to or "",
                str(a.due_date) if a.due_date else "",
                str(a.completed_at.date()) if a.completed_at else "",
                str(a.created_at.date()) if a.created_at else "",
            ]
        )

    csv_bytes = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=actions_client_{client_id}.csv"},
    )
