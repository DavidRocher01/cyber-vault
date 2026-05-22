"""
Integration tests — /api/v1/bookings
Covers: admin slots (list, add, delete), auth guard, selectinload regression.
The selectinload fix prevents MissingGreenlet (500) when _slot_to_out accesses
slot.bookings in async context.
"""
import pytest
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


@contextmanager
def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    mock.CONTACT_EMAIL = "admin@test.com"
    mock.FRONTEND_URL = "http://localhost:4200"
    with patch("app.api.v1.endpoints.bookings.settings", mock), \
         patch("app.core.deps.settings", mock):
        yield


# ── Auth guard ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_slots_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/bookings/admin/slots")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_slots_wrong_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/bookings/admin/slots", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


# ── List slots (selectinload regression) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_slots_valid_key_returns_200_not_500():
    """Regression: slot.bookings lazy load crashed with MissingGreenlet (500)."""
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/bookings/admin/slots", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_slots_empty_db_returns_empty_list():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/bookings/admin/slots", headers={"x-admin-key": "test-secret-key"})
    assert r.json() == []


# ── Add slot ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_add_slot_returns_created_slot():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/bookings/admin/slots",
                json={"slots": [{"date": "2026-12-01", "time": "10:00", "duration_minutes": 30, "label": "Appel découverte"}]},
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 201
    data = r.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-12-01"
    assert data[0]["time"] == "10:00"
    assert data[0]["is_booked"] is False


@pytest.mark.asyncio
async def test_admin_add_slot_then_list_returns_it():
    """After adding a slot, list must return it without 500 (selectinload test)."""
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/bookings/admin/slots",
                json={"slots": [{"date": "2026-12-15", "time": "14:00", "duration_minutes": 45, "label": "Audit"}]},
                headers={"x-admin-key": "test-secret-key"},
            )
            r = await c.get(f"{BASE}/bookings/admin/slots", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) == 1
    assert slots[0]["date"] == "2026-12-15"
    assert slots[0]["is_booked"] is False


@pytest.mark.asyncio
async def test_admin_list_slots_month_filter():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/bookings/admin/slots",
                json={"slots": [
                    {"date": "2026-11-01", "time": "09:00", "duration_minutes": 30, "label": "Nov"},
                    {"date": "2026-12-01", "time": "09:00", "duration_minutes": 30, "label": "Dec"},
                ]},
                headers={"x-admin-key": "test-secret-key"},
            )
            r = await c.get(f"{BASE}/bookings/admin/slots?month=2026-11", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) == 1
    assert slots[0]["label"] == "Nov"


# ── Delete slot ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_delete_slot_returns_204():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            created = await c.post(
                f"{BASE}/bookings/admin/slots",
                json={"slots": [{"date": "2026-12-20", "time": "11:00", "duration_minutes": 30, "label": "Test"}]},
                headers={"x-admin-key": "test-secret-key"},
            )
            slot_id = created.json()[0]["id"]
            r = await c.delete(f"{BASE}/bookings/admin/slots/{slot_id}", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_admin_delete_unknown_slot_returns_404():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(f"{BASE}/bookings/admin/slots/99999", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 404


# ── Public list slots ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_public_slots_requires_month_param():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/bookings/slots")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_public_slots_invalid_month_format_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/bookings/slots?month=invalid")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_public_slots_returns_200_not_500():
    """Regression: selectinload must be applied on public endpoint too."""
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/bookings/admin/slots",
                json={"slots": [{"date": "2026-12-01", "time": "10:00", "duration_minutes": 30, "label": "Test"}]},
                headers={"x-admin-key": "test-secret-key"},
            )
            r = await c.get(f"{BASE}/bookings/slots?month=2026-12")
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) == 1
    assert slots[0]["is_booked"] is False
