"""
Endpoint public de vérification des attestations — aucune authentification requise.

GET /verify-certificate/{public_id}?token=...
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.awareness import CertificateVerifyOut
from app.services.awareness_certificate_service import verify_certificate

router = APIRouter(tags=["awareness-verify"])


@router.get("/verify-certificate/{public_id}", response_model=CertificateVerifyOut)
async def verify_certificate_endpoint(
    public_id: str,
    token: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
) -> CertificateVerifyOut:
    """
    Vérifie l'authenticité d'une attestation.
    Endpoint public — utilisé par les QR codes sur les certificats PDF.
    """
    result = await verify_certificate(db, public_id, token)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Attestation introuvable, révoquée ou expirée.",
        )
    return CertificateVerifyOut(**result)
