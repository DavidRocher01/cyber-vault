"""Service de la liste d'attente API."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_waitlist import ApiWaitlist


async def get_by_email(db: AsyncSession, email: str) -> ApiWaitlist | None:
    result = await db.execute(select(ApiWaitlist).where(ApiWaitlist.email == email))
    return result.scalar_one_or_none()


async def add_entry(
    db: AsyncSession, *, email: str, role: str | None, company: str | None
) -> ApiWaitlist:
    entry = ApiWaitlist(
        email=email,
        role=role,
        company=company,
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()
    return entry


async def count_entries(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(ApiWaitlist.id)))
    return result.scalar() or 0
