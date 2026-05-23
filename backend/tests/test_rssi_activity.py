"""
Integration tests — /api/v1/rssi/clients/{id}/activity (Sprint 3)
Covers: auth guards, log creation, list pagination, invalid inputs, security isolation.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1"


# ── helpers ────────────────────────────────────────────────────────────────────

async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await http_client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_client(http_client: AsyncClient, headers: dict, name: str = "Acme") -> dict:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _log(http_client: AsyncClient, headers: dict, client_id: int, action_type: str = "view_client", **kwargs) -> dict:
    payload = {"action_type": action_type, **kwargs}
    r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/activity", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Auth guards ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_activity_requires_auth(http_client: AsyncClient):
    r = await http_client.post(f"{BASE}/rssi/clients/1/activity", json={"action_type": "view_client"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_activity_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients/1/activity")
    assert r.status_code == 401


# ── 404 on unknown / other-user client ────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_activity_unknown_client(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_unknown@test.com")
    r = await http_client.post(f"{BASE}/rssi/clients/99999/activity", json={"action_type": "view_client"}, headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_activity_unknown_client(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_getunknown@test.com")
    r = await http_client.get(f"{BASE}/rssi/clients/99999/activity", headers=h)
    assert r.status_code == 404


# ── Log creation ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_activity_basic(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_basic@test.com")
    c = await _create_client(http_client, h, "BasicCo")

    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/activity",
        json={"action_type": "view_client"},
        headers=h,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["action_type"] == "view_client"
    assert data["client_id"] == c["id"]
    assert data["resource_type"] is None
    assert data["resource_id"] is None
    assert "performed_at" in data
    assert "id" in data


@pytest.mark.asyncio
async def test_log_activity_with_resource(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_resource@test.com")
    c = await _create_client(http_client, h, "ResoCo")

    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/activity",
        json={"action_type": "view_findings", "resource_type": "scan", "resource_id": 42},
        headers=h,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["resource_type"] == "scan"
    assert data["resource_id"] == 42


@pytest.mark.asyncio
async def test_log_activity_all_valid_types(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_alltypes@test.com")
    c = await _create_client(http_client, h, "AllTypesCo")

    valid_types = [
        "view_client", "view_sites", "view_scans", "view_findings",
        "generate_report", "send_deliverable", "create_action", "update_action",
        "create_visit", "update_visit",
    ]
    for action in valid_types:
        r = await http_client.post(
            f"{BASE}/rssi/clients/{c['id']}/activity",
            json={"action_type": action},
            headers=h,
        )
        assert r.status_code == 201, f"Failed for action_type={action}: {r.text}"


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_activity_invalid_action_type(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_invalid@test.com")
    c = await _create_client(http_client, h, "InvalidCo")

    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/activity",
        json={"action_type": "hack_the_planet"},
        headers=h,
    )
    assert r.status_code == 422


# ── List / pagination ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_activity_empty(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_emptylist@test.com")
    c = await _create_client(http_client, h, "EmptyCo")

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/activity", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_activity_returns_entries(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_list@test.com")
    c = await _create_client(http_client, h, "ListCo")

    await _log(http_client, h, c["id"], "view_client")
    await _log(http_client, h, c["id"], "view_scans")
    await _log(http_client, h, c["id"], "view_findings")

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/activity", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    # Most recent first
    assert data[0]["action_type"] == "view_findings"


@pytest.mark.asyncio
async def test_get_activity_limit(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_limit@test.com")
    c = await _create_client(http_client, h, "LimitCo")

    for _ in range(5):
        await _log(http_client, h, c["id"], "view_client")

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/activity?limit=3", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_get_activity_limit_invalid(http_client: AsyncClient):
    h = await _auth(http_client, "actlog_badlimit@test.com")
    c = await _create_client(http_client, h, "BadLimitCo")

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/activity?limit=0", headers=h)
    assert r.status_code == 422

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/activity?limit=201", headers=h)
    assert r.status_code == 422


# ── Security isolation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cannot_log_activity_on_other_user_client(http_client: AsyncClient):
    h1 = await _auth(http_client, "actlog_owner@test.com")
    h2 = await _auth(http_client, "actlog_attacker@test.com")
    c = await _create_client(http_client, h1, "OwnerCo")

    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/activity",
        json={"action_type": "view_client"},
        headers=h2,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cannot_read_activity_of_other_user_client(http_client: AsyncClient):
    h1 = await _auth(http_client, "actlog_owner2@test.com")
    h2 = await _auth(http_client, "actlog_spy@test.com")
    c = await _create_client(http_client, h1, "OwnerCo2")
    await _log(http_client, h1, c["id"], "view_client")

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/activity", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_activity_logs_are_isolated_per_consultant(http_client: AsyncClient):
    """Two consultants with clients of same name — each sees only their own logs."""
    h1 = await _auth(http_client, "actlog_iso1@test.com")
    h2 = await _auth(http_client, "actlog_iso2@test.com")
    c1 = await _create_client(http_client, h1, "SharedName")
    c2 = await _create_client(http_client, h2, "SharedName")

    await _log(http_client, h1, c1["id"], "view_client")
    await _log(http_client, h1, c1["id"], "view_scans")
    await _log(http_client, h2, c2["id"], "view_client")

    r1 = await http_client.get(f"{BASE}/rssi/clients/{c1['id']}/activity", headers=h1)
    r2 = await http_client.get(f"{BASE}/rssi/clients/{c2['id']}/activity", headers=h2)
    assert len(r1.json()) == 2
    assert len(r2.json()) == 1
    # All entries belong to the correct consultant
    for entry in r1.json():
        assert entry["client_id"] == c1["id"]
    for entry in r2.json():
        assert entry["client_id"] == c2["id"]
