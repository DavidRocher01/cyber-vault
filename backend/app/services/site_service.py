"""Service d'acces aux sites surveilles (CRUD + verification de domaine).

Les operations de verification de domaine delèguent la logique metier a
`phishing_service` (partagee) et se contentent de porter la frontiere de
transaction (commit) cote service, pour garder l'endpoint sans acces DB.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan
from app.models.site import Site
from app.services import phishing_service


async def get_owned_site(db: AsyncSession, site_id: int, user_id: int) -> Site | None:
    """Site par id s'il appartient a l'utilisateur, sinon None."""
    result = await db.execute(select(Site).where(Site.id == site_id, Site.user_id == user_id))
    return result.scalar_one_or_none()


async def get_owned_active_site(db: AsyncSession, site_id: int, user_id: int) -> Site | None:
    """Site actif par id s'il appartient a l'utilisateur, sinon None."""
    result = await db.execute(
        select(Site).where(
            Site.id == site_id,
            Site.user_id == user_id,
            Site.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_active_sites(db: AsyncSession, user_id: int) -> list[Site]:
    """Sites actifs de l'utilisateur."""
    result = await db.execute(
        select(Site).where(Site.user_id == user_id, Site.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def count_active_sites(db: AsyncSession, user_id: int) -> int:
    """Nombre de sites actifs de l'utilisateur."""
    result = await db.execute(
        select(func.count(Site.id)).where(
            Site.user_id == user_id,
            Site.is_active == True,  # noqa: E712
        )
    )
    return result.scalar() or 0


async def create_site(
    db: AsyncSession, *, user_id: int, url: str, name: str, rssi_client_id: int | None
) -> Site:
    """Cree un site surveille pour l'utilisateur."""
    site = Site(user_id=user_id, url=url, name=name, rssi_client_id=rssi_client_id)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


async def deactivate_site(db: AsyncSession, site: Site) -> None:
    """Desactive un site (soft delete)."""
    site.is_active = False
    await db.commit()


async def get_latest_completed_scan(db: AsyncSession, site_id: int) -> Scan | None:
    """Dernier scan termine (avec resultats) pour un site, sinon None."""
    result = await db.execute(
        select(Scan)
        .where(
            Scan.site_id == site_id,
            Scan.status == "done",
            Scan.results_json.isnot(None),
        )
        .order_by(Scan.finished_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def request_domain_verification(db: AsyncSession, user_id: int, domain: str):
    """Emet/renouvelle le token de verification DNS pour un domaine, puis commit."""
    record = await phishing_service.request_domain_verification(user_id, domain, db)
    await db.commit()
    return record


async def confirm_domain_verification(db: AsyncSession, record) -> bool:
    """Verifie le TXT DNS ; commit si le domaine devient verifie."""
    verified = await phishing_service.check_domain_verification(record, db)
    if verified:
        await db.commit()
    return verified
