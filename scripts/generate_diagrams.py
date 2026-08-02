#!/usr/bin/env python3
"""Extrait les schémas Mermaid de `docs/ARCHITECTURE.md` vers `docs/diagrams/`.

**`docs/ARCHITECTURE.md` fait foi.** Les blocs ```mermaid qu'il contient sont la
seule version éditable ; les `.mmd` en sont dérivés, comme le
`docs/architecture.html` que `.gitignore` déclare régénérable.

Pourquoi ce script existe : les neuf `.mmd` avaient été extraits une fois, en
janvier, puis plus jamais. Le 2026-08-02, `02.mmd` annonçait encore un frontend
« Angular 20 » que `ARCHITECTURE.md` avait corrigé en 21. Rien ne le signalait —
personne ne relit un fichier qu'aucun lien ne pointe.

    python scripts/generate_diagrams.py            # régénère
    python scripts/generate_diagrams.py --check    # échoue si désynchronisé (CI)

Les `.svg` ne sont PAS produits ici : leur rendu demande `mermaid-cli`, qui n'est
pas une dépendance du projet. Voir `docs/diagrams/README.md`.
"""

from __future__ import annotations

import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[1]
SOURCE = RACINE / "docs" / "ARCHITECTURE.md"
DESTINATION = RACINE / "docs" / "diagrams"

_BLOC = re.compile(r"^```mermaid\s*$(.*?)^```\s*$", re.M | re.S)


def _titre_courant(lignes: list[str], fin: int) -> str:
    """Le dernier titre rencontré avant la ligne `fin` — sert de légende."""
    for ligne in reversed(lignes[:fin]):
        if ligne.startswith("#"):
            return ligne.lstrip("# ").strip()
    return ""


def extraire() -> list[tuple[str, str, str]]:
    """[(nom de fichier, section d'origine, contenu mermaid)]"""
    texte = SOURCE.read_text(encoding="utf-8")
    lignes = texte.splitlines()
    resultats = []
    for n, correspondance in enumerate(_BLOC.finditer(texte), 1):
        corps = correspondance.group(1).strip("\n")
        ligne_debut = texte[: correspondance.start()].count("\n")
        resultats.append((f"{n:02d}.mmd", _titre_courant(lignes, ligne_debut), corps))
    return resultats


def main() -> int:
    verifier = "--check" in sys.argv
    if not SOURCE.exists():
        print(f"Source introuvable : {SOURCE}")
        return 1

    blocs = extraire()
    if not blocs:
        print(f"Aucun bloc mermaid trouvé dans {SOURCE.name} — extraction suspecte.")
        return 1

    ecarts = []
    for nom, section, corps in blocs:
        cible = DESTINATION / nom
        attendu = corps + "\n"
        actuel = cible.read_text(encoding="utf-8") if cible.exists() else None
        if actuel == attendu:
            continue
        ecarts.append((nom, section, "absent" if actuel is None else "désynchronisé"))
        if not verifier:
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(attendu, encoding="utf-8")

    # Un .mmd qui ne correspond plus à aucun bloc : schéma supprimé de la doc.
    attendus = {nom for nom, _, _ in blocs}
    orphelins = sorted(p.name for p in DESTINATION.glob("*.mmd") if p.name not in attendus)

    if verifier:
        if not ecarts and not orphelins:
            print(f"OK - {len(blocs)} schémas synchronisés avec {SOURCE.name}")
            return 0
        print(f"Schémas désynchronisés de {SOURCE.name} :\n")
        for nom, section, etat in ecarts:
            print(f"  {nom:<10} {etat:<14} {section}")
        for nom in orphelins:
            print(f"  {nom:<10} orphelin       (plus aucun bloc correspondant)")
        print("\nLancer : python scripts/generate_diagrams.py")
        return 1

    print(f"{len(blocs)} schémas extraits de {SOURCE.name} vers {DESTINATION.relative_to(RACINE)}")
    for nom, section, etat in ecarts:
        print(f"  {etat:<14} {nom}  ({section})")
    if not ecarts:
        print("  (aucun changement)")
    for nom in orphelins:
        print(f"  ORPHELIN       {nom} — à supprimer à la main si le schéma a disparu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
