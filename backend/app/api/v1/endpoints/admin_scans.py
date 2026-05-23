import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.public_scan import PublicScan

router = APIRouter(prefix="/admin/scans", tags=["admin"])


def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


@router.get("", dependencies=[Depends(_require_admin)])
async def list_public_scans(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PublicScan).order_by(PublicScan.created_at.desc()).limit(limit)
    )
    scans = result.scalars().all()
    return [
        {
            "id": s.id,
            "target_url": s.target_url,
            "status": s.status,
            "overall_status": s.overall_status,
            "created_at": s.created_at.isoformat(),
            "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            "error_message": s.error_message,
        }
        for s in scans
    ]
