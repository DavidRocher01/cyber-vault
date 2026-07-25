"""Job digest mensuel — récapitulatif sécurité envoyé le 1er de chaque mois
à chaque utilisateur payant."""

import asyncio
import json
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.utils import mask_email
from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription
from app.services.email_service import send_monthly_digest

_MONTHS_FR = [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]


async def _send_monthly_digest_job() -> None:
    """1st of each month: send a security digest to every paying user."""
    from calendar import monthrange

    from app.core.config import settings
    from app.models.user import User

    now = datetime.now(UTC)
    last_month = now.month - 1 if now.month > 1 else 12
    last_year = now.year if now.month > 1 else now.year - 1
    _, days_in_month = monthrange(last_year, last_month)
    start = datetime(last_year, last_month, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(last_year, last_month, days_in_month, 23, 59, 59, tzinfo=UTC)
    month_label = f"{_MONTHS_FR[last_month - 1]} {last_year}"

    async with AsyncSessionLocal() as db:
        # Load all (user, site) pairs for active subscriptions
        result = await db.execute(
            select(User, Site)
            .join(Subscription, Subscription.user_id == User.id)
            .join(Site, Site.user_id == User.id)
            .where(Subscription.status == "active", Site.is_active == True)
        )
        pairs = result.all()
        if not pairs:
            return

        # Group sites by user
        user_map: dict[int, User] = {}
        sites_by_user: dict[int, list[Site]] = {}
        for user, site in pairs:
            user_map[user.id] = user
            sites_by_user.setdefault(user.id, []).append(site)

        all_site_ids = [s.id for sites in sites_by_user.values() for s in sites]

        # Load scans for last month in a single query
        scans_result = await db.execute(
            select(Scan)
            .where(
                Scan.site_id.in_(all_site_ids),
                Scan.created_at >= start,
                Scan.created_at <= end,
                Scan.status == "done",
            )
            .order_by(Scan.site_id, Scan.created_at.desc())
        )
        scans_by_site: dict[int, list[Scan]] = {}
        for scan in scans_result.scalars().all():
            scans_by_site.setdefault(scan.site_id, []).append(scan)

    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"

    for user_id, sites in sites_by_user.items():
        user = user_map[user_id]
        sites_summary = []
        for site in sites:
            scans = scans_by_site.get(site.id, [])
            latest = scans[0] if scans else None
            overall_status = latest.overall_status if latest else None
            critical_count = 0
            warning_count = 0
            if latest and latest.results_json:
                try:
                    results = json.loads(latest.results_json)
                    for module in results.values():
                        if isinstance(module, dict):
                            s = module.get("status")
                            if s == "CRITICAL":
                                critical_count += 1
                            elif s == "WARNING":
                                warning_count += 1
                except (json.JSONDecodeError, AttributeError) as exc:
                    logger.warning(
                        "results_json illisible pour un site (alertes SSL), ignore : {}", exc
                    )
            sites_summary.append(
                {
                    "url": site.url,
                    "overall_status": overall_status,
                    "scans_count": len(scans),
                    "critical_count": critical_count,
                    "warning_count": warning_count,
                }
            )

        try:
            await asyncio.to_thread(
                send_monthly_digest,
                to_email=user.email,
                month_label=month_label,
                sites=sites_summary,
                dashboard_url=dashboard_url,
            )
        except Exception as exc:
            logger.warning(f"Monthly digest email failed for {mask_email(user.email)}: {exc}")
