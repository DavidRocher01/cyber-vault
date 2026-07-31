#!/usr/bin/env python3
"""Verifie que chaque bloc `run:` des workflows est du shell syntaxiquement valide.

POURQUOI CE GARDE-FOU EXISTE
Le 2026-07-31, un commentaire ajoute dans le programme jq de `deploy.yml`
contenait une apostrophe (« avant d'etre liste »). Ce programme vit dans une
chaine shell a guillemets SIMPLES : l'apostrophe l'a refermee, et le
deploiement a echoue sur `syntax error near unexpected token 'as'`.

Rien ne l'avait vu. La CI ne teste pas les workflows, et l'erreur ne se
manifeste qu'a l'execution — c'est-a-dire pendant une mise en production.
Le job frontend etait deja passe, laissant un frontend a jour devant un
backend inchange.

Ce script rejoue `bash -n` (analyse syntaxique sans execution) sur chaque bloc
`run:` de chaque workflow. Il aurait attrape l'apostrophe.

LIMITE CONNUE : les expressions GitHub `${{ ... }}` sont laissees telles
quelles. Elles sont inertes pour `bash -n` dans tous les blocs actuels, mais
une expression contenant des quotes desequilibrees produirait un faux positif.
Le cas echeant, isoler l'etape plutot que de desactiver le script.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
WORKFLOWS = RACINE / ".github" / "workflows"


def blocs_run(chemin: Path) -> list[tuple[str, str]]:
    """Renvoie (etiquette, code shell) pour chaque `run:` du workflow."""
    contenu = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    trouves: list[tuple[str, str]] = []
    for nom_job, spec in (contenu.get("jobs") or {}).items():
        for i, etape in enumerate(spec.get("steps") or []):
            code = etape.get("run")
            if not code:
                continue
            # `shell:` non-bash (python, pwsh...) : hors perimetre.
            if etape.get("shell") and etape["shell"] not in ("bash", "sh"):
                continue
            etiquette = etape.get("name") or f"etape {i}"
            trouves.append((f"{chemin.name} > {nom_job} > {etiquette}", code))
    return trouves


def bash_utilisable() -> bool:
    """Vrai si `bash` existe ET sait executer quelque chose.

    Sur un poste Windows, `shutil.which` peut trouver le relais WSL, qui est
    present mais incapable de lancer /bin/bash. Sans cette sonde, TOUS les
    blocs remontaient en erreur et le script criait au loup sur 47 etapes
    saines — un garde-fou qui ne distingue pas « outil casse » de « code
    invalide » ne vaut rien.
    """
    if not shutil.which("bash"):
        return False
    try:
        return (
            subprocess.run(["bash", "-c", "exit 0"], capture_output=True).returncode
            == 0
        )
    except OSError:
        return False


def main() -> int:
    if not bash_utilisable():
        print(
            "bash indisponible sur ce poste — verification ignoree "
            "(elle tourne en CI, sur ubuntu-latest).",
            file=sys.stderr,
        )
        return 0

    echecs: list[str] = []
    total = 0
    for workflow in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        for etiquette, code in blocs_run(workflow):
            total += 1
            with tempfile.NamedTemporaryFile(
                "w", suffix=".sh", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                temporaire = f.name
            try:
                res = subprocess.run(
                    ["bash", "-n", temporaire], capture_output=True, text=True
                )
            finally:
                Path(temporaire).unlink(missing_ok=True)
            if res.returncode != 0:
                echecs.append(f"  {etiquette}\n    {res.stderr.strip()}")

    if echecs:
        print(f"Blocs shell invalides ({len(echecs)} sur {total}) :\n", file=sys.stderr)
        print("\n".join(echecs), file=sys.stderr)
        print(
            "\nRappel : dans deploy.yml le programme jq vit dans une chaine a "
            "guillemets simples — aucune apostrophe, meme en commentaire.",
            file=sys.stderr,
        )
        return 1

    print(f"OK — {total} blocs shell de workflow parsent correctement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
