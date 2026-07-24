from pathlib import Path

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.services import admin_stats_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/stats", dependencies=[Depends(require_admin)], summary="[Admin] Statistiques globales"
)
async def get_stats(db: AsyncSession = Depends(get_db)):
    return await admin_stats_service.compute_dashboard_stats(db)


@router.post(
    "/awareness/sync-content",
    dependencies=[Depends(require_admin)],
    summary="[Admin] Réimporter le contenu de sensibilisation",
)
async def sync_awareness_content():
    """Reimporte le contenu NIS2 depuis les fichiers YAML/Markdown (idempotent)."""
    from app.core.database import AsyncSessionLocal
    from app.services.awareness_content_importer import import_from_directory

    content_dir = Path(__file__).parents[4] / "content" / "fr"
    if not content_dir.exists():
        return {"error": f"Dossier contenu introuvable : {content_dir}"}

    async with AsyncSessionLocal() as db:
        try:
            summary = await import_from_directory(db, content_dir)
            logger.info(
                f"Admin sync: {summary['programs']} programmes, {summary['modules']} modules"
            )
            return {
                "status": "ok",
                "programs": summary["programs"],
                "modules": summary["modules"],
                "errors": summary.get("errors", []),
            }
        except Exception as exc:
            logger.error(f"Admin sync failed: {exc}")
            return {"error": str(exc)}
