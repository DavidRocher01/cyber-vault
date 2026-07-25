"""Persistance des scans dark web (lecture du dernier scan, enregistrement)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.darkweb_scan import DarkwebScan


async def get_latest_scan(db: AsyncSession, user_id: int) -> DarkwebScan | None:
    """Retourne le dernier scan dark web de l'utilisateur, sinon None."""
    result = await db.execute(
        select(DarkwebScan)
        .where(DarkwebScan.user_id == user_id)
        .order_by(DarkwebScan.checked_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_scan(db: AsyncSession, user_id: int, email: str, data: dict) -> DarkwebScan:
    """Enregistre un nouveau scan dark web à partir du résultat provider."""
    scan = DarkwebScan(
        user_id=user_id,
        email=email,
        total_breaches=data["total"],
        status=data["status"],
        checked_at=datetime.now(UTC),
        results_json=json.dumps(data["breaches"]),
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan
