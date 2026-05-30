from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.cyberscan import CheckoutSessionOut, SubscriptionOut
from app.services import stripe_service

ADDON_EXTRA_SITES_COUNT = settings.ADDON_EXTRA_SITES_COUNT
ADDON_EXTRA_SITES_PRICE_EUR = settings.ADDON_EXTRA_SITES_PRICE_EUR

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
        now = datetime.now(UTC)
        if existing:
            existing.plan_id = plan.id
            existing.status = "active"
            existing.current_period_start = now
            existing.current_period_end = now + timedelta(days=max(plan.scan_interval_days * 2, 30))
        else:
            db.add(
                Subscription(
                    user_id=current_user.id,
                    plan_id=plan.id,
                    stripe_customer_id="dev_customer",
                    stripe_subscription_id="dev_subscription",
                    status="active",
                    current_period_start=now,
                    current_period_end=now + timedelta(days=max(plan.scan_interval_days * 2, 30)),
                )
            )
        await db.commit()
        return {"checkout_url": f"{FRONTEND_URL}/cyberscan/success"}

    # Free plan: activate directly without Stripe
    if plan.price_eur == 0:
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == current_user.id)
        )
        existing = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if existing:
            existing.plan_id = plan.id
            existing.status = "active"
            existing.current_period_start = now
            existing.current_period_end = now + timedelta(days=365 * 10)
        else:
            db.add(
                Subscription(
                    user_id=current_user.id,
                    plan_id=plan.id,
                    stripe_customer_id=None,
                    stripe_subscription_id=None,
                    status="active",
                    current_period_start=now,
                    current_period_end=now + timedelta(days=365 * 10),
                )
            )
        await db.commit()
        return {"checkout_url": f"{FRONTEND_URL}/cyberscan/dashboard"}

    # Production: real Stripe flow
    if not plan.stripe_price_id:
        raise HTTPException(status_code=400, detail="Plan not configured in Stripe yet")

    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
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


@router.get("/addons/extra-sites")
async def get_extra_sites_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current extra-sites count and add-on pricing."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id, Subscription.status == "active"
        )
    )
    sub = result.scalar_one_or_none()
    return {
        "extra_sites": sub.extra_sites if sub else 0,
        "pack_size": ADDON_EXTRA_SITES_COUNT,
        "pack_price_eur": ADDON_EXTRA_SITES_PRICE_EUR,
    }


@router.post("/addons/extra-sites/checkout", response_model=CheckoutSessionOut)
async def purchase_extra_sites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Purchase an extra-sites pack (+5 site slots)."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id, Subscription.status == "active"
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=403, detail="Abonnement actif requis")

    if DEV_MODE:
        sub.extra_sites += ADDON_EXTRA_SITES_COUNT
        await db.commit()
        return {"checkout_url": f"{FRONTEND_URL}/cyberscan/dashboard?addon=extra_sites"}

    price_id = settings.ADDON_EXTRA_SITES_STRIPE_PRICE_ID
    if not price_id:
        raise HTTPException(status_code=400, detail="Add-on non configuré")

    checkout_url = stripe_service.create_checkout_session(
        customer_id=sub.stripe_customer_id,
        price_id=price_id,
        success_url=f"{FRONTEND_URL}/cyberscan/dashboard?addon=extra_sites",
        cancel_url=f"{FRONTEND_URL}/cyberscan/dashboard",
        metadata={"addon_type": "extra_sites", "user_id": str(current_user.id)},
    )
    return {"checkout_url": checkout_url}
