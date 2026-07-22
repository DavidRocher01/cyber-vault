"""Contrôles de propriété/appartenance pour le module sensibilisation.

Lectures simples avec garde (org possédée par l'utilisateur, learner rattaché
à une org). Les endpoints y délèguent puis lèvent le 404 HTTP eux-mêmes.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization


async def get_org_for_owner(
    db: AsyncSession, org_id: int, owner_user_id: int
) -> AwarenessOrganization | None:
    """Retourne l'organisation si elle appartient à l'utilisateur, sinon None."""
    result = await db.execute(
        select(AwarenessOrganization).where(
            AwarenessOrganization.id == org_id,
            AwarenessOrganization.owner_user_id == owner_user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_learner_in_org(
    db: AsyncSession, learner_id: int, org_id: int
) -> AwarenessLearner | None:
    """Retourne le learner s'il est rattaché à l'organisation, sinon None."""
    result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.id == learner_id,
            AwarenessLearner.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()
