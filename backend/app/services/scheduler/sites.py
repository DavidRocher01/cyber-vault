"""Chargement partagé des sites actifs — utilisé par les jobs scans-dus et
alertes-SSL (bloc commun pour éviter la dérive d'un fix appliqué à un seul)."""

from sqlalchemy import func, select

from app.models.plan import Plan
from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription


async def _load_active_sites_with_last_scan(db):
    """Charge les sites actifs (abonnement actif) + leur dernier scan 'done' et
    leur propriétaire, en 3 requêtes (pas de N+1).

    Renvoie ``(rows, last_scan_map, user_map)`` où ``rows`` est une liste de
    tuples ``(Site, Plan)``. Bloc partagé entre les jobs scans-dus et
    alertes-SSL (évite la dérive d'un fix d'index/filtre applique a un seul).
    """
    from app.models.user import User

    result = await db.execute(
        select(Site, Plan)
        .join(Subscription, Subscription.user_id == Site.user_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(
            Site.is_active == True,
            Subscription.status == "active",
        )
    )
    rows = result.all()
    if not rows:
        return [], {}, {}

    # Batch load last done scan per site — single query, no N+1
    site_ids = [site.id for site, _ in rows]
    subq = (
        select(func.max(Scan.id).label("max_id"))
        .where(Scan.site_id.in_(site_ids), Scan.status == "done")
        .group_by(Scan.site_id)
        .subquery()
    )
    last_scans_result = await db.execute(select(Scan).where(Scan.id.in_(select(subq.c.max_id))))
    last_scan_map: dict[int, Scan] = {s.site_id: s for s in last_scans_result.scalars().all()}

    # Batch load users
    user_ids = list({site.user_id for site, _ in rows})
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    user_map: dict[int, User] = {u.id: u for u in users_result.scalars().all()}

    return rows, last_scan_map, user_map
