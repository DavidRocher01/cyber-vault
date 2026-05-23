"""RSSI Externalisé — multi-client dashboard for security consultants.

Sprint 1: client CRUD (enhanced), visits CRUD, actions CRUD.
"""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.rssi_action import RssiAction
from app.models.rssi_activity_log import RssiActivityLog
from app.models.rssi_client import RssiClient
from app.models.rssi_deliverable import RssiDeliverable
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


# ── Aggregation helper ─────────────────────────────────────────────────────────

async def _compute_aggregates(
    client_ids: list[int],
    user_id: int,
    db: AsyncSession,
) -> dict[int, tuple[int, str | None, datetime | None]]:
    """Returns {client_id: (sites_count, worst_status, last_scan_at)} for each id."""
    if not client_ids:
        return {}

    sites_result = await db.execute(
        select(Site).where(
            Site.user_id == user_id,
            Site.rssi_client_id.in_(client_ids),
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

    aggregates: dict[int, tuple[int, str | None, datetime | None]] = {}
    for cid in client_ids:
        client_sites = sites_by_client.get(cid, [])
        client_scans = [latest_scans[s.id] for s in client_sites if s.id in latest_scans]

        worst: str | None = None
        if client_scans:
            statuses = [sc.overall_status for sc in client_scans if sc.overall_status]
            if statuses:
                worst = sorted(statuses, key=lambda x: STATUS_ORDER.get(x, 99))[0]

        last_scan_at = max((sc.finished_at for sc in client_scans if sc.finished_at), default=None)
        aggregates[cid] = (len(client_sites), worst, last_scan_at)

    return aggregates


# ── Client endpoints ───────────────────────────────────────────────────────────

@router.get("/clients", response_model=list[RssiClientOut])
async def list_clients(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    clients_result = await db.execute(
        select(RssiClient)
        .where(RssiClient.consultant_user_id == current_user.id)
        .order_by(RssiClient.created_at.desc())
    )
    clients = clients_result.scalars().all()
    aggregates = await _compute_aggregates([c.id for c in clients], current_user.id, db)

    return [
        _build_client_out(c, *aggregates.get(c.id, (0, None, None)))
        for c in clients
    ]


@router.get("/clients/{client_id}", response_model=RssiClientOut)
async def get_client(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user.id, db)
    aggregates = await _compute_aggregates([client_id], current_user.id, db)
    return _build_client_out(client, *aggregates.get(client_id, (0, None, None)))


@router.post("/clients", response_model=RssiClientOut, status_code=201)
async def create_client(
    payload: RssiClientCreate,
    current_user: User = Depends(get_rssi_consultant),
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
    current_user: User = Depends(get_rssi_consultant),
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
    current_user: User = Depends(get_rssi_consultant),
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


# ── Sites for RSSI client (Sprint 5C) ─────────────────────────────────────────

class RssiSiteOut(BaseModel):
    id: int
    url: str
    name: str
    is_active: bool
    created_at: datetime
    latest_scan_status: str | None   # OK | WARNING | CRITICAL | None
    last_scan_at: datetime | None

    model_config = {"from_attributes": False}


@router.get("/clients/{client_id}/sites", response_model=list[RssiSiteOut])
async def list_client_sites(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Active sites linked to this RSSI client, with latest scan status."""
    await _get_client_or_404(client_id, current_user.id, db)

    sites_result = await db.execute(
        select(Site).where(
            Site.user_id == current_user.id,
            Site.rssi_client_id == client_id,
            Site.is_active == True,  # noqa: E712
        ).order_by(Site.created_at.desc())
    )
    sites = sites_result.scalars().all()

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

    return [
        RssiSiteOut(
            id=s.id,
            url=s.url,
            name=s.name,
            is_active=s.is_active,
            created_at=s.created_at,
            latest_scan_status=latest_scans[s.id].overall_status if s.id in latest_scans else None,
            last_scan_at=latest_scans[s.id].finished_at if s.id in latest_scans else None,
        )
        for s in sites
    ]


class UnlinkedSiteOut(BaseModel):
    id: int
    url: str
    name: str

    model_config = {"from_attributes": True}


@router.get("/sites/unlinked", response_model=list[UnlinkedSiteOut])
async def list_unlinked_sites(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Active sites of this consultant that are not linked to any RSSI client."""
    result = await db.execute(
        select(Site).where(
            Site.user_id == current_user.id,
            Site.is_active == True,  # noqa: E712
            Site.rssi_client_id.is_(None),
        ).order_by(Site.name)
    )
    return result.scalars().all()


@router.put("/clients/{client_id}/sites/{site_id}", response_model=RssiSiteOut)
async def link_site_to_client(
    client_id: int,
    site_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Link an existing site to an RSSI client."""
    await _get_client_or_404(client_id, current_user.id, db)

    site_result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id, Site.is_active == True)  # noqa: E712
    )
    site = site_result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    if site.rssi_client_id is not None and site.rssi_client_id != client_id:
        raise HTTPException(status_code=409, detail="Ce site est déjà lié à un autre client RSSI")

    site.rssi_client_id = client_id
    await db.commit()
    await db.refresh(site)

    latest_scan: Scan | None = None
    scan_result = await db.execute(
        select(Scan).where(Scan.site_id == site_id, Scan.status == "done")
        .order_by(Scan.finished_at.desc()).limit(1)
    )
    latest_scan = scan_result.scalar_one_or_none()

    return RssiSiteOut(
        id=site.id, url=site.url, name=site.name, is_active=site.is_active,
        created_at=site.created_at,
        latest_scan_status=latest_scan.overall_status if latest_scan else None,
        last_scan_at=latest_scan.finished_at if latest_scan else None,
    )


@router.delete("/clients/{client_id}/sites/{site_id}", status_code=204)
async def unlink_site_from_client(
    client_id: int,
    site_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Remove the link between a site and an RSSI client (site is NOT deleted)."""
    await _get_client_or_404(client_id, current_user.id, db)

    site_result = await db.execute(
        select(Site).where(
            Site.id == site_id,
            Site.user_id == current_user.id,
            Site.rssi_client_id == client_id,
        )
    )
    site = site_result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé ou non lié à ce client")

    site.rssi_client_id = None
    await db.commit()


# ── Visit endpoints ────────────────────────────────────────────────────────────

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


# ── Action endpoints ───────────────────────────────────────────────────────────

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


# ── Dashboard endpoints (Sprint 2) ────────────────────────────────────────────

from app.services import rssi_aggregation_service as _agg


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated stats across all active clients."""
    overview = await _agg.compute_overview(current_user.id, db)
    return overview.dict()


@router.get("/dashboard/clients-summary")
async def get_clients_summary(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Per-client summary with action counts and next visit."""
    return await _agg.get_clients_summary(current_user.id, db)


@router.get("/dashboard/alerts")
async def get_pending_alerts(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Alerts requiring attention: overdue actions, renewals, no recent visit."""
    return await _agg.get_pending_alerts(current_user.id, db)


@router.get("/dashboard/upcoming-events")
async def get_upcoming_events(
    days_ahead: int = 14,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Planned visits in the next N days (default 14)."""
    return await _agg.get_upcoming_events(current_user.id, days_ahead, db)


@router.get("/dashboard/suggestions")
async def get_suggestions(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Rule-based suggestions: upsell, engagement alerts, high overdue."""
    return await _agg.compute_suggestions(current_user.id, db)


# ── Activity log (Sprint 3) ────────────────────────────────────────────────────

class ActivityLogCreate(BaseModel):
    action_type: str           # view_client | view_sites | view_scans | view_findings | generate_report | send_deliverable | …
    resource_type: str | None = None
    resource_id: int | None = None


class ActivityLogOut(BaseModel):
    id: int
    consultant_id: int
    client_id: int
    action_type: str
    resource_type: str | None
    resource_id: int | None
    performed_at: datetime

    model_config = {"from_attributes": True}


_VALID_ACTION_TYPES = {
    "view_client", "view_sites", "view_scans", "view_findings",
    "generate_report", "send_deliverable", "create_action", "update_action",
    "create_visit", "update_visit",
}


@router.post("/clients/{client_id}/activity", response_model=ActivityLogOut, status_code=201)
async def log_activity(
    client_id: int,
    body: ActivityLogCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Record a consultant action on a client account."""
    await _get_client_or_404(client_id, current_user.id, db)

    if body.action_type not in _VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"action_type invalide. Valeurs acceptées: {sorted(_VALID_ACTION_TYPES)}",
        )

    entry = RssiActivityLog(
        consultant_id=current_user.id,
        client_id=client_id,
        action_type=body.action_type,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/clients/{client_id}/activity", response_model=list[ActivityLogOut])
async def get_activity_log(
    client_id: int,
    limit: int = 50,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """List the N most recent activity log entries for a client (default 50)."""
    await _get_client_or_404(client_id, current_user.id, db)

    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit doit être entre 1 et 200",
        )

    result = await db.execute(
        select(RssiActivityLog)
        .where(
            RssiActivityLog.client_id == client_id,
            RssiActivityLog.consultant_id == current_user.id,
        )
        .order_by(RssiActivityLog.performed_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ── PDF report (Sprint 5) ──────────────────────────────────────────────────────

@router.get("/clients/{client_id}/report")
async def get_client_report(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Generate and stream a PDF report for a client."""
    from app.services.rssi_report_pdf import generate_rssi_report

    client = await _get_client_or_404(client_id, current_user.id, db)

    visits_result = await db.execute(
        select(RssiVisit)
        .where(RssiVisit.client_id == client_id)
        .order_by(RssiVisit.scheduled_date.desc())
    )
    actions_result = await db.execute(
        select(RssiAction)
        .where(RssiAction.client_id == client_id)
        .order_by(RssiAction.created_at.desc())
    )
    deliverables_result = await db.execute(
        select(RssiDeliverable)
        .where(RssiDeliverable.client_id == client_id)
        .order_by(RssiDeliverable.delivered_at.desc())
    )

    client_dict = {
        "name":                  client.name,
        "email":                 client.email,
        "description":           client.description,
        "formula":               client.formula,
        "monthly_amount":        float(client.monthly_amount) if client.monthly_amount else None,
        "contract_renewal_at":   str(client.contract_renewal_at) if client.contract_renewal_at else None,
        "status":                client.status,
        "notion_workspace_url":  client.notion_workspace_url,
        "pipedrive_deal_id":     client.pipedrive_deal_id,
        "pennylane_customer_id": client.pennylane_customer_id,
    }
    actions_list = [
        {
            "title":       a.title,
            "priority":    a.priority,
            "status":      a.status,
            "due_date":    str(a.due_date) if a.due_date else None,
            "assigned_to": a.assigned_to,
            "category":    a.category,
        }
        for a in actions_result.scalars().all()
    ]
    visits_list = [
        {
            "scheduled_date": str(v.scheduled_date),
            "visit_type":     v.visit_type,
            "location":       v.location,
            "status":         v.status,
            "duration_hours": float(v.duration_hours) if v.duration_hours else None,
            "actual_date":    str(v.actual_date) if v.actual_date else None,
        }
        for v in visits_result.scalars().all()
    ]
    deliverables_list = [
        {
            "title":        d.title,
            "doc_type":     d.doc_type,
            "delivered_at": str(d.delivered_at),
            "file_url":     d.file_url,
            "notes":        d.notes,
        }
        for d in deliverables_result.scalars().all()
    ]

    consultant_dict = {
        "email":        current_user.email,
        "display_name": current_user.display_name,
        "company_name": current_user.company_name,
        "phone":        current_user.phone,
    }
    pdf_bytes = generate_rssi_report(client_dict, actions_list, visits_list, deliverables_list, consultant_dict)
    safe_name  = client.name.replace(" ", "_").replace("/", "-").lower()
    filename   = f"rapport_rssi_{safe_name}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Deliverables (Sprint 5A) ───────────────────────────────────────────────────

_VALID_DOC_TYPES = {"compte_rendu", "rapport", "recommandation", "contrat", "autre"}


class RssiDeliverableCreate(BaseModel):
    title: str
    doc_type: str = "autre"         # compte_rendu | rapport | recommandation | contrat | autre
    file_url: str | None = None
    notes: str | None = None
    delivered_at: date


class RssiDeliverableUpdate(BaseModel):
    title: str | None = None
    doc_type: str | None = None
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
    result = await db.execute(
        select(RssiDeliverable)
        .where(RssiDeliverable.client_id == client_id)
        .order_by(RssiDeliverable.delivered_at.desc())
    )
    return result.scalars().all()


@router.post("/clients/{client_id}/deliverables", response_model=RssiDeliverableOut, status_code=201)
async def create_deliverable(
    client_id: int,
    payload: RssiDeliverableCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)

    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="Le titre du livrable est requis")
    if payload.doc_type not in _VALID_DOC_TYPES:
        raise HTTPException(status_code=422, detail=f"Type de document invalide. Valeurs: {_VALID_DOC_TYPES}")

    deliverable = RssiDeliverable(
        client_id=client_id,
        title=payload.title.strip(),
        doc_type=payload.doc_type,
        file_url=payload.file_url,
        notes=payload.notes,
        delivered_at=payload.delivered_at,
    )
    db.add(deliverable)
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


@router.put("/clients/{client_id}/deliverables/{deliverable_id}", response_model=RssiDeliverableOut)
async def update_deliverable(
    client_id: int,
    deliverable_id: int,
    payload: RssiDeliverableUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    result = await db.execute(
        select(RssiDeliverable).where(
            RssiDeliverable.id == deliverable_id,
            RssiDeliverable.client_id == client_id,
        )
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")

    if payload.doc_type is not None and payload.doc_type not in _VALID_DOC_TYPES:
        raise HTTPException(status_code=422, detail=f"Type de document invalide. Valeurs: {_VALID_DOC_TYPES}")

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

    deliverable.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


@router.delete("/clients/{client_id}/deliverables/{deliverable_id}", status_code=204)
async def delete_deliverable(
    client_id: int,
    deliverable_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, current_user.id, db)
    result = await db.execute(
        select(RssiDeliverable).where(
            RssiDeliverable.id == deliverable_id,
            RssiDeliverable.client_id == client_id,
        )
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")
    await db.delete(deliverable)
    await db.commit()


# ── Consultant profile (P6) ────────────────────────────────────────────────────

class ConsultantProfileOut(BaseModel):
    email: str
    display_name: str | None
    company_name: str | None
    phone: str | None

    model_config = {"from_attributes": False}


class ConsultantProfileUpdate(BaseModel):
    display_name: str | None = None
    company_name: str | None = None
    phone: str | None = None


@router.get("/profile", response_model=ConsultantProfileOut)
async def get_consultant_profile(
    current_user: User = Depends(get_rssi_consultant),
):
    return ConsultantProfileOut(
        email=current_user.email,
        display_name=current_user.display_name,
        company_name=current_user.company_name,
        phone=current_user.phone,
    )


@router.patch("/profile", response_model=ConsultantProfileOut)
async def update_consultant_profile(
    payload: ConsultantProfileUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name.strip() or None
    if payload.company_name is not None:
        current_user.company_name = payload.company_name.strip() or None
    if payload.phone is not None:
        current_user.phone = payload.phone.strip() or None
    await db.commit()
    await db.refresh(current_user)
    return ConsultantProfileOut(
        email=current_user.email,
        display_name=current_user.display_name,
        company_name=current_user.company_name,
        phone=current_user.phone,
    )


# ── CSV export (P7) ────────────────────────────────────────────────────────────

@router.get("/clients/{client_id}/actions/export")
async def export_actions_csv(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Export all actions for a client as a CSV file."""
    import csv
    import io

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

    csv_bytes = buf.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=actions_client_{client_id}.csv"},
    )


# ── File upload / download (P8) ────────────────────────────────────────────────

@router.post("/clients/{client_id}/deliverables/upload")
async def upload_deliverable_file(
    client_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file for a client deliverable and return its storage key."""
    from app.services.storage import upload_file, validate_upload, MAX_UPLOAD_BYTES

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

    result = await db.execute(
        select(RssiDeliverable).where(
            RssiDeliverable.id == deliverable_id,
            RssiDeliverable.client_id == client_id,
        )
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")
    if not deliverable.file_url:
        raise HTTPException(status_code=404, detail="Aucun fichier attaché à ce livrable")

    url = get_download_url(deliverable.file_url)
    return {"url": url}
