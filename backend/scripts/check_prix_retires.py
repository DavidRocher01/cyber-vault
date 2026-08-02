#!/usr/bin/env python3
"""Interdit la reapparition d'un tarif retire dans les surfaces visibles.

Pourquoi : la grille a change trois fois en 2026 (avril, juin, juillet). A
chaque fois, des montants sont restes ecrits en dur dans des pages que personne
ne rouvrait. Le 2026-08-01, cinq surfaces annoncaient encore des prix perimes,
dont un article de blog intitule « combien ca coute vraiment » qui affichait
9,90 EUR pour un abonnement facture 49 EUR — huit fois moins.

Aucun test ne pouvait le voir : le code etait juste, c'est la copie qui mentait.

Ce controle lit les montants retires depuis `app/core/pricing.py`
(`LIBELLES_RETIRES`), seule liste a tenir a jour lors d'un changement de grille.

Limite assumee : les articles de blog vivent en base, pas dans le depot. Ils
restent a corriger par migration de donnees — cf.
`f7fb572e4e16_blog_tarifs_grille_juillet_2026.py`.

Usage : python scripts/check_prix_retires.py   (sortie 1 si un tarif refait surface)
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.pricing import LIBELLES_RETIRES  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]

# Surfaces lues par un prospect ou un client.
CIBLES = [
    ("frontend/src", ("*.html", "*.ts")),
    ("docs", ("*.md",)),
]

# Fichiers isoles, listes un par un. Un `rglob("README.md")` depuis la racine
# ratissait tout le depot et signalait deux fois les README deja couverts par
# les entrees ci-dessus.
FICHIERS_ISOLES = ("README.md",)

# Les migrations decrivent l'histoire : elles DOIVENT citer les anciens montants.
EXCLUS = ("node_modules", "dist", ".angular", "alembic/versions", "__pycache__")


def _fichiers():
    vus = set()
    for dossier, motifs in CIBLES:
        base = RACINE / dossier
        if not base.is_dir():
            continue
        for motif in motifs:
            for chemin in base.rglob(motif):
                relatif = chemin.relative_to(RACINE).as_posix()
                if relatif in vus or any(exclu in relatif for exclu in EXCLUS):
                    continue
                vus.add(relatif)
                yield chemin, relatif
    for nom in FICHIERS_ISOLES:
        chemin = RACINE / nom
        if chemin.is_file() and nom not in vus:
            vus.add(nom)
            yield chemin, nom


# Le montant retire, borne des deux cotes : « 9,90 » ne doit pas se declencher
# sur « 49,90 », ni sur un numero de version ou un identifiant.
def _motif(libelle: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\d,]){re.escape(libelle)}(?![\d])")


# Exiger le symbole colle au montant laissait passer les fourchettes : le
# formulaire de contact annoncait « 14,90–149 €/mois », ou le € suit l'autre
# borne. On demande donc seulement que la ligne parle d'argent.
_CONTEXTE_MONETAIRE = re.compile(r"€|\bEUR\b|/\s*mois|par mois|HT\b|TTC\b", re.IGNORECASE)

# Echappatoire pour les mentions volontaires : un runbook ou un ADR doit pouvoir
# raconter qu'une migration facturait 14,90 EUR sans faire echouer la CI. Marquer
# la ligne avec `prix-historique` (en commentaire HTML dans un .md).
_MENTION_ASSUMEE = "prix-historique"


def main() -> int:
    motifs = {libelle: _motif(libelle) for libelle in LIBELLES_RETIRES}

    trouvailles = []
    for chemin, relatif in _fichiers():
        try:
            lignes = chemin.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for numero, ligne in enumerate(lignes, 1):
            if _MENTION_ASSUMEE in ligne or not _CONTEXTE_MONETAIRE.search(ligne):
                continue
            for libelle, motif in motifs.items():
                if motif.search(ligne):
                    trouvailles.append((relatif, numero, libelle, ligne.strip()[:100]))

    if not trouvailles:
        print(f"OK - aucun tarif retire ({', '.join(LIBELLES_RETIRES)}) dans les surfaces visibles")
        return 0

    print("Tarifs RETIRES encore affiches :\n")
    for relatif, numero, libelle, extrait in trouvailles:
        print(f"  {relatif}:{numero}  [{libelle} €]  {extrait}")
    print(
        f"\n{len(trouvailles)} occurrence(s). Ces montants ne sont plus factures : "
        "les remplacer par la grille en vigueur (app/core/pricing.py)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
