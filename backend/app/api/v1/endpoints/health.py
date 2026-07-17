"""Health endpoint exposed under /api/v1 (joignable via CloudFront, qui ne route
que /api/* vers le backend). Le /health "bare app" de main.py sert la sonde ALB
mais n'est PAS atteignable depuis l'exterieur ; celui-ci l'est, ce qui permet a
la recette post-mise-en-production de confirmer la connectivite DB, la version
deployee et la revision Alembic reellement appliquee."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.__version__ import __version__
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    db_status = "ok"
    db_revision: str | None = None
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    # Revision Alembic : best-effort et informative. Son absence (ex: schema de
    # test construit via create_all, sans table alembic_version) ne doit PAS
    # degrader le statut DB.
    if db_status == "ok":
        try:
            db_revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception:
            db_revision = None
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": __version__,
        "environment": settings.APP_ENV,
        "database": db_status,
        "db_revision": db_revision,
    }
