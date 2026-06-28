"""
Seed the plans table with the 4 CyberScan subscription plans.
Run once: python seed_plans.py
Update stripe_price_id after creating prices in Stripe dashboard.
"""

import asyncio

from sqlalchemy import select

import app.models.code_scan  # noqa: F401
import app.models.scan  # noqa: F401
import app.models.site  # noqa: F401
import app.models.subscription  # noqa: F401 — force relationship resolution
import app.models.user  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.models.plan import Plan

PLANS = [
    {
        "name": "free",
        "display_name": "Gratuit",
        "price_eur": 0,  # 0,00 €
        "max_sites": 1,
        "scan_interval_days": 0,  # scan manuel uniquement
        "tier_level": 1,
        "stripe_price_id": "",
    },
    {
        "name": "starter",
        "display_name": "Surveillance Starter",
        "price_eur": 1490,  # 14,90 €
        "max_sites": 1,
        "scan_interval_days": 7,  # 4 scans/mois (hebdo)
        "tier_level": 2,
        "stripe_price_id": "",  # À créer dans Stripe (nouveau prix)
    },
    {
        "name": "pro",
        "display_name": "Surveillance Pro",
        "price_eur": 4900,  # 49,00 €
        "max_sites": 5,
        "scan_interval_days": 7,  # 20 scans/mois (5/sem)
        "tier_level": 3,
        "stripe_price_id": "",  # À créer dans Stripe (nouveau prix)
    },
    {
        "name": "business",
        "display_name": "Surveillance Business",
        "price_eur": 14900,  # 149,00 €
        "max_sites": 15,
        "scan_interval_days": 1,  # quotidien
        "tier_level": 4,
        "stripe_price_id": "",  # À créer dans Stripe (nouveau prix)
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for plan_data in PLANS:
            result = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
            existing = result.scalar_one_or_none()
            if existing:
                changed = False
                if existing.price_eur != plan_data["price_eur"]:
                    existing.price_eur = plan_data["price_eur"]
                    existing.max_sites = plan_data["max_sites"]
                    existing.scan_interval_days = plan_data["scan_interval_days"]
                    changed = True
                if (
                    plan_data["stripe_price_id"]
                    and existing.stripe_price_id != plan_data["stripe_price_id"]
                ):
                    existing.stripe_price_id = plan_data["stripe_price_id"]
                    changed = True
                print(
                    f"Plan '{plan_data['name']}' {'mis à jour' if changed else 'déjà à jour — ignoré'}"
                )
                continue
            plan = Plan(**plan_data)
            db.add(plan)
            print(f"Plan '{plan_data['name']}' créé")
        await db.commit()
    print("Seed terminé.")


if __name__ == "__main__":
    asyncio.run(seed())
