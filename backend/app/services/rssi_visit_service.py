"""Service d'acces aux visites RSSI (CRUD lie a un client)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_visit import RssiVisit


async def list_client_visits(db: AsyncSession, client_id: int) -> list[RssiVisit]:
    """Visites d'un client, les plus recentes d'abord."""
    result = await db.execute(
        select(RssiVisit)
        .where(RssiVisit.client_id == client_id)
        .order_by(RssiVisit.scheduled_date.desc())
    )
    return list(result.scalars().all())


async def get_client_visit(db: AsyncSession, client_id: int, visit_id: int) -> RssiVisit | None:
    """Visite d'un client par id, sinon None."""
    result = await db.execute(
        select(RssiVisit).where(RssiVisit.id == visit_id, RssiVisit.client_id == client_id)
    )
    return result.scalar_one_or_none()


async def create_visit(
    db: AsyncSession,
    *,
    client_id: int,
    scheduled_date: date,
    visit_type: str,
    location: str,
    notes: str | None,
) -> RssiVisit:
    """Cree une visite pour un client."""
    visit = RssiVisit(
        client_id=client_id,
        scheduled_date=scheduled_date,
        visit_type=visit_type,
        location=location,
        notes=notes,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


async def save_visit(db: AsyncSession, visit: RssiVisit) -> RssiVisit:
    """Persiste les modifications d'une visite (met a jour updated_at)."""
    visit.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(visit)
    return visit


async def delete_visit(db: AsyncSession, visit: RssiVisit) -> None:
    """Supprime une visite."""
    await db.delete(visit)
    await db.commit()
