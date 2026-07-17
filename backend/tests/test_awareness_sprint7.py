"""
Tests — Awareness Sprint 7 : multi-tenancy dashboards.

Couvre :
  - GET /awareness/consultant/dashboard : structure, isolation (orgs de l'user uniquement)
  - GET /awareness/organizations/{id}/admin-dashboard : funnel, programmes, at-risk vides
  - Sécurité : auth requise, org d'un autre user → 404
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _admin_headers(email: str) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
        r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── Consultant dashboard ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consultant_dashboard_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/consultant/dashboard")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_consultant_dashboard_empty_for_new_user():
    h = await _admin_headers("consultant_new@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/consultant/dashboard", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["organizations"] == []
    assert body["summary"]["total_organizations"] == 0
    assert body["summary"]["total_learners"] == 0


@pytest.mark.asyncio
async def test_consultant_dashboard_shows_own_orgs_only():
    h1 = await _admin_headers("consultant1@test.com")
    h2 = await _admin_headers("consultant2@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/awareness/organizations", json={"name": "Org C1"}, headers=h1)
        await c.post(f"{BASE}/awareness/organizations", json={"name": "Org C2"}, headers=h2)
        r1 = await c.get(f"{BASE}/awareness/consultant/dashboard", headers=h1)
        r2 = await c.get(f"{BASE}/awareness/consultant/dashboard", headers=h2)
    assert len(r1.json()["organizations"]) == 1
    assert r1.json()["organizations"][0]["name"] == "Org C1"
    assert len(r2.json()["organizations"]) == 1
    assert r2.json()["organizations"][0]["name"] == "Org C2"


@pytest.mark.asyncio
async def test_consultant_dashboard_kpi_structure():
    h = await _admin_headers("consultant_kpi@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations",
                json={"name": "KPI Org", "max_learners": 20},
                headers=h,
            )
        ).json()["id"]
        r = await c.get(f"{BASE}/awareness/consultant/dashboard", headers=h)

    org_kpi = r.json()["organizations"][0]
    assert "learner_count" in org_kpi
    assert "completion_rate" in org_kpi
    assert "at_risk_count" in org_kpi
    assert "certificates_issued" in org_kpi
    assert "alerts" in org_kpi
    assert isinstance(org_kpi["alerts"], list)


@pytest.mark.asyncio
async def test_consultant_dashboard_summary_counts():
    h = await _admin_headers("consultant_sum@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/awareness/organizations", json={"name": "Org A"}, headers=h)
        await c.post(f"{BASE}/awareness/organizations", json={"name": "Org B"}, headers=h)
        r = await c.get(f"{BASE}/awareness/consultant/dashboard", headers=h)

    summary = r.json()["summary"]
    assert summary["total_organizations"] == 2
    assert "global_completion_rate" in summary
    assert "total_at_risk_learners" in summary


# ── Org Admin dashboard ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_org_admin_dashboard_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/organizations/1/admin-dashboard")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_org_admin_dashboard_404_other_user():
    h1 = await _admin_headers("dash_owner@test.com")
    h2 = await _admin_headers("dash_other@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations", json={"name": "Private Org"}, headers=h1
            )
        ).json()["id"]
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/admin-dashboard", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_org_admin_dashboard_structure():
    h = await _admin_headers("dash_admin@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Dash Org"}, headers=h)
        ).json()["id"]
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/admin-dashboard", headers=h)

    assert r.status_code == 200
    body = r.json()
    assert "organization" in body
    assert "engagement" in body
    assert "programs" in body
    assert "at_risk_learners" in body
    assert "certificates_issued" in body


@pytest.mark.asyncio
async def test_org_admin_dashboard_engagement_funnel():
    h = await _admin_headers("funnel_admin@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations",
                json={"name": "Funnel Org", "max_learners": 50},
                headers=h,
            )
        ).json()["id"]
        # Add 3 learners
        for i in range(3):
            await c.post(
                f"{BASE}/awareness/organizations/{org_id}/learners",
                json={"email": f"learner{i}@funnel.com"},
                headers=h,
            )
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/admin-dashboard", headers=h)

    engagement = r.json()["engagement"]
    assert engagement["total_learners"] == 3
    assert engagement["enrolled_learners"] == 0
    assert engagement["enrollment_rate"] == 0.0


@pytest.mark.asyncio
async def test_org_admin_dashboard_at_risk_empty_initially():
    h = await _admin_headers("risk_admin@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Risk Org"}, headers=h)
        ).json()["id"]
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/admin-dashboard", headers=h)

    assert r.json()["at_risk_learners"] == []
