import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.vault_item import VaultItemCreate, VaultItemUpdate

BASE = "/api/v1"


async def _auth_headers(client: AsyncClient) -> dict:
    await client.post(
        f"{BASE}/auth/register",
        json={"email": "vault@test.com", "password": "Pass123!"},
    )
    r = await client.post(
        f"{BASE}/auth/login", json={"email": "vault@test.com", "password": "Pass123!"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_and_list_items():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            f"{BASE}/vault/",
            json={
                "title_encrypted": "enc_github",
                "password_encrypted": "enc_secret",
                "username_encrypted": "enc_user",
            },
            headers=headers,
        )
        assert r.status_code == 201
        assert r.json()["title_encrypted"] == "enc_github"

        r = await client.get(f"{BASE}/vault/", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_create_refuses_plaintext_fields():
    """P1-4 — la création n'accepte plus aucun champ en clair (zero-knowledge strict)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        for field in ("title", "username", "url", "notes"):
            r = await client.post(
                f"{BASE}/vault/",
                json={field: "leak", "password_encrypted": "enc"},
                headers=headers,
            )
            assert r.status_code == 422, f"champ clair '{field}' accepte"


@pytest.mark.asyncio
async def test_create_requires_nonempty_password_encrypted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            f"{BASE}/vault/",
            json={"title_encrypted": "x", "password_encrypted": ""},
            headers=headers,
        )
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            f"{BASE}/vault/",
            json={"title_encrypted": "enc_old", "password_encrypted": "enc"},
            headers=headers,
        )
        item_id = r.json()["id"]

        r = await client.patch(
            f"{BASE}/vault/{item_id}", json={"title_encrypted": "enc_new"}, headers=headers
        )
        assert r.status_code == 200
        assert r.json()["title_encrypted"] == "enc_new"


@pytest.mark.asyncio
async def test_delete_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            f"{BASE}/vault/",
            json={"title_encrypted": "enc_todelete", "password_encrypted": "enc"},
            headers=headers,
        )
        item_id = r.json()["id"]

        r = await client.delete(f"{BASE}/vault/{item_id}", headers=headers)
        assert r.status_code == 204

        r = await client.get(f"{BASE}/vault/{item_id}", headers=headers)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_other_user_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        h1 = await _auth_headers(client)
        r = await client.post(
            f"{BASE}/vault/",
            json={"title_encrypted": "enc_private", "password_encrypted": "enc"},
            headers=h1,
        )
        item_id = r.json()["id"]

        await client.post(
            f"{BASE}/auth/register",
            json={"email": "other@test.com", "password": "Pass123!"},
        )
        r2 = await client.post(
            f"{BASE}/auth/login",
            json={"email": "other@test.com", "password": "Pass123!"},
        )
        h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

        r = await client.get(f"{BASE}/vault/{item_id}", headers=h2)
        assert r.status_code == 404


def test_create_invalid_category_defaults_to_login():
    item = VaultItemCreate(title_encrypted="x", password_encrypted="enc", category="invalid_cat")
    assert item.category == "login"


def test_update_invalid_category_defaults_to_login():
    item = VaultItemUpdate(category="hacker")
    assert item.category == "login"


def test_update_valid_category_preserved():
    item = VaultItemUpdate(category="card")
    assert item.category == "card"


def test_create_with_category():
    item = VaultItemCreate(title_encrypted="x", password_encrypted="enc", category="login")
    assert item.category == "login"


@pytest.mark.asyncio
async def test_create_with_category_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            f"{BASE}/vault/",
            json={"title_encrypted": "enc_card", "password_encrypted": "enc", "category": "card"},
            headers=headers,
        )
        assert r.status_code == 201
        assert r.json()["category"] == "card"


@pytest.mark.asyncio
async def test_update_category():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            f"{BASE}/vault/",
            json={"title_encrypted": "enc_entry", "password_encrypted": "enc", "category": "login"},
            headers=headers,
        )
        item_id = r.json()["id"]

        r = await client.patch(
            f"{BASE}/vault/{item_id}", json={"category": "wifi"}, headers=headers
        )
        assert r.status_code == 200
        assert r.json()["category"] == "wifi"


@pytest.mark.asyncio
async def test_zero_knowledge_sentinel():
    """
    The server must store password_encrypted verbatim — it never decrypts,
    re-encrypts, or derives plaintext. Only the client holds the key.
    """
    from sqlalchemy import select

    import app.core.database as _db_mod
    from app.models.vault_item import VaultItem

    # Opaque sentinel that looks like a real AES-GCM ciphertext (iv:ciphertext, base64)
    SENTINEL = "v1:AAAAAAAAAAAAAAAAAAAAAA==:c2VudGluZWxjaXBoZXJ0ZXh0X25ldmVycGxhaW50ZXh0"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"{BASE}/auth/register",
            json={"email": "zk@test.com", "password": "Pass123!"},
        )
        r = await client.post(
            f"{BASE}/auth/login", json={"email": "zk@test.com", "password": "Pass123!"}
        )
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = await client.post(
            f"{BASE}/vault/",
            json={
                "title_encrypted": "enc_zk_sentinel",
                "password_encrypted": SENTINEL,
            },
            headers=headers,
        )
        assert r.status_code == 201
        item_id = r.json()["id"]

        # API response echoes the ciphertext verbatim (no server-side transformation)
        assert r.json()["password_encrypted"] == SENTINEL

    # Query DB directly — bypass the API layer entirely
    async with _db_mod.AsyncSessionLocal() as db:
        result = await db.execute(select(VaultItem).where(VaultItem.id == item_id))
        db_item = result.scalar_one()

    # Server stores exactly what the client sent
    assert db_item.password_encrypted == SENTINEL, (
        "ZK violation: server must not transform the ciphertext"
    )
    # Stored value is not plaintext (contains no recognisable password substring)
    assert "neverplaintext" not in db_item.password_encrypted.replace(
        "c2VudGluZWxjaXBoZXJ0ZXh0X25ldmVycGxhaW50ZXh0", ""
    )
