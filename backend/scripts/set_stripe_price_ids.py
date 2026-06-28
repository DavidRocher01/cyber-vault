#!/usr/bin/env python3
"""
Backfill des `plans.stripe_price_id` après la migration `reprice_plans_v2`
(qui vide les price IDs). Script idempotent et hors chaîne Alembic
(cf. dette #2 : le data/seed reste hors des migrations de schéma).

Pré-requis : avoir créé les 3 produits/prix en mode LIVE dans Stripe et noté
leurs `price_...`. Les nouveaux tarifs attendus :
    starter  -> 14,90 €   pro -> 49,00 €   business -> 149,00 €

Usage (dans le conteneur ECS) :
    python scripts/set_stripe_price_ids.py \
        --starter  price_LIVE_starter \
        --pro      price_LIVE_pro \
        --business price_LIVE_business

Via ECS exec (cf. scripts/create_admin.py pour la commande aws ecs execute-command).
On peut ne passer qu'un sous-ensemble de plans (les autres sont laissés tels quels).
"""

import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")

from app.core.config import settings
from app.models.plan import Plan


async def main(mapping: dict[str, str]) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    updated, missing = [], []
    async with Session() as db:
        for name, price_id in mapping.items():
            result = await db.execute(select(Plan).where(Plan.name == name))
            plan = result.scalar_one_or_none()
            if not plan:
                missing.append(name)
                continue
            if plan.stripe_price_id == price_id:
                print(f"= {name}: déjà à jour ({price_id})")
                continue
            print(f"~ {name}: '{plan.stripe_price_id or '(vide)'}' -> '{price_id}'")
            plan.stripe_price_id = price_id
            updated.append(name)
        await db.commit()

    await engine.dispose()

    print("\n" + "=" * 50)
    print(f"  Plans mis à jour : {updated or 'aucun'}")
    if missing:
        print(f"  ⚠️  Plans introuvables : {missing}")
    print("=" * 50)
    if missing:
        sys.exit(1)


def _parse() -> dict[str, str]:
    p = argparse.ArgumentParser(description="Backfill plans.stripe_price_id")
    p.add_argument("--starter")
    p.add_argument("--pro")
    p.add_argument("--business")
    args = p.parse_args()
    mapping = {
        name: pid
        for name, pid in (
            ("starter", args.starter),
            ("pro", args.pro),
            ("business", args.business),
        )
        if pid
    }
    if not mapping:
        p.error("Fournir au moins un --starter / --pro / --business")
    bad = [f"{n}={v}" for n, v in mapping.items() if not v.startswith("price_")]
    if bad:
        p.error(f"price_id invalide (doit commencer par 'price_') : {bad}")
    return mapping


if __name__ == "__main__":
    asyncio.run(main(_parse()))
