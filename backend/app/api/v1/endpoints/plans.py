from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.plan import Plan
from app.schemas.cyberscan import PlanOut

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Return all active subscription plans."""
    result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.price_eur))
    return result.scalars().all()
