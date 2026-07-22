"""Shared helpers used across the awareness sub-package."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization
from app.models.user import User
from app.services import awareness_access_service


async def _get_org_or_404(org_id: int, user: User, db: AsyncSession) -> AwarenessOrganization:
    org = await awareness_access_service.get_org_for_owner(db, org_id, user.id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organisation introuvable.")
    return org


async def _get_learner_or_404(learner_id: int, org_id: int, db: AsyncSession) -> AwarenessLearner:
    learner = await awareness_access_service.get_learner_in_org(db, learner_id, org_id)
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner introuvable.")
    return learner
