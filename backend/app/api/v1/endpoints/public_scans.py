"""
Public scan endpoints — no authentication required.
Rate limited to 3 scans/hour per IP to prevent abuse.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, get_db
from app.core.limiter import limiter
from app.core.ssrf import assert_no_ssrf
from app.models.public_scan import PublicScan
from app.schemas.public_scan import PublicScanCreate, PublicScanOut
from app.services.public_scan_service import run_public_scan
from fastapi import Depends

router = APIRouter(prefix="/public-scans", tags=["public-scans"])


async def _run_background(public_scan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_public_scan(public_scan_id, db)


@router.post("", response_model=PublicScanOut, status_code=202)
@limiter.limit("3/hour")
async def create_public_scan(
    payload: PublicScanCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> PublicScanOut:
    url = payload.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        assert_no_ssrf(url)
    except Exception:
        raise HTTPException(status_code=422, detail="URL non autorisée")

    scan = PublicScan(target_url=url, status="pending")
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    background_tasks.add_task(_run_background, scan.id)
    return PublicScanOut.from_orm_obj(scan)


@router.get("/{token}", response_model=PublicScanOut)
async def get_public_scan(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> PublicScanOut:
    result = await db.execute(
        select(PublicScan).where(PublicScan.session_token == token)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    return PublicScanOut.from_orm_obj(scan)
