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


async def get_plan(db: AsyncSession, plan_id: int) -> Plan | None:
    """Retourne un plan par son identifiant, sinon None."""
    return await db.get(Plan, plan_id)


async def get_plan_by_name(db: AsyncSession, name: str) -> Plan | None:
    """Retourne un plan actif par son nom technique (ex. 'starter'), sinon None."""
    result = await db.execute(select(Plan).where(Plan.name == name, Plan.is_active.is_(True)))
    return result.scalar_one_or_none()
