"""Module PCA Light — generates a mini Business Continuity Plan PDF."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.core.deps import get_current_user
from app.models.user import User
from app.services.pca_pdf import generate_pca_pdf

router = APIRouter(prefix="/pca", tags=["pca"])


class PcaCompany(BaseModel):
    name: str
    sector: str = ""
    contact: str = ""
    email: str = ""
    phone: str = ""


class PcaSystem(BaseModel):
    name: str
    description: str = ""
    rto_hours: int = 4
    rpo_hours: int = 1
    responsible: str = ""


class PcaTeamMember(BaseModel):
    name: str
    role: str = ""
    phone: str = ""
    email: str = ""


class PcaRequest(BaseModel):
    company: PcaCompany
    critical_systems: list[PcaSystem] = []
    response_team: list[PcaTeamMember] = []
    communication_plan: str = ""


@router.post("/generate")
async def generate_pca(
    payload: PcaRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a PCA Light PDF from the wizard data."""
    data = payload.model_dump()
    pdf_bytes = generate_pca_pdf(data)
    filename = f"pca_{payload.company.name.replace(' ', '_').lower()}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
