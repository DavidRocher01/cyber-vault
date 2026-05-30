"""
Quote service — sequential numbering, creation, and email dispatch.
Format: DEVIS-YYYY-NNNN (per-year sequence, zero-padded to 4 digits).
"""

from __future__ import annotations

import base64
import os
import secrets
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote
from app.services.quote_pdf import generate_quote_pdf

BASE_URL = os.getenv("APP_BASE_URL", "https://cyberscanapp.com")


async def _next_seq(db: AsyncSession, year: int) -> int:
    result = await db.execute(select(func.max(Quote.quote_seq)).where(Quote.quote_year == year))
    return (result.scalar() or 0) + 1


async def create_quote(
    db: AsyncSession,
    *,
    user_id: int | None,
    client_name: str,
    client_email: str,
    client_address: str | None,
    subject: str,
    items: list[dict],
    validity_days: int = 30,
    issue_date: date | None = None,
) -> Quote:
    today = issue_date or datetime.now(UTC).date()
    year = today.year
    seq = await _next_seq(db, year)

    total_cents = sum(item.get("quantity", 1) * item.get("unit_price_cents", 0) for item in items)

    quote = Quote(
        quote_number=f"DEVIS-{year}-{seq:04d}",
        quote_seq=seq,
        quote_year=year,
        user_id=user_id,
        client_name=client_name,
        client_email=client_email,
        client_address=client_address,
        subject=subject,
        items=items,
        total_cents=total_cents,
        validity_days=validity_days,
        status="sent",
        issue_date=today,
        acceptance_token=secrets.token_urlsafe(32),
    )
    db.add(quote)
    await db.flush()
    return quote


async def send_quote_by_email(quote: Quote) -> None:
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        return

    pdf_bytes = generate_quote_pdf(
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
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    expiry = quote.issue_date + timedelta(days=quote.validity_days)
    total_eur = f"{quote.total_cents / 100:,.2f} €".replace(",", " ")
    expiry_str = expiry.strftime("%d/%m/%Y")
    token = quote.acceptance_token or ""
    accept_url = f"{BASE_URL}/cyberscan/devis/{token}/accepter"
    reject_url = f"{BASE_URL}/cyberscan/devis/{token}/refuser"

    html = (
        '<div style="font-family:sans-serif;max-width:600px;color:#1e293b">'
        '<div style="background:#0f172a;padding:20px 24px;border-radius:12px 12px 0 0">'
        '<span style="color:#fff;font-size:20px;font-weight:700">CyberScan</span>'
        '<span style="color:#06b6d4;font-size:24px;margin-left:4px">&#9679;</span>'
        "</div>"
        '<div style="border:1px solid #e2e8f0;border-top:none;padding:28px 24px;border-radius:0 0 12px 12px">'
        f"<p>Bonjour <strong>{quote.client_name}</strong>,</p>"
        f"<p>Veuillez trouver ci-joint votre devis <strong>{quote.quote_number}</strong>"
        " pour la prestation suivante :</p>"
        '<div style="background:#f1f5f9;border-left:3px solid #06b6d4;padding:12px 16px;'
        'border-radius:6px;margin:16px 0">'
        f"<strong>{quote.subject}</strong><br>"
        f'<span style="color:#64748b;font-size:14px">Montant : {total_eur} HT<br>'
        f"Valable jusqu'au : {expiry_str}</span>"
        "</div>"
        "<p>Vous pouvez répondre directement à ce devis :</p>"
        '<div style="margin:20px 0">'
        f'<a href="{accept_url}" style="display:inline-block;background:#06b6d4;color:#fff;'
        'font-weight:700;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:15px">'
        "&#10003; Accepter le devis</a>"
        f'<a href="{reject_url}" style="display:inline-block;background:#e2e8f0;color:#64748b;'
        "font-weight:600;padding:12px 28px;border-radius:8px;text-decoration:none;"
        'font-size:15px;margin-left:12px">Refuser</a>'
        "</div>"
        '<p style="color:#64748b;font-size:13px">TVA non applicable, art. 293 B du CGI.</p>'
        "<p>Cordialement,<br><strong>David Rocher</strong><br>"
        'CyberScan — <a href="https://cyberscanapp.com" style="color:#06b6d4">cyberscanapp.com</a></p>'
        "</div></div>"
    )

    payload = {
        "from": "CyberScan <contact@cyberscanapp.com>",
        "to": [quote.client_email],
        "subject": f"Devis {quote.quote_number} — {quote.subject}",
        "html": html,
        "attachments": [
            {
                "filename": f"{quote.quote_number}.pdf",
                "content": pdf_b64,
            }
        ],
    }

    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
