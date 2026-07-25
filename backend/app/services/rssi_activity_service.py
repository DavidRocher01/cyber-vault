"""Service du journal d'activité RSSI (actions consultant sur un client)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_activity_log import RssiActivityLog


async def create_activity_log(
    db: AsyncSession,
    *,
    consultant_id: int,
    client_id: int,
    action_type: str,
    resource_type: str | None,
    resource_id: int | None,
) -> RssiActivityLog:
    entry = RssiActivityLog(
        consultant_id=consultant_id,
        client_id=client_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        performed_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_recent_activity(
    db: AsyncSession, *, client_id: int, consultant_id: int, limit: int
) -> list[RssiActivityLog]:
    result = await db.execute(
        select(RssiActivityLog)
        .where(
            RssiActivityLog.client_id == client_id,
            RssiActivityLog.consultant_id == consultant_id,
        )
        .order_by(RssiActivityLog.performed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
