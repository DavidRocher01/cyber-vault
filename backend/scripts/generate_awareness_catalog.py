"""
Genere le catalogue de sensibilisation consomme par le frontend.

POURQUOI CE SCRIPT
------------------
Le catalogue (nombre de modules, duree des parcours, intitules) etait recopie A
LA MAIN dans le code frontend. Consequence, constatee le 2026-07-30 : cinq
emplacements annoncaient « 17 modules » et trois « 28 » alors que le contenu en
compte 28, et la duree affichee etait de 72 minutes contre 143 reelles. L'offre
etait presentee moitie moins grande qu'elle ne l'est. Meme cause que le tarif
NIS2 affiche a 49 EUR au lieu de 79 le meme jour.

La source de verite est `content/fr/` : les fichiers que l'equipe edite quand
elle ecrit un module. Ce script en derive un fichier TypeScript unique, que le
frontend importe au lieu de reecrire les chiffres.

Usage :
    python scripts/generate_awareness_catalog.py           # ecrit le fichier
    python scripts/generate_awareness_catalog.py --check   # verifie qu'il est a jour

Le mode --check tourne en CI : il echoue si quelqu'un ajoute un module sans
regenerer, ce qui est exactement la derive qu'on veut empecher.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import yaml

# Force UTF-8 output (avoids cp1252 issues on Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RACINE = Path(__file__).parent.parent.parent
CONTENT_DIR = RACINE / "content" / "fr"
MODULES_DIR = CONTENT_DIR / "modules"
PROGRAMS_DIR = CONTENT_DIR / "programs"
# Dans shared/ : le catalogue est consomme par plusieurs features (landing,
# tarifs, admin, page sensibilisation), c'est la convention du projet.
CIBLE = RACINE / "frontend" / "src" / "app" / "shared" / "awareness-catalog.generated.ts"

# Ordre d'affichage : du plus complet au plus court. Les parcours absents de
# cette liste sont ajoutes ensuite, par ordre alphabetique.
ORDRE_PARCOURS = ["nis2-essentiel", "nis2-technique", "nis2-direction", "nis2-onboarding"]

# Public vise par parcours — donnee commerciale, absente des YAML de contenu.
PUBLICS = {
    "nis2-essentiel": "Tout le personnel",
    "nis2-technique": "Équipes IT, développeurs, DevOps",
    "nis2-direction": "Dirigeants, managers, RSSI",
    "nis2-onboarding": "Nouveaux arrivants",
}


def _charger_modules() -> dict[str, dict]:
    modules: dict[str, dict] = {}
    for dossier in sorted(MODULES_DIR.iterdir()):
        meta = dossier / "meta.yaml"
        if dossier.is_dir() and meta.exists():
            modules[dossier.name] = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
    return modules


def _charger_parcours() -> list[dict]:
    parcours = []
    for fichier in sorted(PROGRAMS_DIR.glob("*.yaml")):
        data = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}
        parcours.append(data)
    rang = {slug: i for i, slug in enumerate(ORDRE_PARCOURS)}
    parcours.sort(key=lambda p: (rang.get(p.get("slug", ""), len(rang)), p.get("slug", "")))
    return parcours


def _echapper(valeur: str) -> str:
    return valeur.replace("\\", "\\\\").replace("'", "\\'")


def _duree_parcours(p: dict, modules: dict[str, dict]) -> int:
    """Duree CALCULEE depuis les modules du parcours, pas celle declaree.

    Le champ `estimated_duration_minutes` des YAML de parcours derive : au
    2026-07-30, nis2-essentiel declarait 143 minutes alors que la somme de ses 28
    modules donnait 144. Recalculer supprime la classe entiere de ce probleme —
    c'est le principe de tout ce fichier.
    """
    return sum(
        int(modules.get(slug, {}).get("estimated_duration_minutes", 0))
        for slug in (p.get("modules") or [])
    )


def construire() -> str:
    modules = _charger_modules()
    parcours = _charger_parcours()

    actifs = {k: v for k, v in modules.items() if v.get("is_active", True)}
    total_minutes = sum(int(v.get("estimated_duration_minutes", 0)) for v in actifs.values())

    # Signale les ecarts entre duree declaree et duree reelle, sans bloquer :
    # c'est au contenu d'etre corrige, pas au catalogue de mentir.
    for p in parcours:
        declaree = int(p.get("estimated_duration_minutes", 0))
        calculee = _duree_parcours(p, modules)
        if declaree != calculee:
            print(
                f"   note : {p.get('slug')} declare {declaree} min, ses modules en"
                f" totalisent {calculee} — le catalogue retient {calculee}."
            )

    lignes = [
        "// ⚠️ FICHIER GÉNÉRÉ — NE PAS ÉDITER À LA MAIN.",
        "//",
        "// Source de vérité : content/fr/ (modules et parcours).",
        "// Régénérer : python backend/scripts/generate_awareness_catalog.py",
        "// La CI vérifie que ce fichier est à jour (--check) : un module ajouté sans",
        "// régénération fait échouer le build, ce qui est le but.",
        "//",
        "// Ce fichier existe parce que ces chiffres étaient recopiés à la main dans huit",
        "// emplacements et avaient dérivé : 17 modules annoncés au lieu de 28, 72 minutes",
        "// au lieu de 143.",
        "",
        "export interface ParcoursAwareness {",
        "  readonly slug: string;",
        "  readonly titre: string;",
        "  readonly public: string;",
        "  readonly nbModules: number;",
        "  readonly dureeMinutes: number;",
        "  readonly scoreRequis: number;",
        "}",
        "",
        "/** Nombre de modules actifs dans le catalogue. */",
        f"export const NB_MODULES = {len(actifs)};",
        "",
        "/** Durée cumulée de tous les modules actifs, en minutes. */",
        f"export const DUREE_TOTALE_MINUTES = {total_minutes};",
        "",
        "/** Parcours proposés, du plus complet au plus court. */",
        "export const PARCOURS: readonly ParcoursAwareness[] = [",
    ]

    for p in parcours:
        if not p.get("is_active", True):
            continue
        slug = p.get("slug", "")
        lignes += [
            "  {",
            f"    slug: '{_echapper(slug)}',",
            f"    titre: '{_echapper(str(p.get('title', '')))}',",
            f"    public: '{_echapper(PUBLICS.get(slug, ''))}',",
            f"    nbModules: {len(p.get('modules') or [])},",
            f"    dureeMinutes: {_duree_parcours(p, modules)},",
            f"    scoreRequis: {int(p.get('passing_score', 0))},",
            "  },",
        ]

    lignes += [
        "] as const;",
        "",
        "/** Nombre de parcours proposés. */",
        "export const NB_PARCOURS = PARCOURS.length;",
        "",
    ]
    return "\n".join(lignes)


def main() -> int:
    contenu = construire()
    verifier = "--check" in sys.argv

    if verifier:
        if not CIBLE.exists():
            print(f"KO - {CIBLE.relative_to(RACINE)} est absent.")
            print("     Lancer : python backend/scripts/generate_awareness_catalog.py")
            return 1
        actuel = CIBLE.read_text(encoding="utf-8")
        if actuel != contenu:
            print(f"KO - {CIBLE.relative_to(RACINE)} n'est plus a jour avec content/fr/.")
            print("     Le contenu a change sans que le catalogue soit regenere.")
            print("     Lancer : python backend/scripts/generate_awareness_catalog.py")
            return 1
        # Compter "    slug: '" (indente + quote) : "slug:" seul matchait aussi
        # `slug: string;` de la declaration d'interface -> 5 parcours au lieu de 4.
        print(f"OK - catalogue a jour ({contenu.count('    slug: ')} parcours)")
        return 0

    CIBLE.parent.mkdir(parents=True, exist_ok=True)
    CIBLE.write_text(contenu, encoding="utf-8")
    print(f"OK - {CIBLE.relative_to(RACINE)} genere")
    return 0


if __name__ == "__main__":
    sys.exit(main())
