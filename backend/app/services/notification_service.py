"""Service du centre de notifications in-app."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def list_recent(db: AsyncSession, user_id: int, *, limit: int = 50) -> list[Notification]:
    """Les notifications les plus recentes d'un utilisateur."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_unread(db: AsyncSession, user_id: int) -> int:
    """Nombre de notifications non lues."""
    result = await db.execute(
        select(func.count()).where(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
    )
    return result.scalar_one()


async def mark_read(db: AsyncSession, notif: Notification) -> None:
    """Marque une notification comme lue."""
    notif.read = True
    await db.commit()


async def mark_all_read(db: AsyncSession, user_id: int) -> None:
    """Marque toutes les notifications non lues d'un utilisateur comme lues."""
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
    )
    for notif in result.scalars().all():
        notif.read = True
    await db.commit()


async def delete_notification(db: AsyncSession, notif: Notification) -> None:
    """Supprime une notification."""
    await db.delete(notif)
    await db.commit()
