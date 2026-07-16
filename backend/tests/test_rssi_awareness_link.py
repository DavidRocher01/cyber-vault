"""Unification RSSI <-> Sensibilisation : activer la formation d'un client crée et lie
une organisation awareness (propriété du consultant), de façon idempotente et isolée."""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login

BASE = "/api/v1"


async def _consultant(client: AsyncClient, email: str) -> dict:
    from sqlalchemy import select

    import app.core.database as _db
    from app.core.security import decode_access_token
    from app.models.user import User

    headers = await register_and_login(client, email)
    uid = int(decode_access_token(headers["Authorization"].removeprefix("Bearer ").strip()))
    async with _db.AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.id == uid))).scalar_one()
        u.is_rssi_consultant = True
        await db.commit()
    return headers


async def _create_client(client: AsyncClient, headers: dict, name: str, formula: str) -> int:
    r = await client.post(
        f"{BASE}/rssi/clients", headers=headers, json={"name": name, "formula": formula}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_enable_awareness_creates_and_links(http_client: AsyncClient):
    ch = await _consultant(http_client, "aw_consult@test.com")
    cid = await _create_client(http_client, ch, "Acme", "premium")

    r = await http_client.post(f"{BASE}/rssi/clients/{cid}/awareness", headers=ch)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["already"] is False
    assert data["name"] == "Acme"
    assert data["max_learners"] == 25  # premium
    org_id = data["id"]

    # Le client expose désormais le lien
    r = await http_client.get(f"{BASE}/rssi/clients/{cid}", headers=ch)
    assert r.json()["awareness_organization_id"] == org_id

    # L'organisation apparaît dans la liste awareness du consultant (même owner)
    r = await http_client.get(f"{BASE}/awareness/organizations", headers=ch)
    assert any(o["id"] == org_id for o in r.json())


@pytest.mark.asyncio
async def test_enable_awareness_idempotent(http_client: AsyncClient):
    ch = await _consultant(http_client, "aw_consult2@test.com")
    cid = await _create_client(http_client, ch, "Beta", "essentiel")

    r1 = await http_client.post(f"{BASE}/rssi/clients/{cid}/awareness", headers=ch)
    r2 = await http_client.post(f"{BASE}/rssi/clients/{cid}/awareness", headers=ch)
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["already"] is True
    assert r1.json()["max_learners"] == 10  # essentiel


@pytest.mark.asyncio
async def test_enable_awareness_isolation(http_client: AsyncClient):
    chA = await _consultant(http_client, "aw_A@test.com")
    chB = await _consultant(http_client, "aw_B@test.com")
    cid_a = await _create_client(http_client, chA, "Client A", "premium")

    # B ne peut pas activer la sensibilisation sur le client de A -> 404
    r = await http_client.post(f"{BASE}/rssi/clients/{cid_a}/awareness", headers=chB)
    assert r.status_code == 404
