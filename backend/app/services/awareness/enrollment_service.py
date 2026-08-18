"""Service de lecture des inscriptions et progressions (module sensibilisation)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_progress import AwarenessProgress


async def list_learner_enrollments(db: AsyncSession, learner_id: int) -> list[AwarenessEnrollment]:
    """Inscriptions d'un learner."""
    result = await db.execute(
        select(AwarenessEnrollment).where(AwarenessEnrollment.learner_id == learner_id)
    )
    return list(result.scalars().all())


async def get_learner_enrollment(
    db: AsyncSession, enrollment_id: int, learner_id: int
) -> AwarenessEnrollment | None:
    """Inscription d'un learner par id, sinon None."""
    result = await db.execute(
        select(AwarenessEnrollment).where(
            AwarenessEnrollment.id == enrollment_id,
            AwarenessEnrollment.learner_id == learner_id,
        )
    )
    return result.scalar_one_or_none()


async def list_progress_for_enrollment(
    db: AsyncSession, enrollment_id: int
) -> list[AwarenessProgress]:
    """Enregistrements de progression d'une inscription."""
    result = await db.execute(
        select(AwarenessProgress).where(AwarenessProgress.enrollment_id == enrollment_id)
    )
    return list(result.scalars().all())
