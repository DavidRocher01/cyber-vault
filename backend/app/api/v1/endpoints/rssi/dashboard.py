from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.user import User
from app.services import rssi_aggregation_service as _agg

router = APIRouter()


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated stats across all active clients."""
    overview = await _agg.compute_overview(current_user.id, db)
    return overview.dict()


@router.get("/dashboard/clients-summary")
async def get_clients_summary(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Per-client summary with action counts and next visit."""
    return await _agg.get_clients_summary(current_user.id, db)


@router.get("/dashboard/alerts")
async def get_pending_alerts(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Alerts requiring attention: overdue actions, renewals, no recent visit."""
    return await _agg.get_pending_alerts(current_user.id, db)


@router.get("/dashboard/upcoming-events")
async def get_upcoming_events(
    days_ahead: int = 14,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Planned visits in the next N days (default 14)."""
    return await _agg.get_upcoming_events(current_user.id, days_ahead, db)


@router.get("/dashboard/suggestions")
async def get_suggestions(
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Rule-based suggestions: upsell, engagement alerts, high overdue."""
    return await _agg.compute_suggestions(current_user.id, db)
