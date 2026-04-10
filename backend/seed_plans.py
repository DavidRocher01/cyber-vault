"""
Seed the plans table with the 4 CyberScan subscription plans.
Run once: python seed_plans.py
Update stripe_price_id after creating prices in Stripe dashboard.
"""

import asyncio
from app.core.database import AsyncSessionLocal
from app.models.plan import Plan
import app.models.subscription  # noqa: F401 — force relationship resolution
import app.models.site           # noqa: F401
import app.models.scan           # noqa: F401
import app.models.user           # noqa: F401
import app.models.code_scan      # noqa: F401
from sqlalchemy import select


PLANS = [
    {
        "name":               "free",
        "display_name":       "Gratuit",
        "price_eur":          0,           # 0,00 €
        "max_sites":          1,
        "scan_interval_days": 0,           # scan manuel uniquement
        "tier_level":         1,
        "stripe_price_id":    "",
    },
    {
        "name":               "starter",
        "display_name":       "Starter",
        "price_eur":          2900,        # 29,00 €
        "max_sites":          1,
        "scan_interval_days": 30,
        "tier_level":         2,
        "stripe_price_id":    "",          # À remplir après création dans Stripe
    },
    {
        "name":               "pro",
        "display_name":       "Pro",
        "price_eur":          4900,        # 49,00 €
        "max_sites":          3,
        "scan_interval_days": 7,
        "tier_level":         3,
        "stripe_price_id":    "",
    },
    {
        "name":               "business",
        "display_name":       "Business",
        "price_eur":          7900,        # 79,00 €
        "max_sites":          10,
        "scan_interval_days": 1,
        "tier_level":         4,
        "stripe_price_id":    "",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for plan_data in PLANS:
            result = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
            existing = result.scalar_one_or_none()
            if existing:
                # Mettre à jour le prix si différent
                if existing.price_eur != plan_data["price_eur"]:
                    existing.price_eur = plan_data["price_eur"]
                    existing.max_sites = plan_data["max_sites"]
                    existing.scan_interval_days = plan_data["scan_interval_days"]
                    print(f"Plan '{plan_data['name']}' mis à jour")
                else:
                    print(f"Plan '{plan_data['name']}' déjà à jour — ignoré")
                continue
            plan = Plan(**plan_data)
            db.add(plan)
            print(f"Plan '{plan_data['name']}' créé")
        await db.commit()
    print("Seed terminé.")


if __name__ == "__main__":
    asyncio.run(seed())
