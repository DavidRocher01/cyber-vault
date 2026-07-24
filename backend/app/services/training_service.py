"""Service d'acces DB pour le module training (modules awareness + progression)."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_module import AwarenessModule
from app.models.awareness_program import AwarenessProgram
from app.models.training_progress import TrainingProgress


async def load_program_modules(
    db: AsyncSession, program_slug: str, excluded_slugs: Iterable[str]
) -> list[AwarenessModule]:
    """Modules actifs du programme donne (par slug), hors slugs exclus, ordonnes par position.

    Retourne [] si le programme n'existe pas.
    """
    prog_result = await db.execute(
        select(AwarenessProgram).where(AwarenessProgram.slug == program_slug)
    )
    program = prog_result.scalar_one_or_none()
    if program is None:
        return []

    mods_result = await db.execute(
        select(AwarenessModule)
        .where(
            AwarenessModule.program_id == program.id,
            AwarenessModule.is_active == True,  # noqa: E712
            AwarenessModule.slug.notin_(list(excluded_slugs)),
        )
        .order_by(AwarenessModule.position)
    )
    return list(mods_result.scalars().all())


async def list_user_progress(db: AsyncSession, user_id: int) -> list[TrainingProgress]:
    """Progression training d'un utilisateur."""
    result = await db.execute(select(TrainingProgress).where(TrainingProgress.user_id == user_id))
    return list(result.scalars().all())


async def mark_module_complete(db: AsyncSession, user_id: int, module_id: str) -> None:
    """Marque un module comme complete (idempotent)."""
    existing = await db.execute(
        select(TrainingProgress).where(
            TrainingProgress.user_id == user_id,
            TrainingProgress.module_id == module_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(TrainingProgress(user_id=user_id, module_id=module_id))
        await db.commit()
