"""
Gamification service — XP, niveaux, badges, leaderboard.

Niveaux :
  1. Apprenti     0–50 XP
  2. Initié       51–150 XP
  3. Vigilant     151–300 XP
  4. Expert       301–500 XP
  5. Sentinelle   501+ XP

XP gagné :
  - Complétion d'un module           : xp_points du module (défaut 10)
  - Quiz réussi du premier coup       : +5 bonus
  - Quiz parfait (100%)               : +10 bonus
  - Programme entier complété         : +50 bonus

Badges (20) — vérifiés après chaque action significative.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_badge import AwarenessBadge
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_learner_badge import AwarenessLearnerBadge
from app.models.awareness_program import AwarenessProgram
from app.models.awareness_progress import AwarenessProgress
from app.models.awareness_quiz_attempt import AwarenessQuizAttempt

# ── Niveau ─────────────────────────────────────────────────────────────────────

LEVELS = [
    (0, 1, "Apprenti"),
    (51, 2, "Initié"),
    (151, 3, "Vigilant"),
    (301, 4, "Expert"),
    (501, 5, "Sentinelle"),
]


def compute_level(xp: int) -> dict:
    level_num, label = 1, "Apprenti"
    for threshold, num, name in LEVELS:
        if xp >= threshold:
            level_num, label = num, name
    # Next threshold
    next_threshold = None
    for threshold, _num, _ in LEVELS:
        if xp < threshold:
            next_threshold = threshold
            break
    return {
        "level": level_num,
        "label": label,
        "xp": xp,
        "next_level_xp": next_threshold,
    }


# ── XP award ──────────────────────────────────────────────────────────────────


async def award_xp(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment: AwarenessEnrollment,
    xp_amount: int,
) -> int:
    """Add XP to learner's enrollment, return new total."""
    enrollment.xp_earned = (enrollment.xp_earned or 0) + xp_amount
    await db.flush()
    return enrollment.xp_earned


async def compute_total_xp(db: AsyncSession, learner_id: int) -> int:
    result = await db.execute(
        select(func.sum(AwarenessEnrollment.xp_earned)).where(
            AwarenessEnrollment.learner_id == learner_id
        )
    )
    return result.scalar_one() or 0


# ── Badge award ────────────────────────────────────────────────────────────────


async def _has_badge(db: AsyncSession, learner_id: int, slug: str) -> bool:
    badge = (
        await db.execute(select(AwarenessBadge).where(AwarenessBadge.slug == slug))
    ).scalar_one_or_none()
    if badge is None:
        return True  # badge not seeded — skip silently
    existing = (
        await db.execute(
            select(AwarenessLearnerBadge).where(
                AwarenessLearnerBadge.learner_id == learner_id,
                AwarenessLearnerBadge.badge_id == badge.id,
            )
        )
    ).scalar_one_or_none()
    return existing is not None


async def _award_badge(
    db: AsyncSession, learner_id: int, slug: str
) -> AwarenessLearnerBadge | None:
    if await _has_badge(db, learner_id, slug):
        return None
    badge = (
        await db.execute(select(AwarenessBadge).where(AwarenessBadge.slug == slug))
    ).scalar_one_or_none()
    if badge is None:
        return None
    lb = AwarenessLearnerBadge(learner_id=learner_id, badge_id=badge.id)
    db.add(lb)
    await db.flush()
    return lb


async def check_and_award_badges(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment: AwarenessEnrollment,
    *,
    quiz_score: int | None = None,
    quiz_attempt_number: int | None = None,
    module_time_seconds: int | None = None,
    module_slug: str | None = None,
) -> list[str]:
    """
    Check badge conditions after a module/quiz completion.
    Returns list of newly earned badge slugs.
    """
    earned: list[str] = []

    async def try_award(slug: str) -> None:
        lb = await _award_badge(db, learner.id, slug)
        if lb:
            earned.append(slug)

    # ── first_step : first module ever completed ───────────────────────────────
    total_completed = (
        await db.execute(
            select(func.count(AwarenessProgress.id)).where(
                AwarenessProgress.enrollment_id == enrollment.id,
                AwarenessProgress.status == "completed",
            )
        )
    ).scalar_one()
    if total_completed == 1:
        await try_award("first_step")

    # ── first_quiz : first quiz passed ────────────────────────────────────────
    if quiz_score is not None and quiz_score >= 60:
        total_passed = (
            await db.execute(
                select(func.count(AwarenessQuizAttempt.id)).where(
                    AwarenessQuizAttempt.learner_id == learner.id,
                    AwarenessQuizAttempt.result == "passed",
                )
            )
        ).scalar_one()
        if total_passed == 1:
            await try_award("first_quiz")

    # ── perfectionist : quiz with 100% ────────────────────────────────────────
    if quiz_score == 100:
        await try_award("perfectionist")

    # ── speed_runner : module completed in < 2 min ────────────────────────────
    if module_time_seconds is not None and module_time_seconds < 120:
        await try_award("speed_runner")

    # ── detective : phishing module with 100% ─────────────────────────────────
    if module_slug and "phishing" in module_slug and quiz_score == 100:
        await try_award("detective")

    # ── persistent : 3 quiz attempts ─────────────────────────────────────────
    if quiz_attempt_number and quiz_attempt_number >= 3:
        await try_award("persistent")

    # ── nis2_ready : NIS2 program completed ───────────────────────────────────
    if enrollment.status == "completed":
        program = (
            await db.execute(
                select(AwarenessProgram).where(AwarenessProgram.id == enrollment.program_id)
            )
        ).scalar_one_or_none()
        if program and "nis2" in program.slug.lower():
            await try_award("nis2_ready")

    # ── all_in : all modules of a program completed ───────────────────────────
    if enrollment.status == "completed":
        await try_award("all_in")

    # ── explorer : 3 different programs started ───────────────────────────────
    started_programs = (
        await db.execute(
            select(func.count(AwarenessEnrollment.id)).where(
                AwarenessEnrollment.learner_id == learner.id,
                AwarenessEnrollment.status.in_(["in_progress", "completed"]),
            )
        )
    ).scalar_one()
    if started_programs >= 3:
        await try_award("explorer")

    # ── shield : 3 programs completed ─────────────────────────────────────────
    completed_programs = (
        await db.execute(
            select(func.count(AwarenessEnrollment.id)).where(
                AwarenessEnrollment.learner_id == learner.id,
                AwarenessEnrollment.status == "completed",
            )
        )
    ).scalar_one()
    if completed_programs >= 3:
        await try_award("shield")

    await db.flush()
    return earned


# ── Leaderboard ────────────────────────────────────────────────────────────────


async def get_leaderboard(
    db: AsyncSession,
    organization_id: int,
    limit: int = 10,
) -> list[dict]:
    """
    Returns top N learners by total XP in an organization.
    Names are anonymised (initials only) — opt-in to full name via preference.
    """
    result = await db.execute(
        select(
            AwarenessLearner.id,
            AwarenessLearner.first_name,
            AwarenessLearner.last_name,
            func.sum(AwarenessEnrollment.xp_earned).label("total_xp"),
        )
        .join(AwarenessEnrollment, AwarenessEnrollment.learner_id == AwarenessLearner.id)
        .where(AwarenessLearner.organization_id == organization_id)
        .group_by(AwarenessLearner.id, AwarenessLearner.first_name, AwarenessLearner.last_name)
        .order_by(func.sum(AwarenessEnrollment.xp_earned).desc())
        .limit(limit)
    )
    rows = result.all()
    board = []
    for rank, row in enumerate(rows, start=1):
        initials = _initials(row.first_name, row.last_name)
        level = compute_level(row.total_xp or 0)
        board.append(
            {
                "rank": rank,
                "display_name": initials,
                "total_xp": row.total_xp or 0,
                "level": level["level"],
                "level_label": level["label"],
            }
        )
    return board


def _initials(first: str | None, last: str | None) -> str:
    parts = []
    if first:
        parts.append(first[0].upper() + ".")
    if last:
        parts.append(last[0].upper() + ".")
    return " ".join(parts) or "?"


# ── Badge catalog ──────────────────────────────────────────────────────────────

BADGE_CATALOG: list[dict] = [
    {
        "slug": "first_step",
        "name": "Premier pas",
        "icon": "🏅",
        "category": "engagement",
        "xp_bonus": 5,
        "description": "Complétez votre premier module",
    },
    {
        "slug": "first_quiz",
        "name": "Premier quiz",
        "icon": "📝",
        "category": "performance",
        "xp_bonus": 5,
        "description": "Réussissez votre premier quiz",
    },
    {
        "slug": "perfectionist",
        "name": "Perfectionniste",
        "icon": "💯",
        "category": "performance",
        "xp_bonus": 10,
        "description": "Obtenez 100% à un quiz",
    },
    {
        "slug": "speed_runner",
        "name": "Speed runner",
        "icon": "⚡",
        "category": "engagement",
        "xp_bonus": 5,
        "description": "Complétez un module en moins de 2 minutes",
    },
    {
        "slug": "detective",
        "name": "Détective",
        "icon": "🔍",
        "category": "performance",
        "xp_bonus": 15,
        "description": "100% au quiz phishing",
    },
    {
        "slug": "shield",
        "name": "Bouclier",
        "icon": "🛡️",
        "category": "performance",
        "xp_bonus": 20,
        "description": "Complétez 3 programmes",
    },
    {
        "slug": "streak_7",
        "name": "Série de 7",
        "icon": "🔥",
        "category": "streak",
        "xp_bonus": 20,
        "description": "7 jours consécutifs d'activité",
    },
    {
        "slug": "noctambule",
        "name": "Noctambule",
        "icon": "🦉",
        "category": "special",
        "xp_bonus": 5,
        "description": "Connexion après 22h",
    },
    {
        "slug": "early_bird",
        "name": "Lève-tôt",
        "icon": "🐦",
        "category": "special",
        "xp_bonus": 5,
        "description": "Connexion avant 8h",
    },
    {
        "slug": "monthly_champion",
        "name": "Champion du mois",
        "icon": "🏆",
        "category": "social",
        "xp_bonus": 30,
        "description": "1er du classement mensuel",
    },
    {
        "slug": "mentor",
        "name": "Mentor",
        "icon": "🤝",
        "category": "social",
        "xp_bonus": 10,
        "description": "Partagez votre certificat",
    },
    {
        "slug": "persistent",
        "name": "Persévérant",
        "icon": "💪",
        "category": "engagement",
        "xp_bonus": 5,
        "description": "3 tentatives sur un même quiz",
    },
    {
        "slug": "fast_learner",
        "name": "Apprenant rapide",
        "icon": "🚀",
        "category": "performance",
        "xp_bonus": 15,
        "description": "5 modules en une semaine",
    },
    {
        "slug": "nis2_ready",
        "name": "Prêt NIS2",
        "icon": "✅",
        "category": "performance",
        "xp_bonus": 25,
        "description": "Programme NIS2 complété",
    },
    {
        "slug": "explorer",
        "name": "Explorateur",
        "icon": "🗺️",
        "category": "engagement",
        "xp_bonus": 10,
        "description": "3 programmes différents commencés",
    },
    {
        "slug": "consistent",
        "name": "Régulier",
        "icon": "📅",
        "category": "streak",
        "xp_bonus": 10,
        "description": "Actif 5 jours consécutifs",
    },
    {
        "slug": "overachiever",
        "name": "Surperformant",
        "icon": "🌟",
        "category": "performance",
        "xp_bonus": 20,
        "description": "Score moyen > 90%",
    },
    {
        "slug": "all_in",
        "name": "Tout complété",
        "icon": "🎯",
        "category": "performance",
        "xp_bonus": 15,
        "description": "Tous les modules d'un programme complétés",
    },
    {
        "slug": "veteran",
        "name": "Vétéran",
        "icon": "🎖️",
        "category": "special",
        "xp_bonus": 30,
        "description": "6 mois d'utilisation",
    },
    {
        "slug": "top_scorer",
        "name": "Meilleur score",
        "icon": "👑",
        "category": "performance",
        "xp_bonus": 25,
        "description": "Score parfait 3 fois",
    },
]


async def seed_badges(db: AsyncSession) -> int:
    """Upsert the 20 badge definitions. Returns count of created badges."""
    created = 0
    for b in BADGE_CATALOG:
        existing = (
            await db.execute(select(AwarenessBadge).where(AwarenessBadge.slug == b["slug"]))
        ).scalar_one_or_none()
        if existing is None:
            db.add(AwarenessBadge(**b))
            created += 1
        else:
            existing.name = b["name"]
            existing.icon = b["icon"]
            existing.xp_bonus = b["xp_bonus"]
            existing.category = b["category"]
            existing.description = b["description"]
    await db.commit()
    return created
