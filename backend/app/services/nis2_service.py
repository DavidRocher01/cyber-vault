"""Service d'acces a l'auto-evaluation NIS2 d'un utilisateur."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nis2_assessment import Nis2Assessment


def _sujet(user_id: int, client_id: int | None):
    """Le couple qui identifie une evaluation : son proprietaire ET son sujet.

    `client_id is None` designe l'auto-evaluation du compte. Il faut l'ecrire
    `.is_(None)` et non `== None` : en SQL, `client_id = NULL` n'est jamais vrai,
    et la requete ramenerait zero ligne au lieu de l'auto-evaluation cherchee.
    """
    condition = (
        Nis2Assessment.client_id.is_(None)
        if client_id is None
        else Nis2Assessment.client_id == client_id
    )
    return (Nis2Assessment.user_id == user_id, condition)


async def get_user_assessment(
    db: AsyncSession, user_id: int, client_id: int | None = None
) -> Nis2Assessment | None:
    """Evaluation NIS2 d'un sujet donne, sinon None.

    Sans `client_id`, on renvoie l'auto-evaluation du compte — le comportement
    d'avant l'etape 5b, et le cas de l'abonne qui veut NIS2 sans consultant.
    """
    result = await db.execute(select(Nis2Assessment).where(*_sujet(user_id, client_id)))
    return result.scalar_one_or_none()


async def upsert_assessment(
    db: AsyncSession,
    user_id: int,
    *,
    items: dict[str, str],
    score: int,
    now: datetime,
    client_id: int | None = None,
) -> Nis2Assessment:
    """Cree ou met a jour l'evaluation NIS2 d'un sujet donne."""
    result = await db.execute(select(Nis2Assessment).where(*_sujet(user_id, client_id)))
    assessment = result.scalar_one_or_none()

    if assessment:
        assessment.items_json = json.dumps(items)
        assessment.score = score
        assessment.updated_at = now
    else:
        assessment = Nis2Assessment(
            user_id=user_id,
            client_id=client_id,
            items_json=json.dumps(items),
            score=score,
            created_at=now,
            updated_at=now,
        )
        db.add(assessment)

    await db.commit()
    await db.refresh(assessment)
    return assessment
