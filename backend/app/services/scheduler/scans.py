"""Job scans automatiques — déclenche un scan sur les sites dont l'intervalle
de plan est échu (exécuté chaque nuit à 02:00 UTC)."""

import asyncio
from datetime import UTC, datetime

from loguru import logger

from app.core.database import AsyncSessionLocal
from app.core.utils import mask_email
from app.models.scan import Scan
from app.services.email_service import send_scan_report
from app.services.scan_service import run_scan
from app.services.scheduler.sites import _load_active_sites_with_last_scan


async def _schedule_due_scans() -> None:
    """Check all active sites and trigger a scan if due."""
    async with AsyncSessionLocal() as db:
        rows, last_scan_map, user_map = await _load_active_sites_with_last_scan(db)
        if not rows:
            return

        now = datetime.now(UTC)
        for site, plan in rows:
            # Plan "à la demande" (intervalle 0 ou négatif, ex. Gratuit) : jamais de scan
            # automatique — sinon `days_since < 0` est toujours faux et le site serait
            # re-scanné chaque nuit.
            if plan.scan_interval_days <= 0:
                continue

            last_scan = last_scan_map.get(site.id)
            if last_scan and last_scan.finished_at:
                days_since = (now - last_scan.finished_at).days
                if days_since < plan.scan_interval_days:
                    continue

            # Create and run scan
            scan = Scan(site_id=site.id, status="pending")
            db.add(scan)
            await db.commit()
            await db.refresh(scan)

            await run_scan(scan.id, db)

            # Send email report — wrapped in thread to avoid blocking the event loop
            await db.refresh(scan)
            if scan.status == "done" and scan.pdf_path:
                user = user_map.get(site.user_id)
                if user:
                    try:
                        await asyncio.to_thread(
                            send_scan_report,
                            to_email=user.email,
                            site_url=site.url,
                            overall_status=scan.overall_status or "OK",
                            pdf_path=scan.pdf_path,
                        )
                    except Exception as exc:
                        logger.warning(
                            f"Scan report email failed for {mask_email(user.email)}: {exc}"
                        )
