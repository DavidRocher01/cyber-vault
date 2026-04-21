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
from app.models.subscription import Subscription
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

    data = event["data"]["object"]

    if event["type"] == "checkout.session.completed":
        await _handle_checkout_completed(data, db)

    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        await _handle_subscription_updated(data, db)

    return {"status": "ok"}


async def _handle_checkout_completed(session: dict, db: AsyncSession) -> None:
    """Create or update Subscription after successful checkout."""
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

    await db.commit()


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
    await db.commit()
