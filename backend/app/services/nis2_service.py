"""Service d'acces a l'auto-evaluation NIS2 d'un utilisateur."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nis2_assessment import Nis2Assessment


async def get_user_assessment(db: AsyncSession, user_id: int) -> Nis2Assessment | None:
    """Auto-evaluation NIS2 de l'utilisateur, sinon None."""
    result = await db.execute(select(Nis2Assessment).where(Nis2Assessment.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert_assessment(
    db: AsyncSession, user_id: int, *, items: dict[str, str], score: int, now: datetime
) -> Nis2Assessment:
    """Cree ou met a jour l'auto-evaluation NIS2 de l'utilisateur."""
    result = await db.execute(select(Nis2Assessment).where(Nis2Assessment.user_id == user_id))
    assessment = result.scalar_one_or_none()

    if assessment:
        assessment.items_json = json.dumps(items)
        assessment.score = score
        assessment.updated_at = now
    else:
        assessment = Nis2Assessment(
            user_id=user_id,
            items_json=json.dumps(items),
            score=score,
            created_at=now,
            updated_at=now,
        )
        db.add(assessment)

    await db.commit()
    await db.refresh(assessment)
    return assessment
