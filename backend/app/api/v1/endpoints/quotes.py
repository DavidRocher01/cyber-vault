"""
Public quote acceptance endpoints.
POST /quotes/{token}/accept  — client accepts the quote
POST /quotes/{token}/reject  — client rejects the quote
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.quote import Quote

router = APIRouter(prefix="/quotes", tags=["quotes"])


async def _get_quote_by_token(token: str, db: AsyncSession) -> Quote:
    result = await db.execute(select(Quote).where(Quote.acceptance_token == token))
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    return quote


@router.post("/{token}/accept")
async def accept_quote(token: str, db: AsyncSession = Depends(get_db)):
    quote = await _get_quote_by_token(token, db)

    if quote.status == "accepted":
        return {"status": "accepted", "quote_number": quote.quote_number, "already": True}

    if quote.status in ("rejected", "expired"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ce devis est déjà {quote.status}",
        )

    quote.status = "accepted"
    quote.accepted_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "accepted", "quote_number": quote.quote_number, "already": False}


@router.post("/{token}/reject")
async def reject_quote(token: str, db: AsyncSession = Depends(get_db)):
    quote = await _get_quote_by_token(token, db)

    if quote.status == "rejected":
        return {"status": "rejected", "quote_number": quote.quote_number, "already": True}

    if quote.status in ("accepted", "expired"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ce devis est déjà {quote.status}",
        )

    quote.status = "rejected"
    quote.rejected_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "rejected", "quote_number": quote.quote_number, "already": False}
