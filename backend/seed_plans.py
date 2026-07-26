"""
Seed the plans table with the 4 Rocher Cybersécurité subscription plans.
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
        "scan_interval_days": 30,  # dégustation : 1 scan/mois
        "tier_level": 1,
        "allow_conformity_export": False,  # export PDF conformité réservé au payant
        "stripe_price_id": "",
    },
    {
        "name": "starter",
        "display_name": "Surveillance Starter",
        "price_eur": 4900,  # 49,00 €
        "max_sites": 5,
        "scan_interval_days": 1,  # quotidien
        "tier_level": 2,
        "allow_conformity_export": True,
        "stripe_price_id": "",  # À créer dans Stripe (nouveau prix)
    },
    {
        "name": "pro",
        "display_name": "Surveillance Pro",
        "price_eur": 14900,  # 149,00 €
        "max_sites": 25,
        "scan_interval_days": 1,  # quotidien
        "tier_level": 3,
        "allow_conformity_export": True,
        "stripe_price_id": "",  # À créer dans Stripe (nouveau prix)
    },
    {
        "name": "business",
        "display_name": "Surveillance Business",
        "price_eur": 39000,  # 390,00 €
        "max_sites": -1,  # illimité
        "scan_interval_days": 1,  # quotidien
        "tier_level": 4,
        "allow_conformity_export": True,
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
                for field in (
                    "price_eur",
                    "max_sites",
                    "scan_interval_days",
                    "tier_level",
                    "allow_conformity_export",
                ):
                    if getattr(existing, field) != plan_data[field]:
                        setattr(existing, field, plan_data[field])
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
