"""
NIS2 Compliance endpoints — save/load user assessment and export PDF.
"""

import asyncio
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_conformity_export
from app.models.user import User
from app.services import awareness_nis2_report, brand_service, nis2_service
from app.services.assessment_service import compute_assessment_score
from app.services.nis2_catalogue import ALL_ITEM_IDS, NIS2_CATEGORIES, VALID_STATUSES

router = APIRouter(prefix="/nis2", tags=["nis2"])

# Le catalogue des criteres vit dans `app/services/nis2_catalogue.py`. Ce
# routeur n'en est qu'un consommateur parmi d'autres : les deux generateurs de
# PDF le lisent aussi, et le rattachement de preuves aux criteres le lira.


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class Nis2SaveIn(BaseModel):
    items: dict[str, str]  # { item_id: status }


class Nis2Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: dict[str, str]
    score: int
    updated_at: datetime | None
    categories: list  # static definition returned for convenience
    # Mesures objectives detenues par la plateforme pour certains items.
    # Ne repond PAS a la place de l'utilisateur : une auto-evaluation remplie
    # automatiquement n'est plus une declaration et perd sa valeur devant un
    # auditeur. On fournit la mesure, il declare.
    preuves: dict = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/me", response_model=Nis2Out)
async def get_assessment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    items = json.loads(assessment.items_json) if assessment else {}
    score = assessment.score if assessment else 0
    updated_at = assessment.updated_at if assessment else None
    preuves: dict = {}
    formation = await awareness_nis2_report.preuve_formation(db, current_user.id)
    if formation:
        preuves["awareness"] = formation

    return {
        "items": items,
        "score": score,
        "updated_at": updated_at,
        "categories": NIS2_CATEGORIES,
        "preuves": preuves,
    }


@router.put("/me", response_model=Nis2Out)
async def save_assessment(
    payload: Nis2SaveIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate statuses
    for item_id, status in payload.items.items():
        if item_id not in ALL_ITEM_IDS:
            raise HTTPException(status_code=422, detail=f"Identifiant inconnu : {item_id}")
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Statut invalide : {status}")

    score = compute_assessment_score(payload.items, ALL_ITEM_IDS)
    now = datetime.now(UTC)

    assessment = await nis2_service.upsert_assessment(
        db, current_user.id, items=payload.items, score=score, now=now
    )

    # Meme calcul que sur le GET : sans cela, les mesures disparaitraient de
    # l'ecran juste apres un enregistrement.
    preuves: dict = {}
    formation = await awareness_nis2_report.preuve_formation(db, current_user.id)
    if formation:
        preuves["awareness"] = formation

    return {
        "items": payload.items,
        "score": score,
        "updated_at": assessment.updated_at,
        "categories": NIS2_CATEGORIES,
        "preuves": preuves,
    }


@router.get("/me/pdf", dependencies=[Depends(require_conformity_export)])
async def export_assessment_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a NIS2 compliance report PDF."""
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    items = json.loads(assessment.items_json) if assessment else {}
    score = compute_assessment_score(
        items, ALL_ITEM_IDS
    )  # recalcul avec la formule corrigée (34 items)
    updated_at = assessment.updated_at if assessment else None

    from app.services.nis2_pdf import generate_nis2_pdf

    pdf_bytes = await asyncio.to_thread(
        generate_nis2_pdf,
        categories=NIS2_CATEGORIES,
        items=items,
        score=score,
        updated_at=updated_at,
        user_email=current_user.email,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rochercybersecurite_nis2_conformite.pdf"'
        },
    )


@router.get("/me/pdf/auditor", dependencies=[Depends(require_conformity_export)])
async def export_auditor_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a formal NIS2 'prêt-à-déposer' document for certified auditor review."""
    assessment = await nis2_service.get_user_assessment(db, current_user.id)
    items = json.loads(assessment.items_json) if assessment else {}
    score = compute_assessment_score(items, ALL_ITEM_IDS)
    updated_at = assessment.updated_at if assessment else None

    # Try to get company name from brand profile
    brand = await brand_service.get_brand_profile(db, current_user.id)
    company_name = brand.company_name if brand else ""

    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    pdf_bytes = await asyncio.to_thread(
        generate_nis2_auditor_pdf,
        categories=NIS2_CATEGORIES,
        items=items,
        score=score,
        user_email=current_user.email,
        updated_at=updated_at,
        company_name=company_name,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rochercybersecurite_nis2_pret_a_deposer.pdf"'
        },
    )
