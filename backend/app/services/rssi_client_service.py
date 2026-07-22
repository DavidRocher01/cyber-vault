"""Service d'accès aux clients RSSI (lecture avec contrôle de propriété)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_client import RssiClient


async def get_client_for_consultant(
    db: AsyncSession, client_id: int, consultant_id: int
) -> RssiClient | None:
    """Retourne le client s'il appartient au consultant, sinon None."""
    result = await db.execute(
        select(RssiClient).where(
            RssiClient.id == client_id,
            RssiClient.consultant_user_id == consultant_id,
        )
    )
    return result.scalar_one_or_none()
