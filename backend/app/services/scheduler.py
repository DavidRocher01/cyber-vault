"""
APScheduler — planifie les scans automatiques selon la fréquence du plan
(`plan.scan_interval_days`, vérifiée chaque nuit à 2h00).
Starter/Pro : hebdomadaire (7 j). Business : quotidien (1 j).
Gratuit (intervalle 0) : jamais de scan automatique (à la demande uniquement).
"""

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.app_setting import AppSetting
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.models.plan import Plan
from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription
from app.services.email_service import (
    send_monthly_digest,
    send_scan_report,
    send_ssl_expiry_alert,
)
from app.services.newsletter_email import send_newsletter_issue
from app.services.scan_service import run_scan


def _make_scheduler() -> AsyncIOScheduler:
    """Create scheduler with Redis jobstore if REDIS_URL is configured, otherwise in-memory."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            from apscheduler.jobstores.redis import RedisJobStore  # lazy — requires redis package

            jobstores = {
                "default": RedisJobStore(
                    jobs_key="cybervault:jobs", run_times_key="cybervault:run_times", url=redis_url
                )
            }
            logger.info(f"APScheduler using Redis jobstore: {redis_url}")
            return AsyncIOScheduler(jobstores=jobstores)
        except Exception as exc:
            logger.warning(f"Redis jobstore unavailable, falling back to in-memory: {exc}")
    return AsyncIOScheduler()


scheduler = _make_scheduler()

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
        last_scans_result = await db.execute(select(Scan).where(Scan.id.in_(select(subq.c.max_id))))
        last_scan_map: dict[int, Scan] = {s.site_id: s for s in last_scans_result.scalars().all()}

        # Batch load users
        from app.models.user import User

        user_ids = list({site.user_id for site, _ in rows})
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map: dict[int, User] = {u.id: u for u in users_result.scalars().all()}

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
                        logger.warning(f"Scan report email failed for {user.email}: {exc}")


_SSL_THRESHOLDS = [7, 14, 30]


async def _check_ssl_alerts() -> None:
    """Daily job: send SSL expiry alerts when cert expires within 30/14/7 days."""
    import json

    from app.core.config import settings
    from app.models.user import User

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
        last_scans_result = await db.execute(select(Scan).where(Scan.id.in_(select(subq.c.max_id))))
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


_NEWSLETTER_CONTENT_KEY = "newsletter_content"

_DEFAULT_NEWSLETTER_CONTENT = {
    "flash_title": "Ransomware : une vague mondiale frappe les PME",
    "flash_body": (
        "Cette quinzaine, plusieurs campagnes de ransomware ont ciblé des PME européennes via "
        "des emails de phishing imitant des factures. Les secteurs les plus touchés : BTP, santé "
        "et services juridiques. Coût moyen estimé : 85 000 € par incident."
    ),
    "reflex_title": "Activez le MFA sur tous vos comptes critiques",
    "reflex_body": (
        "La double authentification bloque 99,9 % des attaques automatisées selon Microsoft. "
        "Commencez par votre messagerie professionnelle, puis votre gestionnaire de mots de passe. "
        "Outils recommandés : Bitwarden, Aegis (Android), Raivo (iOS)."
    ),
    "legal_title": "NIS2 : êtes-vous concerné(e) ?",
    "legal_body": (
        "La directive NIS2, transposée en droit français depuis octobre 2024, élargit les "
        "obligations cyber à ~15 000 nouvelles entités (ETI, collectivités, sous-traitants). "
        "Vérifiez votre périmètre sur le site de l'ANSSI et anticipez l'audit obligatoire."
    ),
}


async def _send_biweekly_newsletter() -> None:
    """Send the Radar Cyber newsletter to all active subscribers."""
    import json as _json

    from loguru import logger

    from app.core.config import settings

    async with AsyncSessionLocal() as db:
        # Read and atomically increment the persisted edition counter
        setting = await db.get(AppSetting, _NEWSLETTER_EDITION_KEY)
        if setting is None:
            setting = AppSetting(key=_NEWSLETTER_EDITION_KEY, value_int=1)
            db.add(setting)
            await db.flush()
        edition = setting.value_int
        setting.value_int = edition + 1

        # Read editorial content from DB; fall back to defaults if not set
        content_setting = await db.get(AppSetting, _NEWSLETTER_CONTENT_KEY)
        content = _DEFAULT_NEWSLETTER_CONTENT
        if content_setting and content_setting.value_text:
            try:
                content = _json.loads(content_setting.value_text)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Contenu newsletter en base illisible (JSON), fallback defaut : {}", exc
                )

        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)
        )
        subscribers = result.scalars().all()
        await db.commit()

    flash_title = content["flash_title"]
    flash_body = content["flash_body"]
    reflex_title = content["reflex_title"]
    reflex_body = content["reflex_body"]
    legal_title = content["legal_title"]
    legal_body = content["legal_body"]

    for sub in subscribers:
        unsubscribe_url = (
            f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={sub.unsubscribe_token}"
        )
        try:
            await asyncio.to_thread(
                send_newsletter_issue,
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
        except Exception as exc:
            logger.warning(f"Newsletter send failed for {sub.email}: {exc}")

    logger.info(f"Newsletter édition #{edition} envoyée à {len(subscribers)} abonné(s)")


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
    import json as _json
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
                    results = _json.loads(latest.results_json)
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
            logger.warning(f"Monthly digest email failed for {user.email}: {exc}")


async def _run_darkweb_monitoring() -> None:
    """Monthly job: re-scan active monitored dossiers and send alerts on new exposures."""
    from app.core.config import settings
    from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
    from app.models.user import User
    from app.services.darkweb_dossier_service import (
        process_dossier,
        send_darkweb_alert_email,
    )

    async with AsyncSessionLocal() as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(DarkwebDossier).where(
                DarkwebDossier.monitor_active == True,  # noqa: E712
                DarkwebDossier.status == "completed",
                DarkwebDossier.next_monitor_at <= now,
            )
        )
        dossiers = result.scalars().all()

    for d in dossiers:
        # Snapshot exposed emails before re-scan
        async with AsyncSessionLocal() as db:
            prev_result = await db.execute(
                select(DarkwebDossierTarget).where(
                    DarkwebDossierTarget.dossier_id == d.id,
                    DarkwebDossierTarget.status == "exposed",
                )
            )
            prev_exposed = {t.email for t in prev_result.scalars().all()}

        # Reset and re-process
        async with AsyncSessionLocal() as db:
            dossier = (
                await db.execute(select(DarkwebDossier).where(DarkwebDossier.id == d.id))
            ).scalar_one_or_none()
            if not dossier:
                continue
            await db.execute(
                DarkwebDossierTarget.__table__.update()
                .where(DarkwebDossierTarget.dossier_id == d.id)
                .values(
                    status="pending",
                    total_breaches=0,
                    breach_sources_json=None,
                    checked_at=None,
                )
            )
            dossier.status = "pending"
            dossier.started_at = None
            dossier.finished_at = None
            dossier.risk_score = None
            dossier.severity_score = None
            dossier.exposed_emails = 0
            dossier.total_breach_instances = 0
            dossier.top_sources_json = None
            await db.commit()

        await process_dossier(d.id, settings.HIBP_API_KEY)

        # Check for new exposures and alert
        async with AsyncSessionLocal() as db:
            new_result = await db.execute(
                select(DarkwebDossierTarget).where(
                    DarkwebDossierTarget.dossier_id == d.id,
                    DarkwebDossierTarget.status == "exposed",
                )
            )
            new_exposed = [
                t.email for t in new_result.scalars().all() if t.email not in prev_exposed
            ]

            user_result = await db.execute(select(User).where(User.id == d.user_id))
            user = user_result.scalar_one_or_none()

        if new_exposed and user:
            dashboard_url = f"{settings.FRONTEND_URL}/darkweb-dossier/{d.id}"
            send_darkweb_alert_email(
                to_email=user.email,
                company_name=d.company_name,
                domain=d.domain,
                exposed_count=len(new_exposed),
                new_exposed=new_exposed,
                dashboard_url=dashboard_url,
            )


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
    # Newsletter toutes les 2 semaines — première exécution dans 2 semaines (pas au démarrage)
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler.add_job(
        _send_biweekly_newsletter,
        trigger=IntervalTrigger(
            weeks=2,
            timezone="UTC",
            start_date=datetime.now(UTC) + timedelta(weeks=2),
        ),
        id="biweekly_newsletter",
        replace_existing=True,
    )
    scheduler.add_job(
        _send_monthly_digest_job,
        trigger=CronTrigger(day=1, hour=8, minute=0),
        id="monthly_digest",
        replace_existing=True,
    )
    # Phishing batch sender — every 15 minutes to drip-send pending emails
    from apscheduler.triggers.interval import IntervalTrigger as _IT

    from app.services.phishing_service import send_pending_batch

    scheduler.add_job(
        send_pending_batch,
        trigger=_IT(minutes=15),
        id="phishing_batch",
        replace_existing=True,
    )
    # Dark web monitoring — daily at 03:00 UTC, processes dossiers whose next_monitor_at is due
    scheduler.add_job(
        _run_darkweb_monitoring,
        trigger=CronTrigger(hour=3, minute=0),
        id="darkweb_monitoring",
        replace_existing=True,
    )
    # Awareness at-risk detection — nightly at 04:00 UTC
    scheduler.add_job(
        _run_awareness_at_risk_detection,
        trigger=CronTrigger(hour=4, minute=0),
        id="awareness_at_risk",
        replace_existing=True,
    )
    scheduler.start()


async def _run_awareness_at_risk_detection() -> None:
    """
    Sprint 10 — Observabilité : détecte les learners à risque et log les métriques.
    Critère : enrollment in_progress + last_activity > 14 jours + completion < 70%.
    """
    from datetime import timedelta

    from sqlalchemy import func, select

    from app.models.awareness_enrollment import AwarenessEnrollment
    from app.models.awareness_learner import AwarenessLearner
    from app.models.awareness_organization import AwarenessOrganization

    _AT_RISK_DAYS = 14
    cutoff = datetime.now(UTC) - timedelta(days=_AT_RISK_DAYS)

    async with AsyncSessionLocal() as db:
        # Count at-risk per organization
        result = await db.execute(
            select(
                AwarenessLearner.organization_id,
                func.count(func.distinct(AwarenessEnrollment.learner_id)).label("at_risk"),
            )
            .join(AwarenessEnrollment, AwarenessEnrollment.learner_id == AwarenessLearner.id)
            .where(
                AwarenessEnrollment.status == "in_progress",
                AwarenessEnrollment.completion_pct < 70,
                AwarenessEnrollment.last_activity_at < cutoff,
            )
            .group_by(AwarenessLearner.organization_id)
        )
        rows = result.all()
        total_at_risk = sum(r.at_risk for r in rows)

        # Log metrics
        logger.info(
            f"[awareness] at-risk detection: {total_at_risk} learners "
            f"across {len(rows)} organisations"
        )

        # Log per-org for monitoring dashboards + notify org owners by email
        from app.core.config import settings
        from app.models.user import User
        from app.services.email_service import send_awareness_at_risk_alert

        for row in rows:
            logger.info(f"[awareness] org_id={row.organization_id} at_risk={row.at_risk}")
            try:
                org = (
                    await db.execute(
                        select(AwarenessOrganization).where(
                            AwarenessOrganization.id == row.organization_id
                        )
                    )
                ).scalar_one_or_none()
                if org is None:
                    continue
                owner = (
                    await db.execute(select(User).where(User.id == org.owner_user_id))
                ).scalar_one_or_none()
                if owner is None:
                    continue
                dashboard_url = f"{settings.FRONTEND_URL}/awareness/org/{org.id}"
                send_awareness_at_risk_alert(
                    to_email=str(owner.email),
                    org_name=org.name,
                    at_risk_count=row.at_risk,
                    dashboard_url=dashboard_url,
                )
            except Exception as exc:
                logger.warning(
                    f"[awareness] at-risk email failed for org {row.organization_id}: {exc}"
                )


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
