"""Aucun endpoint public ne doit repondre 500.

CE QUE CE TEST AURAIT EVITE. Le 2026-08-11, deux pages d'acquisition — le quiz
de maturite et le calculateur de cout — ont repondu 500 EN PRODUCTION pendant
une heure. Cause : leurs schemas de reponse declaraient `id: str` alors que les
identifiants sont des entiers.

Le typage etait cense proteger, et il a casse. Pourquoi personne ne l'a vu :

  - aucun test n'exercait ces deux endpoints ;
  - la recette post-prod ne les touche pas — elle couvre les parcours
    authentifies et la vitrine, pas les outils publics ;
  - un `response_model` faux ne se voit qu'a l'EXECUTION, jamais a la
    compilation ni au typage statique.

CE TEST BALAIE TOUS LES GET PUBLICS SANS PARAMETRE, et n'exige qu'une chose :
pas de 500. Il ne verifie pas le contenu — c'est le role des tests dedies — mais
il garantit qu'aucune page publique ne devient une erreur serveur sans que
personne ne le remarque.

LA LISTE EST DERIVEE DU SCHEMA OPENAPI, pas ecrite a la main : un outil public
ajoute demain sera couvert sans que personne n'y pense.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _get_publics() -> list[str]:
    """GET sans parametre de chemin. Les routes authentifiees repondront 401 :
    c'est une reponse valide, ce test ne juge que l'absence de 500."""
    chemins = []
    for chemin, operations in app.openapi()["paths"].items():
        if "get" not in operations or "{" in chemin:
            continue
        chemins.append(chemin)
    return sorted(chemins)


@pytest.mark.asyncio
async def test_le_balayage_lit_vraiment_des_routes():
    """Un inventaire vide ferait passer le test suivant sans rien verifier."""
    assert len(_get_publics()) > 20, "inventaire OpenAPI suspect"


@pytest.mark.asyncio
async def test_aucun_get_public_ne_repond_500():
    casses = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for chemin in _get_publics():
            try:
                r = await c.get(chemin)
            except Exception as exc:  # une exception non rattrapee vaut un 500
                casses.append(f"{chemin} -> {type(exc).__name__}: {exc}")
                continue
            if r.status_code >= 500:
                casses.append(f"{chemin} -> {r.status_code} {r.text[:120]}")

    assert not casses, "endpoint(s) public(s) en erreur serveur :\n  " + "\n  ".join(casses)
