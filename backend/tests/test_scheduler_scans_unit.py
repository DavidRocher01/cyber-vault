"""Job des scans nocturnes — `_schedule_due_scans`, 02:00 UTC.

Ce job tourne sans personne devant l'écran. Ses deux façons d'échouer sont
silencieuses : ne rien scanner (le client ne reçoit plus rien et ne le sait
pas), ou tout rescanner chaque nuit (facture d'exécution et courriels en
rafale). Aucune ne lève d'exception.

Le cas le plus délicat est l'intervalle nul du plan Gratuit : `days_since`
n'est jamais inférieur à 0, donc sans le garde explicite le site serait
rescanné **toutes les nuits** — exactement ce que « à la demande » exclut.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.plan import Plan
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User
from app.services.scheduler.scans import _schedule_due_scans

MODULE = "app.services.scheduler.scans"


# ─── fabriques ───────────────────────────────────────────────────────────────


def _site(site_id: int = 1, user_id: int = 1) -> MagicMock:
    s = MagicMock(spec=Site)
    s.id = site_id
    s.user_id = user_id
    s.url = "https://exemple.fr"
    return s


def _plan(intervalle: int = 7) -> MagicMock:
    p = MagicMock(spec=Plan)
    p.scan_interval_days = intervalle
    return p


def _user(user_id: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    u.email = f"client{user_id}@exemple.fr"
    return u


def _dernier_scan(jours: int | None, site_id: int = 1) -> MagicMock:
    """Dernier scan terminé il y a `jours` jours. `None` = jamais terminé."""
    sc = MagicMock(spec=Scan)
    sc.site_id = site_id
    sc.finished_at = None if jours is None else datetime.now(UTC) - timedelta(days=jours)
    return sc


def _session(apres_scan: dict | None = None):
    """Session factice. `apres_scan` est appliqué à l'objet passé à `refresh`,
    ce qui simule la relecture du scan une fois le moteur passé dessus."""
    db = AsyncMock()
    db.add = MagicMock()

    async def _refresh(objet):
        for cle, valeur in (apres_scan or {}).items():
            setattr(objet, cle, valeur)

    db.refresh = _refresh

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return db, patch(f"{MODULE}.AsyncSessionLocal", MagicMock(return_value=cm))


def _chargement(rows, derniers=None, utilisateurs=None):
    return patch(
        f"{MODULE}._load_active_sites_with_last_scan",
        AsyncMock(return_value=(rows, derniers or {}, utilisateurs or {})),
    )


# ─── déclenchement ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_aucun_site_actif_ne_declenche_rien():
    db, session = _session()
    with session, _chargement([]), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_plan_a_la_demande_n_est_jamais_scanne():
    """Intervalle 0 (plan Gratuit) : aucun scan automatique, jamais.

    Sans le garde, `days_since < 0` étant toujours faux, le site repasserait
    chaque nuit."""
    db, session = _session()
    rows = [(_site(), _plan(intervalle=0))]

    with session, _chargement(rows), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_not_called()


@pytest.mark.asyncio
async def test_intervalle_negatif_n_est_jamais_scanne():
    db, session = _session()
    rows = [(_site(), _plan(intervalle=-1))]

    with session, _chargement(rows), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_not_called()


@pytest.mark.asyncio
async def test_site_jamais_scanne_est_scanne():
    db, session = _session()
    rows = [(_site(), _plan(intervalle=7))]

    with session, _chargement(rows, derniers={}), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_called_once()
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_scan_trop_recent_est_ignore():
    db, session = _session()
    rows = [(_site(), _plan(intervalle=7))]
    derniers = {1: _dernier_scan(jours=3)}

    with session, _chargement(rows, derniers), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_not_called()


@pytest.mark.asyncio
async def test_intervalle_echu_declenche_un_scan():
    db, session = _session()
    rows = [(_site(), _plan(intervalle=7))]
    derniers = {1: _dernier_scan(jours=9)}

    with session, _chargement(rows, derniers), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_called_once()


@pytest.mark.asyncio
async def test_intervalle_pile_atteint_declenche_un_scan():
    """`days_since == intervalle` : la comparaison est stricte, donc on scanne.
    La borne compte — c'est elle qui fait la différence entre « hebdomadaire »
    et « tous les huit jours »."""
    db, session = _session()
    rows = [(_site(), _plan(intervalle=7))]
    derniers = {1: _dernier_scan(jours=7)}

    with session, _chargement(rows, derniers), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_called_once()


@pytest.mark.asyncio
async def test_dernier_scan_sans_date_de_fin_declenche_un_scan():
    """Un scan resté en cours ne doit pas bloquer les suivants indéfiniment."""
    db, session = _session()
    rows = [(_site(), _plan(intervalle=7))]
    derniers = {1: _dernier_scan(jours=None)}

    with session, _chargement(rows, derniers), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    lance.assert_called_once()


@pytest.mark.asyncio
async def test_chaque_site_est_traite_independamment():
    db, session = _session()
    rows = [
        (_site(site_id=1, user_id=1), _plan(intervalle=7)),
        (_site(site_id=2, user_id=2), _plan(intervalle=0)),
        (_site(site_id=3, user_id=3), _plan(intervalle=1)),
    ]
    derniers = {1: _dernier_scan(jours=9, site_id=1), 3: _dernier_scan(jours=0, site_id=3)}

    with session, _chargement(rows, derniers), patch(f"{MODULE}.run_scan", AsyncMock()) as lance:
        await _schedule_due_scans()

    # site 1 échu → scanné ; site 2 à la demande → non ; site 3 scanné aujourd'hui → non
    assert lance.call_count == 1


# ─── rapport par courriel ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rapport_envoye_quand_le_scan_aboutit():
    db, session = _session(apres_scan={"status": "done", "pdf_path": "/tmp/rapport.pdf"})
    rows = [(_site(), _plan(intervalle=7))]

    with (
        session,
        _chargement(rows, utilisateurs={1: _user()}),
        patch(f"{MODULE}.run_scan", AsyncMock()),
        patch("asyncio.to_thread", new_callable=AsyncMock) as envoi,
    ):
        await _schedule_due_scans()

    envoi.assert_called_once()
    arguments = envoi.call_args.kwargs
    assert arguments["to_email"] == "client1@exemple.fr"
    assert arguments["site_url"] == "https://exemple.fr"
    assert arguments["pdf_path"] == "/tmp/rapport.pdf"


@pytest.mark.asyncio
async def test_scan_en_echec_n_envoie_pas_de_rapport():
    db, session = _session(apres_scan={"status": "failed", "pdf_path": "/tmp/rapport.pdf"})
    rows = [(_site(), _plan(intervalle=7))]

    with (
        session,
        _chargement(rows, utilisateurs={1: _user()}),
        patch(f"{MODULE}.run_scan", AsyncMock()),
        patch("asyncio.to_thread", new_callable=AsyncMock) as envoi,
    ):
        await _schedule_due_scans()

    envoi.assert_not_called()


@pytest.mark.asyncio
async def test_sans_pdf_pas_de_rapport():
    db, session = _session(apres_scan={"status": "done", "pdf_path": None})
    rows = [(_site(), _plan(intervalle=7))]

    with (
        session,
        _chargement(rows, utilisateurs={1: _user()}),
        patch(f"{MODULE}.run_scan", AsyncMock()),
        patch("asyncio.to_thread", new_callable=AsyncMock) as envoi,
    ):
        await _schedule_due_scans()

    envoi.assert_not_called()


@pytest.mark.asyncio
async def test_proprietaire_introuvable_n_interrompt_pas_le_job():
    db, session = _session(apres_scan={"status": "done", "pdf_path": "/tmp/rapport.pdf"})
    rows = [(_site(), _plan(intervalle=7))]

    with (
        session,
        _chargement(rows, utilisateurs={}),
        patch(f"{MODULE}.run_scan", AsyncMock()),
        patch("asyncio.to_thread", new_callable=AsyncMock) as envoi,
    ):
        await _schedule_due_scans()

    envoi.assert_not_called()


@pytest.mark.asyncio
async def test_echec_d_envoi_n_interrompt_pas_les_sites_suivants():
    """Un serveur de courriel en panne ne doit pas priver de scan les sites
    qui suivent dans la boucle."""
    db, session = _session(apres_scan={"status": "done", "pdf_path": "/tmp/rapport.pdf"})
    rows = [
        (_site(site_id=1, user_id=1), _plan(intervalle=7)),
        (_site(site_id=2, user_id=2), _plan(intervalle=7)),
    ]

    with (
        session,
        _chargement(rows, utilisateurs={1: _user(1), 2: _user(2)}),
        patch(f"{MODULE}.run_scan", AsyncMock()) as lance,
        patch("asyncio.to_thread", AsyncMock(side_effect=Exception("SMTP injoignable"))),
    ):
        await _schedule_due_scans()  # ne doit pas lever

    assert lance.call_count == 2
