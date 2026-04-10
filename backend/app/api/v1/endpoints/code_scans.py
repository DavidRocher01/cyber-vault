from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_current_user
from app.models.code_scan import CodeScan
from app.models.user import User
from app.schemas.cyberscan import (
    CodeScanCreate,
    CodeScanOut,
    CodeScanTriggerOut,
    PaginatedCodeScans,
)
from app.services.code_scan_service import run_code_scan

router = APIRouter(prefix="/code-scans", tags=["code-scans"])


def _embed_token(url: str, token: str | None) -> str:
    """Inject PAT token into HTTPS GitHub URL."""
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return parsed._replace(netloc=f"{token}@{parsed.netloc}").geturl()
    return url


def _repo_name(url: str) -> str:
    clean = url.rstrip("/").rstrip(".git")
    parts = clean.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1]


async def _run_background(scan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_code_scan(scan_id, db)


@router.post("", response_model=CodeScanTriggerOut, status_code=202)
async def trigger_code_scan(
    body: CodeScanCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a code security analysis on a GitHub repository."""
    # Basic URL validation
    parsed = urlparse(body.repo_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=422, detail="URL de dépôt invalide (https:// requis)")

    # Embed token if provided (for private repos)
    clone_url = _embed_token(body.repo_url, body.github_token)

    scan = CodeScan(
        user_id=current_user.id,
        repo_url=body.repo_url,  # store clean URL (no token)
        repo_name=_repo_name(body.repo_url),
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Patch clone URL with token into the object used by the background task
    # We pass scan_id; the service re-fetches from DB. We store the token-embedded
    # URL temporarily by overwriting repo_url before the task reads it.
    if body.github_token:
        scan.repo_url = clone_url
        await db.commit()

    background_tasks.add_task(_run_background, scan.id)

    # Restore clean URL in response
    scan.repo_url = body.repo_url
    return {"scan_id": scan.id, "message": "Analyse de code lancée en arrière-plan"}


@router.get("", response_model=PaginatedCodeScans)
async def list_code_scans(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(
        select(func.count()).select_from(CodeScan).where(CodeScan.user_id == current_user.id)
    )
    total = total_result.scalar_one()

    scans_result = await db.execute(
        select(CodeScan)
        .where(CodeScan.user_id == current_user.id)
        .order_by(CodeScan.created_at.desc())
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


@router.get("/{scan_id}", response_model=CodeScanOut)
async def get_code_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CodeScan).where(CodeScan.id == scan_id, CodeScan.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    return scan


@router.delete("/{scan_id}", status_code=204)
async def delete_code_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CodeScan).where(CodeScan.id == scan_id, CodeScan.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    await db.delete(scan)
    await db.commit()
