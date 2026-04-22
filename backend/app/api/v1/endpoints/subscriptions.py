from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.schemas.cyberscan import CheckoutSessionOut, SubscriptionOut
from app.services import stripe_service
from app.core.config import settings

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

FRONTEND_URL = settings.FRONTEND_URL
DEV_MODE = settings.APP_ENV == "development"


@router.get("/me", response_model=SubscriptionOut | None)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's active subscription."""
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == current_user.id, Subscription.status == "active")
    )
    return result.scalar_one_or_none()


@router.post("/checkout/{plan_id}", response_model=CheckoutSessionOut)
async def create_checkout(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session (or simulate it in dev mode)."""
    plan = await db.get(Plan, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")

    if DEV_MODE:
        # Simulate subscription activation without Stripe
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == current_user.id)
        )
        existing = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if existing:
            existing.plan_id = plan.id
            existing.status = "active"
            existing.current_period_start = now
            existing.current_period_end = now + timedelta(days=max(plan.scan_interval_days * 2, 30))
        else:
            db.add(Subscription(
                user_id=current_user.id,
                plan_id=plan.id,
                stripe_customer_id="dev_customer",
                stripe_subscription_id="dev_subscription",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=max(plan.scan_interval_days * 2, 30)),
            ))
        await db.commit()
        return {"checkout_url": f"{FRONTEND_URL}/cyberscan/success"}

    # Free plan: activate directly without Stripe
    if plan.price_cents == 0:
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == current_user.id)
        )
        existing = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if existing:
            existing.plan_id = plan.id
            existing.status = "active"
            existing.current_period_start = now
            existing.current_period_end = now + timedelta(days=365 * 10)
        else:
            db.add(Subscription(
                user_id=current_user.id,
                plan_id=plan.id,
                stripe_customer_id=None,
                stripe_subscription_id=None,
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=365 * 10),
            ))
        await db.commit()
        return {"checkout_url": f"{FRONTEND_URL}/cyberscan/dashboard"}

    # Production: real Stripe flow
    if not plan.stripe_price_id:
        raise HTTPException(status_code=400, detail="Plan not configured in Stripe yet")

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()
    if existing and existing.stripe_customer_id:
        customer_id = existing.stripe_customer_id
    else:
        customer_id = stripe_service.create_customer(current_user.email)

    checkout_url = stripe_service.create_checkout_session(
        customer_id=customer_id,
        price_id=plan.stripe_price_id,
        success_url=f"{FRONTEND_URL}/cyberscan/dashboard?subscribed=true",
        cancel_url=f"{FRONTEND_URL}/cyberscan?checkout=cancel",
    )
    return {"checkout_url": checkout_url}


@router.get("/portal", response_model=CheckoutSessionOut)
async def billing_portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redirect to Stripe Billing Portal (or dashboard in dev mode)."""
    if DEV_MODE:
        return {"checkout_url": f"{FRONTEND_URL}/cyberscan/dashboard"}

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
        )
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No active subscription found")

    portal_url = stripe_service.create_billing_portal_session(
        customer_id=sub.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/cyberscan/dashboard",
    )
    return {"checkout_url": portal_url}
