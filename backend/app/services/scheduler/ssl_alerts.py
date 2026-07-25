"""Job alertes SSL — prévient quand un certificat expire dans 30/14/7 jours
(exécuté chaque jour à 09:00 UTC)."""

import asyncio
import json
from datetime import UTC, datetime

from loguru import logger

from app.core.database import AsyncSessionLocal
from app.services.email_service import send_ssl_expiry_alert
from app.services.scheduler.sites import _load_active_sites_with_last_scan

_SSL_THRESHOLDS = [7, 14, 30]


async def _check_ssl_alerts() -> None:
    """Daily job: send SSL expiry alerts when cert expires within 30/14/7 days."""
    from app.core.config import settings

    async with AsyncSessionLocal() as db:
        rows, last_scan_map, user_map = await _load_active_sites_with_last_scan(db)
        if not rows:
            return

        for site, _ in rows:
            user = user_map.get(site.user_id)
            if not user or not user.notif_ssl_expiry:
                continue

            last_scan = last_scan_map.get(site.id)
            if not last_scan or not last_scan.results_json:
                continue

            try:
                results = json.loads(last_scan.results_json)
                ssl = results.get("ssl") or {}
                days = ssl.get("days_remaining")
                expiry_date = ssl.get("expiry_date", "")
                if days is None:
                    continue
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

            # Reset alert state if cert was renewed
            if days > 30 and site.ssl_alert_threshold is not None:
                site.ssl_alert_threshold = None
                site.ssl_alert_sent_at = None
                await db.commit()
                continue

            # Find the applicable threshold
            threshold = next((t for t in _SSL_THRESHOLDS if days <= t), None)
            if threshold is None:
                continue

            # Skip if already alerted for this threshold or a lower one
            if site.ssl_alert_threshold is not None and site.ssl_alert_threshold <= threshold:
                continue

            dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
            try:
                await asyncio.to_thread(
                    send_ssl_expiry_alert,
                    to_email=user.email,
                    site_url=site.url,
                    days_remaining=days,
                    expiry_date=expiry_date,
                    dashboard_url=dashboard_url,
                )
                site.ssl_alert_threshold = threshold
                site.ssl_alert_sent_at = datetime.now(UTC)
                await db.commit()
            except Exception as exc:
                logger.warning(f"SSL expiry alert email failed for {site.url}: {exc}")
