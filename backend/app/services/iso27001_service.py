"""Service d'acces a l'auto-evaluation ISO 27001 d'un utilisateur."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iso27001_assessment import Iso27001Assessment


async def get_user_assessment(db: AsyncSession, user_id: int) -> Iso27001Assessment | None:
    """Auto-evaluation ISO 27001 de l'utilisateur, sinon None."""
    result = await db.execute(
        select(Iso27001Assessment).where(Iso27001Assessment.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_assessment(
    db: AsyncSession, user_id: int, *, items: dict[str, str], score: int, now: datetime
) -> Iso27001Assessment:
    """Cree ou met a jour l'auto-evaluation ISO 27001 de l'utilisateur."""
    result = await db.execute(
        select(Iso27001Assessment).where(Iso27001Assessment.user_id == user_id)
    )
    assessment = result.scalar_one_or_none()

    if assessment:
        assessment.items_json = json.dumps(items)
        assessment.score = score
        assessment.updated_at = now
    else:
        assessment = Iso27001Assessment(
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
