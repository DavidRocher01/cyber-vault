"""
Admin invoice endpoints.
POST /admin/invoices        — manually create an invoice (audit type)
GET  /admin/invoices        — list all invoices
GET  /admin/invoices/{id}   — get invoice detail
GET  /admin/invoices/{id}/pdf — download PDF
"""

import asyncio
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.invoice import Invoice
from app.services import invoice_service, user_admin_service
from app.services.invoice_pdf import generate_invoice_pdf
from app.services.invoice_service import create_invoice

router = APIRouter(prefix="/admin/invoices", tags=["admin"])


class InvoiceCreateRequest(BaseModel):
    client_name: str
    client_email: EmailStr
    client_address: str | None = None
    description: str
    amount_cents: int
    user_email: str | None = None  # link to existing user account (optional)
    issue_date: date | None = None


@router.post(
    "", dependencies=[Depends(require_admin)], status_code=201, summary="[Admin] Créer une facture"
)
async def admin_create_invoice(
    body: InvoiceCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id: int | None = None
    if body.user_email:
        user = await user_admin_service.get_user_by_email(db, body.user_email)
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
        commit=True,
    )
    return _serialize(invoice)


@router.get("", dependencies=[Depends(require_admin)], summary="[Admin] Lister les factures")
async def admin_list_invoices(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    invoices = await invoice_service.list_all_invoices(db, limit=limit, offset=offset)
    return [_serialize(inv) for inv in invoices]


@router.get(
    "/{invoice_id}", dependencies=[Depends(require_admin)], summary="[Admin] Détail d'une facture"
)
async def admin_get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_by_id(invoice_id, db)
    return _serialize(inv)


@router.get(
    "/{invoice_id}/pdf",
    dependencies=[Depends(require_admin)],
    summary="[Admin] Télécharger la facture (PDF)",
)
async def admin_download_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_by_id(invoice_id, db)
    pdf_bytes = await asyncio.to_thread(
        generate_invoice_pdf,
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
    inv = await invoice_service.get_invoice_by_id(db, invoice_id)
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
