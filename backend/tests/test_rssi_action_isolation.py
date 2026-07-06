"""Régression sécurité — isolation multi-tenant de `source_visit_id` sur les actions RSSI.

Un consultant ne doit pas pouvoir créer une action pour un client A en la reliant à une
visite appartenant à un autre client B (référence FK cross-tenant).
"""

from httpx import AsyncClient
from sqlalchemy import select

BASE = "/api/v1"


async def _auth_consultant(http_client: AsyncClient, email: str) -> dict:
    import app.core.database as _db_mod
    from app.models.user import User

    await http_client.post(
        f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"}
    )
    r = await http_client.post(
        f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"}
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    async with _db_mod.AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return headers


async def _create_client(http_client: AsyncClient, headers: dict, name: str) -> int:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_visit(http_client: AsyncClient, headers: dict, client_id: int) -> int:
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/visits",
        json={"scheduled_date": "2026-01-15", "visit_type": "monthly", "location": "onsite"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_source_visit_id_from_other_client_is_rejected(http_client: AsyncClient):
    headers = await _auth_consultant(http_client, "consultant-iso@test.com")
    client_a = await _create_client(http_client, headers, "Client A")
    client_b = await _create_client(http_client, headers, "Client B")
    visit_b = await _create_visit(http_client, headers, client_b)

    # Action sous client A référençant la visite du client B → refusée (422).
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_a}/actions",
        json={"title": "Isolation", "priority": "medium", "source_visit_id": visit_b},
        headers=headers,
    )
    assert r.status_code == 422, r.text

    # Avec une visite du BON client → acceptée (201).
    visit_a = await _create_visit(http_client, headers, client_a)
    r_ok = await http_client.post(
        f"{BASE}/rssi/clients/{client_a}/actions",
        json={"title": "Isolation", "priority": "medium", "source_visit_id": visit_a},
        headers=headers,
    )
    assert r_ok.status_code == 201, r_ok.text
    assert r_ok.json()["source_visit_id"] == visit_a
