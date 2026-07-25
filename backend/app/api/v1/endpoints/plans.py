from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.http_cache import cache_public
from app.schemas.cyberscan import PlanOut
from app.services.plan_service import list_active_plans

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanOut], dependencies=[Depends(cache_public(300))])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Return all active subscription plans."""
    return await list_active_plans(db)
