"""Accès DB des endpoints de scan (propriété, quota, historique, statuts).

L'endpoint garde les préoccupations HTTP et métier non-DB : garde SSRF
(`assert_no_ssrf`, patché en test), déclenchement du scan en tâche de fond
(`run_scan`, patché en test), génération CSV/PDF (brandé et rapport), parsing
des scripts de remédiation. Ce service ne porte que les requêtes et le staging
des mutations.

⚠️ Atomicité du quota de scans (à préserver) : `lock_user_row` pose un verrou
`FOR UPDATE` sur la ligne user, tenu jusqu'au commit de `create_pending_scan`.
Cela sérialise les triggers concurrents du même utilisateur et ferme la race
check-then-act du quota (le décompte et l'insertion du scan sont dans la même
transaction). Le 429 doit être levé PENDANT la tenue du verrou (le rollback de
la session le relâche).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import paginate
from app.models.brand_profile import BrandProfile
from app.models.finding_status import FindingStatus
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User

# ── Propriété / lookups sites ────────────────────────────────────────────────


async def get_owned_active_site(db: AsyncSession, site_id: int, user_id: int) -> Site | None:
    """Site actif appartenant à l'utilisateur, sinon None."""
    result = await db.execute(
        select(Site).where(
            Site.id == site_id,
            Site.user_id == user_id,
            Site.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_owned_site(db: AsyncSession, site_id: int, user_id: int) -> Site | None:
    """Site appartenant à l'utilisateur (actif ou non), sinon None."""
    result = await db.execute(select(Site).where(Site.id == site_id, Site.user_id == user_id))
    return result.scalar_one_or_none()


async def get_site(db: AsyncSession, site_id: int) -> Site | None:
    """Site par identifiant (sans contrôle de propriété), sinon None."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    return result.scalar_one_or_none()


# ── Quota de scans (verrou + décompte + création) ────────────────────────────


async def lock_user_row(db: AsyncSession, user_id: int) -> None:
    """Verrou FOR UPDATE sur la ligne user — sérialise les triggers concurrents.

    Tenu jusqu'au commit de `create_pending_scan` (ou relâché par rollback).
    """
    await db.execute(select(User.id).where(User.id == user_id).with_for_update())


async def count_scans_in_window(
    db: AsyncSession, user_id: int, in_flight: tuple[str, ...], since: datetime
) -> int:
    """Nombre de scans comptant dans le quota de l'utilisateur.

    Compte les scans "en vol" (pending/running) + les scans "done" terminés
    depuis `since`, sur TOUS les sites de l'utilisateur (anti-bypass via
    delete+recreate d'un site).
    """
    result = await db.execute(
        select(func.count(Scan.id))
        .join(Site, Scan.site_id == Site.id)
        .where(
            Site.user_id == user_id,
            or_(
                Scan.status.in_(in_flight),
                and_(Scan.status == "done", Scan.finished_at >= since),
            ),
        )
    )
    return result.scalar()


async def create_pending_scan(db: AsyncSession, site_id: int) -> Scan:
    """Crée un scan `pending` et COMMITTE — relâche le verrou user."""
    scan = Scan(site_id=site_id, status="pending")
    db.add(scan)
    await db.flush()
    await db.refresh(scan)
    await db.commit()
    return scan


# ── Historique de scans ──────────────────────────────────────────────────────


async def get_owned_scan(db: AsyncSession, scan_id: int, user_id: int) -> Scan | None:
    """Scan appartenant (via son site) à l'utilisateur, sinon None."""
    result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Scan.id == scan_id, Site.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def paginate_site_scans(db: AsyncSession, site_id: int, page: int, per_page: int) -> dict:
    """Historique de scans paginé d'un site (du plus récent au plus ancien)."""
    return await paginate(
        db,
        base_query=select(Scan).where(Scan.site_id == site_id).order_by(Scan.created_at.desc()),
        count_query=select(func.count()).where(Scan.site_id == site_id),
        page=page,
        per_page=per_page,
    )


async def list_site_scans(db: AsyncSession, site_id: int) -> list[Scan]:
    """Tous les scans d'un site (du plus récent au plus ancien)."""
    result = await db.execute(
        select(Scan).where(Scan.site_id == site_id).order_by(Scan.created_at.desc())
    )
    return list(result.scalars().all())


# ── Profil de marque (PDF brandé) ────────────────────────────────────────────


async def get_brand_profile(db: AsyncSession, user_id: int) -> BrandProfile | None:
    """Profil de marque de l'utilisateur (PDF white-label), sinon None."""
    result = await db.execute(select(BrandProfile).where(BrandProfile.user_id == user_id))
    return result.scalar_one_or_none()


# ── Statuts de correction (finding status) ───────────────────────────────────


async def list_finding_statuses(db: AsyncSession, site_id: int) -> list[FindingStatus]:
    """Statuts de correction enregistrés pour un site."""
    result = await db.execute(select(FindingStatus).where(FindingStatus.site_id == site_id))
    return list(result.scalars().all())


async def upsert_finding_status(
    db: AsyncSession,
    *,
    site_id: int,
    module_key: str,
    status: str,
    note: str | None,
    now: datetime,
) -> FindingStatus:
    """Crée ou met à jour le statut de correction d'un module, puis COMMITTE."""
    result = await db.execute(
        select(FindingStatus).where(
            FindingStatus.site_id == site_id,
            FindingStatus.module_key == module_key,
        )
    )
    row = result.scalar_one_or_none()

    if row:
        row.status = status
        row.note = note
        row.updated_at = now
    else:
        row = FindingStatus(
            site_id=site_id,
            module_key=module_key,
            status=status,
            note=note,
            updated_at=now,
        )
        db.add(row)

    await db.commit()
    return row
