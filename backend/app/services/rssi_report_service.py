"""Lecture des données consolidées pour le rapport RSSI d'un client."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_action import RssiAction
from app.models.rssi_deliverable import RssiDeliverable
from app.models.rssi_visit import RssiVisit


async def list_client_visits(db: AsyncSession, client_id: int) -> list[RssiVisit]:
    result = await db.execute(
        select(RssiVisit)
        .where(RssiVisit.client_id == client_id)
        .order_by(RssiVisit.scheduled_date.desc())
    )
    return list(result.scalars().all())


async def list_client_actions(db: AsyncSession, client_id: int) -> list[RssiAction]:
    result = await db.execute(
        select(RssiAction)
        .where(RssiAction.client_id == client_id)
        .order_by(RssiAction.created_at.desc())
    )
    return list(result.scalars().all())


async def list_client_deliverables(db: AsyncSession, client_id: int) -> list[RssiDeliverable]:
    result = await db.execute(
        select(RssiDeliverable)
        .where(RssiDeliverable.client_id == client_id)
        .order_by(RssiDeliverable.delivered_at.desc())
    )
    return list(result.scalars().all())
