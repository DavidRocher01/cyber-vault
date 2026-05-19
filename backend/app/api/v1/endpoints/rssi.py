"""RSSI Externalisé — multi-client dashboard for security consultants."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.rssi_client import RssiClient
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/rssi", tags=["rssi"])


class RssiClientCreate(BaseModel):
    name: str
    email: str | None = None
    description: str | None = None


class RssiClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    description: str | None = None


class RssiClientOut(BaseModel):
    id: int
    name: str
    email: str | None
    description: str | None
    created_at: datetime
    sites_count: int
    worst_status: str | None
    last_scan_at: datetime | None

    model_config = {"from_attributes": False}


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
            Site.is_active == True,
        )
    )
    sites = sites_result.scalars().all()
    sites_by_client: dict[int, list[Site]] = {}
    for s in sites:
        sites_by_client.setdefault(s.rssi_client_id, []).append(s)  # type: ignore[index]

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

    STATUS_ORDER = {"CRITICAL": 0, "WARNING": 1, "OK": 2}

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

        out.append(RssiClientOut(
            id=c.id,
            name=c.name,
            email=c.email,
            description=c.description,
            created_at=c.created_at,
            sites_count=len(client_sites),
            worst_status=worst,
            last_scan_at=last_scan_at,
        ))
    return out


@router.post("/clients", response_model=RssiClientOut, status_code=201)
async def create_client(
    payload: RssiClientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Le nom du client est requis")
    client = RssiClient(
        consultant_user_id=current_user.id,
        name=payload.name.strip(),
        email=payload.email,
        description=payload.description,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return RssiClientOut(
        id=client.id,
        name=client.name,
        email=client.email,
        description=client.description,
        created_at=client.created_at,
        sites_count=0,
        worst_status=None,
        last_scan_at=None,
    )


@router.put("/clients/{client_id}", response_model=RssiClientOut)
async def update_client(
    client_id: int,
    payload: RssiClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RssiClient).where(RssiClient.id == client_id, RssiClient.consultant_user_id == current_user.id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    if payload.name is not None:
        client.name = payload.name.strip()
    if payload.email is not None:
        client.email = payload.email
    if payload.description is not None:
        client.description = payload.description
    await db.commit()
    await db.refresh(client)
    return RssiClientOut(
        id=client.id,
        name=client.name,
        email=client.email,
        description=client.description,
        created_at=client.created_at,
        sites_count=0,
        worst_status=None,
        last_scan_at=None,
    )


@router.delete("/clients/{client_id}", status_code=204)
async def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RssiClient).where(RssiClient.id == client_id, RssiClient.consultant_user_id == current_user.id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    # Detach sites from this client before deleting
    sites_result = await db.execute(
        select(Site).where(Site.rssi_client_id == client_id)
    )
    for site in sites_result.scalars().all():
        site.rssi_client_id = None

    await db.delete(client)
    await db.commit()
