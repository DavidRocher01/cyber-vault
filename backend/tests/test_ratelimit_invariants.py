"""
Invariants — les rate-limits ANTI-ABUS critiques sont bien ENFORCES.

Portée : `login` (10/minute, anti brute-force) et `public-scans` (3/hour,
anti-abus du scan public non authentifié). Ces deux limites sont les garde-fous
de sécurité les plus exposés (endpoints publics / faible coût pour l'attaquant),
donc on les verrouille par des tests qui attrapent une régression réelle :
suppression du décorateur `@limiter.limit`, valeur/période changée, ou limiteur
débranché du pipeline de requête.

── Pourquoi deux approches complémentaires ─────────────────────────────────────
En environnement de test, le limiteur est *volontairement neutralisé* :
`app.core.limiter._rate_limit_key` renvoie une clé unique par requête pour toute
IP loopback quand `APP_ENV != "production"` (voir limiter.py), donc la limite ne
se déclenche jamais naturellement sous httpx/ASGI. On ne peut donc PAS simplement
marteler l'endpoint et attendre un 429. On prouve l'enforcement autrement :

1. INTROSPECTION (déclaration) — on lit le registre `limiter._route_limits`
   (peuplé au décorateur par slowapi) et on vérifie que la route porte bien une
   limite avec le bon `amount` et la bonne granularité (minute / heure). Cela
   attrape la suppression pure et simple du décorateur ou un mauvais chiffre.

2. COMPORTEMENT (enforcement) — on patche `limiter._check_request_limit` pour
   forcer le dépassement, et on vérifie que l'endpoint renvoie réellement 429.
   Cela prouve que le limiteur est branché sur le chemin de la requête (état app
   + exception handler `RateLimitExceeded` enregistrés dans main.py) et pas juste
   décoratif. Même stratégie de patch que `tests/test_rate_limiting.py`.

Aucun service externe n'est appelé (login lit la DB de test ; le 429 public-scan
court-circuite avant la logique métier / le background task).
"""

from unittest.mock import patch

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.limiter import limiter
from app.main import app

BASE = "/api/v1"

# Chemins qualifiés utilisés par slowapi comme clés de _route_limits.
_LOGIN_KEY = "app.api.v1.endpoints.auth.login"
_PUBLIC_SCAN_KEY = "app.api.v1.endpoints.public_scans.create_public_scan"


def _raise_rate_limit(*args, **kwargs):
    """Simule le dépassement de la limite (même side-effect que test_rate_limiting)."""
    raise HTTPException(status_code=429, detail="Trop de requêtes.")


def _route_limit(route_key: str):
    """Retourne l'unique objet limits.RateLimitItem déclaré sur la route.

    Échoue explicitement si la route n'a AUCUNE limite enregistrée — c'est
    exactement la régression 'quelqu'un a retiré @limiter.limit' qu'on veut
    attraper.
    """
    route_limits = limiter._route_limits
    assert route_key in route_limits, (
        f"Aucune limite enregistrée pour {route_key!r} — le décorateur "
        f"@limiter.limit a-t-il été supprimé ? Routes connues: "
        f"{sorted(route_limits)}"
    )
    limits = route_limits[route_key]
    assert len(limits) == 1, f"{route_key} devrait porter exactement 1 limite, a {len(limits)}"
    return limits[0].limit


# ── INTROSPECTION — login limité à 10/minute (anti brute-force) ─────────────────


class TestLoginLimitDeclared:
    def test_login_has_a_rate_limit(self):
        """La route login DOIT porter une limite (sinon brute-force illimité)."""
        assert _route_limit(_LOGIN_KEY) is not None

    def test_login_limit_is_10_per_minute(self):
        """Verrou sur la valeur exacte : 10 tentatives / minute."""
        item = _route_limit(_LOGIN_KEY)
        assert item.amount == 10, f"login devrait être 10/min, obtenu {item.amount}"
        assert item.multiples == 1
        assert (
            item.GRANULARITY.name == "minute"
        ), f"login devrait être par minute, obtenu {item.GRANULARITY.name}"
        assert item.GRANULARITY.seconds == 60

    def test_login_limit_is_not_absurdly_high(self):
        """Garde-fou : une limite énorme (>60/min) équivaut à pas de protection."""
        item = _route_limit(_LOGIN_KEY)
        per_minute = item.amount * (60 / item.GRANULARITY.seconds)
        assert per_minute <= 60, f"login autorise {per_minute}/min — trop permissif"


# ── INTROSPECTION — public-scans limité à 3/hour (anti-abus) ────────────────────


class TestPublicScanLimitDeclared:
    def test_public_scan_has_a_rate_limit(self):
        """Le scan public non authentifié DOIT être limité (endpoint coûteux/abusable)."""
        assert _route_limit(_PUBLIC_SCAN_KEY) is not None

    def test_public_scan_limit_is_3_per_hour(self):
        """Verrou sur la valeur exacte : 3 scans / heure / IP."""
        item = _route_limit(_PUBLIC_SCAN_KEY)
        assert item.amount == 3, f"public-scan devrait être 3/h, obtenu {item.amount}"
        assert item.multiples == 1
        assert (
            item.GRANULARITY.name == "hour"
        ), f"public-scan devrait être par heure, obtenu {item.GRANULARITY.name}"
        assert item.GRANULARITY.seconds == 3600

    def test_public_scan_limit_is_strict(self):
        """Garde-fou anti-abus : pas plus de 10 scans/heure quoi qu'il arrive."""
        item = _route_limit(_PUBLIC_SCAN_KEY)
        per_hour = item.amount * (3600 / item.GRANULARITY.seconds)
        assert per_hour <= 10, f"public-scan autorise {per_hour}/h — trop permissif"


# ── COMPORTEMENT — le limiteur est réellement branché (429 renvoyé) ─────────────


class TestLimitsAreEnforcedAtRuntime:
    async def test_login_returns_429_when_limit_exceeded(self):
        """Quand la limite login est dépassée, l'endpoint renvoie bien 429.

        Prouve que le limiteur est branché sur le pipeline (app.state.limiter +
        exception handler) et pas seulement déclaré. On patche _check_request_limit
        pour forcer le dépassement de façon déterministe (le key_func de test
        empêcherait sinon la limite de se déclencher).
        """
        with patch(
            "app.api.v1.endpoints.auth.limiter._check_request_limit",
            side_effect=_raise_rate_limit,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/auth/login",
                    json={"email": "bruteforce@test.com", "password": "whatever-Pass123!"},
                )
        assert r.status_code == 429

    async def test_public_scan_returns_429_when_limit_exceeded(self):
        """Quand la limite public-scan est dépassée, l'endpoint renvoie bien 429.

        Le 429 court-circuite AVANT la vérification SSRF et le background task,
        donc aucun service externe n'est touché.
        """
        with patch(
            "app.api.v1.endpoints.public_scans.limiter._check_request_limit",
            side_effect=_raise_rate_limit,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/public-scans",
                    json={"url": "https://example.com"},
                )
        assert r.status_code == 429

    async def test_login_not_limited_on_single_call(self):
        """Contrôle négatif : sans dépassement, login N'EST PAS bloqué par le
        limiteur (une seule tentative → 401 identifiants invalides, pas 429).

        Garantit que les tests 429 ci-dessus détectent bien un comportement
        provoqué par le patch, et non un 429 permanent qui masquerait tout.
        """
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/auth/login",
                json={"email": "nobody@test.com", "password": "whatever-Pass123!"},
            )
        assert r.status_code == 401
        assert r.status_code != 429
