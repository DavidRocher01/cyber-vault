"""Dark web surveillance — email breach monitoring via HIBP."""
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.darkweb_scan import DarkwebScan
from app.models.user import User
from app.services.darkweb_service import check_email_breaches

router = APIRouter(prefix="/darkweb", tags=["darkweb"])

REFRESH_INTERVAL_HOURS = 24


class DarkwebStatusOut(BaseModel):
    email: str
    total_breaches: int
    status: str
    checked_at: datetime | None
    breaches: list[dict]
    error: str | None
    fresh: bool


@router.get("/status", response_model=DarkwebStatusOut)
async def get_darkweb_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return last cached dark-web breach check (no HIBP call)."""
    result = await db.execute(
        select(DarkwebScan)
        .where(DarkwebScan.user_id == current_user.id)
        .order_by(DarkwebScan.checked_at.desc())
        .limit(1)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return DarkwebStatusOut(
            email=current_user.email,
            total_breaches=0,
            status="not_checked",
            checked_at=None,
            breaches=[],
            error=None,
            fresh=False,
        )
    age = datetime.now(timezone.utc) - scan.checked_at
    try:
        breaches = json.loads(scan.results_json or "[]")
    except Exception:
        breaches = []
    return DarkwebStatusOut(
        email=scan.email,
        total_breaches=scan.total_breaches,
        status=scan.status,
        checked_at=scan.checked_at,
        breaches=breaches,
        error=None,
        fresh=age < timedelta(hours=REFRESH_INTERVAL_HOURS),
    )


@router.post("/check", response_model=DarkwebStatusOut)
async def run_darkweb_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a fresh HIBP breach check for the current user's email."""
    # Rate-limit: only one fresh check per 24h
    result = await db.execute(
        select(DarkwebScan)
        .where(DarkwebScan.user_id == current_user.id)
        .order_by(DarkwebScan.checked_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        age = datetime.now(timezone.utc) - existing.checked_at
        if age < timedelta(hours=REFRESH_INTERVAL_HOURS):
            try:
                breaches = json.loads(existing.results_json or "[]")
            except Exception:
                breaches = []
            return DarkwebStatusOut(
                email=existing.email,
                total_breaches=existing.total_breaches,
                status=existing.status,
                checked_at=existing.checked_at,
                breaches=breaches,
                error=None,
                fresh=True,
            )

    data = check_email_breaches(current_user.email, settings.HIBP_API_KEY)
    scan = DarkwebScan(
        user_id=current_user.id,
        email=current_user.email,
        total_breaches=data["total"],
        status=data["status"],
        checked_at=datetime.now(timezone.utc),
        results_json=json.dumps(data["breaches"]),
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    return DarkwebStatusOut(
        email=scan.email,
        total_breaches=scan.total_breaches,
        status=scan.status,
        checked_at=scan.checked_at,
        breaches=data["breaches"],
        error=data.get("error"),
        fresh=True,
    )
