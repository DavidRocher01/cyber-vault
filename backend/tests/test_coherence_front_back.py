"""Le frontend n'appelle que des routes que le backend expose vraiment.

POURQUOI CE TEST EXISTE. Les chemins d'API sont ecrits DEUX FOIS : dans les
routeurs FastAPI, et dans les services Angular. Rien ne les confrontait. Renommer
une route backend laissait le frontend appeler l'ancienne — sans erreur de
compilation, sans test rouge, jusqu'au 404 chez l'utilisateur. C'est la meme
famille que le « clic mort » : l'application parait fonctionner, et ne fonctionne
pas.

LA MEME LECON QUE LE RESTE DE LA SEMAINE, sous un autre visage : une information
ecrite a deux endroits diverge, et seule une confrontation automatique le voit.
Sitemap contre routes, couverture de recette contre fichier de routes, routes
prerendues contre inventaire du build, modes de rendu contre `canActivate` — et
maintenant appels du frontend contre routes du backend.

CE TEST NE TROUVE AUCUN DEFAUT AUJOURD'HUI, et c'est normal : 146 chemins
appeles, tous exposes. Il est ecrit pour le jour ou ce ne sera plus vrai.

CE QU'IL NE FAIT PAS. Il ne verifie ni les methodes HTTP, ni les corps, ni les
codes de retour — seulement l'existence du chemin. Et il ne signale pas les
routes backend que personne n'appelle : beaucoup sont legitimes (webhooks,
console d'administration, sonde de sante), et en faire un echec produirait du
bruit qu'on finirait par ignorer.
"""

import re
from pathlib import Path

import pytest

from app.main import app

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app"

# `const API = '/api/v1/awareness'` : la base seule n'est pas un endpoint. Sans
# cette exclusion, chaque service se signalerait lui-meme comme introuvable.
_DECLARATION = re.compile(r"const ([A-Z_]+) = '(/api/v1[^']*)'")
_LITTERAL = re.compile(r"['\"`](/api/v1/[^'\"`$]*)['\"`]")


def _normaliser(chemin: str) -> str:
    """Un parametre vaut un parametre, quel que soit son nom.

    Le frontend interpole (`${scanId}`), le backend nomme (`{scan_id}`) : on
    ramene les deux a la meme forme avant de comparer.
    """
    sans_query = chemin.split("?")[0]
    return re.sub(r"\$\{[^}]*\}|\{[^}]*\}", "{}", sans_query).rstrip("/")


def _appels_du_frontend() -> dict[str, set[str]]:
    appels: dict[str, set[str]] = {}
    for fichier in _FRONT.rglob("*.ts"):
        if ".spec." in fichier.name:
            continue
        source = fichier.read_text(encoding="utf-8")
        bases = dict(_DECLARATION.findall(source))

        for nom, base in bases.items():
            for suite in re.findall(r"\$\{" + nom + r"\}([^`'\"]*)", source):
                appels.setdefault(_normaliser(base + suite), set()).add(fichier.name)

        for brut in _LITTERAL.findall(source):
            if brut.rstrip("/") in {b.rstrip("/") for b in bases.values()}:
                continue  # simple declaration de base
            appels.setdefault(_normaliser(brut), set()).add(fichier.name)
    return appels


def _routes_du_backend() -> set[str]:
    return {_normaliser(p) for p in app.openapi()["paths"]}


@pytest.fixture(scope="module")
def appels() -> dict[str, set[str]]:
    return _appels_du_frontend()


def test_le_parseur_lit_vraiment_les_services(appels):
    """Un parseur muet ferait passer le test suivant sans rien verifier."""
    assert len(appels) > 100, f"seulement {len(appels)} appels lus — extraction cassee ?"


def test_toute_route_appelee_par_le_frontend_existe(appels):
    exposees = _routes_du_backend()
    assert len(exposees) > 100, "inventaire backend suspect"

    inconnues = sorted(c for c in appels if c not in exposees)
    detail = "\n  ".join(f"{c}  (appele par {', '.join(sorted(appels[c]))})" for c in inconnues)

    assert not inconnues, (
        f"{len(inconnues)} chemin(s) appele(s) par le frontend sans route backend "
        f"correspondante — 404 garanti chez l'utilisateur :\n  {detail}"
    )
