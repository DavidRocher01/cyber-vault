"""
Integration tests — /api/v1/notifications
Covers: list empty, list with items + unread count, mark one read,
        mark all read, delete, auth isolation, 404 on wrong user.
"""

import pytest
from datetime import datetime
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.notification import Notification

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_notification(user_id: int, title: str = "Test", read: bool = False) -> int:
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        notif = Notification(
            user_id=user_id,
            type="scan_done",
            title=title,
            body="Corps de la notification",
            link="/cyberscan/dashboard",
            read=read,
            created_at=datetime.utcnow(),
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        return notif.id


async def _get_user_id(client: AsyncClient, headers: dict) -> int:
    """Retrieve current user ID via the /users/me endpoint."""
    r = await client.get(f"{BASE}/users/me", headers=headers)
    return r.json()["id"]


# ── GET /notifications ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notifications_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "notif1@test.com")
        r = await c.get(f"{BASE}/notifications", headers=h)
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_list_notifications_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/notifications")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_notifications_returns_seeded_items():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "notif2@test.com")
        uid = await _get_user_id(c, h)
        await _seed_notification(uid, "Scan terminé", read=False)
        await _seed_notification(uid, "Menace détectée", read=True)
        r = await c.get(f"{BASE}/notifications", headers=h)
    data = r.json()
    assert r.status_code == 200
    assert len(data["items"]) == 2
    assert data["unread_count"] == 1


@pytest.mark.asyncio
async def test_list_notifications_isolation():
    """User B must not see User A's notifications."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _headers(c, "notif_owner@test.com")
        h2 = await _headers(c, "notif_spy@test.com")
        uid1 = await _get_user_id(c, h1)
        await _seed_notification(uid1, "Private notification")
        r = await c.get(f"{BASE}/notifications", headers=h2)
    assert r.json()["items"] == []
    assert r.json()["unread_count"] == 0


# ── POST /notifications/{id}/read ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_notification_read():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "read1@test.com")
        uid = await _get_user_id(c, h)
        nid = await _seed_notification(uid, "À lire", read=False)
        r = await c.post(f"{BASE}/notifications/{nid}/read", headers=h)
    assert r.status_code == 200
    assert r.json()["read"] is True


@pytest.mark.asyncio
async def test_mark_notification_read_updates_unread_count():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "read2@test.com")
        uid = await _get_user_id(c, h)
        nid = await _seed_notification(uid, "Non lu", read=False)
        await c.post(f"{BASE}/notifications/{nid}/read", headers=h)
        r = await c.get(f"{BASE}/notifications", headers=h)
    assert r.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_notification_read_other_user_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _headers(c, "read_owner@test.com")
        h2 = await _headers(c, "read_spy@test.com")
        uid1 = await _get_user_id(c, h1)
        nid = await _seed_notification(uid1, "Privé")
        r = await c.post(f"{BASE}/notifications/{nid}/read", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_mark_notification_read_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "read3@test.com")
        r = await c.post(f"{BASE}/notifications/99999/read", headers=h)
    assert r.status_code == 404


# ── POST /notifications/read-all ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_all_read_returns_204():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "all1@test.com")
        uid = await _get_user_id(c, h)
        await _seed_notification(uid, "N1", read=False)
        await _seed_notification(uid, "N2", read=False)
        r = await c.post(f"{BASE}/notifications/read-all", headers=h)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_mark_all_read_clears_unread_count():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "all2@test.com")
        uid = await _get_user_id(c, h)
        await _seed_notification(uid, "N1", read=False)
        await _seed_notification(uid, "N2", read=False)
        await _seed_notification(uid, "N3", read=True)
        await c.post(f"{BASE}/notifications/read-all", headers=h)
        r = await c.get(f"{BASE}/notifications", headers=h)
    assert r.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_all_read_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/notifications/read-all")
    assert r.status_code == 403


# ── DELETE /notifications/{id} ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_notification_returns_204():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "deln1@test.com")
        uid = await _get_user_id(c, h)
        nid = await _seed_notification(uid, "À supprimer")
        r = await c.delete(f"{BASE}/notifications/{nid}", headers=h)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_notification_removes_from_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "deln2@test.com")
        uid = await _get_user_id(c, h)
        nid = await _seed_notification(uid, "Ephémère")
        await c.delete(f"{BASE}/notifications/{nid}", headers=h)
        r = await c.get(f"{BASE}/notifications", headers=h)
    assert r.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_notification_other_user_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _headers(c, "deln_owner@test.com")
        h2 = await _headers(c, "deln_spy@test.com")
        uid1 = await _get_user_id(c, h1)
        nid = await _seed_notification(uid1, "Protégée")
        r = await c.delete(f"{BASE}/notifications/{nid}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_notification_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "deln3@test.com")
        r = await c.delete(f"{BASE}/notifications/99999", headers=h)
    assert r.status_code == 404
