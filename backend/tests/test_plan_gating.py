"""Gating par tier (require_min_tier) — features réservées aux plans payants.

Grille : analyse de code + scripts de remédiation = Starter+ (tier 2) ;
surveillance dark web + dossier = Pro+ (tier 3). Le plan Gratuit (tier 1 ou aucun
abonnement) doit recevoir 403 sur ces endpoints, un plan suffisant doit passer le gate
(on vérifie alors "pas 403" : 422/404 prouvent que la dépendance de tier a laissé passer).
"""

import pytest
from httpx import AsyncClient

from tests.conftest import create_plan_and_subscription, register_and_login

BASE = "/api/v1"


# ── Analyse de code : Starter+ (tier 2) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_code_scan_blocked_for_free(http_client: AsyncClient):
    headers = await register_and_login(http_client, "gate_free_code@test.com")
    r = await http_client.post(
        f"{BASE}/code-scans", json={"repo_url": "https://github.com/acme/app"}, headers=headers
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_code_scan_allowed_for_starter(http_client: AsyncClient):
    headers = await register_and_login(http_client, "gate_starter_code@test.com")
    await create_plan_and_subscription(http_client, headers, tier=2)
    # body vide -> 422 (validation) : prouve que le gate tier a laissé passer (pas 403)
    r = await http_client.post(f"{BASE}/code-scans", json={}, headers=headers)
    assert r.status_code != 403


# ── Dark web : Pro+ (tier 3) ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_darkweb_status_blocked_for_starter(http_client: AsyncClient):
    headers = await register_and_login(http_client, "gate_starter_dw@test.com")
    await create_plan_and_subscription(http_client, headers, tier=2)
    r = await http_client.get(f"{BASE}/darkweb/status", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_darkweb_status_allowed_for_pro(http_client: AsyncClient):
    headers = await register_and_login(http_client, "gate_pro_dw@test.com")
    await create_plan_and_subscription(http_client, headers, tier=3)
    r = await http_client.get(f"{BASE}/darkweb/status", headers=headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_darkweb_dossier_create_blocked_for_starter(http_client: AsyncClient):
    headers = await register_and_login(http_client, "gate_starter_dossier@test.com")
    await create_plan_and_subscription(http_client, headers, tier=2)
    r = await http_client.post(f"{BASE}/darkweb-dossier", headers=headers)
    assert r.status_code == 403


# ── Scripts de remédiation : Starter+ (tier 2) ────────────────────────────────


@pytest.mark.asyncio
async def test_remediation_blocked_for_free(http_client: AsyncClient):
    headers = await register_and_login(http_client, "gate_free_remed@test.com")
    # Le gate tier s'évalue avant le 404 (scan inexistant) : free => 403.
    r = await http_client.get(f"{BASE}/scans/1/remediation/ssl_fix", headers=headers)
    assert r.status_code == 403
