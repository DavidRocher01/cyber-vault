"""
Réaligne la table `plans` sur la grille tarifaire.

Contrairement au seed de démarrage (`app.main._seed_plans`), qui n'insère que
les plans absents, ce script **met aussi à jour les plans existants**. C'est
l'outil de rattrapage quand une base a dérivé.

Lancer : `python seed_plans.py` (depuis `backend/`)

La grille vient de `app.core.pricing`, comme le seed de démarrage, la migration
`a5875bea88a0` et la garde de facturation. Ce fichier portait auparavant sa
propre copie des tarifs, avec des `stripe_price_id` vides : changer un prix dans
`pricing.py` sans y penser aurait suffi à le faire régresser silencieusement au
prochain lancement. C'est exactement le genre d'écart qui a fait facturer
9,90 € un abonnement affiché 49 €.
"""

import asyncio

from sqlalchemy import select

import app.models.code_scan  # noqa: F401
import app.models.scan  # noqa: F401
import app.models.site  # noqa: F401
import app.models.subscription  # noqa: F401 — force relationship resolution
import app.models.user  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.pricing import GRILLE, seed_plan_kwargs
from app.models.plan import Plan

# Champs realignés sur un plan déjà présent. `name` en est absent : c'est la clé
# de recherche. Les `stripe_price_id` en font partie — les laisser de côté était
# la faille du script précédent.
CHAMPS_REALIGNES = (
    "display_name",
    "price_eur",
    "max_sites",
    "scan_interval_days",
    "tier_level",
    "allow_conformity_export",
    "stripe_price_id",
    "stripe_price_id_yearly",
)


async def seed():
    async with AsyncSessionLocal() as db:
        for plan in GRILLE:
            attendu = seed_plan_kwargs(plan)
            result = await db.execute(select(Plan).where(Plan.name == plan.name))
            existant = result.scalar_one_or_none()

            if not existant:
                db.add(Plan(**attendu))
                print(f"Plan '{plan.name}' créé")
                continue

            ecarts = []
            for champ in CHAMPS_REALIGNES:
                actuel = getattr(existant, champ)
                if actuel != attendu[champ]:
                    ecarts.append(f"{champ}: {actuel!r} -> {attendu[champ]!r}")
                    setattr(existant, champ, attendu[champ])

            if ecarts:
                print(f"Plan '{plan.name}' réaligné :")
                for e in ecarts:
                    print(f"    {e}")
            else:
                print(f"Plan '{plan.name}' déjà conforme")

        await db.commit()
    print("Seed terminé.")


if __name__ == "__main__":
    asyncio.run(seed())
