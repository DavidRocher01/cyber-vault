"""Routes phishing — report."""

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.models.user import User
from app.services.phishing import campaigns
from app.services.phishing_report_pdf import generate_phishing_report

from ._shared import (
    _REPORTABLE_STATUSES,
    _get_owned,
    _require_status,
)

router = APIRouter()


@router.get("/campaigns/{campaign_id}/pdf")
@limiter.limit("10/minute")
async def download_report_pdf(
    request: Request,
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_owned(campaign_id, current_user.id, db)

    _require_status(
        campaign,
        _REPORTABLE_STATUSES,
        "Le rapport PDF n'est disponible que pour les campagnes actives ou terminées.",
    )

    targets = await campaigns.get_targets(campaign_id, db)

    # Rendu ReportLab déporté en thread : ne bloque plus l'event loop (une
    # campagne de 500 cibles gelait le worker pendant tout le rendu).
    pdf_bytes = await asyncio.to_thread(generate_phishing_report, campaign, targets)
    filename = f"rapport-phishing-{campaign_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
