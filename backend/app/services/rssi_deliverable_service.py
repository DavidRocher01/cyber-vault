"""Service d'acces aux livrables RSSI (CRUD lie a un client)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_deliverable import RssiDeliverable


async def list_client_deliverables(db: AsyncSession, client_id: int) -> list[RssiDeliverable]:
    """Livrables d'un client, les plus recents d'abord."""
    result = await db.execute(
        select(RssiDeliverable)
        .where(RssiDeliverable.client_id == client_id)
        .order_by(RssiDeliverable.delivered_at.desc())
    )
    return list(result.scalars().all())


async def get_client_deliverable(
    db: AsyncSession, client_id: int, deliverable_id: int
) -> RssiDeliverable | None:
    """Livrable d'un client par id, sinon None."""
    result = await db.execute(
        select(RssiDeliverable).where(
            RssiDeliverable.id == deliverable_id,
            RssiDeliverable.client_id == client_id,
        )
    )
    return result.scalar_one_or_none()


async def create_deliverable(
    db: AsyncSession,
    *,
    client_id: int,
    title: str,
    doc_type: str,
    file_url: str | None,
    notes: str | None,
    delivered_at: date,
) -> RssiDeliverable:
    """Cree un livrable pour un client."""
    deliverable = RssiDeliverable(
        client_id=client_id,
        title=title,
        doc_type=doc_type,
        file_url=file_url,
        notes=notes,
        delivered_at=delivered_at,
    )
    db.add(deliverable)
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


async def save_deliverable(db: AsyncSession, deliverable: RssiDeliverable) -> RssiDeliverable:
    """Persiste les modifications d'un livrable (met a jour updated_at)."""
    deliverable.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


async def delete_deliverable(db: AsyncSession, deliverable: RssiDeliverable) -> None:
    """Supprime un livrable."""
    await db.delete(deliverable)
    await db.commit()
