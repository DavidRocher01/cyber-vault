from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.rssi_client import RssiClient
from app.models.user import User
from app.schemas.administration import ClientAwarenessOut, PortalInviteOut

# Schemas deplaces dans schemas/rssi_client.py ; re-exportes ici pour ne pas
# casser les imports existants (rssi/__init__.py, tests).
from app.schemas.rssi_client import (
    ClientFormula,  # noqa: F401
    ClientStatus,  # noqa: F401
    RssiClientCreate,
    RssiClientOut,
    RssiClientUpdate,
    RssiSiteOut,
    UnlinkedSiteOut,  # noqa: F401
)
from app.services.rssi import client_service

from ._shared import _get_client_or_404

router = APIRouter()


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


# ── Client CRUD ────────────────────────────────────────────────────────────────


@router.get("/clients", response_model=list[RssiClientOut])
async def list_clients(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    clients = await client_service.list_clients_for_consultant(db, current_user.id)
    aggregates = await client_service.compute_client_aggregates(
        db, [c.id for c in clients], current_user.id
    )
    return [_build_client_out(c, *aggregates.get(c.id, (0, None, None))) for c in clients]


@router.get("/clients/{client_id}", response_model=RssiClientOut)
async def get_client(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user.id, db)
    aggregates = await client_service.compute_client_aggregates(db, [client_id], current_user.id)
    return _build_client_out(client, *aggregates.get(client_id, (0, None, None)))


@router.post("/clients", response_model=RssiClientOut, status_code=201)
async def create_client(
    payload: RssiClientCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Le nom du client est requis")

    client = await client_service.create_client(
        db,
        consultant_user_id=current_user.id,
        values={
            "name": payload.name.strip(),
            "email": payload.email,
            "description": payload.description,
            "formula": payload.formula,
            "monthly_amount": payload.monthly_amount,
            "contract_start_date": payload.contract_start_date,
            "contract_renewal_at": payload.contract_renewal_at,
            "notion_workspace_url": payload.notion_workspace_url,
            "pipedrive_deal_id": payload.pipedrive_deal_id,
            "pennylane_customer_id": payload.pennylane_customer_id,
        },
    )
    return _build_client_out(client, 0, None, None)


@router.put("/clients/{client_id}", response_model=RssiClientOut)
async def update_client(
    client_id: int,
    payload: RssiClientUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user.id, db)

    # Patch partiel : seuls les champs fournis non-nuls sont appliques (memes
    # semantiques que l'ancienne cascade de `if payload.x is not None`).
    updates = payload.model_dump(exclude_none=True)
    if "name" in updates:
        updates["name"] = updates["name"].strip()

    client = await client_service.update_client(db, client, updates)
    return _build_client_out(client, 0, None, None)


@router.delete("/clients/{client_id}", status_code=204)
async def delete_client(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, current_user.id, db)
    await client_service.delete_client(db, client)


# ── Sites for RSSI client ──────────────────────────────────────────────────────


@router.get("/clients/{client_id}/sites", response_model=list[RssiSiteOut])
async def list_client_sites(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Active sites linked to this RSSI client, with latest scan status."""
    await _get_client_or_404(client_id, current_user.id, db)

    sites = await client_service.list_active_sites_for_client(db, current_user.id, client_id)
    latest_scans = await client_service.latest_done_scans_by_site(db, [s.id for s in sites])

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
    return await client_service.list_unlinked_sites(db, current_user.id)


@router.put("/clients/{client_id}/sites/{site_id}", response_model=RssiSiteOut)
async def link_site_to_client(
    client_id: int,
    site_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Link an existing site to an RSSI client."""
    await _get_client_or_404(client_id, current_user.id, db)

    site = await client_service.get_active_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    if site.rssi_client_id is not None and site.rssi_client_id != client_id:
        raise HTTPException(status_code=409, detail="Ce site est déjà lié à un autre client RSSI")

    site = await client_service.link_site(db, site, client_id)
    latest_scan = await client_service.latest_done_scan_for_site(db, site_id)

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

    site = await client_service.get_linked_site(db, site_id, current_user.id, client_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé ou non lié à ce client")

    await client_service.unlink_site(db, site)


@router.post("/clients/{client_id}/invite", response_model=PortalInviteOut)
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
    from datetime import UTC, datetime, timedelta

    from app.core.config import settings
    from app.core.security import hash_password, hash_token
    from app.services.email_service import send_portal_invitation

    INVITE_TTL_DAYS = 7

    client = await _get_client_or_404(client_id, current_user.id, db)
    if not client.email:
        raise HTTPException(
            status_code=422, detail="Renseignez l'email du client avant de l'inviter."
        )

    user = await client_service.get_user_by_email(db, client.email)
    account_created = False
    if user is None:
        user = await client_service.create_portal_user(
            db,
            email=client.email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        account_created = True

    # Ce compte ne doit pas déjà être rattaché à un AUTRE client (unicité du portail).
    other = await client_service.get_other_client_for_user(
        db, user_id=user.id, exclude_client_id=client.id
    )
    if other is not None:
        raise HTTPException(
            status_code=409, detail="Ce compte est déjà rattaché à un autre client."
        )

    raw_token = secrets.token_urlsafe(32)
    await client_service.link_client_and_add_reset_token(
        db,
        client=client,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=INVITE_TTL_DAYS),
    )

    invite_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={raw_token}&invite=1"
    background_tasks.add_task(
        send_portal_invitation,
        client.email,
        invite_url,
        client.name,
        current_user.display_name,
        INVITE_TTL_DAYS,
    )
    resp = {"status": "invited", "email": client.email, "account_created": account_created}
    # DEV_MODE only : expose le lien d'activation (token brut) pour l'E2E — le token
    # est hache en base, donc irrecuperable autrement. Jamais expose en prod.
    if settings.is_dev_mode:
        resp["invite_url"] = invite_url
    return resp


@router.post("/clients/{client_id}/awareness", response_model=ClientAwarenessOut)
async def enable_client_awareness(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Active la sensibilisation NIS2 pour un client : crée (ou renvoie) l'organisation de
    formation liée, propriété du consultant. Idempotent (unifie client RSSI <-> org awareness)."""
    from app.models.awareness_organization import AwarenessOrganization

    client = await _get_client_or_404(client_id, current_user.id, db)

    async def _out(org: AwarenessOrganization, already: bool) -> dict:
        count = await client_service.count_learners(db, org.id)
        return {
            "id": org.id,
            "name": org.name,
            "max_learners": org.max_learners,
            "learner_count": count,
            "already": already,
        }

    # Déjà liée -> renvoie l'organisation existante
    if client.awareness_organization_id is not None:
        org = await client_service.get_awareness_org(db, client.awareness_organization_id)
        if org is not None:
            return await _out(org, already=True)

    # Sinon création + liaison (même propriétaire que le consultant, isolation cohérente).
    seats = {"essentiel": 10, "premium": 25, "excellence": 50}.get(client.formula or "", 10)
    org = await client_service.create_awareness_org_for_client(
        db,
        client=client,
        owner_user_id=current_user.id,
        name=client.name,
        max_learners=seats,
    )
    return await _out(org, already=False)
