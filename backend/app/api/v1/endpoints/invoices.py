"""
User invoice endpoints.
GET /invoices          — list authenticated user's invoices (paginated)
GET /invoices/{id}     — get invoice detail
GET /invoices/{id}/pdf — download PDF
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.invoice import Invoice
from app.models.user import User
from app.services.invoice_pdf import generate_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("")
async def list_invoices(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    total_result = await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.user_id == current_user.id)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == current_user.id)
        .order_by(Invoice.issue_date.desc(), Invoice.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    invoices = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
        "items": [_serialize(inv) for inv in invoices],
    }


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_owned(invoice_id, current_user.id, db)
    return _serialize(inv)


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_owned(invoice_id, current_user.id, db)
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


async def _get_owned(invoice_id: int, user_id: int, db: AsyncSession) -> Invoice:
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    return inv


def _serialize(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "type": inv.type,
        "client_name": inv.client_name,
        "client_email": inv.client_email,
        "client_address": inv.client_address,
        "description": inv.description,
        "amount_cents": inv.amount_cents,
        "amount_eur": inv.amount_cents / 100,
        "status": inv.status,
        "issue_date": inv.issue_date.isoformat(),
        "created_at": inv.created_at.isoformat(),
    }
