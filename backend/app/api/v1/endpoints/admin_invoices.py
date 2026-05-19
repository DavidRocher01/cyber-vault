"""
Admin invoice endpoints.
POST /admin/invoices        — manually create an invoice (audit type)
GET  /admin/invoices        — list all invoices
GET  /admin/invoices/{id}   — get invoice detail
GET  /admin/invoices/{id}/pdf — download PDF
"""
import secrets
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.services.invoice_pdf import generate_invoice_pdf
from app.services.invoice_service import create_invoice

router = APIRouter(prefix="/admin/invoices", tags=["admin"])


def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


class InvoiceCreateRequest(BaseModel):
    client_name: str
    client_email: EmailStr
    client_address: str | None = None
    description: str
    amount_cents: int
    user_email: str | None = None  # link to existing user account (optional)
    issue_date: date | None = None


@router.post("", dependencies=[Depends(_require_admin)], status_code=201)
async def admin_create_invoice(
    body: InvoiceCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id: int | None = None
    if body.user_email:
        result = await db.execute(select(User).where(User.email == body.user_email))
        user = result.scalar_one_or_none()
        if user:
            user_id = user.id

    invoice = await create_invoice(
        db,
        user_id=user_id,
        type="audit",
        client_name=body.client_name,
        client_email=body.client_email,
        client_address=body.client_address,
        description=body.description,
        amount_cents=body.amount_cents,
        status="paid",
        issue_date=body.issue_date,
    )
    await db.commit()
    await db.refresh(invoice)
    return _serialize(invoice)


@router.get("", dependencies=[Depends(_require_admin)])
async def admin_list_invoices(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice)
        .order_by(Invoice.issue_date.desc(), Invoice.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_serialize(inv) for inv in result.scalars().all()]


@router.get("/{invoice_id}", dependencies=[Depends(_require_admin)])
async def admin_get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_by_id(invoice_id, db)
    return _serialize(inv)


@router.get("/{invoice_id}/pdf", dependencies=[Depends(_require_admin)])
async def admin_download_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_by_id(invoice_id, db)
    pdf_bytes = generate_invoice_pdf(
        invoice_number=inv.invoice_number,
        issue_date=inv.issue_date,
        client_name=inv.client_name,
        client_email=inv.client_email,
        client_address=inv.client_address,
        description=inv.description,
        amount_cents=inv.amount_cents,
    )
    filename = f"{inv.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _get_by_id(invoice_id: int, db: AsyncSession) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    return inv


def _serialize(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "type": inv.type,
        "user_id": inv.user_id,
        "client_name": inv.client_name,
        "client_email": inv.client_email,
        "client_address": inv.client_address,
        "description": inv.description,
        "amount_cents": inv.amount_cents,
        "amount_eur": inv.amount_cents / 100,
        "status": inv.status,
        "stripe_invoice_id": inv.stripe_invoice_id,
        "issue_date": inv.issue_date.isoformat(),
        "created_at": inv.created_at.isoformat(),
    }
