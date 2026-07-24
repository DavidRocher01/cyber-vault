import os
import tempfile
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import get_user_resource
from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_current_user, require_min_tier
from app.core.ssrf import assert_no_ssrf
from app.models.code_scan import CodeScan
from app.models.user import User
from app.schemas.cyberscan import (
    CodeScanCreate,
    CodeScanOut,
    CodeScanTriggerOut,
    PaginatedCodeScans,
)
from app.services import code_scan_crud_service
from app.services.code_scan_service import run_code_scan, run_code_scan_zip

_SCAN_IN_PROGRESS = (
    "Un scan est déjà en cours. Attendez qu'il se termine avant d'en lancer un nouveau."
)

router = APIRouter(prefix="/code-scans", tags=["code-scans"])

_GIT_ALLOWED_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}


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
    if await code_scan_crud_service.has_running_scan(db, user_id):
        raise HTTPException(status_code=429, detail=_SCAN_IN_PROGRESS)


@router.post(
    "/upload",
    response_model=CodeScanTriggerOut,
    status_code=202,
    dependencies=[Depends(require_min_tier(2))],  # Analyse de code : Starter+
)
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

    fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="rochercybersecurite_upload_")
    os.close(fd)
    with open(zip_path, "wb") as f:
        f.write(content)

    repo_name = file.filename[:-4] if file.filename.lower().endswith(".zip") else file.filename

    scan = await code_scan_crud_service.create_code_scan(
        db,
        user_id=current_user.id,
        repo_url=f"upload:{file.filename}",
        repo_name=repo_name,
    )
    if scan is None:
        raise HTTPException(status_code=429, detail=_SCAN_IN_PROGRESS)

    background_tasks.add_task(_run_zip_background, scan.id, zip_path)
    return {"scan_id": scan.id, "message": "Analyse lancée en arrière-plan"}


@router.post(
    "",
    response_model=CodeScanTriggerOut,
    status_code=202,
    dependencies=[Depends(require_min_tier(2))],  # Analyse de code : Starter+
)
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

    host = parsed.hostname or ""
    if host not in _GIT_ALLOWED_HOSTS:
        raise HTTPException(
            status_code=422,
            detail=f"Hôte non autorisé. Plateformes acceptées : {', '.join(sorted(_GIT_ALLOWED_HOSTS))}",
        )

    assert_no_ssrf(body.repo_url)
    clone_url = _embed_token(body.repo_url, body.github_token)

    scan = await code_scan_crud_service.create_code_scan(
        db,
        user_id=current_user.id,
        repo_url=body.repo_url,
        repo_name=_repo_name(body.repo_url),
    )
    if scan is None:
        raise HTTPException(status_code=429, detail=_SCAN_IN_PROGRESS)

    background_tasks.add_task(_run_background, scan.id, clone_url if body.github_token else None)
    return {"scan_id": scan.id, "message": "Analyse de code lancée en arrière-plan"}


@router.get("", response_model=PaginatedCodeScans)
async def list_code_scans(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await code_scan_crud_service.list_user_code_scans(
        db, current_user.id, page=page, per_page=per_page
    )


@router.get("/{scan_id}", response_model=CodeScanOut)
async def get_code_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_resource(db, CodeScan, scan_id, current_user.id, "Analyse non trouvée")


@router.delete("/{scan_id}", status_code=204)
async def delete_code_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    scan = await get_user_resource(db, CodeScan, scan_id, current_user.id, "Analyse non trouvée")
    await code_scan_crud_service.delete_code_scan(db, scan)
