from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.rssi_client import RssiClient
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User

from ._shared import _get_client_or_404

router = APIRouter()

STATUS_ORDER = {"CRITICAL": 0, "WARNING": 1, "OK": 2}

ClientFormula = Literal["essentiel", "premium", "excellence"]
ClientStatus = Literal["active", "inactive", "churned"]


# ── Schemas ────────────────────────────────────────────────────────────────────


class RssiClientCreate(BaseModel):
    name: str
    email: str | None = None
    description: str | None = None
    formula: ClientFormula | None = None
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
    formula: ClientFormula | None = None
    monthly_amount: float | None = None
    contract_start_date: date | None = None
    contract_renewal_at: date | None = None
    status: ClientStatus | None = None
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
    awareness_organization_id: int | None
    created_at: datetime
    updated_at: datetime | None
    sites_count: int
    worst_status: str | None
    last_scan_at: datetime | None

    model_config = {"from_attributes": False}


class RssiSiteOut(BaseModel):
    id: int
    url: str
    name: str
    is_active: bool
    created_at: datetime
    latest_scan_status: str | None
    last_scan_at: datetime | None

    model_config = {"from_attributes": False}


class UnlinkedSiteOut(BaseModel):
    id: int
    url: str
    name: str

    model_config = {"from_attributes": True}


# ── Aggregation helpers ────────────────────────────────────────────────────────


def _build_client_out(
    c: RssiClient, sites_count: int, worst: str | None, last_scan_at: datetime | None
) -> RssiClientOut:
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
        awareness_organization_id=c.awareness_organization_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
        sites_count=sites_count,
        worst_status=worst,
        last_scan_at=last_scan_at,
    )


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


# ── Client CRUD ────────────────────────────────────────────────────────────────


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
    return [_build_client_out(c, *aggregates.get(c.id, (0, None, None))) for c in clients]


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

    client.updated_at = datetime.now(UTC)
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

    sites_result = await db.execute(select(Site).where(Site.rssi_client_id == client_id))
    for site in sites_result.scalars().all():
        site.rssi_client_id = None

    await db.delete(client)
    await db.commit()


# ── Sites for RSSI client ──────────────────────────────────────────────────────


@router.get("/clients/{client_id}/sites", response_model=list[RssiSiteOut])
async def list_client_sites(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Active sites linked to this RSSI client, with latest scan status."""
    await _get_client_or_404(client_id, current_user.id, db)

    sites_result = await db.execute(
        select(Site)
        .where(
            Site.user_id == current_user.id,
            Site.rssi_client_id == client_id,
            Site.is_active == True,  # noqa: E712
        )
        .order_by(Site.created_at.desc())
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


@router.get("/sites/unlinked", response_model=list[UnlinkedSiteOut])
async def list_unlinked_sites(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Active sites of this consultant that are not linked to any RSSI client."""
    result = await db.execute(
        select(Site)
        .where(
            Site.user_id == current_user.id,
            Site.is_active == True,  # noqa: E712
            Site.rssi_client_id.is_(None),
        )
        .order_by(Site.name)
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
        select(Site).where(
            Site.id == site_id, Site.user_id == current_user.id, Site.is_active == True
        )  # noqa: E712
    )
    site = site_result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    if site.rssi_client_id is not None and site.rssi_client_id != client_id:
        raise HTTPException(status_code=409, detail="Ce site est déjà lié à un autre client RSSI")

    site.rssi_client_id = client_id
    await db.commit()
    await db.refresh(site)

    scan_result = await db.execute(
        select(Scan)
        .where(Scan.site_id == site_id, Scan.status == "done")
        .order_by(Scan.finished_at.desc())
        .limit(1)
    )
    latest_scan = scan_result.scalar_one_or_none()

    return RssiSiteOut(
        id=site.id,
        url=site.url,
        name=site.name,
        is_active=site.is_active,
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


@router.post("/clients/{client_id}/invite")
async def invite_client_to_portal(
    client_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Invite le client à son espace : crée (ou lie) un compte User avec l'email du client,
    rattache le RssiClient (client_user_id) et envoie un e-mail de définition de mot de passe
    (réutilise le flux reset-password). Le client accède ensuite à /espace-client."""
    import secrets
    from datetime import timedelta

    from app.core.config import settings
    from app.core.security import hash_password, hash_token
    from app.models.password_reset_token import PasswordResetToken
    from app.services.email_service import send_password_reset

    client = await _get_client_or_404(client_id, current_user.id, db)
    if not client.email:
        raise HTTPException(
            status_code=422, detail="Renseignez l'email du client avant de l'inviter."
        )

    user = (await db.execute(select(User).where(User.email == client.email))).scalar_one_or_none()
    account_created = False
    if user is None:
        user = User(
            email=client.email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            is_active=True,
        )
        db.add(user)
        await db.flush()
        account_created = True

    # Ce compte ne doit pas déjà être rattaché à un AUTRE client (unicité du portail).
    other = (
        await db.execute(
            select(RssiClient).where(
                RssiClient.client_user_id == user.id, RssiClient.id != client.id
            )
        )
    ).scalar_one_or_none()
    if other is not None:
        raise HTTPException(
            status_code=409, detail="Ce compte est déjà rattaché à un autre client."
        )

    client.client_user_id = user.id

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    await db.commit()

    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={raw_token}"
    background_tasks.add_task(send_password_reset, client.email, reset_url)
    return {"status": "invited", "email": client.email, "account_created": account_created}


@router.post("/clients/{client_id}/awareness")
async def enable_client_awareness(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Active la sensibilisation NIS2 pour un client : crée (ou renvoie) l'organisation de
    formation liée, propriété du consultant. Idempotent (unifie client RSSI <-> org awareness)."""
    from sqlalchemy import func

    from app.models.awareness_learner import AwarenessLearner
    from app.models.awareness_organization import AwarenessOrganization

    client = await _get_client_or_404(client_id, current_user.id, db)

    async def _out(org: AwarenessOrganization, already: bool) -> dict:
        count = (
            await db.execute(
                select(func.count(AwarenessLearner.id)).where(
                    AwarenessLearner.organization_id == org.id
                )
            )
        ).scalar()
        return {
            "id": org.id,
            "name": org.name,
            "max_learners": org.max_learners,
            "learner_count": count or 0,
            "already": already,
        }

    # Déjà liée -> renvoie l'organisation existante
    if client.awareness_organization_id is not None:
        org = (
            await db.execute(
                select(AwarenessOrganization).where(
                    AwarenessOrganization.id == client.awareness_organization_id
                )
            )
        ).scalar_one_or_none()
        if org is not None:
            return await _out(org, already=True)

    # Sinon création + liaison (même propriétaire que le consultant, isolation cohérente).
    seats = {"essentiel": 10, "premium": 25, "excellence": 50}.get(client.formula or "", 10)
    org = AwarenessOrganization(owner_user_id=current_user.id, name=client.name, max_learners=seats)
    db.add(org)
    await db.flush()
    client.awareness_organization_id = org.id
    await db.commit()
    return await _out(org, already=False)
