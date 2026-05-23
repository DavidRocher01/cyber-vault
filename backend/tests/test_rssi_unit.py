"""
Unit tests for RSSI Externalisé endpoints.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.rssi import (
    list_clients,
    create_client,
    update_client,
    delete_client,
    RssiClientCreate,
    RssiClientUpdate,
)
from app.models.rssi_client import RssiClient
from app.models.user import User


# ── helpers ────────────────────────────────────────────────────────────────────

def _user(uid: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uid
    return u


def _client(cid: int = 10, uid: int = 1, name: str = "Acme") -> MagicMock:
    c = MagicMock(spec=RssiClient)
    c.id = cid
    c.consultant_user_id = uid
    c.name = name
    c.email = "acme@example.com"
    c.description = "Test client"
    c.formula = None
    c.monthly_amount = None
    c.contract_start_date = None
    c.contract_renewal_at = None
    c.status = "active"
    c.notion_workspace_url = None
    c.pipedrive_deal_id = None
    c.pennylane_customer_id = None
    c.created_at = datetime.now(timezone.utc)
    c.updated_at = None
    return c


def _db_empty():
    db = AsyncMock()

    async def execute(query):
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        r.scalar_one_or_none.return_value = None
        return r

    db.execute = execute
    return db


def _db_with_clients(clients: list):
    db = AsyncMock()
    call_count = {"n": 0}

    async def execute(query):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalars.return_value.all.return_value = clients
        else:
            r.scalars.return_value.all.return_value = []
        return r

    db.execute = execute
    return db


# ── list_clients ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_clients_empty():
    result = await list_clients(_user(), _db_empty())
    assert result == []


@pytest.mark.asyncio
async def test_list_clients_returns_client_with_stats():
    client = _client()
    result = await list_clients(_user(), _db_with_clients([client]))
    assert len(result) == 1
    c = result[0]
    assert c.id == 10
    assert c.name == "Acme"
    assert c.sites_count == 0
    assert c.worst_status is None
    assert c.status == "active"


# ── create_client ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_client_success():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def refresh(obj):
        obj.id = 42
        obj.formula = None
        obj.monthly_amount = None
        obj.contract_start_date = None
        obj.contract_renewal_at = None
        obj.status = "active"
        obj.notion_workspace_url = None
        obj.pipedrive_deal_id = None
        obj.pennylane_customer_id = None
        obj.updated_at = None
        obj.created_at = datetime.now(timezone.utc)

    db.refresh = refresh

    payload = RssiClientCreate(name="NewCo", email="new@example.com", description="desc")
    result = await create_client(payload, _user(), db)

    assert result.name == "NewCo"
    assert result.email == "new@example.com"
    assert result.sites_count == 0
    assert result.worst_status is None
    assert result.status == "active"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_client_with_formula():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def refresh(obj):
        obj.id = 43
        obj.formula = "premium"
        obj.monthly_amount = 3200.0
        obj.contract_start_date = None
        obj.contract_renewal_at = None
        obj.status = "active"
        obj.notion_workspace_url = None
        obj.pipedrive_deal_id = None
        obj.pennylane_customer_id = None
        obj.updated_at = None
        obj.created_at = datetime.now(timezone.utc)

    db.refresh = refresh

    payload = RssiClientCreate(name="Corp", formula="premium", monthly_amount=3200.0)
    result = await create_client(payload, _user(), db)

    assert result.formula == "premium"
    assert result.monthly_amount == 3200.0


@pytest.mark.asyncio
async def test_create_client_invalid_formula_raises():
    from fastapi import HTTPException
    db = AsyncMock()
    payload = RssiClientCreate(name="Corp", formula="invalid")
    with pytest.raises(HTTPException) as exc:
        await create_client(payload, _user(), db)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_client_empty_name_raises():
    from fastapi import HTTPException
    db = AsyncMock()
    payload = RssiClientCreate(name="   ")
    with pytest.raises(HTTPException) as exc:
        await create_client(payload, _user(), db)
    assert exc.value.status_code == 422


# ── update_client ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_client_not_found_raises():
    from fastapi import HTTPException
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        return r

    db.execute = execute

    with pytest.raises(HTTPException) as exc:
        await update_client(999, RssiClientUpdate(name="X"), _user(), db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_client_updates_fields():
    client = _client()
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = client
        return r

    async def refresh(obj):
        pass

    db.execute = execute
    db.commit = AsyncMock()
    db.refresh = refresh

    result = await update_client(10, RssiClientUpdate(name="Updated", description="new desc"), _user(), db)
    assert client.name == "Updated"
    assert client.description == "new desc"


@pytest.mark.asyncio
async def test_update_client_invalid_status_raises():
    from fastapi import HTTPException
    client = _client()
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = client
        return r

    db.execute = execute

    with pytest.raises(HTTPException) as exc:
        await update_client(10, RssiClientUpdate(status="invalid"), _user(), db)
    assert exc.value.status_code == 422


# ── delete_client ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_client_not_found_raises():
    from fastapi import HTTPException
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        r.scalars.return_value.all.return_value = []
        return r

    db.execute = execute

    with pytest.raises(HTTPException) as exc:
        await delete_client(999, _user(), db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_client_detaches_sites():
    from app.models.site import Site
    client = _client()
    site = MagicMock(spec=Site)
    site.rssi_client_id = 10

    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = client
        else:
            r.scalars.return_value.all.return_value = [site]
        return r

    db.execute = execute
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    await delete_client(10, _user(), db)

    assert site.rssi_client_id is None
    db.delete.assert_awaited_once_with(client)
    db.commit.assert_awaited_once()


# ── RssiClientCreate schema ───────────────────────────────────────────────────

def test_schema_optional_fields():
    c = RssiClientCreate(name="Test")
    assert c.email is None
    assert c.description is None
    assert c.formula is None
    assert c.monthly_amount is None


def test_schema_full_fields():
    c = RssiClientCreate(name="Test", email="t@t.com", description="desc", formula="premium", monthly_amount=3200.0)
    assert c.email == "t@t.com"
    assert c.description == "desc"
    assert c.formula == "premium"
    assert c.monthly_amount == 3200.0
