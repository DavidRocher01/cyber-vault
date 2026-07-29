"""Recette post-mise-en-production — fixtures partagees.

Cette suite tape une instance DEPLOYEE (par defaut la prod) via HTTP, avec un
compte CANARI dedie. Elle n'importe PAS l'app : c'est une recette boite noire.

Variables d'environnement :
- RECETTE_BASE_URL : racine de l'API (defaut https://rochercybersecurite.com)
- RECETTE_EMAIL / RECETTE_PASSWORD : identifiants du compte canari dedie
  (jamais un vrai compte client — la suite fait table rase de son coffre et de
  ses scans a chaque passage).

Les tests d'ecriture (vault, scan) sont SKIP si les identifiants sont absents,
pour qu'un run "lecture seule" reste possible sans secret.
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

BASE_URL = os.environ.get("RECETTE_BASE_URL", "https://rochercybersecurite.com").rstrip("/")
API = f"{BASE_URL}/api/v1"
CANARY_EMAIL = os.environ.get("RECETTE_EMAIL", "")
CANARY_PASSWORD = os.environ.get("RECETTE_PASSWORD", "")
# Prefixe des ressources creees par la recette (tracabilite / nettoyage).
MARKER = "RECETTE"
TIMEOUT = httpx.Timeout(30.0, connect=15.0)

_requires_canary = pytest.mark.skipif(
    not (CANARY_EMAIL and CANARY_PASSWORD),
    reason="RECETTE_EMAIL / RECETTE_PASSWORD non definis (tests d'ecriture ignores)",
)
requires_canary = _requires_canary


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def api() -> str:
    return API


# La recette demarre juste apres la bascule des taches ECS : une connexion peut
# etre coupee en plein etablissement (reset TCP), ce qui declenchait un rollback
# de prod alors que rien n'etait casse. `retries` de httpx ne rejoue QUE les
# echecs de connexion — une reponse HTTP (401, 500...) reste un echec franc, donc
# aucune regression fonctionnelle n'est masquee.
_TRANSPORT_RETRIES = 3

# `aws ecs wait services-stable` rend la main avant que l'ancienne cible ait fini
# de se desenregistrer de l'ALB : on exige des reponses saines CONSECUTIVES avant
# de lancer la suite, sinon les premiers tests tapent une cible en cours de retrait.
_READY_CONSECUTIVE = 3
_READY_TIMEOUT_S = 90.0
_READY_INTERVAL_S = 1.0


def _make_client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        timeout=TIMEOUT,
        follow_redirects=False,
        transport=httpx.HTTPTransport(retries=_TRANSPORT_RETRIES),
    )


@pytest.fixture(scope="session", autouse=True)
def backend_ready() -> None:
    """Attend que l'instance deployee reponde de facon stable avant les tests."""
    deadline = time.monotonic() + _READY_TIMEOUT_S
    streak = 0
    derniere = "aucune tentative"
    with _make_client() as c:
        while time.monotonic() < deadline:
            try:
                r = c.get(f"{API}/health")
                if r.status_code == 200:
                    streak += 1
                    if streak >= _READY_CONSECUTIVE:
                        return
                else:
                    streak = 0
                    derniere = f"HTTP {r.status_code}"
            except httpx.HTTPError as exc:
                streak = 0
                derniere = f"{type(exc).__name__}: {exc}"
            time.sleep(_READY_INTERVAL_S)
    pytest.fail(
        f"Backend non stabilise apres {_READY_TIMEOUT_S:.0f}s "
        f"({_READY_CONSECUTIVE} reponses 200 consecutives attendues sur {API}/health). "
        f"Derniere observation : {derniere}"
    )


@pytest.fixture()
def client() -> httpx.Client:
    """Client anonyme (cookies actives pour le refresh_token httpOnly)."""
    with _make_client() as c:
        yield c


def _login(c: httpx.Client) -> str:
    r = c.post(
        f"{API}/auth/login",
        json={"email": CANARY_EMAIL, "password": CANARY_PASSWORD},
    )
    assert r.status_code == 200, f"login canari KO: {r.status_code} {r.text[:300]}"
    body = r.json()
    token = body.get("access_token")
    assert token, f"pas d'access_token dans la reponse login: {body}"
    return token


@pytest.fixture(scope="session")
def canary(backend_ready: None) -> dict:
    """Session canari : client httpx authentifie (Bearer + cookie refresh).

    Fait TABLE RASE au demarrage (coffre + url-scans) pour ne jamais accumuler
    de residus d'un run precedent qui aurait crashe avant son teardown.
    """
    if not (CANARY_EMAIL and CANARY_PASSWORD):
        pytest.skip("compte canari non configure")
    c = _make_client()
    token = _login(c)
    c.headers["Authorization"] = f"Bearer {token}"
    _wipe_canary(c)
    yield {"client": c, "token": token, "email": CANARY_EMAIL}
    # Nettoyage final + fermeture.
    _wipe_canary(c)
    c.close()


# Garde-fou : le drainage relit toujours la page 1, une boucle bornee evite de
# tourner indefiniment si un DELETE echoue silencieusement.
_WIPE_MAX_PAGES = 20


def _wipe_warn(quoi: str, detail: object) -> None:
    """Le wipe reste non bloquant (c'est un filet de securite, pas un test) mais
    il ne doit plus echouer en silence : un nettoyage qui ne nettoie rien s'est
    deja produit sans que personne le voie."""
    print(f"[wipe canari] nettoyage {quoi} incomplet: {detail}")


def _wipe_canary(c: httpx.Client) -> None:
    """Fait table rase des donnees mutables du canari (coffre, url-scans, sites,
    clients RSSI) — filet de securite si un run precedent a crashe avant teardown.
    NB: la progression training n'est pas nettoyable (pas d'endpoint DELETE) mais
    reste idempotente."""
    try:
        items = c.get(f"{API}/vault/", params={"limit": 200}).json()
        for it in items:
            c.delete(f"{API}/vault/{it['id']}")
    except Exception as exc:
        _wipe_warn("vault", exc)
    try:
        # per_page est plafonne cote API a 50 (Query(10, ge=1, le=50)) : demander
        # 100 renvoyait un 422 dont le corps n'a pas de cle "items" -> la boucle
        # tournait a vide et les scans du canari s'accumulaient a chaque run.
        # On draine page 1 en boucle puisque chaque passage supprime ce qu'il lit.
        for _ in range(_WIPE_MAX_PAGES):
            resp = c.get(f"{API}/url-scans", params={"page": 1, "per_page": 50})
            if resp.status_code != 200:
                _wipe_warn("url-scans", f"HTTP {resp.status_code}: {resp.text[:200]}")
                break
            scans = resp.json().get("items", [])
            if not scans:
                break
            for s in scans:
                c.delete(f"{API}/url-scans/{s['id']}")
    except Exception as exc:
        _wipe_warn("url-scans", exc)
    try:
        for site in c.get(f"{API}/sites").json():
            c.delete(f"{API}/sites/{site['id']}")  # soft delete
    except Exception as exc:
        _wipe_warn("sites", exc)
    try:
        for cl in c.get(f"{API}/rssi/clients").json():
            if str(cl.get("name", "")).startswith(MARKER):
                c.delete(f"{API}/rssi/clients/{cl['id']}")
    except Exception as exc:
        _wipe_warn("rssi/clients", exc)
    try:
        for camp in c.get(f"{API}/phishing/campaigns").json():
            if str(camp.get("name", "")).startswith(MARKER):
                c.delete(f"{API}/phishing/campaigns/{camp['id']}")
    except Exception as exc:
        _wipe_warn("phishing/campaigns", exc)


def poll_until(fn, predicate, timeout_s: float, interval_s: float = 3.0):
    """Poll fn() jusqu'a predicate(result) vrai ou timeout. Retourne le dernier
    resultat (meme si timeout, pour permettre une assertion parlante)."""
    deadline = time.monotonic() + timeout_s
    result = fn()
    while time.monotonic() < deadline:
        if predicate(result):
            return result
        time.sleep(interval_s)
        result = fn()
    return result
