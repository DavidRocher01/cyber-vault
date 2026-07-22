"""Endpoints badges, leaderboard et gamification (Sprint 6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_learner, get_current_user
from app.models.awareness_learner import AwarenessLearner
from app.models.user import User
from app.schemas.awareness import BadgeOut, LeaderboardEntry, LearnerLevelOut

from .helpers import _get_org_or_404

router = APIRouter()


@router.get("/me/level", response_model=LearnerLevelOut)
async def get_my_level(
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> LearnerLevelOut:
    """Retourne le niveau et les XP totaux du learner authentifié."""
    from app.services.awareness_gamification import compute_level, compute_total_xp

    total_xp = await compute_total_xp(db, learner.id)
    level = compute_level(total_xp)
    return LearnerLevelOut(**level)


@router.get("/me/badges", response_model=list[BadgeOut])
async def get_my_badges(
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> list[BadgeOut]:
    """Retourne les badges gagnés par le learner authentifié."""
    from app.services.awareness_gamification import list_learner_badges

    rows = await list_learner_badges(db, learner.id)
    out = []
    for lb, badge in rows:
        b = BadgeOut.model_validate(badge)
        b.earned_at = lb.earned_at
        out.append(b)
    return out


@router.get("/organizations/{org_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard_endpoint(
    org_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardEntry]:
    """Classement des learners par XP total (noms anonymisés). Accès admin de l'org."""
    await _get_org_or_404(org_id, current_user, db)
    from app.services.awareness_gamification import get_leaderboard

    rows = await get_leaderboard(db, org_id, limit)
    return [LeaderboardEntry(**r) for r in rows]


@router.get("/learner/leaderboard", response_model=list[LeaderboardEntry])
async def get_learner_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardEntry]:
    """Classement de l'organisation du learner authentifié."""
    from app.services.awareness_gamification import get_leaderboard

    rows = await get_leaderboard(db, learner.organization_id, limit)
    return [LeaderboardEntry(**r) for r in rows]
