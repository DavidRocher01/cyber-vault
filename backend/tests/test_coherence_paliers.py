"""Aucun palier exige ne doit etre hors d'atteinte.

POURQUOI CE TEST EXISTE. Le niveau requis pour une fonctionnalite est ecrit a
TROIS endroits : `require_min_tier(N)` dans les endpoints, `tier_level >= N`
dans les composants et gabarits Angular, et la grille `app/core/pricing.py` qui
dit quels paliers existent reellement.

Si un endpoint exige un palier qu'AUCUN plan n'atteint, la fonctionnalite est
inaccessible a tout le monde — y compris au client qui a paye le plan le plus
cher. Et personne ne s'en apercoit : il n'y a pas d'erreur, juste un 403 que
l'on met sur le compte des droits.

Si un ecran s'affiche a partir d'un palier plus BAS que celui exige par
l'endpoint qu'il appelle, on obtient l'inverse : un bouton visible qui repond
403. C'est la famille du clic mort — celle qui a ete trouvee a la main le
2026-08-08, quand le back-office affichait un plan que le serveur refusait.

CE TEST NE COUVRE QUE LA MOITIE TRACTABLE du probleme : que tout palier exige
soit atteignable. Faire correspondre CHAQUE bouton a CHAQUE endpoint demanderait
une table ecrite a la main — et une table ecrite a la main se perime, c'est la
lecon repetee toute la semaine. On garde ce qui se derive.
"""

import re
from pathlib import Path

from app.core.pricing import GRILLE

_RACINE = Path(__file__).resolve().parents[2]
_BACKEND = _RACINE / "backend" / "app"
_FRONT = _RACINE / "frontend" / "src" / "app"

_PALIER_MAX = max(p.tier_level for p in GRILLE)


def _paliers_exiges_par_le_backend() -> dict[int, set[str]]:
    exiges: dict[int, set[str]] = {}
    for fichier in _BACKEND.rglob("*.py"):
        for n in re.findall(r"require_min_tier\((\d+)\)", fichier.read_text(encoding="utf-8")):
            exiges.setdefault(int(n), set()).add(fichier.name)
    return exiges


def _paliers_testes_par_le_frontend() -> dict[int, set[str]]:
    testes: dict[int, set[str]] = {}
    motif = re.compile(r"tier_level[^0-9\n]{0,20}>=?\s*(\d+)|TIER_REQUIS\s*=\s*(\d+)")
    for fichier in list(_FRONT.rglob("*.ts")) + list(_FRONT.rglob("*.html")):
        if ".spec." in fichier.name:
            continue
        for a, b in motif.findall(fichier.read_text(encoding="utf-8")):
            testes.setdefault(int(a or b), set()).add(fichier.name)
    return testes


def test_la_grille_declare_bien_plusieurs_paliers():
    """Un parseur muet ferait passer les tests suivants sans rien verifier."""
    assert _PALIER_MAX >= 2, f"grille tarifaire suspecte : palier maximum {_PALIER_MAX}"


def test_le_backend_n_exige_aucun_palier_inatteignable():
    exiges = _paliers_exiges_par_le_backend()
    assert exiges, "aucun require_min_tier lu — extraction cassee ?"

    hors_atteinte = {n: f for n, f in exiges.items() if n > _PALIER_MAX}
    assert not hors_atteinte, (
        f"palier(s) exige(s) qu'aucun plan n'atteint (maximum de la grille : {_PALIER_MAX}) — "
        f"fonctionnalite inaccessible a TOUS, y compris au plan le plus cher : "
        f"{ {n: sorted(f) for n, f in hors_atteinte.items()} }"
    )


def test_le_frontend_ne_gate_sur_aucun_palier_inatteignable():
    """Un ecran conditionne a un palier inexistant ne s'affiche jamais.

    Aucune erreur, aucun test rouge : la fonctionnalite est simplement absente
    de l'interface, et on la croit livree.
    """
    testes = _paliers_testes_par_le_frontend()
    assert testes, "aucun test de tier_level lu — extraction cassee ?"

    hors_atteinte = {n: f for n, f in testes.items() if n > _PALIER_MAX}
    assert not hors_atteinte, (
        f"ecran(s) conditionne(s) a un palier inexistant (maximum : {_PALIER_MAX}) — "
        f"jamais affiche(s) : { {n: sorted(f) for n, f in hors_atteinte.items()} }"
    )
