"""
Admin quote endpoints.
POST /admin/quotes          — create a quote and email it to the client
GET  /admin/quotes          — list all quotes
GET  /admin/quotes/{id}/pdf — download PDF
"""

import asyncio
import secrets
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.quote import Quote
from app.models.user import User
from app.services.quote_pdf import generate_quote_pdf
from app.services.quote_service import create_quote, send_quote_by_email

router = APIRouter(prefix="/admin/quotes", tags=["admin"])


def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(
        x_admin_key, settings.ADMIN_API_KEY
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


class QuoteItem(BaseModel):
    description: str
    quantity: int = 1
    unit_price_cents: int

    @field_validator("quantity")
    @classmethod
    def qty_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity doit être ≥ 1")
        return v

    @field_validator("unit_price_cents")
    @classmethod
    def price_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("unit_price_cents doit être ≥ 0")
        return v


class QuoteCreateRequest(BaseModel):
    client_name: str
    client_email: EmailStr
    client_address: str | None = None
    subject: str
    items: list[QuoteItem]
    validity_days: int = 30
    user_email: str | None = None
    issue_date: date | None = None

    @field_validator("items")
    @classmethod
    def at_least_one_item(cls, v: list) -> list:
        if not v:
            raise ValueError("Le devis doit contenir au moins une ligne")
        return v


class QuoteOut(BaseModel):
    id: int
    quote_number: str
    client_name: str
    client_email: str
    client_address: str | None
    subject: str
    items: list[dict]
    total_cents: int
    total_eur: float
    validity_days: int
    status: str
    issue_date: str
    created_at: str

    model_config = {"from_attributes": True}


def _serialize(q: Quote) -> dict:
    return {
        "id": q.id,
        "quote_number": q.quote_number,
        "client_name": q.client_name,
        "client_email": q.client_email,
        "client_address": q.client_address,
        "subject": q.subject,
        "items": q.items,
        "total_cents": q.total_cents,
        "total_eur": q.total_cents / 100,
        "validity_days": q.validity_days,
        "status": q.status,
        "issue_date": q.issue_date.isoformat(),
        "created_at": q.created_at.isoformat(),
    }


@router.post(
    "", dependencies=[Depends(_require_admin)], status_code=201, summary="[Admin] Créer un devis"
)
async def admin_create_quote(
    body: QuoteCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user_id: int | None = None
    if body.user_email:
        result = await db.execute(select(User).where(User.email == body.user_email))
        user = result.scalar_one_or_none()
        if user:
            user_id = user.id

    quote = await create_quote(
        db,
        user_id=user_id,
        client_name=body.client_name,
        client_email=body.client_email,
        client_address=body.client_address,
        subject=body.subject,
        items=[item.model_dump() for item in body.items],
        validity_days=body.validity_days,
        issue_date=body.issue_date,
    )
    await db.commit()
    await db.refresh(quote)

    background_tasks.add_task(send_quote_by_email, quote)

    return _serialize(quote)


@router.get("", dependencies=[Depends(_require_admin)], summary="[Admin] Lister les devis")
async def admin_list_quotes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quote).order_by(Quote.created_at.desc()))
    return [_serialize(q) for q in result.scalars().all()]


@router.get(
    "/{quote_id}/pdf",
    dependencies=[Depends(_require_admin)],
    summary="[Admin] Télécharger le devis (PDF)",
)
async def admin_download_quote_pdf(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Quote).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")

    pdf = await asyncio.to_thread(
        generate_quote_pdf,
        quote_number=quote.quote_number,
        issue_date=quote.issue_date,
        validity_days=quote.validity_days,
        client_name=quote.client_name,
        client_email=quote.client_email,
        client_address=quote.client_address,
        subject=quote.subject,
        items=quote.items,
        total_cents=quote.total_cents,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.quote_number}.pdf"'},
    )
