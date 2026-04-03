"""
APScheduler — planifie les scans automatiques selon la fréquence du plan.
Starter/Pro : toutes les 30 nuits à 2h00.
Business : toutes les 7 nuits à 2h00.
"""

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.services.scan_service import run_scan
from app.services.email_service import send_scan_report

scheduler = AsyncIOScheduler()


async def _schedule_due_scans() -> None:
    """Check all active sites and trigger a scan if due."""
    async with AsyncSessionLocal() as db:
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

        for site, plan in rows:
            # Find last scan
            last_result = await db.execute(
                select(Scan)
                .where(Scan.site_id == site.id, Scan.status == "done")
                .order_by(Scan.finished_at.desc())
                .limit(1)
            )
            last_scan = last_result.scalar_one_or_none()

            now = datetime.utcnow()
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

            # Send email report
            await db.refresh(scan)
            if scan.status == "done" and scan.pdf_path:
                from app.models.user import User
                user_result = await db.execute(select(User).where(User.id == site.user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    try:
                        send_scan_report(
                            to_email=user.email,
                            site_url=site.url,
                            overall_status=scan.overall_status or "OK",
                            pdf_path=scan.pdf_path,
                        )
                    except Exception:
                        pass  # Ne pas bloquer si l'email échoue


def start_scheduler() -> None:
    """Start the APScheduler with a nightly job at 02:00 UTC."""
    scheduler.add_job(
        _schedule_due_scans,
        trigger=CronTrigger(hour=2, minute=0),
        id="nightly_scans",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
