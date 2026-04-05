import csv
import io
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User
from app.models.site import Site
from app.models.scan import Scan
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.schemas.cyberscan import ScanOut, ScanTriggerOut, PaginatedScans
from app.services.scan_service import run_scan

router = APIRouter(prefix="/scans", tags=["scans"])


async def _run_scan_background(scan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_scan(scan_id, db)


@router.post("/trigger/{site_id}", response_model=ScanTriggerOut, status_code=202)
async def trigger_scan(
    site_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id, Site.is_active == True)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    # Enforce scan frequency based on active subscription plan
    plan_result = await db.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == current_user.id, Subscription.status == "active")
    )
    plan = plan_result.scalar_one_or_none()
    interval_days = plan.scan_interval_days if plan else 30

    last_result = await db.execute(
        select(Scan)
        .where(Scan.site_id == site_id, Scan.status == "done")
        .order_by(Scan.finished_at.desc())
        .limit(1)
    )
    last_scan = last_result.scalar_one_or_none()

    if last_scan and last_scan.finished_at:
        days_since = (datetime.utcnow() - last_scan.finished_at).days
        if days_since < interval_days:
            days_left = interval_days - days_since
            raise HTTPException(
                status_code=429,
                detail=f"Scan trop récent. Prochain scan disponible dans {days_left} jour(s) selon votre plan.",
            )

    scan = Scan(site_id=site_id, status="pending")
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    background_tasks.add_task(_run_scan_background, scan.id)
    return {"scan_id": scan.id, "message": "Scan lancé en arrière-plan"}


@router.get("/site/{site_id}", response_model=PaginatedScans)
async def list_scans(
    site_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Site non trouvé")

    total_result = await db.execute(
        select(func.count()).where(Scan.site_id == site_id)
    )
    total = total_result.scalar_one()

    scans_result = await db.execute(
        select(Scan)
        .where(Scan.site_id == site_id)
        .order_by(Scan.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = scans_result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),  # ceiling division
    }


@router.get("/site/{site_id}/export")
async def export_scans_csv(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export scan history as CSV."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    scans_result = await db.execute(
        select(Scan).where(Scan.site_id == site_id).order_by(Scan.created_at.desc())
    )
    scans = scans_result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Site", "Statut", "Résultat", "Créé le", "Terminé le", "Durée (s)"])
    for s in scans:
        duration = ""
        if s.started_at and s.finished_at:
            duration = str(int((s.finished_at - s.started_at).total_seconds()))
        writer.writerow([
            s.id, site.url, s.status, s.overall_status or "",
            s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            s.finished_at.strftime("%Y-%m-%d %H:%M") if s.finished_at else "",
            duration,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cyberscan_site_{site_id}.csv"},
    )


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Scan.id == scan_id, Site.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    return scan


@router.get("/{scan_id}/pdf")
async def download_pdf(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Scan.id == scan_id, Site.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    if scan.status != "done" or not scan.pdf_path:
        raise HTTPException(status_code=404, detail="Rapport PDF non disponible")

    return FileResponse(
        path=scan.pdf_path,
        media_type="application/pdf",
        filename=f"cyberscan_rapport_{scan_id}.pdf",
    )
