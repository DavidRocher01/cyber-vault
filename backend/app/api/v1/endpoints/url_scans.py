"""
URL Scan endpoints — trigger and consult suspicious URL analyses.
"""

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User
from app.models.url_scan import UrlScan
from app.schemas.url_scan import UrlScanCreate, UrlScanOut, PaginatedUrlScans
from app.services.url_scan_service import run_url_scan
from app.core.limiter import limiter

router = APIRouter(prefix="/url-scans", tags=["url-scans"])


async def _run_url_scan_background(url_scan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_url_scan(url_scan_id, db)


@router.post("", response_model=UrlScanOut, status_code=202)
@limiter.limit("10/minute")
async def trigger_url_scan(
    request: Request,
    payload: UrlScanCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a URL for suspicious content analysis."""
    from datetime import datetime, timezone
    url_scan = UrlScan(
        user_id=current_user.id,
        url=payload.url,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(url_scan)
    await db.commit()
    await db.refresh(url_scan)

    background_tasks.add_task(_run_url_scan_background, url_scan.id)
    return url_scan


@router.get("", response_model=PaginatedUrlScans)
async def list_url_scans(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all URL scans for the authenticated user."""
    total_result = await db.execute(
        select(func.count()).where(UrlScan.user_id == current_user.id)
    )
    total = total_result.scalar_one()

    scans_result = await db.execute(
        select(UrlScan)
        .where(UrlScan.user_id == current_user.id)
        .order_by(UrlScan.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = scans_result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    }


@router.get("/{scan_id}", response_model=UrlScanOut)
async def get_url_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific URL scan by ID."""
    result = await db.execute(
        select(UrlScan).where(
            UrlScan.id == scan_id,
            UrlScan.user_id == current_user.id,
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    return scan


@router.get("/{scan_id}/pdf")
async def download_url_scan_pdf(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return a PDF report for a completed URL scan."""
    result = await db.execute(
        select(UrlScan).where(
            UrlScan.id == scan_id,
            UrlScan.user_id == current_user.id,
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    if scan.status != "done" or not scan.results_json:
        raise HTTPException(status_code=404, detail="Rapport non disponible — scan non terminé")

    try:
        results = json.loads(scan.results_json)
    except Exception:
        raise HTTPException(status_code=500, detail="Données de scan invalides")

    results["url"] = scan.url
    results["created_at"] = scan.created_at

    from app.services.url_scan_pdf import generate_url_scan_pdf
    pdf_bytes = generate_url_scan_pdf(results)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cyberscan_url_{scan_id}.pdf"'},
    )


@router.delete("/{scan_id}", status_code=204)
async def delete_url_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a URL scan (RGPD — droit à l'oubli)."""
    result = await db.execute(
        select(UrlScan).where(
            UrlScan.id == scan_id,
            UrlScan.user_id == current_user.id,
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    await db.delete(scan)
    await db.commit()
