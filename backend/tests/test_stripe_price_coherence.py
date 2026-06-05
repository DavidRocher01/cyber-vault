"""
G2 — Test cohérence prix Stripe ↔ DB.
Vérifie que chaque plan actif avec un stripe_price_id a le même montant en DB et sur Stripe.
Skipped si STRIPE_SECRET_KEY n'est pas disponible (CI sans secrets Stripe).
"""

import os

import pytest
import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.plan import Plan

pytestmark = pytest.mark.skipif(
    not os.getenv("STRIPE_SECRET_KEY"),
    reason="STRIPE_SECRET_KEY not set — skipping Stripe coherence check",
)


@pytest.mark.asyncio
async def test_plan_prices_match_stripe(pg_url):
    """Every active plan with a stripe_price_id must match Stripe's unit_amount."""
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    engine = create_async_engine(pg_url, echo=False)
    AsyncTestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncTestSession() as session:
        result = await session.execute(
            select(Plan).where(
                Plan.is_active == True,  # noqa: E712
                Plan.stripe_price_id != "",
            )
        )
        plans = result.scalars().all()

    await engine.dispose()

    if not plans:
        pytest.skip("No active plans with stripe_price_id in DB — seed DB first")

    mismatches = []
    for plan in plans:
        stripe_price = stripe.Price.retrieve(plan.stripe_price_id)
        if stripe_price.unit_amount != plan.price_eur:
            mismatches.append(
                f"{plan.name}: DB={plan.price_eur}c vs Stripe={stripe_price.unit_amount}c"
            )
        if stripe_price.tax_behavior != "exclusive":
            mismatches.append(
                f"{plan.name}: tax_behavior={stripe_price.tax_behavior} (expected 'exclusive')"
            )

    assert not mismatches, "Stripe ↔ DB price mismatch:\n" + "\n".join(mismatches)
