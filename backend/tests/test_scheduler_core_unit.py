"""Câblage APScheduler — `start_scheduler()` et `_make_scheduler()`.

POURQUOI CE FICHIER EXISTE.

Deux défauts de ce câblage ne produisent **aucune erreur** à l'exécution :

1. **`replace_existing=True` sur chaque `add_job`.** Deux jobs qui
   partageraient un identifiant ne lèveraient rien : le second remplacerait le
   premier en silence, et une tâche nocturne entière disparaîtrait.

2. **Un module de job écrit puis jamais enregistré.** Le code existe, il est
   testé, il est couvert — et il ne tourne jamais.

Les deux se lisent dans le code et ne se voient jamais à l'usage : personne ne
remarque un job qui ne s'exécute pas. D'où la liste **dérivée du code** plutôt
que recopiée, sur le principe de `e2e/recette/couverture-routes.ts` — le jour
où quelqu'un ajoute un job, le test réclame son enregistrement ou une raison
écrite.
"""

import ast
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.scheduler import core

PAQUET = pathlib.Path(core.__file__).parent

# Jobs enregistrés par `start_scheduler()` mais dont le code vit ailleurs que
# dans `scheduler/`. Chaque entrée est une décision, pas un oubli — et une
# entrée qui ne correspondrait plus à rien est signalée par un test.
JOBS_HORS_PAQUET = {
    "phishing_batch": (
        "app.services.phishing.sending.send_pending_batch — l'envoi par lots "
        "vit avec le reste du phishing, pas dans scheduler/"
    ),
}


def _coroutines_de_job() -> set[str]:
    """Les jobs du paquet, **lus dans le code** plutôt que recopiés.

    Critère : coroutine de premier niveau, préfixée `_`, **sans argument** —
    c'est exactement ce qu'APScheduler sait appeler. Il écarte de lui-même les
    aides, qui en prennent au moins un (`_load_active_sites_with_last_scan(db)`),
    et `purge_expired_data`, publique parce que réutilisée ailleurs.

    `core.py` est exclu : il contient le câblage, pas des jobs.
    """
    jobs: set[str] = set()
    for fichier in sorted(PAQUET.glob("*.py")):
        if fichier.name in {"core.py", "__init__.py"}:
            continue
        for noeud in ast.parse(fichier.read_text(encoding="utf-8")).body:
            if not isinstance(noeud, ast.AsyncFunctionDef):
                continue
            if not noeud.name.startswith("_"):
                continue
            if noeud.args.args or noeud.args.kwonlyargs:
                continue
            jobs.add(noeud.name)
    return jobs


@pytest.fixture
def enregistrements(monkeypatch):
    """Lance `start_scheduler()` sur un ordonnanceur factice et retient les appels.

    On remplace l'instance partagée : la vraie démarrerait un ordonnanceur réel
    dans la boucle du test, avec des jobs qui se déclencheraient pour de bon.
    """
    appels: list[tuple[object, dict]] = []
    faux = MagicMock()
    faux.add_job = lambda func, **kw: appels.append((func, kw))
    monkeypatch.setattr(core, "scheduler", faux)

    core.start_scheduler()
    return appels, faux


# ─── enregistrement des jobs ─────────────────────────────────────────────────


def test_la_liste_derivee_trouve_bien_des_jobs():
    """Garde-fou du garde-fou : un critère devenu trop strict ne renverrait rien,
    et tous les tests ci-dessous passeraient sur un ensemble vide."""
    assert len(_coroutines_de_job()) >= 8


def test_tous_les_jobs_du_paquet_sont_enregistres(enregistrements):
    appels, _ = enregistrements
    enregistres = {f.__name__ for f, _ in appels}

    manquants = _coroutines_de_job() - enregistres
    assert not manquants, (
        f"Ces coroutines de scheduler/ ne sont jamais enregistrées : "
        f"{sorted(manquants)}. Le code existe et ne s'exécutera jamais."
    )


def test_aucun_identifiant_en_double(enregistrements):
    """`replace_existing=True` fait qu'un doublon d'identifiant écrase
    silencieusement le job précédent."""
    appels, _ = enregistrements
    identifiants = [kw["id"] for _, kw in appels]

    doublons = sorted({i for i in identifiants if identifiants.count(i) > 1})
    assert not doublons, (
        f"Identifiants de job en double : {doublons}. Avec replace_existing=True, "
        f"le dernier enregistré efface le précédent sans rien signaler."
    )


def test_les_jobs_venus_d_ailleurs_sont_declares(enregistrements):
    """Un job dont le code ne vit pas dans `scheduler/` doit être justifié ici."""
    appels, _ = enregistrements
    du_paquet = _coroutines_de_job()

    non_declares = sorted(
        kw["id"]
        for f, kw in appels
        if f.__name__ not in du_paquet and kw["id"] not in JOBS_HORS_PAQUET
    )
    assert not non_declares, (
        f"Ces jobs sont enregistrés depuis l'extérieur de scheduler/ sans "
        f"justification : {non_declares}. Les déclarer dans JOBS_HORS_PAQUET."
    )


def test_aucune_declaration_orpheline(enregistrements):
    """La carte doit rester fidèle au territoire : une justification qui ne
    correspond plus à aucun job enregistré est un reste."""
    appels, _ = enregistrements
    identifiants = {kw["id"] for _, kw in appels}

    orphelines = sorted(set(JOBS_HORS_PAQUET) - identifiants)
    assert not orphelines, f"JOBS_HORS_PAQUET décrit des jobs qui n'existent plus : {orphelines}"


def test_chaque_job_est_remplacable(enregistrements):
    """Sans `replace_existing`, un redémarrage sur jobstore Redis lèverait
    `ConflictingIdError` et l'application ne démarrerait pas."""
    appels, _ = enregistrements
    sans = sorted(kw["id"] for _, kw in appels if not kw.get("replace_existing"))
    assert not sans, f"Jobs sans replace_existing : {sans}"


def test_l_ordonnanceur_est_demarre(enregistrements):
    _, faux = enregistrements
    faux.start.assert_called_once()


def test_stop_scheduler_n_attend_pas_les_jobs(monkeypatch):
    """`wait=False` : un arrêt qui attendrait la fin des jobs bloquerait
    l'extinction du conteneur derrière un scan en cours."""
    faux = MagicMock()
    monkeypatch.setattr(core, "scheduler", faux)

    core.stop_scheduler()

    faux.shutdown.assert_called_once_with(wait=False)


# ─── choix du magasin de jobs ────────────────────────────────────────────────


def test_sans_redis_url_magasin_en_memoire(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)

    sched = core._make_scheduler()

    assert isinstance(sched, AsyncIOScheduler)


def test_avec_redis_url_le_magasin_redis_est_configure(monkeypatch):
    """Le paquet `redis` n'est pas installé ici : on fournit un faux module,
    ce qui teste le chemin nominal sans dépendre de l'environnement."""
    captures: dict = {}

    class FauxRedisJobStore(MemoryJobStore):
        def __init__(self, **kwargs):
            super().__init__()
            captures.update(kwargs)

    faux_module = types.ModuleType("apscheduler.jobstores.redis")
    faux_module.RedisJobStore = FauxRedisJobStore
    monkeypatch.setitem(sys.modules, "apscheduler.jobstores.redis", faux_module)
    monkeypatch.setenv("REDIS_URL", "redis://exemple:6379/0")

    sched = core._make_scheduler()

    assert isinstance(sched, AsyncIOScheduler)
    assert captures["url"] == "redis://exemple:6379/0"
    # Les clés sont préfixées : plusieurs applications peuvent partager le Redis.
    assert captures["jobs_key"] == "cybervault:jobs"
    assert captures["run_times_key"] == "cybervault:run_times"


def test_redis_indisponible_retombe_en_memoire_sans_lever(monkeypatch):
    """Redis configuré mais injoignable : l'application doit démarrer quand même,
    avec des compteurs locaux, plutôt que refuser de se lancer."""
    monkeypatch.setitem(sys.modules, "apscheduler.jobstores.redis", None)
    monkeypatch.setenv("REDIS_URL", "redis://injoignable:6379/0")

    sched = core._make_scheduler()

    assert isinstance(sched, AsyncIOScheduler)
