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


@pytest.fixture()
def client() -> httpx.Client:
    """Client anonyme (cookies actives pour le refresh_token httpOnly)."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, follow_redirects=False) as c:
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
def canary() -> dict:
    """Session canari : client httpx authentifie (Bearer + cookie refresh).

    Fait TABLE RASE au demarrage (coffre + url-scans) pour ne jamais accumuler
    de residus d'un run precedent qui aurait crashe avant son teardown.
    """
    if not (CANARY_EMAIL and CANARY_PASSWORD):
        pytest.skip("compte canari non configure")
    c = httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, follow_redirects=False)
    token = _login(c)
    c.headers["Authorization"] = f"Bearer {token}"
    _wipe_canary(c)
    yield {"client": c, "token": token, "email": CANARY_EMAIL}
    # Nettoyage final + fermeture.
    _wipe_canary(c)
    c.close()


def _wipe_canary(c: httpx.Client) -> None:
    """Supprime tous les items de coffre et url-scans du canari (clean slate)."""
    try:
        items = c.get(f"{API}/vault/", params={"limit": 200}).json()
        for it in items:
            c.delete(f"{API}/vault/{it['id']}")
    except Exception:
        pass
    try:
        page = c.get(f"{API}/url-scans", params={"page": 1, "per_page": 100}).json()
        for s in page.get("items", []):
            c.delete(f"{API}/url-scans/{s['id']}")
    except Exception:
        pass


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
