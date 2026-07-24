"""Service d'acces aux programmes de sensibilisation et a leurs modules actifs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_module import AwarenessModule
from app.models.awareness_program import AwarenessProgram


async def list_active_programs(db: AsyncSession) -> list[AwarenessProgram]:
    """Tous les programmes actifs."""
    result = await db.execute(
        select(AwarenessProgram).where(AwarenessProgram.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_active_program(db: AsyncSession, program_id: int) -> AwarenessProgram | None:
    """Programme actif par id, sinon None."""
    result = await db.execute(
        select(AwarenessProgram).where(
            AwarenessProgram.id == program_id,
            AwarenessProgram.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_active_modules(db: AsyncSession, program_ids: list[int]) -> list[AwarenessModule]:
    """Modules actifs des programmes donnes, ordonnes par (program_id, position)."""
    if not program_ids:
        return []
    result = await db.execute(
        select(AwarenessModule)
        .where(
            AwarenessModule.program_id.in_(program_ids),
            AwarenessModule.is_active == True,  # noqa: E712
        )
        .order_by(AwarenessModule.program_id, AwarenessModule.position)
    )
    return list(result.scalars().all())
