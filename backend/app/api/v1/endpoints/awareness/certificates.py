"""Endpoints attestations, dashboards multi-tenancy, rapports NIS2
(Sprints 5, 7, 8)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_learner, get_current_user
from app.models.awareness_learner import AwarenessLearner
from app.models.user import User
from app.schemas.awareness import (
    AwarenessCertificateOut,
    ConsultantDashboardOut,
    OrgAdminDashboardOut,
)

from .helpers import _get_org_or_404

router = APIRouter()


# ── Attestations (Sprint 5) ────────────────────────────────────────────────────


@router.get("/enrollments/{enrollment_id}/certificate", response_model=AwarenessCertificateOut)
async def get_certificate(
    enrollment_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessCertificateOut:
    """Retourne les métadonnées du certificat d'une inscription complétée."""
    from app.models.awareness_certificate import AwarenessCertificate

    cert = (
        await db.execute(
            select(AwarenessCertificate).where(
                AwarenessCertificate.enrollment_id == enrollment_id,
                AwarenessCertificate.learner_id == learner.id,
            )
        )
    ).scalar_one_or_none()
    if cert is None:
        raise HTTPException(
            status_code=404, detail="Certificat introuvable — programme non complété."
        )
    return AwarenessCertificateOut.model_validate(cert)


@router.get("/enrollments/{enrollment_id}/certificate/download")
async def download_certificate_pdf(
    enrollment_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le PDF du certificat."""
    from fastapi.responses import Response

    from app.models.awareness_certificate import AwarenessCertificate
    from app.services.awareness_certificate_service import generate_certificate_pdf

    cert = (
        await db.execute(
            select(AwarenessCertificate).where(
                AwarenessCertificate.enrollment_id == enrollment_id,
                AwarenessCertificate.learner_id == learner.id,
            )
        )
    ).scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificat introuvable.")

    frozen = __import__("json").loads(cert.frozen_data_json)
    pdf_bytes = await asyncio.to_thread(generate_certificate_pdf, cert, frozen)
    filename = f"attestation-{cert.public_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Dashboards multi-tenancy (Sprint 7) ───────────────────────────────────────


@router.get("/consultant/dashboard", response_model=ConsultantDashboardOut)
async def consultant_dashboard_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsultantDashboardOut:
    """
    Vue agrégée RSSI consultant : toutes ses organisations clientes,
    KPIs globaux, alertes.
    """
    from app.services.awareness_dashboard import consultant_dashboard

    data = await consultant_dashboard(db, current_user.id)
    return ConsultantDashboardOut(**data)


@router.get("/organizations/{org_id}/admin-dashboard", response_model=OrgAdminDashboardOut)
async def org_admin_dashboard_endpoint(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgAdminDashboardOut:
    """
    Vue détaillée admin : funnel engagement, stats par programme,
    learners à risque (initiales seulement — RGPD).
    """
    await _get_org_or_404(org_id, current_user, db)
    from app.services.awareness_dashboard import org_admin_dashboard

    data = await org_admin_dashboard(db, org_id)
    return OrgAdminDashboardOut(**data)


# ── Rapport NIS2 compliance (Sprint 8) ────────────────────────────────────────


@router.get("/organizations/{org_id}/nis2-report")
async def get_nis2_report(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retourne les métriques NIS2 Article 21 en JSON."""
    await _get_org_or_404(org_id, current_user, db)
    from app.services.awareness_nis2_report import build_nis2_report

    return await build_nis2_report(db, org_id)


@router.get("/organizations/{org_id}/nis2-report/pdf")
async def download_nis2_report_pdf(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Génère et télécharge le rapport PDF NIS2."""
    from fastapi.responses import Response

    from app.services.awareness_nis2_report import (
        build_nis2_report,
        generate_nis2_report_pdf,
    )

    await _get_org_or_404(org_id, current_user, db)
    data = await build_nis2_report(db, org_id)
    pdf_bytes = generate_nis2_report_pdf(
        data["org_name"],
        data["requirements"],
        data["global_score"],
        data["metrics"],
        data["certificate_count"],
        data["generated_at"],
    )
    filename = f"rapport-nis2-{org_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
