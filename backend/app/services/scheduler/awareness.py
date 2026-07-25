"""Job détection learners à risque (sensibilisation) — nightly 04:00 UTC.
Sprint 10 — Observabilité : log les métriques et alerte les responsables d'orga."""

from datetime import UTC, datetime

from loguru import logger

from app.core.database import AsyncSessionLocal


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
