"""
Integration tests — /api/v1/bookings
Covers: admin slots (list, add, delete), auth guard, selectinload regression.
The selectinload fix prevents MissingGreenlet (500) when _slot_to_out accesses
slot.bookings in async context.
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


# ── Auth guard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_admin_slots_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/bookings/admin/slots")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_slots_wrong_key_returns_403(entetes_non_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/bookings/admin/slots", headers=entetes_non_admin)
    assert r.status_code == 403


# ── List slots (selectinload regression) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_slots_valid_key_returns_200_not_500(entetes_admin):
    """Regression: slot.bookings lazy load crashed with MissingGreenlet (500)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"{BASE}/bookings/admin/slots",
            headers=entetes_admin,
        )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_slots_empty_db_returns_empty_list(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"{BASE}/bookings/admin/slots",
            headers=entetes_admin,
        )
    assert r.json() == []


# ── Add slot ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_add_slot_returns_created_slot(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2026-12-01",
                        "time": "10:00",
                        "duration_minutes": 30,
                        "label": "Appel découverte",
                    }
                ]
            },
            headers=entetes_admin,
        )
    assert r.status_code == 201
    data = r.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-12-01"
    assert data[0]["time"] == "10:00"
    assert data[0]["is_booked"] is False


@pytest.mark.asyncio
async def test_admin_add_slot_then_list_returns_it(entetes_admin):
    """After adding a slot, list must return it without 500 (selectinload test)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2026-12-15",
                        "time": "14:00",
                        "duration_minutes": 45,
                        "label": "Audit",
                    }
                ]
            },
            headers=entetes_admin,
        )
        r = await c.get(
            f"{BASE}/bookings/admin/slots",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) == 1
    assert slots[0]["date"] == "2026-12-15"
    assert slots[0]["is_booked"] is False


@pytest.mark.asyncio
async def test_admin_list_slots_month_filter(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2026-11-01",
                        "time": "09:00",
                        "duration_minutes": 30,
                        "label": "Nov",
                    },
                    {
                        "date": "2026-12-01",
                        "time": "09:00",
                        "duration_minutes": 30,
                        "label": "Dec",
                    },
                ]
            },
            headers=entetes_admin,
        )
        r = await c.get(
            f"{BASE}/bookings/admin/slots?month=2026-11",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) == 1
    assert slots[0]["label"] == "Nov"


# ── Delete slot ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_delete_slot_returns_204(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2026-12-20",
                        "time": "11:00",
                        "duration_minutes": 30,
                        "label": "Test",
                    }
                ]
            },
            headers=entetes_admin,
        )
        slot_id = created.json()[0]["id"]
        r = await c.delete(
            f"{BASE}/bookings/admin/slots/{slot_id}",
            headers=entetes_admin,
        )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_admin_delete_unknown_slot_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(
            f"{BASE}/bookings/admin/slots/99999",
            headers=entetes_admin,
        )
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
async def test_public_slots_returns_200_not_500(entetes_admin):
    """Regression: selectinload must be applied on public endpoint too."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2026-12-01",
                        "time": "10:00",
                        "duration_minutes": 30,
                        "label": "Test",
                    }
                ]
            },
            headers=entetes_admin,
        )
        r = await c.get(f"{BASE}/bookings/slots?month=2026-12")
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) == 1
    assert slots[0]["is_booked"] is False


# ── Create booking ─────────────────────────────────────────────────────────────

_BOOKING_PAYLOAD = {
    "slot_id": None,  # filled per-test
    "name": "Jean Dupont",
    "email": "jean@test.com",
    "phone": "0600000000",
    "need_type": "audit-flash",
    "message": "Test booking",
}


@pytest.mark.asyncio
async def test_create_booking_slot_not_found_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with (
            patch("app.api.v1.endpoints.bookings.send_booking_confirmation"),
            patch("app.api.v1.endpoints.bookings.send_booking_admin_notification"),
        ):
            r = await c.post(
                f"{BASE}/bookings",
                json={**_BOOKING_PAYLOAD, "slot_id": 99999},
            )
    assert r.status_code == 404
    assert "introuvable" in r.json()["detail"]


@pytest.mark.asyncio
async def test_create_booking_past_slot_returns_410(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2020-01-01",
                        "time": "10:00",
                        "duration_minutes": 30,
                        "label": "Past",
                    }
                ]
            },
            headers=entetes_admin,
        )
        slot_id = created.json()[0]["id"]
        with (
            patch("app.api.v1.endpoints.bookings.send_booking_confirmation"),
            patch("app.api.v1.endpoints.bookings.send_booking_admin_notification"),
        ):
            r = await c.post(f"{BASE}/bookings", json={**_BOOKING_PAYLOAD, "slot_id": slot_id})
    assert r.status_code == 410
    assert "passé" in r.json()["detail"]


@pytest.mark.asyncio
async def test_create_booking_success_returns_201(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2030-06-15",
                        "time": "14:00",
                        "duration_minutes": 60,
                        "label": "Appel",
                    }
                ]
            },
            headers=entetes_admin,
        )
        slot_id = created.json()[0]["id"]
        with (
            patch("app.api.v1.endpoints.bookings.send_booking_confirmation"),
            patch("app.api.v1.endpoints.bookings.send_booking_admin_notification"),
        ):
            r = await c.post(f"{BASE}/bookings", json={**_BOOKING_PAYLOAD, "slot_id": slot_id})
    assert r.status_code == 201
    assert "booking_id" in r.json()
    assert "Réservation confirmée" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_booking_already_booked_returns_409(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2030-07-20",
                        "time": "09:00",
                        "duration_minutes": 30,
                        "label": "Slot",
                    }
                ]
            },
            headers=entetes_admin,
        )
        slot_id = created.json()[0]["id"]
        with (
            patch("app.api.v1.endpoints.bookings.send_booking_confirmation"),
            patch("app.api.v1.endpoints.bookings.send_booking_admin_notification"),
        ):
            # First booking — should succeed
            await c.post(f"{BASE}/bookings", json={**_BOOKING_PAYLOAD, "slot_id": slot_id})
            # Second booking on same slot — should conflict
            r = await c.post(f"{BASE}/bookings", json={**_BOOKING_PAYLOAD, "slot_id": slot_id})
    assert r.status_code == 409
    assert "déjà réservé" in r.json()["detail"]


# ── Cancel booking (public) ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_booking_invalid_token_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/bookings/cancel?token=fake-invalid-token-xyz")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cancel_booking_valid_token_cancels(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2030-08-10",
                        "time": "11:00",
                        "duration_minutes": 30,
                        "label": "Cancel",
                    }
                ]
            },
            headers=entetes_admin,
        )
        slot_id = created.json()[0]["id"]
        with (
            patch("app.api.v1.endpoints.bookings.send_booking_confirmation"),
            patch("app.api.v1.endpoints.bookings.send_booking_admin_notification"),
        ):
            booking_r = await c.post(
                f"{BASE}/bookings", json={**_BOOKING_PAYLOAD, "slot_id": slot_id}
            )
        booking_id = booking_r.json()["booking_id"]

        # Fetch cancel token from DB
        from sqlalchemy import select

        import app.core.database as _db
        from app.models.booking import Booking

        async with _db.AsyncSessionLocal() as db:
            result = await db.execute(select(Booking).where(Booking.id == booking_id))
            booking = result.scalar_one()
            token = booking.cancel_token

        r = await c.get(f"{BASE}/bookings/cancel?token={token}")
    assert r.status_code == 200
    assert "annulée" in r.json()["message"]


@pytest.mark.asyncio
async def test_cancel_booking_already_cancelled_returns_message(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2030-09-05",
                        "time": "15:00",
                        "duration_minutes": 30,
                        "label": "X",
                    }
                ]
            },
            headers=entetes_admin,
        )
        slot_id = created.json()[0]["id"]
        with (
            patch("app.api.v1.endpoints.bookings.send_booking_confirmation"),
            patch("app.api.v1.endpoints.bookings.send_booking_admin_notification"),
        ):
            booking_r = await c.post(
                f"{BASE}/bookings", json={**_BOOKING_PAYLOAD, "slot_id": slot_id}
            )
        booking_id = booking_r.json()["booking_id"]

        from sqlalchemy import select

        import app.core.database as _db
        from app.models.booking import Booking

        async with _db.AsyncSessionLocal() as db:
            result = await db.execute(select(Booking).where(Booking.id == booking_id))
            token = result.scalar_one().cancel_token

        await c.get(f"{BASE}/bookings/cancel?token={token}")
        r = await c.get(f"{BASE}/bookings/cancel?token={token}")
    assert r.status_code == 200
    assert "déjà annulée" in r.json()["message"]


# ── Admin list bookings + cancel ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_bookings_returns_list(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"{BASE}/bookings/admin/bookings",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_cancel_booking_unknown_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(
            f"{BASE}/bookings/admin/bookings/99999/cancel",
            headers=entetes_admin,
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_cancel_booking_returns_200(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        created = await c.post(
            f"{BASE}/bookings/admin/slots",
            json={
                "slots": [
                    {
                        "date": "2030-10-01",
                        "time": "10:00",
                        "duration_minutes": 30,
                        "label": "Admin cancel",
                    }
                ]
            },
            headers=entetes_admin,
        )
        slot_id = created.json()[0]["id"]
        with (
            patch("app.api.v1.endpoints.bookings.send_booking_confirmation"),
            patch("app.api.v1.endpoints.bookings.send_booking_admin_notification"),
        ):
            booking_r = await c.post(
                f"{BASE}/bookings", json={**_BOOKING_PAYLOAD, "slot_id": slot_id}
            )
        booking_id = booking_r.json()["booking_id"]

        r = await c.patch(
            f"{BASE}/bookings/admin/bookings/{booking_id}/cancel",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert "annulée" in r.json()["message"]
