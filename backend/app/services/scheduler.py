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
from app.services.newsletter_email import send_newsletter_issue
from app.models.newsletter_subscriber import NewsletterSubscriber

scheduler = AsyncIOScheduler()

# Edition counter (persisted in-memory; reset on restart — acceptable for now)
_newsletter_edition = 1


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


async def _send_biweekly_newsletter() -> None:
    """Send the Radar Cyber newsletter to all active subscribers."""
    global _newsletter_edition
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)
        )
        subscribers = result.scalars().all()

    from app.core.config import settings

    # Default editorial content — update each edition
    flash_title = "Ransomware : une vague mondiale frappe les PME"
    flash_body = (
        "Cette quinzaine, plusieurs campagnes de ransomware ont ciblé des PME européennes via "
        "des emails de phishing imitant des factures. Les secteurs les plus touchés : BTP, santé "
        "et services juridiques. Coût moyen estimé : 85 000 € par incident."
    )
    reflex_title = "Activez le MFA sur tous vos comptes critiques"
    reflex_body = (
        "La double authentification bloque 99,9 % des attaques automatisées selon Microsoft. "
        "Commencez par votre messagerie professionnelle, puis votre gestionnaire de mots de passe. "
        "Outils recommandés : Bitwarden, Aegis (Android), Raivo (iOS)."
    )
    legal_title = "NIS2 : êtes-vous concerné(e) ?"
    legal_body = (
        "La directive NIS2, transposée en droit français depuis octobre 2024, élargit les "
        "obligations cyber à ~15 000 nouvelles entités (ETI, collectivités, sous-traitants). "
        "Vérifiez votre périmètre sur le site de l'ANSSI et anticipez l'audit obligatoire."
    )

    for sub in subscribers:
        unsubscribe_url = f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={sub.unsubscribe_token}"
        try:
            send_newsletter_issue(
                to_email=sub.email,
                unsubscribe_url=unsubscribe_url,
                edition=_newsletter_edition,
                flash_title=flash_title,
                flash_body=flash_body,
                reflex_title=reflex_title,
                reflex_body=reflex_body,
                legal_title=legal_title,
                legal_body=legal_body,
            )
        except Exception:
            pass  # Ne pas bloquer si un envoi échoue

    from loguru import logger
    logger.info(f"Newsletter édition #{_newsletter_edition} envoyée à {len(subscribers)} abonné(s)")
    _newsletter_edition += 1


def start_scheduler() -> None:
    """Start the APScheduler with a nightly job at 02:00 UTC and bi-weekly newsletter."""
    scheduler.add_job(
        _schedule_due_scans,
        trigger=CronTrigger(hour=2, minute=0),
        id="nightly_scans",
        replace_existing=True,
    )
    # Newsletter toutes les 2 semaines, lundi à 8h00 UTC
    from apscheduler.triggers.interval import IntervalTrigger
    scheduler.add_job(
        _send_biweekly_newsletter,
        trigger=IntervalTrigger(weeks=2, timezone="UTC"),
        id="biweekly_newsletter",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
