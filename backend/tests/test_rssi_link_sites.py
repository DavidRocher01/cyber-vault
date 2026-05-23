"""
Integration tests — Sprint link/unlink sites (P1)
Covers:
  - GET  /rssi/sites/unlinked
  - PUT  /rssi/clients/{id}/sites/{site_id}   (link)
  - DELETE /rssi/clients/{id}/sites/{site_id} (unlink)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.site import Site

BASE = "/api/v1"


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await http_client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_client(http_client: AsyncClient, headers: dict, name: str = "Acme") -> dict:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _get_user_id(db_session: AsyncSession, email: str) -> int:
    row = await db_session.execute(select(User).where(User.email == email))
    return row.scalar_one().id


async def _insert_site(db_session: AsyncSession, user_id: int,
                       url: str = "https://example.com", name: str = "Test site",
                       rssi_client_id: int | None = None) -> Site:
    site = Site(user_id=user_id, url=url, name=name,
                rssi_client_id=rssi_client_id, is_active=True)
    db_session.add(site)
    await db_session.flush()
    await db_session.commit()
    return site


# ── Auth guards ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unlinked_sites_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/sites/unlinked")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_link_site_requires_auth(http_client: AsyncClient):
    r = await http_client.put(f"{BASE}/rssi/clients/1/sites/1")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_unlink_site_requires_auth(http_client: AsyncClient):
    r = await http_client.delete(f"{BASE}/rssi/clients/1/sites/1")
    assert r.status_code == 401


# ── GET /rssi/sites/unlinked ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unlinked_sites_empty(http_client: AsyncClient):
    h = await _auth(http_client, "unlinked_empty@test.com")
    r = await http_client.get(f"{BASE}/rssi/sites/unlinked", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_unlinked_sites_returns_free_sites(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "unlinked_free@test.com"
    h = await _auth(http_client, email)
    user_id = await _get_user_id(db_session, email)

    await _insert_site(db_session, user_id, url="https://free.example.com", name="Free")
    r = await http_client.get(f"{BASE}/rssi/sites/unlinked", headers=h)
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert "Free" in names


@pytest.mark.asyncio
async def test_unlinked_sites_excludes_already_linked(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "unlinked_excl@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "ExclCo")
    user_id = await _get_user_id(db_session, email)

    await _insert_site(db_session, user_id, url="https://linked.example.com", name="Linked",
                       rssi_client_id=c["id"])
    await _insert_site(db_session, user_id, url="https://free2.example.com", name="Free2")

    r = await http_client.get(f"{BASE}/rssi/sites/unlinked", headers=h)
    names = [s["name"] for s in r.json()]
    assert "Linked" not in names
    assert "Free2" in names


@pytest.mark.asyncio
async def test_unlinked_sites_cross_user_isolation(
    http_client: AsyncClient, db_session: AsyncSession
):
    email1 = "unlinked_u1@test.com"
    email2 = "unlinked_u2@test.com"
    h1 = await _auth(http_client, email1)
    h2 = await _auth(http_client, email2)
    uid1 = await _get_user_id(db_session, email1)

    await _insert_site(db_session, uid1, url="https://user1site.example.com", name="U1Site")

    r = await http_client.get(f"{BASE}/rssi/sites/unlinked", headers=h2)
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert "U1Site" not in names


# ── PUT /rssi/clients/{id}/sites/{site_id} — link ─────────────────────────────

@pytest.mark.asyncio
async def test_link_site_success(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "link_ok@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "LinkCo")
    user_id = await _get_user_id(db_session, email)
    site = await _insert_site(db_session, user_id, url="https://tolink.example.com")

    r = await http_client.put(f"{BASE}/rssi/clients/{c['id']}/sites/{site.id}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == site.id
    assert body["url"] == "https://tolink.example.com"

    # Verify it no longer appears as unlinked
    r2 = await http_client.get(f"{BASE}/rssi/sites/unlinked", headers=h)
    ids = [s["id"] for s in r2.json()]
    assert site.id not in ids


@pytest.mark.asyncio
async def test_link_site_appears_in_client_sites(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "link_appear@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "AppearCo")
    user_id = await _get_user_id(db_session, email)
    site = await _insert_site(db_session, user_id, url="https://appear.example.com")

    await http_client.put(f"{BASE}/rssi/clients/{c['id']}/sites/{site.id}", headers=h)
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    ids = [s["id"] for s in r.json()]
    assert site.id in ids


@pytest.mark.asyncio
async def test_link_site_unknown_client_returns_404(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "link_404c@test.com"
    h = await _auth(http_client, email)
    user_id = await _get_user_id(db_session, email)
    site = await _insert_site(db_session, user_id)

    r = await http_client.put(f"{BASE}/rssi/clients/99999/sites/{site.id}", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_link_site_unknown_site_returns_404(http_client: AsyncClient):
    h = await _auth(http_client, "link_404s@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.put(f"{BASE}/rssi/clients/{c['id']}/sites/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_link_site_already_linked_to_other_client_returns_409(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "link_409@test.com"
    h = await _auth(http_client, email)
    c1 = await _create_client(http_client, h, "Client1")
    c2 = await _create_client(http_client, h, "Client2")
    user_id = await _get_user_id(db_session, email)
    site = await _insert_site(db_session, user_id, rssi_client_id=c1["id"])

    r = await http_client.put(f"{BASE}/rssi/clients/{c2['id']}/sites/{site.id}", headers=h)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_link_site_cross_user_isolation(
    http_client: AsyncClient, db_session: AsyncSession
):
    email1 = "link_iso1@test.com"
    email2 = "link_iso2@test.com"
    h1 = await _auth(http_client, email1)
    h2 = await _auth(http_client, email2)
    c2 = await _create_client(http_client, h2, "Spy client")
    uid1 = await _get_user_id(db_session, email1)
    site = await _insert_site(db_session, uid1, url="https://u1.example.com")

    r = await http_client.put(f"{BASE}/rssi/clients/{c2['id']}/sites/{site.id}", headers=h2)
    # client belongs to h2, site belongs to h1 → site not found for h2
    assert r.status_code == 404


# ── DELETE /rssi/clients/{id}/sites/{site_id} — unlink ────────────────────────

@pytest.mark.asyncio
async def test_unlink_site_success(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "unlink_ok@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "UnlinkCo")
    user_id = await _get_user_id(db_session, email)
    site = await _insert_site(db_session, user_id, rssi_client_id=c["id"])

    r = await http_client.delete(f"{BASE}/rssi/clients/{c['id']}/sites/{site.id}", headers=h)
    assert r.status_code == 204

    # Site still exists but is no longer linked
    r2 = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    ids = [s["id"] for s in r2.json()]
    assert site.id not in ids

    r3 = await http_client.get(f"{BASE}/rssi/sites/unlinked", headers=h)
    ids_free = [s["id"] for s in r3.json()]
    assert site.id in ids_free


@pytest.mark.asyncio
async def test_unlink_site_unknown_returns_404(http_client: AsyncClient):
    h = await _auth(http_client, "unlink_404@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.delete(f"{BASE}/rssi/clients/{c['id']}/sites/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_unlink_site_not_linked_to_client_returns_404(
    http_client: AsyncClient, db_session: AsyncSession
):
    """Trying to unlink a site that belongs to the user but is NOT linked to this client."""
    email = "unlink_wrong@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "WrongCo")
    user_id = await _get_user_id(db_session, email)
    site = await _insert_site(db_session, user_id)  # rssi_client_id = None

    r = await http_client.delete(f"{BASE}/rssi/clients/{c['id']}/sites/{site.id}", headers=h)
    assert r.status_code == 404
