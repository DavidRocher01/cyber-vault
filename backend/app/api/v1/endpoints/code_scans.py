import os
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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
from app.core.ssrf import assert_no_ssrf
from app.services.code_scan_service import run_code_scan, run_code_scan_zip

router = APIRouter(prefix="/code-scans", tags=["code-scans"])


def _embed_token(url: str, token: str | None) -> str:
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


async def _run_background(scan_id: int, clone_url: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        await run_code_scan(scan_id, db, clone_url=clone_url)


async def _run_zip_background(scan_id: int, zip_path: str) -> None:
    async with AsyncSessionLocal() as db:
        await run_code_scan_zip(scan_id, zip_path, db)


async def _check_no_running_scan(user_id: int, db: AsyncSession) -> None:
    """Raise 429 if the user already has a pending or running code scan."""
    result = await db.execute(
        select(CodeScan).where(
            CodeScan.user_id == user_id,
            CodeScan.status.in_(["pending", "running"]),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=429,
            detail="Un scan est déjà en cours. Attendez qu'il se termine avant d'en lancer un nouveau.",
        )


@router.post("/upload", response_model=CodeScanTriggerOut, status_code=202)
async def upload_code_scan(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a code security analysis from an uploaded ZIP archive."""
    await _check_no_running_scan(current_user.id, db)

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Seuls les fichiers .zip sont acceptés")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50 MB)")

    fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="cyberscan_upload_")
    os.close(fd)
    with open(zip_path, "wb") as f:
        f.write(content)

    repo_name = file.filename[:-4] if file.filename.lower().endswith(".zip") else file.filename

    scan = CodeScan(
        user_id=current_user.id,
        repo_url=f"upload:{file.filename}",
        repo_name=repo_name,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="Un scan est déjà en cours. Attendez qu'il se termine avant d'en lancer un nouveau.",
        )
    await db.refresh(scan)

    background_tasks.add_task(_run_zip_background, scan.id, zip_path)
    return {"scan_id": scan.id, "message": "Analyse lancée en arrière-plan"}


@router.post("", response_model=CodeScanTriggerOut, status_code=202)
async def trigger_code_scan(
    body: CodeScanCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a code security analysis on a Git repository."""
    await _check_no_running_scan(current_user.id, db)

    parsed = urlparse(body.repo_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=422, detail="URL de dépôt invalide (https:// requis)")

    assert_no_ssrf(body.repo_url)
    clone_url = _embed_token(body.repo_url, body.github_token)

    scan = CodeScan(
        user_id=current_user.id,
        repo_url=body.repo_url,
        repo_name=_repo_name(body.repo_url),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="Un scan est déjà en cours. Attendez qu'il se termine avant d'en lancer un nouveau.",
        )
    await db.refresh(scan)

    background_tasks.add_task(_run_background, scan.id, clone_url if body.github_token else None)
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
