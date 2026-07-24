"""Service CRUD des learners (module sensibilisation)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_learner import AwarenessLearner


async def count_active_learners(db: AsyncSession, org_id: int) -> int:
    """Nombre de learners actifs d'une organisation (quota)."""
    result = await db.execute(
        select(func.count(AwarenessLearner.id)).where(
            AwarenessLearner.organization_id == org_id,
            AwarenessLearner.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one()


async def get_learner_by_email(
    db: AsyncSession, org_id: int, email: str
) -> AwarenessLearner | None:
    """Learner d'une organisation par email, sinon None (detection de doublon)."""
    result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.organization_id == org_id,
            AwarenessLearner.email == email,
        )
    )
    return result.scalar_one_or_none()


async def create_learner(
    db: AsyncSession,
    *,
    org_id: int,
    email: str,
    first_name: str,
    last_name: str,
    department: str | None,
    job_title: str | None,
    preferred_language: str,
) -> AwarenessLearner:
    """Cree et persiste un learner."""
    learner = AwarenessLearner(
        organization_id=org_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        department=department,
        job_title=job_title,
        preferred_language=preferred_language,
    )
    db.add(learner)
    await db.commit()
    await db.refresh(learner)
    return learner


async def list_org_learners(
    db: AsyncSession, org_id: int, *, active_only: bool
) -> list[AwarenessLearner]:
    """Learners d'une organisation (option: actifs uniquement)."""
    query = select(AwarenessLearner).where(AwarenessLearner.organization_id == org_id)
    if active_only:
        query = query.where(AwarenessLearner.is_active == True)  # noqa: E712
    result = await db.execute(query)
    return list(result.scalars().all())


async def save_learner(db: AsyncSession, learner: AwarenessLearner) -> None:
    """Persiste les modifications d'un learner deja charge."""
    await db.commit()
    await db.refresh(learner)
