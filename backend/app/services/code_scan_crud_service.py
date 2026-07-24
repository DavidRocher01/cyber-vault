"""Service CRUD des analyses de code (creation/liste/suppression + garde de concurrence)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import paginate
from app.models.code_scan import CodeScan


async def has_running_scan(db: AsyncSession, user_id: int) -> bool:
    """Vrai si l'utilisateur a deja un scan pending ou running."""
    result = await db.execute(
        select(CodeScan).where(
            CodeScan.user_id == user_id,
            CodeScan.status.in_(["pending", "running"]),
        )
    )
    return result.scalar_one_or_none() is not None


async def create_code_scan(
    db: AsyncSession, *, user_id: int, repo_url: str, repo_name: str
) -> CodeScan | None:
    """Cree un scan en statut 'pending'. Retourne None si un scan concurrent existe deja
    (violation de l'index unique partiel -> l'endpoint renvoie 429)."""
    scan = CodeScan(
        user_id=user_id,
        repo_url=repo_url,
        repo_name=repo_name,
        status="pending",
        created_at=datetime.now(UTC),
    )
    db.add(scan)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(scan)
    return scan


async def list_user_code_scans(db: AsyncSession, user_id: int, *, page: int, per_page: int) -> dict:
    """Page des analyses de code d'un utilisateur (plus recentes d'abord)."""
    return await paginate(
        db,
        base_query=select(CodeScan)
        .where(CodeScan.user_id == user_id)
        .order_by(CodeScan.created_at.desc()),
        count_query=select(func.count()).select_from(CodeScan).where(CodeScan.user_id == user_id),
        page=page,
        per_page=per_page,
    )


async def delete_code_scan(db: AsyncSession, scan: CodeScan) -> None:
    """Supprime une analyse de code."""
    await db.delete(scan)
    await db.commit()
