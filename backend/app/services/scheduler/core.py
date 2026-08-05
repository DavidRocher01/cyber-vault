"""APScheduler — instance partagée + démarrage/arrêt.

Planifie les scans automatiques selon la fréquence du plan
(`plan.scan_interval_days`, vérifiée chaque nuit à 2h00), plus les jobs SSL,
newsletter, digest mensuel, dark web et sensibilisation.
Starter/Pro : hebdomadaire (7 j). Business : quotidien (1 j).
Gratuit (intervalle 0) : jamais de scan automatique (à la demande uniquement).
"""

import os
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger


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


def start_scheduler() -> None:
    """Start the APScheduler with a nightly job at 02:00 UTC and bi-weekly newsletter."""
    from apscheduler.triggers.interval import IntervalTrigger

    from app.services.phishing_service import send_pending_batch
    from app.services.scheduler.awareness import _run_awareness_at_risk_detection
    from app.services.scheduler.darkweb import _run_darkweb_monitoring
    from app.services.scheduler.monthly_digest import _send_monthly_digest_job
    from app.services.scheduler.newsletter import _send_biweekly_newsletter
    from app.services.scheduler.retention import (
        _run_data_retention_purge,
        _run_rafraichir_analyses,
    )
    from app.services.scheduler.scans import _schedule_due_scans
    from app.services.scheduler.ssl_alerts import _check_ssl_alerts

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
    scheduler.add_job(
        send_pending_batch,
        trigger=IntervalTrigger(minutes=15),
        id="phishing_batch",
        replace_existing=True,
    )
    # Verdict antivirus des fichiers deposes — relecture de la balise GuardDuty.
    # 2 minutes : les scans prennent 20 a 45 s (mesure du 2026-08-05). Le cout
    # est nul quand rien n attend, la requete ne rendant que les `en_analyse`.
    scheduler.add_job(
        _run_rafraichir_analyses,
        trigger=IntervalTrigger(minutes=2),
        id="depot_rafraichir_analyses",
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
    # Rétention / purge RGPD — nightly at 05:00 UTC (public_scans + Dark Web expirés)
    scheduler.add_job(
        _run_data_retention_purge,
        trigger=CronTrigger(hour=5, minute=0),
        id="data_retention_purge",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
