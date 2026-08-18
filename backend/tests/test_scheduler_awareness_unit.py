"""Job de détection des apprenants à risque — `_run_awareness_at_risk_detection`,
04:00 UTC.

Ce job prévient le responsable d'une organisation que ses salariés décrochent
de la formation NIS2. C'est le seul signal qu'il reçoit : s'il ne part pas,
personne ne s'en aperçoit — ni lui, qui n'attend rien de précis, ni nous.

Le corps de la boucle est enveloppé dans un `try`, ce qui est correct (une
organisation en erreur ne doit pas priver les autres de leur alerte) mais rend
tout échec invisible. D'où ces tests.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scheduler.awareness import _run_awareness_at_risk_detection

MODULE = "app.services.scheduler.awareness"
# L'envoi est importé DANS la fonction, depuis le paquet email_service : c'est
# donc là qu'il faut le remplacer, pas dans le module du job.
ENVOI = "app.services.email_service.send_awareness_at_risk_alert"


def _ligne(organisation_id: int = 1, a_risque: int = 3) -> SimpleNamespace:
    """Une ligne du regroupement `organization_id → nombre d'apprenants`."""
    return SimpleNamespace(organization_id=organisation_id, at_risk=a_risque)


def _organisation(org_id: int = 1, nom: str = "Menuiserie Dupont", proprietaire: int = 10):
    o = MagicMock()
    o.id = org_id
    o.name = nom
    o.owner_user_id = proprietaire
    return o


def _proprietaire(email: str = "dirigeant@exemple.fr"):
    u = MagicMock()
    u.email = email
    return u


def _session(lignes, suite):
    """Session factice.

    Le job fait une requête de regroupement, puis deux requêtes par ligne
    (organisation puis propriétaire). `suite` fournit, dans l'ordre, ce que
    renvoient ces requêtes-là.
    """
    compteur = {"n": 0}
    db = AsyncMock()

    async def _execute(*_a, **_k):
        indice = compteur["n"]
        compteur["n"] += 1
        r = MagicMock()
        if indice == 0:
            r.all.return_value = lignes
        else:
            r.scalar_one_or_none.return_value = suite[indice - 1]
        return r

    db.execute = _execute

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch(f"{MODULE}.AsyncSessionLocal", MagicMock(return_value=cm))


@pytest.mark.asyncio
async def test_aucun_apprenant_a_risque_n_alerte_personne():
    with _session([], []), patch(ENVOI) as envoi:
        await _run_awareness_at_risk_detection()

    envoi.assert_not_called()


@pytest.mark.asyncio
async def test_alerte_le_proprietaire_avec_le_bon_decompte():
    lignes = [_ligne(organisation_id=1, a_risque=4)]
    suite = [_organisation(org_id=1, nom="Menuiserie Dupont"), _proprietaire("patron@exemple.fr")]

    with _session(lignes, suite), patch(ENVOI) as envoi:
        await _run_awareness_at_risk_detection()

    envoi.assert_called_once()
    arguments = envoi.call_args.kwargs
    assert arguments["to_email"] == "patron@exemple.fr"
    assert arguments["org_name"] == "Menuiserie Dupont"
    assert arguments["at_risk_count"] == 4
    # Le lien doit mener à l'organisation concernée : c'est ce qui rend
    # l'alerte actionnable plutôt que simplement inquiétante.
    assert arguments["dashboard_url"].endswith("/awareness/org/1")


@pytest.mark.asyncio
async def test_organisation_introuvable_est_ignoree():
    """Organisation supprimée entre la requête de regroupement et sa relecture."""
    lignes = [_ligne(organisation_id=1)]
    suite = [None]

    with _session(lignes, suite), patch(ENVOI) as envoi:
        await _run_awareness_at_risk_detection()

    envoi.assert_not_called()


@pytest.mark.asyncio
async def test_proprietaire_introuvable_est_ignore():
    lignes = [_ligne(organisation_id=1)]
    suite = [_organisation(), None]

    with _session(lignes, suite), patch(ENVOI) as envoi:
        await _run_awareness_at_risk_detection()

    envoi.assert_not_called()


@pytest.mark.asyncio
async def test_chaque_organisation_recoit_sa_propre_alerte():
    lignes = [_ligne(1, a_risque=2), _ligne(2, a_risque=9)]
    suite = [
        _organisation(org_id=1, nom="Alpha"),
        _proprietaire("alpha@exemple.fr"),
        _organisation(org_id=2, nom="Beta"),
        _proprietaire("beta@exemple.fr"),
    ]

    with _session(lignes, suite), patch(ENVOI) as envoi:
        await _run_awareness_at_risk_detection()

    assert envoi.call_count == 2
    envois = [(a.kwargs["org_name"], a.kwargs["at_risk_count"]) for a in envoi.call_args_list]
    assert envois == [("Alpha", 2), ("Beta", 9)]


@pytest.mark.asyncio
async def test_un_echec_n_interrompt_pas_les_organisations_suivantes():
    """C'est la raison d'être du `try` autour de la boucle : une organisation
    qui échoue ne doit pas faire taire l'alerte des autres."""
    lignes = [_ligne(1), _ligne(2)]
    suite = [
        _organisation(org_id=1, nom="Alpha"),
        _proprietaire("alpha@exemple.fr"),
        _organisation(org_id=2, nom="Beta"),
        _proprietaire("beta@exemple.fr"),
    ]

    appels = {"n": 0}

    def _envoi(**_k):
        appels["n"] += 1
        if appels["n"] == 1:
            raise RuntimeError("serveur de courriel injoignable")

    with _session(lignes, suite), patch(ENVOI, _envoi):
        await _run_awareness_at_risk_detection()  # ne doit pas lever

    assert appels["n"] == 2
