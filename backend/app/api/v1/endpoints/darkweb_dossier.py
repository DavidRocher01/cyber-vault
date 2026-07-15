"""
Darkweb Dossier endpoints — B2B dark web exposure reports.

Routes:
  POST   /darkweb-dossier              — create dossier (CSV email upload)
  GET    /darkweb-dossier              — list user's dossiers
  GET    /darkweb-dossier/{id}         — dossier detail + targets
  DELETE /darkweb-dossier/{id}         — delete dossier
  GET    /darkweb-dossier/{id}/pdf     — download PDF report
  POST   /darkweb-dossier/catalog/sync — sync HIBP breach catalog (admin)
"""

import asyncio
import csv
import io
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_min_tier
from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
from app.models.user import User
from app.services.darkweb_dossier_service import (
    export_dossier_csv,
    generate_dossier_pdf,
    process_dossier,
    sync_breach_catalog,
)

router = APIRouter(prefix="/darkweb-dossier", tags=["darkweb-dossier"])

_MAX_EMAILS = 500
_MAX_DOSSIERS_PER_USER = 20


# ── Schemas ───────────────────────────────────────────────────────────────────


class TargetOut(BaseModel):
    id: int
    email: str
    status: str
    check_status: str = "pending"
    total_breaches: int
    breach_sources_json: str | None
    checked_at: datetime | None


class DossierOut(BaseModel):
    id: int
    company_name: str
    domain: str
    status: str
    total_emails: int
    exposed_emails: int
    total_breach_instances: int
    checked_count: int = 0
    unverified_count: int = 0
    risk_score: int | None
    severity_score: int | None
    top_sources_json: str | None
    error_message: str | None
    monitor_active: bool
    last_monitored_at: datetime | None
    next_monitor_at: datetime | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    targets: list[TargetOut] = []


class DossierListItem(BaseModel):
    id: int
    company_name: str
    domain: str
    status: str
    total_emails: int
    exposed_emails: int
    checked_count: int = 0
    unverified_count: int = 0
    risk_score: int | None
    severity_score: int | None
    monitor_active: bool
    created_at: datetime
    finished_at: datetime | None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_emails_csv(content: bytes) -> list[str]:
    """Extract emails from a CSV file (first column or any column named 'email')."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    emails: list[str] = []
    email_col: str | None = None

    for row in reader:
        if email_col is None:
            for col in row:
                if "email" in col.lower() or "mail" in col.lower():
                    email_col = col
                    break
            if email_col is None and row:
                email_col = list(row.keys())[0]
        if email_col and email_col in row:
            val = row[email_col].strip().lower()
            if "@" in val and "." in val.split("@")[-1]:
                emails.append(val)

    return list(dict.fromkeys(emails))  # deduplicate, preserve order


def _to_dossier_out(d: DarkwebDossier) -> DossierOut:
    return DossierOut(
        id=d.id,
        company_name=d.company_name,
        domain=d.domain,
        status=d.status,
        total_emails=d.total_emails,
        exposed_emails=d.exposed_emails,
        total_breach_instances=d.total_breach_instances,
        checked_count=d.checked_count or 0,
        unverified_count=d.unverified_count or 0,
        risk_score=d.risk_score,
        severity_score=d.severity_score,
        top_sources_json=d.top_sources_json,
        error_message=d.error_message,
        monitor_active=d.monitor_active,
        last_monitored_at=d.last_monitored_at,
        next_monitor_at=d.next_monitor_at,
        created_at=d.created_at,
        started_at=d.started_at,
        finished_at=d.finished_at,
        targets=[
            TargetOut(
                id=t.id,
                email=t.email,
                status=t.status,
                check_status=t.check_status or "pending",
                total_breaches=t.total_breaches,
                breach_sources_json=t.breach_sources_json,
                checked_at=t.checked_at,
            )
            for t in (d.targets or [])
        ],
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=DossierOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_min_tier(3))],  # Dark Web Dossier : Pro+
)
async def create_dossier(
    background_tasks: BackgroundTasks,
    company_name: str = Form(..., min_length=2, max_length=200),
    domain: str = Form(..., min_length=3, max_length=255),
    emails_csv: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new dossier and start background processing."""
    # Enforce per-user dossier limit
    count_result = await db.execute(
        select(DarkwebDossier).where(DarkwebDossier.user_id == current_user.id)
    )
    if len(count_result.scalars().all()) >= _MAX_DOSSIERS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Limite atteinte — maximum {_MAX_DOSSIERS_PER_USER} dossiers par compte",
        )

    raw = await emails_csv.read()
    emails = _parse_emails_csv(raw)
    if not emails:
        raise HTTPException(status_code=400, detail="Aucun email valide trouvé dans le fichier CSV")
    if len(emails) > _MAX_EMAILS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {_MAX_EMAILS} emails par dossier (fichier contient {len(emails)})",
        )

    dossier = DarkwebDossier(
        user_id=current_user.id,
        company_name=company_name.strip(),
        domain=domain.strip().lower().removeprefix("www."),
        status="pending",
        total_emails=len(emails),
    )
    db.add(dossier)
    await db.flush()

    for email in emails:
        db.add(DarkwebDossierTarget(dossier_id=dossier.id, email=email))

    await db.commit()
    await db.refresh(dossier)

    background_tasks.add_task(process_dossier, dossier.id, settings.HIBP_API_KEY)

    return _to_dossier_out(dossier)


@router.get("", response_model=list[DossierListItem])
async def list_dossiers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkwebDossier)
        .where(DarkwebDossier.user_id == current_user.id)
        .order_by(DarkwebDossier.created_at.desc())
    )
    dossiers = result.scalars().all()
    return [
        DossierListItem(
            id=d.id,
            company_name=d.company_name,
            domain=d.domain,
            status=d.status,
            total_emails=d.total_emails,
            exposed_emails=d.exposed_emails,
            checked_count=d.checked_count or 0,
            unverified_count=d.unverified_count or 0,
            risk_score=d.risk_score,
            severity_score=d.severity_score,
            monitor_active=d.monitor_active,
            created_at=d.created_at,
            finished_at=d.finished_at,
        )
        for d in dossiers
    ]


@router.get("/{dossier_id}", response_model=DossierOut)
async def get_dossier(
    dossier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkwebDossier).where(
            DarkwebDossier.id == dossier_id,
            DarkwebDossier.user_id == current_user.id,
        )
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return _to_dossier_out(dossier)


@router.delete("/{dossier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dossier(
    dossier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkwebDossier).where(
            DarkwebDossier.id == dossier_id,
            DarkwebDossier.user_id == current_user.id,
        )
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    await db.delete(dossier)
    await db.commit()


@router.get("/{dossier_id}/pdf")
async def download_dossier_pdf(
    dossier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DarkwebDossier).where(
            DarkwebDossier.id == dossier_id,
            DarkwebDossier.user_id == current_user.id,
        )
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    if dossier.status != "completed":
        raise HTTPException(status_code=400, detail="Le dossier n'est pas encore terminé")

    pdf_bytes = await asyncio.to_thread(generate_dossier_pdf, dossier, dossier.targets or [])
    filename = f"dossier-darkweb-{dossier.domain}-{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/catalog/sync", dependencies=[Depends(require_admin)])
async def sync_catalog(
    db: AsyncSession = Depends(get_db),
):
    """Sync HIBP public breach catalog — admin only, no API key required."""
    count = await sync_breach_catalog(db)
    return {"synced": count, "message": f"{count} entrées synchronisées depuis HIBP"}


@router.post(
    "/{dossier_id}/rescan",
    response_model=DossierOut,
    dependencies=[Depends(require_min_tier(3))],  # Dark Web Dossier : Pro+
)
async def rescan_dossier(
    dossier_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset a dossier and relaunch background processing."""
    result = await db.execute(
        select(DarkwebDossier).where(
            DarkwebDossier.id == dossier_id,
            DarkwebDossier.user_id == current_user.id,
        )
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    if dossier.status in ("pending", "processing"):
        raise HTTPException(status_code=400, detail="Analyse déjà en cours")

    # Reset targets
    await db.execute(
        DarkwebDossierTarget.__table__.update()
        .where(DarkwebDossierTarget.dossier_id == dossier_id)
        .values(
            status="pending",
            check_status="pending",
            total_breaches=0,
            breach_sources_json=None,
            checked_at=None,
        )
    )
    dossier.status = "pending"
    dossier.started_at = None
    dossier.finished_at = None
    dossier.risk_score = None
    dossier.severity_score = None
    dossier.error_message = None
    dossier.exposed_emails = 0
    dossier.total_breach_instances = 0
    dossier.top_sources_json = None
    dossier.checked_count = 0
    dossier.unverified_count = 0
    await db.commit()
    await db.refresh(dossier)

    background_tasks.add_task(process_dossier, dossier.id, settings.HIBP_API_KEY)
    return _to_dossier_out(dossier)


@router.get("/{dossier_id}/csv")
async def export_csv(
    dossier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export dossier targets as CSV."""
    result = await db.execute(
        select(DarkwebDossier).where(
            DarkwebDossier.id == dossier_id,
            DarkwebDossier.user_id == current_user.id,
        )
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    if dossier.status != "completed":
        raise HTTPException(status_code=400, detail="Le dossier n'est pas encore terminé")

    csv_bytes = export_dossier_csv(dossier, dossier.targets or [])
    filename = f"dossier-darkweb-{dossier.domain}-{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{dossier_id}/monitor")
async def toggle_monitor(
    dossier_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable monthly monitoring for a dossier."""
    from datetime import timedelta

    result = await db.execute(
        select(DarkwebDossier).where(
            DarkwebDossier.id == dossier_id,
            DarkwebDossier.user_id == current_user.id,
        )
    )
    dossier = result.scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    dossier.monitor_active = not dossier.monitor_active
    if dossier.monitor_active:
        dossier.next_monitor_at = datetime.now(UTC) + timedelta(days=30)
    else:
        dossier.next_monitor_at = None
    await db.commit()
    return {
        "monitor_active": dossier.monitor_active,
        "next_monitor_at": dossier.next_monitor_at,
    }
