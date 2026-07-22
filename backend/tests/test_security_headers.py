"""Vérifie que SecurityHeadersMiddleware pose une CSP durcie + les en-têtes de sécurité."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _headers() -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/plans")  # endpoint public
    return dict(r.headers)


@pytest.mark.asyncio
async def test_csp_is_hardened():
    csp = (await _headers()).get("content-security-policy", "")
    # Scripts verrouillés à 'self' (le '; ' garantit l'absence d'unsafe-inline côté script).
    assert "script-src 'self'; " in csp
    assert "default-src 'self'" in csp
    # Directives de durcissement — sans repli sur default-src, donc réellement fermées.
    for directive in (
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-src 'none'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ):
        assert directive in csp, directive


@pytest.mark.asyncio
async def test_baseline_security_headers_present():
    h = await _headers()
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("x-frame-options") == "DENY"
    assert h.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert h.get("cross-origin-opener-policy") == "same-origin"
