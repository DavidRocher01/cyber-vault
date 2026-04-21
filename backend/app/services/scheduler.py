"""
APScheduler — planifie les scans automatiques selon la fréquence du plan.
Starter/Pro : toutes les 30 nuits à 2h00.
Business : toutes les 7 nuits à 2h00.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.app_setting import AppSetting
from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.services.scan_service import run_scan
from app.services.email_service import send_scan_report, send_ssl_expiry_alert
from app.services.newsletter_email import send_newsletter_issue
from app.models.newsletter_subscriber import NewsletterSubscriber

scheduler = AsyncIOScheduler()

_NEWSLETTER_EDITION_KEY = "newsletter_edition"


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
        if not rows:
            return

        # Batch load last done scan per site — single query, no N+1
        site_ids = [site.id for site, _ in rows]
        subq = (
            select(func.max(Scan.id).label("max_id"))
            .where(Scan.site_id.in_(site_ids), Scan.status == "done")
            .group_by(Scan.site_id)
            .subquery()
        )
        last_scans_result = await db.execute(
            select(Scan).where(Scan.id.in_(select(subq.c.max_id)))
        )
        last_scan_map: dict[int, Scan] = {s.site_id: s for s in last_scans_result.scalars().all()}

        # Batch load users
        from app.models.user import User
        user_ids = list({site.user_id for site, _ in rows})
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map: dict[int, User] = {u.id: u for u in users_result.scalars().all()}

        now = datetime.now(timezone.utc)
        for site, plan in rows:
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
                    except Exception:
                        pass  # Ne pas bloquer si l'email échoue


_SSL_THRESHOLDS = [7, 14, 30]


async def _check_ssl_alerts() -> None:
    """Daily job: send SSL expiry alerts when cert expires within 30/14/7 days."""
    from app.models.user import User
    from app.core.config import settings
    import json

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Site, Plan)
            .join(Subscription, Subscription.user_id == Site.user_id)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(Site.is_active == True, Subscription.status == "active")
        )
        rows = result.all()
        if not rows:
            return

        site_ids = [site.id for site, _ in rows]
        subq = (
            select(func.max(Scan.id).label("max_id"))
            .where(Scan.site_id.in_(site_ids), Scan.status == "done")
            .group_by(Scan.site_id)
            .subquery()
        )
        last_scans_result = await db.execute(
            select(Scan).where(Scan.id.in_(select(subq.c.max_id)))
        )
        last_scan_map: dict[int, Scan] = {s.site_id: s for s in last_scans_result.scalars().all()}

        user_ids = list({site.user_id for site, _ in rows})
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map: dict[int, User] = {u.id: u for u in users_result.scalars().all()}

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
            except Exception:
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

            dashboard_url = f"{settings.FRONTEND_URL}/cyberscan/dashboard"
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
                site.ssl_alert_sent_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception:
                pass


async def _send_biweekly_newsletter() -> None:
    """Send the Radar Cyber newsletter to all active subscribers."""
    from app.core.config import settings
    from loguru import logger

    async with AsyncSessionLocal() as db:
        # Read and atomically increment the persisted edition counter
        setting = await db.get(AppSetting, _NEWSLETTER_EDITION_KEY)
        if setting is None:
            setting = AppSetting(key=_NEWSLETTER_EDITION_KEY, value_int=1)
            db.add(setting)
            await db.flush()
        edition = setting.value_int
        setting.value_int = edition + 1

        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)
        )
        subscribers = result.scalars().all()
        await db.commit()

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
                edition=edition,
                flash_title=flash_title,
                flash_body=flash_body,
                reflex_title=reflex_title,
                reflex_body=reflex_body,
                legal_title=legal_title,
                legal_body=legal_body,
            )
        except Exception:
            pass  # Ne pas bloquer si un envoi échoue

    logger.info(f"Newsletter édition #{edition} envoyée à {len(subscribers)} abonné(s)")


def start_scheduler() -> None:
    """Start the APScheduler with a nightly job at 02:00 UTC and bi-weekly newsletter."""
    scheduler.add_job(
        _schedule_due_scans,
        trigger=CronTrigger(hour=2, minute=0),
        id="nightly_scans",
        replace_existing=True,
    )
    scheduler.add_job(
        _check_ssl_alerts,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_ssl_alerts",
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
