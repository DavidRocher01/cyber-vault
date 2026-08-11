import asyncio
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.cyberscan import CheckoutSessionOut, SubscriptionOut
from app.schemas.divers import ExtraSitesInfoOut
from app.services import plan_service, stripe_service, subscription_service

ADDON_EXTRA_SITES_COUNT = settings.ADDON_EXTRA_SITES_COUNT
ADDON_EXTRA_SITES_PRICE_EUR = settings.ADDON_EXTRA_SITES_PRICE_EUR

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

FRONTEND_URL = settings.FRONTEND_URL
# DEV_MODE allows checkout simulation without Stripe — forbidden in production.
DEV_MODE = (
    settings.APP_ENV == "development" and "rochercybersecurite.com" not in settings.FRONTEND_URL
)

if settings.APP_ENV == "development" and "rochercybersecurite.com" in settings.FRONTEND_URL:
    import logging as _logging

    _logging.getLogger(__name__).critical(
        "DEV_MODE blocked: APP_ENV=development detected against production FRONTEND_URL. "
        "Set APP_ENV=production in ECS environment variables."
    )
    raise RuntimeError("DEV_MODE forbidden in production environment")


@router.get("/me", response_model=SubscriptionOut | None)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's active subscription."""
    return await subscription_service.get_active_subscription_with_plan(db, current_user.id)


@router.post("/checkout/{plan_id}", response_model=CheckoutSessionOut)
async def create_checkout(
    plan_id: int,
    interval: Literal["monthly", "yearly"] = "monthly",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session (or simulate it in dev mode).

    `interval` selects monthly (default) or yearly billing (2 months free).
    The interval is materialised entirely by which Stripe price_id is used.
    """
    plan = await plan_service.get_plan(db, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")

    if DEV_MODE:
        # Simulate subscription activation without Stripe
        now = datetime.now(UTC)
        await subscription_service.upsert_active_subscription(
            db,
            user_id=current_user.id,
            plan_id=plan.id,
            now=now,
            period_end=now + timedelta(days=max(plan.scan_interval_days * 2, 30)),
            stripe_customer_id="dev_customer",
            stripe_subscription_id="dev_subscription",
        )
        return {"checkout_url": f"{FRONTEND_URL}/success"}

    # Free plan: activate directly without Stripe
    if plan.price_eur == 0:
        now = datetime.now(UTC)
        await subscription_service.upsert_active_subscription(
            db,
            user_id=current_user.id,
            plan_id=plan.id,
            now=now,
            period_end=now + timedelta(days=365 * 10),
            stripe_customer_id=None,
            stripe_subscription_id=None,
        )
        return {"checkout_url": f"{FRONTEND_URL}/dashboard"}

    # Production: real Stripe flow. Le price_id porte l'intervalle de facturation.
    annuel = interval == "yearly"
    price_id = plan.stripe_price_id_yearly if annuel else plan.stripe_price_id
    montant_attendu = plan.price_eur_yearly if annuel else plan.price_eur
    intervalle_attendu = "year" if annuel else "month"
    if not price_id:
        detail = (
            "Yearly billing not configured for this plan yet"
            if interval == "yearly"
            else "Plan not configured in Stripe yet"
        )
        raise HTTPException(status_code=400, detail=detail)

    existing = await subscription_service.get_subscription(db, current_user.id)
    if existing and existing.stripe_customer_id:
        customer_id = existing.stripe_customer_id
    else:
        customer_id = await asyncio.to_thread(stripe_service.create_customer, current_user.email)

    # Appels Stripe synchrones déportés en thread (ne pas bloquer l'event loop).
    checkout_url = await asyncio.to_thread(
        stripe_service.create_checkout_session,
        customer_id=customer_id,
        price_id=price_id,
        success_url=f"{FRONTEND_URL}/dashboard?subscribed=true",
        cancel_url=f"{FRONTEND_URL}/?checkout=cancel",
        montant_attendu=montant_attendu,
        intervalle_attendu=intervalle_attendu,
    )
    return {"checkout_url": checkout_url}


@router.get("/portal", response_model=CheckoutSessionOut)
async def billing_portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redirect to Stripe Billing Portal (or dashboard in dev mode)."""
    if DEV_MODE:
        return {"checkout_url": f"{FRONTEND_URL}/dashboard"}

    sub = await subscription_service.get_active_subscription(db, current_user.id)
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No active subscription found")

    portal_url = await asyncio.to_thread(
        stripe_service.create_billing_portal_session,
        customer_id=sub.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/dashboard",
    )
    return {"checkout_url": portal_url}


@router.get("/addons/extra-sites", response_model=ExtraSitesInfoOut)
async def get_extra_sites_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current extra-sites count and add-on pricing."""
    sub = await subscription_service.get_active_subscription(db, current_user.id)
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
    sub = await subscription_service.get_active_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=403, detail="Abonnement actif requis")

    if DEV_MODE:
        await subscription_service.add_extra_sites(db, sub, ADDON_EXTRA_SITES_COUNT)
        return {"checkout_url": f"{FRONTEND_URL}/dashboard?addon=extra_sites"}

    price_id = settings.ADDON_EXTRA_SITES_STRIPE_PRICE_ID
    if not price_id:
        raise HTTPException(status_code=400, detail="Add-on non configuré")

    checkout_url = await asyncio.to_thread(
        stripe_service.create_checkout_session,
        customer_id=sub.stripe_customer_id,
        price_id=price_id,
        success_url=f"{FRONTEND_URL}/dashboard?addon=extra_sites",
        cancel_url=f"{FRONTEND_URL}/dashboard",
        montant_attendu=ADDON_EXTRA_SITES_PRICE_EUR,
        intervalle_attendu="month",
        metadata={"addon_type": "extra_sites", "user_id": str(current_user.id)},
    )
    return {"checkout_url": checkout_url}
