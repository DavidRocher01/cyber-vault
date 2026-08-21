#!/usr/bin/env python3
"""Confronte ce que le site AFFICHE à ce que Stripe FACTURERA réellement.

POURQUOI CE SCRIPT EXISTE.

`tests/test_stripe_price_coherence.py` fait la même comparaison, et il ne l'a
jamais faite : il est `skipif(not STRIPE_SECRET_KEY)`, et la CI n'a pas ce
secret. Il est donc SKIPPED à chaque exécution depuis sa création.

Et même avec la clé, il ne répondrait pas à la question : il lit la base de
TEST via la fixture `pg_url`. Il comparerait donc les prix Stripe réels à ce
qu'un seed a écrit — pas à ce qu'un client voit sur le site.

Ce script part de l'autre bout : les montants réellement servis par
`/api/v1/plans` en production, confrontés aux prix Stripe désignés par les
`stripe_price_id` en base.

CE QU'IL NE PEUT PAS VOIR, et c'est écrit ici pour que personne ne s'y trompe :
la correspondance plan → price_id vit dans la base de production, hors d'atteinte
depuis l'extérieur du VPC. Le script la reprend donc de la migration qui l'a
posée. Si quelqu'un a modifié `plans.stripe_price_id` à la main en base après
cette migration, ce script ne le verra pas. La parade est de ne jamais le faire
à la main — c'est déjà la règle du dépôt.

Usage :
    python scripts/verifier_prix_stripe.py            # production
    python scripts/verifier_prix_stripe.py --json     # sortie machine
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request

API_PLANS = "https://rochercybersecurite.com/api/v1/plans"
SECRET_ARN = "cybervault/prod"
COMPORTEMENT_TVA_ATTENDU = "inclusive"

# Correspondance posée par la migration `a5875bea88a0` (grille du 2026-07-26),
# qui est la dernière de la chaîne à toucher aux prix — vérifié via
# `alembic history`. Le plan gratuit n'a pas de prix Stripe : rien à facturer.
PRICE_IDS: dict[str, tuple[str, str]] = {
    "starter": ("price_1TxQ6B1kFVtkWldS5UuJBANP", "price_1TxQ6Z1kFVtkWldS2NK9MR3v"),
    "pro": ("price_1TxQ811kFVtkWldS6j432oEy", "price_1TxQ8K1kFVtkWldSuwGN0x5K"),
    "business": ("price_1TxQ9Z1kFVtkWldS3zxEZK9H", "price_1TxQA91kFVtkWldS3cxc9zMa"),
}


def cle_stripe() -> str:
    """Lit la clé dans Secrets Manager. Elle ne transite ni par l'environnement
    du shell ni par la sortie : elle reste dans ce processus."""
    brut = subprocess.run(
        [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            SECRET_ARN,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    valeur = json.loads(brut).get("STRIPE_SECRET_KEY", "")
    if not valeur:
        raise SystemExit("STRIPE_SECRET_KEY absente de Secrets Manager")
    return valeur


def plans_affiches() -> dict[str, dict]:
    with urllib.request.urlopen(API_PLANS, timeout=20) as reponse:  # noqa: S310
        charge = json.load(reponse)
    plans = charge if isinstance(charge, list) else charge.get("plans", charge)
    return {p["name"]: p for p in plans}


def verifier() -> list[str]:
    import stripe

    stripe.api_key = cle_stripe()
    affiches = plans_affiches()
    ecarts: list[str] = []

    for nom, (id_mensuel, id_annuel) in PRICE_IDS.items():
        plan = affiches.get(nom)
        if plan is None:
            ecarts.append(f"{nom} : absent de {API_PLANS}")
            continue

        for libelle, price_id, attendu, intervalle in (
            ("mensuel", id_mensuel, plan["price_eur"], "month"),
            ("annuel", id_annuel, plan["price_eur_yearly"], "year"),
        ):
            if libelle == "annuel" and not plan.get("yearly_available"):
                # Le sélecteur annuel est masqué côté site : on vérifie quand
                # même le prix, pour qu'activer la bascule ne réserve pas de
                # surprise.
                pass

            prix = stripe.Price.retrieve(price_id)

            if prix.unit_amount != attendu:
                ecarts.append(
                    f"{nom} {libelle} : le site affiche {attendu / 100:.2f} EUR, "
                    f"Stripe facturerait {prix.unit_amount / 100:.2f} EUR"
                )
            if not prix.active:
                ecarts.append(f"{nom} {libelle} : prix ARCHIVE chez Stripe ({price_id})")
            if prix.currency != "eur":
                ecarts.append(f"{nom} {libelle} : devise {prix.currency} (attendu eur)")
            if prix.tax_behavior != COMPORTEMENT_TVA_ATTENDU:
                ecarts.append(
                    f"{nom} {libelle} : tax_behavior={prix.tax_behavior} "
                    f"(attendu {COMPORTEMENT_TVA_ATTENDU})"
                )
            reel = (prix.recurring or {}).get("interval")
            if reel != intervalle:
                ecarts.append(f"{nom} {libelle} : interval={reel} (attendu {intervalle})")

    return ecarts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="sortie machine")
    args = parser.parse_args()

    ecarts = verifier()

    if args.json:
        print(json.dumps({"conforme": not ecarts, "ecarts": ecarts}, ensure_ascii=False))
    elif ecarts:
        print(f"{len(ecarts)} ECART(S) entre l'affichage et la facturation :")
        for e in ecarts:
            print(f"  - {e}")
    else:
        print("Conforme : chaque prix affiche est celui que Stripe facturera.")

    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
