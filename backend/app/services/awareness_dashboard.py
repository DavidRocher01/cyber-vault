"""
Dashboard service — vues agrégées multi-tenant.

Niveau 1 — RSSI Consultant : vue consolidée de toutes ses organisations clientes.
Niveau 2 — Org Admin       : vue détaillée d'une organisation.
Niveau 3 — Learner         : dashboard individuel (Sprint 3).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_certificate import AwarenessCertificate
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_module import AwarenessModule
from app.models.awareness_organization import AwarenessOrganization
from app.models.awareness_program import AwarenessProgram
from app.models.awareness_progress import AwarenessProgress

_AT_RISK_DAYS = 14       # learner inactif depuis N jours avec complétion < 70%
_INACTIVE_DAYS = 30      # learner sans activité depuis N jours


# ── RSSI Consultant dashboard ──────────────────────────────────────────────────

async def consultant_dashboard(db: AsyncSession, owner_user_id: int) -> dict:
    """
    Vue agrégée pour le consultant RSSI.
    Retourne toutes ses organisations avec KPIs globaux.
    """
    orgs = (
        await db.execute(
            select(AwarenessOrganization).where(
                AwarenessOrganization.owner_user_id == owner_user_id,
                AwarenessOrganization.is_active == True,
            )
        )
    ).scalars().all()

    org_kpis = []
    total_learners = 0
    total_enrolled = 0
    total_completed = 0
    total_at_risk = 0

    for org in orgs:
        kpi = await _org_kpi(db, org)
        org_kpis.append(kpi)
        total_learners += kpi["learner_count"]
        total_enrolled += kpi["active_enrollments"]
        total_completed += kpi["completed_enrollments"]
        total_at_risk += kpi["at_risk_count"]

    global_completion = (
        round(total_completed / total_enrolled * 100, 1)
        if total_enrolled > 0 else 0.0
    )

    return {
        "organizations": org_kpis,
        "summary": {
            "total_organizations": len(orgs),
            "total_learners": total_learners,
            "total_active_enrollments": total_enrolled,
            "total_completed_enrollments": total_completed,
            "global_completion_rate": global_completion,
            "total_at_risk_learners": total_at_risk,
        },
    }


async def _org_kpi(db: AsyncSession, org: AwarenessOrganization) -> dict:
    """KPIs pour une organisation."""
    learner_count = (
        await db.execute(
            select(func.count(AwarenessLearner.id)).where(
                AwarenessLearner.organization_id == org.id,
                AwarenessLearner.is_active == True,
            )
        )
    ).scalar_one()

    active_enrollments = (
        await db.execute(
            select(func.count(AwarenessEnrollment.id)).where(
                AwarenessEnrollment.organization_id == org.id,
                AwarenessEnrollment.status.in_(["pending", "in_progress"]),
            )
        )
    ).scalar_one()

    completed_enrollments = (
        await db.execute(
            select(func.count(AwarenessEnrollment.id)).where(
                AwarenessEnrollment.organization_id == org.id,
                AwarenessEnrollment.status == "completed",
            )
        )
    ).scalar_one()

    total_enrollments = active_enrollments + completed_enrollments
    completion_rate = (
        round(completed_enrollments / total_enrollments * 100, 1)
        if total_enrollments > 0 else 0.0
    )

    at_risk_count = await _count_at_risk(db, org.id)

    certificates_issued = (
        await db.execute(
            select(func.count(AwarenessCertificate.id))
            .join(AwarenessLearner, AwarenessLearner.id == AwarenessCertificate.learner_id)
            .where(
                AwarenessLearner.organization_id == org.id,
                AwarenessCertificate.is_revoked == False,
            )
        )
    ).scalar_one()

    return {
        "id": org.id,
        "name": org.name,
        "sector": org.sector,
        "learner_count": learner_count,
        "max_learners": org.max_learners,
        "active_enrollments": active_enrollments,
        "completed_enrollments": completed_enrollments,
        "completion_rate": completion_rate,
        "at_risk_count": at_risk_count,
        "certificates_issued": certificates_issued,
        "alerts": _build_alerts(learner_count, org.max_learners, at_risk_count, completion_rate),
    }


def _build_alerts(
    learner_count: int, max_learners: int,
    at_risk: int, completion_rate: float,
) -> list[str]:
    alerts = []
    if learner_count >= max_learners * 0.9:
        alerts.append("Quota learners presque atteint")
    if at_risk > 0:
        alerts.append(f"{at_risk} learner(s) à risque (inactif + < 70%)")
    if completion_rate < 60:
        alerts.append("Taux de complétion faible (< 60%)")
    return alerts


# ── Org Admin dashboard ────────────────────────────────────────────────────────

async def org_admin_dashboard(db: AsyncSession, org_id: int) -> dict:
    """Vue détaillée pour l'admin d'une organisation."""
    org = (
        await db.execute(select(AwarenessOrganization).where(AwarenessOrganization.id == org_id))
    ).scalar_one()

    # Engagement funnel
    total_learners = (
        await db.execute(
            select(func.count(AwarenessLearner.id)).where(
                AwarenessLearner.organization_id == org_id,
                AwarenessLearner.is_active == True,
            )
        )
    ).scalar_one()

    enrolled_learners = (
        await db.execute(
            select(func.count(func.distinct(AwarenessEnrollment.learner_id))).where(
                AwarenessEnrollment.organization_id == org_id,
            )
        )
    ).scalar_one()

    active_learners = (
        await db.execute(
            select(func.count(func.distinct(AwarenessEnrollment.learner_id))).where(
                AwarenessEnrollment.organization_id == org_id,
                AwarenessEnrollment.status == "in_progress",
            )
        )
    ).scalar_one()

    completed_learners = (
        await db.execute(
            select(func.count(func.distinct(AwarenessEnrollment.learner_id))).where(
                AwarenessEnrollment.organization_id == org_id,
                AwarenessEnrollment.status == "completed",
            )
        )
    ).scalar_one()

    # Per-program stats
    programs = await _program_stats(db, org_id)

    # At-risk learners (names anonymised — initials only)
    at_risk = await _at_risk_learners(db, org_id)

    # Certificates
    certificates = (
        await db.execute(
            select(func.count(AwarenessCertificate.id))
            .join(AwarenessLearner, AwarenessLearner.id == AwarenessCertificate.learner_id)
            .where(
                AwarenessLearner.organization_id == org_id,
                AwarenessCertificate.is_revoked == False,
            )
        )
    ).scalar_one()

    return {
        "organization": {
            "id": org.id,
            "name": org.name,
            "sector": org.sector,
            "max_learners": org.max_learners,
        },
        "engagement": {
            "total_learners": total_learners,
            "enrolled_learners": enrolled_learners,
            "active_learners": active_learners,
            "completed_learners": completed_learners,
            "enrollment_rate": round(enrolled_learners / total_learners * 100, 1) if total_learners else 0.0,
        },
        "programs": programs,
        "at_risk_learners": at_risk,
        "certificates_issued": certificates,
    }


async def _program_stats(db: AsyncSession, org_id: int) -> list[dict]:
    programs = (
        await db.execute(select(AwarenessProgram).where(AwarenessProgram.is_active == True))
    ).scalars().all()

    stats = []
    for prog in programs:
        total_modules = (
            await db.execute(
                select(func.count(AwarenessModule.id)).where(
                    AwarenessModule.program_id == prog.id,
                    AwarenessModule.is_active == True,
                )
            )
        ).scalar_one()

        enrolled = (
            await db.execute(
                select(func.count(AwarenessEnrollment.id)).where(
                    AwarenessEnrollment.organization_id == org_id,
                    AwarenessEnrollment.program_id == prog.id,
                )
            )
        ).scalar_one()

        if enrolled == 0:
            continue

        completed = (
            await db.execute(
                select(func.count(AwarenessEnrollment.id)).where(
                    AwarenessEnrollment.organization_id == org_id,
                    AwarenessEnrollment.program_id == prog.id,
                    AwarenessEnrollment.status == "completed",
                )
            )
        ).scalar_one()

        avg_pct = (
            await db.execute(
                select(func.avg(AwarenessEnrollment.completion_pct)).where(
                    AwarenessEnrollment.organization_id == org_id,
                    AwarenessEnrollment.program_id == prog.id,
                )
            )
        ).scalar_one() or 0.0

        stats.append({
            "program_id": prog.id,
            "program_title": prog.title,
            "total_modules": total_modules,
            "enrolled_learners": enrolled,
            "completed_learners": completed,
            "completion_rate": round(completed / enrolled * 100, 1),
            "avg_completion_pct": round(float(avg_pct), 1),
        })

    return stats


async def _count_at_risk(db: AsyncSession, org_id: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=_AT_RISK_DAYS)
    result = await db.execute(
        select(func.count(func.distinct(AwarenessEnrollment.learner_id))).where(
            AwarenessEnrollment.organization_id == org_id,
            AwarenessEnrollment.status == "in_progress",
            AwarenessEnrollment.completion_pct < 70,
            AwarenessEnrollment.last_activity_at < cutoff,
        )
    )
    return result.scalar_one()


async def _at_risk_learners(db: AsyncSession, org_id: int) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=_AT_RISK_DAYS)
    result = await db.execute(
        select(
            AwarenessLearner.id,
            AwarenessLearner.first_name,
            AwarenessLearner.last_name,
            AwarenessLearner.department,
            AwarenessEnrollment.completion_pct,
            AwarenessEnrollment.last_activity_at,
        )
        .join(AwarenessEnrollment, AwarenessEnrollment.learner_id == AwarenessLearner.id)
        .where(
            AwarenessLearner.organization_id == org_id,
            AwarenessEnrollment.status == "in_progress",
            AwarenessEnrollment.completion_pct < 70,
            AwarenessEnrollment.last_activity_at < cutoff,
        )
        .limit(20)
    )
    rows = result.all()
    return [
        {
            "learner_id": r.id,
            "display_name": _anon_name(r.first_name, r.last_name),
            "department": r.department,
            "completion_pct": r.completion_pct,
            "last_activity_at": r.last_activity_at.isoformat() if r.last_activity_at else None,
            "days_inactive": (datetime.now(UTC) - r.last_activity_at).days if r.last_activity_at else None,
        }
        for r in rows
    ]


def _anon_name(first: str | None, last: str | None) -> str:
    """Aggregated dashboards show initials only (GDPR)."""
    parts = []
    if first:
        parts.append(first[0].upper() + ".")
    if last:
        parts.append(last[0].upper() + ".")
    return " ".join(parts) or "?"
