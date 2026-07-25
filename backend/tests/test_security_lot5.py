"""
Verrous de non-regression — Lot 5 de la campagne de remediation securite.

Couvre :
  * S-1  — rate-limit anti-abus sur `/scans/trigger` et `POST /sites`
           (introspection du registre slowapi, meme approche que
           test_ratelimit_invariants).
  * S-9  — login sur email INEXISTANT execute quand meme un verify_password
           factice (temps constant) pour ne pas fuiter l'existence d'un compte
           par timing.

En env test le limiteur est neutralise (clef unique par requete loopback), donc
on prouve S-1 par introspection du decorateur, pas par martelage.
"""

from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.core.limiter import limiter
from app.main import app

BASE = "/api/v1"

_TRIGGER_KEY = "app.api.v1.endpoints.scans.trigger_scan"
_ADD_SITE_KEY = "app.api.v1.endpoints.sites.add_site"


def _route_limit(route_key: str):
    route_limits = limiter._route_limits
    assert route_key in route_limits, (
        f"Aucune limite enregistree pour {route_key!r} — @limiter.limit a-t-il "
        f"ete supprime ? Routes connues: {sorted(route_limits)}"
    )
    limits = route_limits[route_key]
    assert len(limits) == 1, f"{route_key} devrait porter exactement 1 limite, a {len(limits)}"
    return limits[0].limit


# ── S-1 : rate-limits declares sur les endpoints de scan/ajout de site ──────────


class TestScanTriggerLimitDeclared:
    def test_trigger_scan_has_a_rate_limit(self):
        """Sans limite, la boucle d'abus (trigger en rafale) sature le worker."""
        assert _route_limit(_TRIGGER_KEY) is not None

    def test_trigger_scan_limit_is_10_per_minute(self):
        item = _route_limit(_TRIGGER_KEY)
        assert item.amount == 10, f"trigger devrait etre 10/min, obtenu {item.amount}"
        assert item.GRANULARITY.name == "minute"
        assert item.GRANULARITY.seconds == 60

    def test_trigger_scan_limit_is_not_absurdly_high(self):
        item = _route_limit(_TRIGGER_KEY)
        per_minute = item.amount * (60 / item.GRANULARITY.seconds)
        assert per_minute <= 30, f"trigger autorise {per_minute}/min — trop permissif"


class TestAddSiteLimitDeclared:
    def test_add_site_has_a_rate_limit(self):
        """Sans limite, on peut inscrire des sites tiers en masse (vecteur recon)."""
        assert _route_limit(_ADD_SITE_KEY) is not None

    def test_add_site_limit_is_20_per_minute(self):
        item = _route_limit(_ADD_SITE_KEY)
        assert item.amount == 20, f"add_site devrait etre 20/min, obtenu {item.amount}"
        assert item.GRANULARITY.name == "minute"
        assert item.GRANULARITY.seconds == 60


# ── S-9 : login temps constant sur email inexistant ─────────────────────────────


class TestLoginConstantTimeOnUnknownEmail:
    async def test_unknown_email_runs_dummy_hash(self):
        """Un login sur un email absent DOIT executer dummy_verify_password.

        Sinon le chemin "pas de compte" saute le bcrypt et repond plus vite que
        "compte existe + mauvais mot de passe" -> enumeration par timing.
        """
        with patch("app.api.v1.endpoints.auth.dummy_verify_password") as dummy:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/auth/login",
                    json={"email": "ghost-account@test.com", "password": "whatever-Pass123!"},
                )
        assert r.status_code == 401
        dummy.assert_called_once()
