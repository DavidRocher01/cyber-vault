from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.plan import Plan
from app.models.subscription import Subscription


async def get_active_plan(db: AsyncSession, user_id: int) -> Plan | None:
    """Return the user's active subscription plan, or None if no active subscription."""
    result = await db.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    return result.scalar_one_or_none()


async def get_effective_max_sites(db: AsyncSession, user_id: int) -> int:
    """Return plan.max_sites + subscription.extra_sites for the active subscription."""
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return 0
    return sub.plan.max_sites + sub.extra_sites
