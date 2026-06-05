"""Shared helpers used across the awareness sub-package."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization
from app.models.user import User


async def _get_org_or_404(org_id: int, user: User, db: AsyncSession) -> AwarenessOrganization:
    result = await db.execute(
        select(AwarenessOrganization).where(
            AwarenessOrganization.id == org_id,
            AwarenessOrganization.owner_user_id == user.id,
        )
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organisation introuvable.")
    return org


async def _get_learner_or_404(learner_id: int, org_id: int, db: AsyncSession) -> AwarenessLearner:
    result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.id == learner_id,
            AwarenessLearner.organization_id == org_id,
        )
    )
    learner = result.scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner introuvable.")
    return learner
