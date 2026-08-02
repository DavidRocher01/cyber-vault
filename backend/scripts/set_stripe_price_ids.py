#!/usr/bin/env python3
"""
Pose manuelle des `plans.stripe_price_id`. **Ce n'est plus le chemin normal.**

Depuis le 2026-08-02, la source de vérité est `app/core/pricing.py` :
  - le seed de démarrage y lit les identifiants pour toute base neuve ;
  - la migration `a5875bea88a0` les pose sur les bases déjà en service ;
  - `test_pricing_source_unique.py` échoue si un identifiant de la grille
    n'apparaît dans aucune migration.

C'est précisément l'usage exclusif de ce script qui avait créé le trou : les
identifiants de production n'existaient nulle part dans le dépôt, et les seules
valeurs versionnées — celles de trois migrations d'avril — pointaient des prix à
9,90 / 39,90 / 49,90 €. Une base reconstruite serait repartie en facturant
9,90 € un abonnement affiché 49 €.

Le script reste utile pour un dépannage ponctuel : basculer un plan sur un
nouveau prix sans attendre un déploiement. Dans ce cas, reporter ensuite la
valeur dans `pricing.py` et écrire la migration correspondante, sinon le
prochain redémarrage sur base neuve repartira sur l'ancienne.

Script idempotent et hors chaîne Alembic
(cf. dette #2 : le data/seed reste hors des migrations de schéma).

Pré-requis : avoir créé les 3 produits/prix en mode LIVE dans Stripe et noté
leurs `price_...`. Les tarifs attendus :
    starter  -> 49,00 €   pro -> 149,00 €   business -> 390,00 €

Chaque plan a un price_id mensuel et un price_id annuel (facturation annuelle,
2 mois offerts). Les deux sont indépendants : configurer l'annuel active le
sélecteur mensuel/annuel côté front pour ce plan.

Usage (dans le conteneur ECS) :
    python scripts/set_stripe_price_ids.py \
        --starter  price_LIVE_starter \
        --pro      price_LIVE_pro \
        --business price_LIVE_business \
        --starter-yearly  price_LIVE_starter_yr \
        --pro-yearly      price_LIVE_pro_yr \
        --business-yearly price_LIVE_business_yr

Via ECS exec (cf. scripts/create_admin.py pour la commande aws ecs execute-command).
On peut ne passer qu'un sous-ensemble de plans/intervalles (les autres sont
laissés tels quels).
"""

import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")

from app.core.config import settings
from app.models.plan import Plan


async def main(mapping: dict[str, dict[str, str]]) -> None:
    """`mapping` : {plan_name: {"stripe_price_id": ..., "stripe_price_id_yearly": ...}}."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    updated, missing = [], []
    async with Session() as db:
        for name, fields in mapping.items():
            result = await db.execute(select(Plan).where(Plan.name == name))
            plan = result.scalar_one_or_none()
            if not plan:
                missing.append(name)
                continue
            for attr, price_id in fields.items():
                current = getattr(plan, attr)
                label = "annuel" if attr.endswith("_yearly") else "mensuel"
                if current == price_id:
                    print(f"= {name} ({label}): déjà à jour ({price_id})")
                    continue
                print(f"~ {name} ({label}): '{current or '(vide)'}' -> '{price_id}'")
                setattr(plan, attr, price_id)
                updated.append(f"{name}/{label}")
        await db.commit()

    await engine.dispose()

    print("\n" + "=" * 50)
    print(f"  Price IDs mis à jour : {updated or 'aucun'}")
    if missing:
        print(f"  ⚠️  Plans introuvables : {missing}")
    print("=" * 50)
    if missing:
        sys.exit(1)


def _parse() -> dict[str, dict[str, str]]:
    p = argparse.ArgumentParser(description="Backfill plans.stripe_price_id (mensuel + annuel)")
    p.add_argument("--starter")
    p.add_argument("--pro")
    p.add_argument("--business")
    p.add_argument("--starter-yearly")
    p.add_argument("--pro-yearly")
    p.add_argument("--business-yearly")
    args = p.parse_args()

    # (plan_name, colonne_modele, valeur) pour chaque option fournie.
    entries = [
        ("starter", "stripe_price_id", args.starter),
        ("pro", "stripe_price_id", args.pro),
        ("business", "stripe_price_id", args.business),
        ("starter", "stripe_price_id_yearly", args.starter_yearly),
        ("pro", "stripe_price_id_yearly", args.pro_yearly),
        ("business", "stripe_price_id_yearly", args.business_yearly),
    ]
    mapping: dict[str, dict[str, str]] = {}
    for name, attr, pid in entries:
        if pid:
            mapping.setdefault(name, {})[attr] = pid

    if not mapping:
        p.error("Fournir au moins un --starter / --pro / --business (mensuel ou -yearly)")
    bad = [
        f"{name}.{attr}={pid}"
        for name, fields in mapping.items()
        for attr, pid in fields.items()
        if not pid.startswith("price_")
    ]
    if bad:
        p.error(f"price_id invalide (doit commencer par 'price_') : {bad}")
    return mapping


if __name__ == "__main__":
    asyncio.run(main(_parse()))
