from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
