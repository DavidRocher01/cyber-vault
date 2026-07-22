"""Service admin des utilisateurs (lecture paginée + rôle consultant RSSI)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User


async def list_users_with_plan(
    db: AsyncSession, *, skip: int, limit: int
) -> list[tuple[User, Subscription | None, Plan | None]]:
    """Liste paginée des utilisateurs avec leur abonnement actif et son plan."""
    result = await db.execute(
        select(User, Subscription, Plan)
        .outerjoin(
            Subscription,
            (Subscription.user_id == User.id) & (Subscription.status == "active"),
        )
        .outerjoin(Plan, Plan.id == Subscription.plan_id)
        .order_by(User.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.all())


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def toggle_rssi_consultant(db: AsyncSession, user: User) -> User:
    user.is_rssi_consultant = not user.is_rssi_consultant
    await db.commit()
    return user
