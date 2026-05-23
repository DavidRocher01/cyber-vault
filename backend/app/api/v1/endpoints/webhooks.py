"""
Stripe webhook handler.
Listens for subscription lifecycle events and updates DB accordingly.
"""

from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.plan import Plan
from app.models.processed_stripe_event import ProcessedStripeEvent
from app.models.subscription import Subscription
from app.services.invoice_service import create_invoice
from app.services.stripe_service import construct_webhook_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_id = event["id"]
    existing = await db.execute(
        select(ProcessedStripeEvent).where(ProcessedStripeEvent.stripe_event_id == event_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "ok"}

    data = event["data"]["object"]

    if event["type"] == "checkout.session.completed":
        await _handle_checkout_completed(data, db)

    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        await _handle_subscription_updated(data, db)

    elif event["type"] == "invoice.payment_succeeded":
        await _handle_invoice_payment_succeeded(data, db)

    db.add(ProcessedStripeEvent(stripe_event_id=event_id))
    await db.commit()
    return {"status": "ok"}


async def _handle_checkout_completed(session: dict, db: AsyncSession) -> None:
    """Create or update Subscription after successful checkout."""
    metadata = session.get("metadata") or {}

    # ── Add-on: extra site slots ──────────────────────────────────────────────
    if metadata.get("addon_type") == "extra_sites":
        user_id = metadata.get("user_id")
        if user_id:
            from app.core.config import settings
            result = await db.execute(
                select(Subscription).where(
                    Subscription.user_id == int(user_id),
                    Subscription.status == "active",
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.extra_sites += settings.ADDON_EXTRA_SITES_COUNT
        return

    customer_id      = session.get("customer")
    subscription_id  = session.get("subscription")
    customer_email   = session.get("customer_details", {}).get("email")

    if not customer_id or not subscription_id:
        return

    # Retrieve full subscription to get price_id and period
    stripe_sub = stripe.Subscription.retrieve(subscription_id)
    price_id   = stripe_sub["items"]["data"][0]["price"]["id"]

    # Find matching plan
    result = await db.execute(select(Plan).where(Plan.stripe_price_id == price_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return

    # Find user by email
    from app.models.user import User
    user_result = await db.execute(select(User).where(User.email == customer_email))
    user = user_result.scalar_one_or_none()
    if not user:
        return

    # Upsert subscription
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = sub_result.scalar_one_or_none()

    period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=timezone.utc)
    period_end   = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)

    if sub:
        sub.plan_id                 = plan.id
        sub.stripe_customer_id      = customer_id
        sub.stripe_subscription_id  = subscription_id
        sub.status                  = "active"
        sub.current_period_start    = period_start
        sub.current_period_end      = period_end
    else:
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            status="active",
            current_period_start=period_start,
            current_period_end=period_end,
        )
        db.add(sub)


async def _handle_subscription_updated(stripe_sub: dict, db: AsyncSession) -> None:
    """Sync subscription status changes (canceled, past_due…)."""
    subscription_id = stripe_sub.get("id")
    if not subscription_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.status = stripe_sub.get("status", sub.status)
    if stripe_sub.get("current_period_end"):
        sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)


async def _handle_invoice_payment_succeeded(stripe_inv: dict, db: AsyncSession) -> None:
    """Auto-create a subscription invoice when Stripe confirms payment."""
    stripe_invoice_id = stripe_inv.get("id")
    customer_email    = stripe_inv.get("customer_email") or (
        stripe_inv.get("customer_details") or {}
    ).get("email")
    amount_paid       = stripe_inv.get("amount_paid", 0)  # cents

    if not stripe_invoice_id or not customer_email or amount_paid <= 0:
        return

    # Avoid duplicate invoices for the same Stripe invoice ID
    from app.models.invoice import Invoice
    existing = await db.execute(
        select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
    )
    if existing.scalar_one_or_none():
        return

    # Resolve user
    from app.models.user import User
    user_result = await db.execute(select(User).where(User.email == customer_email))
    user = user_result.scalar_one_or_none()

    # Build description from Stripe line items if available
    lines = stripe_inv.get("lines", {}).get("data", [])
    description = lines[0].get("description", "Abonnement CyberScan") if lines else "Abonnement CyberScan"

    invoice_date = datetime.fromtimestamp(
        stripe_inv.get("created", datetime.now(timezone.utc).timestamp()), tz=timezone.utc
    ).date()

    await create_invoice(
        db,
        user_id=user.id if user else None,
        type="subscription",
        client_name=stripe_inv.get("customer_name") or (user.email if user else customer_email),
        client_email=customer_email,
        client_address=None,
        description=description,
        amount_cents=amount_paid,
        status="paid",
        stripe_invoice_id=stripe_invoice_id,
        issue_date=invoice_date,
    )
