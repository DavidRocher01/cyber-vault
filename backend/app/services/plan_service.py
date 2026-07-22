"""Service des plans d'abonnement (lecture)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan


async def list_active_plans(db: AsyncSession) -> list[Plan]:
    """Retourne tous les plans actifs, triés par prix croissant."""
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.price_eur)  # noqa: E712
    )
    return list(result.scalars().all())
