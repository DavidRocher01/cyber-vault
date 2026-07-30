#!/usr/bin/env python3
"""Verifie que les runtimes declares sont coherents entre tous les endroits.

Contexte : l'audit du 2026-07-30 a trouve un poste de dev en Python 3.12 alors que
la prod et la CI tournaient en 3.14, et une CI en Node 20 alors que le poste etait
en Node 24. Les versions etaient recopiees a la main dans 11 emplacements de
workflows plus le Dockerfile : rien ne signalait la derive.

Depuis, `.python-version` et `.nvmrc` sont les seules sources de verite, lues par
les workflows via `python-version-file` / `node-version-file`. Ce script verifie
les endroits qui NE PEUVENT PAS les lire (le Dockerfile, `engines` de package.json)
et rattrape tout epinglage en dur reintroduit dans un workflow.

Usage : python scripts/check_runtime_versions.py   (code retour 1 si incoherent)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def _lire(chemin: Path) -> str:
    return chemin.read_text(encoding="utf-8").strip()


def verifier() -> list[str]:
    erreurs: list[str] = []

    py_attendu = _lire(RACINE / ".python-version")
    node_attendu = _lire(RACINE / ".nvmrc")

    # ── Dockerfile : ne peut pas lire .python-version, on compare le tag ──────
    dockerfile = (RACINE / "backend" / "Dockerfile").read_text(encoding="utf-8")
    tags = re.findall(r"^FROM\s+python:([0-9]+\.[0-9]+)", dockerfile, re.M)
    if not tags:
        erreurs.append("backend/Dockerfile : aucune image `FROM python:<version>` trouvee")
    for tag in set(tags):
        if tag != py_attendu:
            erreurs.append(
                f"backend/Dockerfile : image python:{tag} alors que "
                f".python-version dit {py_attendu} — la PROD tournerait sur une autre "
                f"version que la CI et les postes de dev"
            )

    # ── package.json : `engines.node` doit englober la version de .nvmrc ──────
    pkg = json.loads((RACINE / "frontend" / "package.json").read_text(encoding="utf-8"))
    engines = (pkg.get("engines") or {}).get("node")
    if not engines:
        erreurs.append("frontend/package.json : `engines.node` absent")
    elif node_attendu not in engines:
        erreurs.append(
            f"frontend/package.json : engines.node = {engines!r} ne mentionne pas "
            f"la version {node_attendu} de .nvmrc"
        )

    # ── Workflows : plus aucun epinglage en dur ───────────────────────────────
    for wf in sorted((RACINE / ".github" / "workflows").glob("*.yml")):
        contenu = wf.read_text(encoding="utf-8")
        for champ in ("python-version", "node-version"):
            # `python-version-file` est la forme attendue : on ne matche que la
            # forme nue suivie d'une valeur.
            if re.search(rf"^\s*{champ}:\s*\S", contenu, re.M):
                erreurs.append(
                    f".github/workflows/{wf.name} : `{champ}:` en dur — utiliser "
                    f"`{champ}-file` pour lire .python-version / .nvmrc"
                )

    return erreurs


def main() -> int:
    erreurs = verifier()
    if erreurs:
        print("Incoherence de versions de runtime :\n")
        for e in erreurs:
            print(f"  - {e}")
        return 1
    print(
        f"OK - runtimes coherents (Python {_lire(RACINE / '.python-version')}, "
        f"Node {_lire(RACINE / '.nvmrc')})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
