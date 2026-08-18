"""Enveloppes de jobs de `scheduler/retention.py`.

`purge_expired_data` — le travail lui-même — est couverte par
`test_retention_unit.py`, `test_depot_purge_orphelins.py` et
`test_depot_retention_client.py`. Ce qui ne l'était pas, ce sont les deux
**enveloppes** que l'ordonnanceur appelle réellement : elles ouvrent la
session, passent l'heure courante et décident de journaliser.

Ce sont huit lignes, et elles portent la seule trace qu'un exploitant verra
passer. Une purge RGPD qui ne s'exécute pas ne fait rien remarquer — c'est
même sa forme d'échec la plus probable.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scheduler.retention import _run_data_retention_purge, _run_rafraichir_analyses

MODULE = "app.services.scheduler.retention"


def _session():
    db = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return db, patch(f"{MODULE}.AsyncSessionLocal", MagicMock(return_value=cm))


RIEN_A_PURGER = {
    "public_scans": 0,
    "darkweb_dossiers": 0,
    "fichiers_orphelins": 0,
    "documents_clients": 0,
}


# ─── purge de rétention ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_la_purge_est_appelee_avec_la_session_et_l_heure():
    db, session = _session()

    with (
        session,
        patch(f"{MODULE}.purge_expired_data", AsyncMock(return_value=RIEN_A_PURGER)) as purge,
    ):
        await _run_data_retention_purge()

    purge.assert_awaited_once()
    session_passee, heure = purge.await_args.args
    assert session_passee is db
    # L'heure est calculée par le job, pas par la fonction de purge : c'est ce
    # qui rend cette dernière testable avec une date figée.
    assert heure.tzinfo is not None


@pytest.mark.asyncio
async def test_nuit_sans_rien_a_purger_ne_journalise_pas():
    """Le cas normal. Journaliser un « 0 supprimé » chaque nuit noierait les
    nuits où quelque chose se passe."""
    _db, session = _session()

    with (
        session,
        patch(f"{MODULE}.purge_expired_data", AsyncMock(return_value=RIEN_A_PURGER)),
        patch(f"{MODULE}.logger") as journal,
    ):
        await _run_data_retention_purge()

    journal.info.assert_not_called()


@pytest.mark.asyncio
async def test_une_seule_suppression_suffit_a_journaliser():
    """`any(counts.values())` : n'importe lequel des quatre compteurs déclenche
    la trace, pas seulement le premier."""
    _db, session = _session()
    comptes = dict(RIEN_A_PURGER, documents_clients=1)

    with (
        session,
        patch(f"{MODULE}.purge_expired_data", AsyncMock(return_value=comptes)),
        patch(f"{MODULE}.logger") as journal,
    ):
        await _run_data_retention_purge()

    journal.info.assert_called_once()


@pytest.mark.asyncio
async def test_les_quatre_compteurs_sont_journalises_dans_l_ordre():
    _db, session = _session()
    comptes = {
        "public_scans": 3,
        "darkweb_dossiers": 5,
        "fichiers_orphelins": 7,
        "documents_clients": 9,
    }

    with (
        session,
        patch(f"{MODULE}.purge_expired_data", AsyncMock(return_value=comptes)),
        patch(f"{MODULE}.logger") as journal,
    ):
        await _run_data_retention_purge()

    assert journal.info.call_args.args[1:] == (3, 5, 7, 9)


# ─── relecture des verdicts antivirus ────────────────────────────────────────


@pytest.mark.asyncio
async def test_relecture_appelee_avec_la_session_et_l_heure():
    db, session = _session()
    vide = {"tranches": 0, "abandonnes": 0}

    with session, patch(f"{MODULE}.depot_service") as depot:
        depot.rafraichir_analyses = AsyncMock(return_value=vide)
        await _run_rafraichir_analyses()

    depot.rafraichir_analyses.assert_awaited_once()
    session_passee, heure = depot.rafraichir_analyses.await_args.args
    assert session_passee is db
    assert heure.tzinfo is not None


@pytest.mark.asyncio
async def test_aucun_fichier_en_attente_ne_journalise_pas():
    """L'état normal : ce job passe toutes les 30 secondes. S'il journalisait
    à vide, il produirait près de 3 000 lignes par jour pour ne rien dire."""
    _db, session = _session()

    with (
        session,
        patch(f"{MODULE}.depot_service") as depot,
        patch(f"{MODULE}.logger") as journal,
    ):
        depot.rafraichir_analyses = AsyncMock(return_value={"tranches": 0, "abandonnes": 0})
        await _run_rafraichir_analyses()

    journal.info.assert_not_called()


@pytest.mark.asyncio
async def test_un_verdict_enregistre_est_journalise():
    _db, session = _session()

    with (
        session,
        patch(f"{MODULE}.depot_service") as depot,
        patch(f"{MODULE}.logger") as journal,
    ):
        depot.rafraichir_analyses = AsyncMock(return_value={"tranches": 2, "abandonnes": 0})
        await _run_rafraichir_analyses()

    journal.info.assert_called_once()
    assert journal.info.call_args.args[1:] == (2, 0)


@pytest.mark.asyncio
async def test_un_abandon_seul_est_journalise():
    """Un fichier abandonné est le cas qu'il faut surtout voir : le dépôt est
    resté en analyse au-delà du délai, donc jamais délivré au client."""
    _db, session = _session()

    with (
        session,
        patch(f"{MODULE}.depot_service") as depot,
        patch(f"{MODULE}.logger") as journal,
    ):
        depot.rafraichir_analyses = AsyncMock(return_value={"tranches": 0, "abandonnes": 1})
        await _run_rafraichir_analyses()

    journal.info.assert_called_once()
