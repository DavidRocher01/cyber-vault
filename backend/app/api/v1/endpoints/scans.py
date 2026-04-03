import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User
from app.models.site import Site
from app.models.scan import Scan
from app.schemas.cyberscan import ScanOut, ScanTriggerOut
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
    """Trigger a manual scan for a site."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id, Site.is_active == True)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    scan = Scan(site_id=site_id, status="pending")
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    background_tasks.add_task(_run_scan_background, scan.id)
    return {"scan_id": scan.id, "message": "Scan lancé en arrière-plan"}


@router.get("/site/{site_id}", response_model=list[ScanOut])
async def list_scans(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all scans for a site."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Site non trouvé")

    scans_result = await db.execute(
        select(Scan).where(Scan.site_id == site_id).order_by(Scan.created_at.desc()).limit(20)
    )
    return scans_result.scalars().all()


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
    """Download the PDF report for a completed scan."""
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
