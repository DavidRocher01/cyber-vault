"""
Public quote acceptance endpoints.
POST /quotes/{token}/accept  — client accepts the quote
POST /quotes/{token}/reject  — client rejects the quote
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.quote import Quote
from app.services import quote_service

router = APIRouter(prefix="/quotes", tags=["quotes"])


async def _get_quote_or_404(token: str, db: AsyncSession) -> Quote:
    quote = await quote_service.get_quote_by_token(db, token)
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    return quote


@router.post("/{token}/accept")
async def accept_quote(token: str, db: AsyncSession = Depends(get_db)):
    quote = await _get_quote_or_404(token, db)

    if quote.status == "accepted":
        return {"status": "accepted", "quote_number": quote.quote_number, "already": True}

    if quote.status in ("rejected", "expired"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ce devis est déjà {quote.status}",
        )

    await quote_service.mark_quote_accepted(db, quote)
    return {"status": "accepted", "quote_number": quote.quote_number, "already": False}


@router.post("/{token}/reject")
async def reject_quote(token: str, db: AsyncSession = Depends(get_db)):
    quote = await _get_quote_or_404(token, db)

    if quote.status == "rejected":
        return {"status": "rejected", "quote_number": quote.quote_number, "already": True}

    if quote.status in ("accepted", "expired"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ce devis est déjà {quote.status}",
        )

    await quote_service.mark_quote_rejected(db, quote)
    return {"status": "rejected", "quote_number": quote.quote_number, "already": False}
