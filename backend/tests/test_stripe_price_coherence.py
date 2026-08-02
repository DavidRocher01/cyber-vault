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

from app.core.pricing import COMPORTEMENT_TVA_ATTENDU
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
        # Un prix archivé reste référençable en base : le checkout échouerait
        # au moment du paiement, pas avant. Sept l'ont été le 2026-08-02.
        if not stripe_price.active:
            mismatches.append(f"{plan.name}: prix archivé chez Stripe ({plan.stripe_price_id})")
        # Attendu déclaré dans la grille, et non codé en dur ici : cette
        # assertion exigeait 'exclusive' alors que les six prix LIVE sont en
        # 'inclusive' — elle aurait échoué au premier lancement avec la clé.
        if stripe_price.tax_behavior != COMPORTEMENT_TVA_ATTENDU:
            mismatches.append(
                f"{plan.name}: tax_behavior={stripe_price.tax_behavior} "
                f"(attendu '{COMPORTEMENT_TVA_ATTENDU}')"
            )

        # Facturation annuelle (2 mois offerts) : le prix annuel Stripe doit valoir
        # price_eur x 10 et être en intervalle 'year'.
        if plan.stripe_price_id_yearly:
            yearly = stripe.Price.retrieve(plan.stripe_price_id_yearly)
            if yearly.unit_amount != plan.price_eur_yearly:
                mismatches.append(
                    f"{plan.name} (annuel): DB={plan.price_eur_yearly}c "
                    f"vs Stripe={yearly.unit_amount}c"
                )
            if (yearly.recurring or {}).get("interval") != "year":
                mismatches.append(
                    f"{plan.name} (annuel): interval="
                    f"{(yearly.recurring or {}).get('interval')} (expected 'year')"
                )

    assert not mismatches, "Stripe ↔ DB price mismatch:\n" + "\n".join(mismatches)
