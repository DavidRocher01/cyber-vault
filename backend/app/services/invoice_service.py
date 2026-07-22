"""
Invoice service — sequential numbering and creation.
Format: FACT-YYYY-NNNN (per-year sequence, zero-padded to 4 digits).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice


async def _next_seq(db: AsyncSession, year: int) -> int:
    result = await db.execute(
        select(func.max(Invoice.invoice_seq)).where(Invoice.invoice_year == year)
    )
    current_max = result.scalar()
    return (current_max or 0) + 1


async def create_invoice(
    db: AsyncSession,
    *,
    user_id: int | None,
    type: str,
    client_name: str,
    client_email: str,
    client_address: str | None,
    description: str,
    amount_cents: int,
    status: str = "paid",
    stripe_invoice_id: str | None = None,
    issue_date: date | None = None,
) -> Invoice:
    today = issue_date or datetime.now(UTC).date()
    year = today.year
    seq = await _next_seq(db, year)
    invoice_number = f"FACT-{year}-{seq:04d}"

    invoice = Invoice(
        invoice_number=invoice_number,
        invoice_seq=seq,
        invoice_year=year,
        user_id=user_id,
        type=type,
        client_name=client_name,
        client_email=client_email,
        client_address=client_address,
        description=description,
        amount_cents=amount_cents,
        status=status,
        stripe_invoice_id=stripe_invoice_id,
        issue_date=today,
    )
    db.add(invoice)
    await db.flush()  # populate id without committing
    return invoice


async def list_user_invoices(
    db: AsyncSession, user_id: int, *, offset: int, limit: int
) -> tuple[int, list[Invoice]]:
    """Total + page des factures d'un utilisateur (anti-chronologique)."""
    total = (
        await db.execute(
            select(func.count()).select_from(Invoice).where(Invoice.user_id == user_id)
        )
    ).scalar_one()
    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == user_id)
        .order_by(Invoice.issue_date.desc(), Invoice.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return total, list(result.scalars().all())


async def get_owned_invoice(db: AsyncSession, invoice_id: int, user_id: int) -> Invoice | None:
    """Facture appartenant a l'utilisateur, ou None."""
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user_id)
    )
    return result.scalar_one_or_none()
