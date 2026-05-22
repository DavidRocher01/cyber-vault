"""RSSI Externalisé — multi-client dashboard for security consultants.

Sprint 1: client CRUD (enhanced), visits CRUD, actions CRUD.
"""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_rssi_consultant
from app.models.rssi_action import RssiAction
from app.models.rssi_client import RssiClient
from app.models.rssi_visit import RssiVisit
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/rssi", tags=["rssi"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class RssiClientCreate(BaseModel):
    name: str
    email: str | None = None
    description: str | None = None
    formula: str | None = None               # essentiel | premium | excellence
    monthly_amount: float | None = None
    contract_start_date: date | None = None
    contract_renewal_at: date | None = None
    notion_workspace_url: str | None = None
    pipedrive_deal_id: str | None = None
    pennylane_customer_id: str | None = None


class RssiClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    description: str | None = None
    formula: str | None = None
    monthly_amount: float | None = None
    contract_start_date: date | None = None
    contract_renewal_at: date | None = None
    status: str | None = None
    notion_workspace_url: str | None = None
    pipedrive_deal_id: str | None = None
    pennylane_customer_id: str | None = None


class RssiClientOut(BaseModel):
    id: int
    name: str
    email: str | None
    description: str | None
    formula: str | None
    monthly_amount: float | None
    contract_start_date: date | None
    contract_renewal_at: date | None
    status: str
    notion_workspace_url: str | None
    pipedrive_deal_id: str | None
    pennylane_customer_id: str | None
    created_at: datetime
    updated_at: datetime | None
    # Aggregated from sites/scans
    sites_count: int
    worst_status: str | None
    last_scan_at: datetime | None

    model_config = {"from_attributes": False}


class RssiVisitCreate(BaseModel):
    scheduled_date: date
    visit_type: str = "monthly"   # monthly | quarterly | annual | urgent
    location: str = "onsite"      # onsite | remote
    notes: str | None = None


class RssiVisitUpdate(BaseModel):
    scheduled_date: date | None = None
    visit_type: str | None = None
    location: str | None = None
    status: str | None = None    # planned | completed | cancelled | postponed
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


class RssiActionCreate(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None   # governance | technical | training | compliance
    priority: str = "medium"      # critical | high | medium | low
    assigned_to: str | None = None
    due_date: date | None = None
    source_visit_id: int | None = None


class RssiActionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    status: str | None = None     # open | in_progress | done | cancelled | postponed
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


# ── Helpers ────────────────────────────────────────────────────────────────────

STATUS_ORDER = {"CRITICAL": 0, "WARNING": 1, "OK": 2}

_VALID_FORMULAS = {"essentiel", "premium", "excellence"}
_VALID_STATUSES = {"active", "inactive", "churned"}
_VALID_VISIT_TYPES = {"monthly", "quarterly", "annual", "urgent"}
_VALID_VISIT_LOCATIONS = {"onsite", "remote"}
_VALID_VISIT_STATUSES = {"planned", "completed", "cancelled", "postponed"}
_VALID_PRIORITIES = {"critical", "high", "medium", "low"}
_VALID_ACTION_STATUSES = {"open", "in_progress", "done", "cancelled", "postponed"}


async def _get_client_or_404(client_id: int, user_id: int, db: AsyncSession) -> RssiClient:
    result = await db.execute(
        select(RssiClient).where(
            RssiClient.id == client_id,
            RssiClient.consultant_user_id == user_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client non trouvé")
    return client


def _build_client_out(c: RssiClient, sites_count: int, worst: str | None, last_scan_at: datetime | None) -> RssiClientOut:
    return RssiClientOut(
        id=c.id,
        name=c.name,
        email=c.email,
        description=c.description,
        formula=c.formula,
        monthly_amount=float(c.monthly_amount) if c.monthly_amount is not None else None,
        contract_start_date=c.contract_start_date,
        contract_renewal_at=c.contract_renewal_at,
        status=c.status,
        notion_workspace_url=c.notion_workspace_url,
        pipedrive_deal_id=c.pipedrive_deal_id,
        pennylane_customer_id=c.pennylane_customer_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
        sites_count=sites_count,
        worst_status=worst,
        last_scan_at=last_scan_at,
    )


# ── Client endpoints ───────────────────────────────────────────────────────────

@router.get("/clients", response_model=list[RssiClientOut])
async def list_clients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clients_result = await db.execute(
        select(RssiClient)
        .where(RssiClient.consultant_user_id == current_user.id)
        .order_by(RssiClient.created_at.desc())
    )
    clients = clients_result.scalars().all()

    sites_result = await db.execute(
        select(Site).where(
            Site.user_id == current_user.id,
            Site.rssi_client_id.in_([c.id for c in clients]),
            Site.is_active == True,  # noqa: E712
        )
    )
    sites = sites_result.scalars().all()
    sites_by_client: dict[int, list[Site]] = {}
    for s in sites:
        sites_by_client.setdefault(s.rssi_client_id, []).append(s)

    site_ids = [s.id for s in sites]
    latest_scans: dict[int, Scan] = {}
    if site_ids:
        scans_result = await db.execute(
            select(Scan)
            .where(Scan.site_id.in_(site_ids), Scan.status == "done")
            .order_by(Scan.finished_at.desc())
        )
        for scan in scans_result.scalars().all():
            if scan.site_id not in latest_scans:
                latest_scans[scan.site_id] = scan

    out = []
    for c in clients:
        client_sites = sites_by_client.get(c.id, [])
        client_scans = [latest_scans[s.id] for s in client_sites if s.id in latest_scans]

        worst = None
        if client_scans:
            statuses = [s.overall_status for s in client_scans if s.overall_status]
            if statuses:
                worst = sorted(statuses, key=lambda x: STATUS_ORDER.get(x, 99))[0]

        last_scan_at = max((s.finished_at for s in client_scans if s.finished_at), default=None)
        out.append(_build_client_out(c, len(client_sites), worst, last_scan_at))
    return out


@router.post("/clients", response_model=RssiClientOut, status_code=201)
async def create_client(
    payload: RssiClientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Le nom du client est requis")
    if payload.formula and payload.formula not in _VALID_FORMULAS:
        raise HTTPException(status_code=422, detail=f"Formule invalide. Valeurs: {_VALID_FORMULAS}")

    client = RssiClient(
        consultant_user_id=current_user.id,
        name=payload.name.strip(),
        email=payload.email,
        description=payload.description,
        formula=payload.formula,
        monthly_amount=payload.monthly_amount,
        contract_start_date=payload.contract_start_date,
        contract_renewal_at=payload.contract_renewal_at,
        notion_workspace_url=payload.notion_workspace_url,
        pipedrive_deal_id=payload.pipedrive_deal_id,
        pennylane_customer_id=payload.pennylane_customer_id,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return _build_client_out(client, 0, None, None)


@router.put("/clients/{client_id}", response_model=RssiClientOut)
async def update_client(
    client_id: int,
    payload: RssiClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user.id, db)

    if payload.formula is not None and payload.formula not in _VALID_FORMULAS:
        raise HTTPException(status_code=422, detail=f"Formule invalide. Valeurs: {_VALID_FORMULAS}")
    if payload.status is not None and payload.status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Statut invalide. Valeurs: {_VALID_STATUSES}")

    if payload.name is not None:
        client.name = payload.name.strip()
    if payload.email is not None:
        client.email = payload.email
    if payload.description is not None:
        client.description = payload.description
    if payload.formula is not None:
        client.formula = payload.formula
    if payload.monthly_amount is not None:
        client.monthly_amount = payload.monthly_amount
    if payload.contract_start_date is not None:
        client.contract_start_date = payload.contract_start_date
    if payload.contract_renewal_at is not None:
        client.contract_renewal_at = payload.contract_renewal_at
    if payload.status is not None:
        client.status = payload.status
    if payload.notion_workspace_url is not None:
        client.notion_workspace_url = payload.notion_workspace_url
    if payload.pipedrive_deal_id is not None:
        client.pipedrive_deal_id = payload.pipedrive_deal_id
    if payload.pennylane_customer_id is not None:
        client.pennylane_customer_id = payload.pennylane_customer_id

    client.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(client)
    return _build_client_out(client, 0, None, None)


@router.delete("/clients/{client_id}", status_code=204)
async def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user.id, db)

    sites_result = await db.execute(
        select(Site).where(Site.rssi_client_id == client_id)
    )
    for site in sites_result.scalars().all():
        site.rssi_client_id = None

    await db.delete(client)
    await db.commit()


# ── Visit endpoints ────────────────────────────────────────────────────────────

@router.get("/clients/{client_id}/visits", response_model=list[RssiVisitOut])
async def list_visits(
    client_id: int,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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


# ── Action endpoints ───────────────────────────────────────────────────────────

@router.get("/clients/{client_id}/actions", response_model=list[RssiActionOut])
async def list_actions(
    client_id: int,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
