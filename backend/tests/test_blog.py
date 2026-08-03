"""
Integration tests — /api/v1/blog
Covers: public list/detail, admin list (all incl. unpublished), admin detail,
admin create/update/delete, auth guards.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"

VALID_ARTICLE = {
    "slug": "test-article",
    "title": "Test Article",
    "description": "A test article description.",
    "date": "2026-06-01",
    "readTime": 5,
    "category": "Sécurité Web",
    "tags": ["sécurité", "test"],
    "htmlContent": "<p>Content here.</p>",
    "isPublished": True,
}


# ── Auth guard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_admin_list_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/blog/admin/articles")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_wrong_key_returns_403(entetes_non_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/blog/admin/articles", headers=entetes_non_admin)
    assert r.status_code == 403


@pytest.mark.asyncio
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_admin_create_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/blog/admin/articles", json=VALID_ARTICLE)
    assert r.status_code == 401


# ── Public endpoints ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_public_list_empty_returns_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/blog/articles")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_public_list_returns_only_published(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
        draft = {**VALID_ARTICLE, "slug": "draft-article", "isPublished": False}
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=draft,
            headers=entetes_admin,
        )
        r = await c.get(f"{BASE}/blog/articles")
    assert r.status_code == 200
    slugs = [a["slug"] for a in r.json()]
    assert "test-article" in slugs
    assert "draft-article" not in slugs


@pytest.mark.asyncio
async def test_public_detail_returns_article(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
        r = await c.get(f"{BASE}/blog/articles/test-article")
    assert r.status_code == 200
    assert r.json()["htmlContent"] == "<p>Content here.</p>"


@pytest.mark.asyncio
async def test_public_detail_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/blog/articles/does-not-exist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_public_detail_draft_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        draft = {**VALID_ARTICLE, "slug": "hidden-draft", "isPublished": False}
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=draft,
            headers=entetes_admin,
        )
        r = await c.get(f"{BASE}/blog/articles/hidden-draft")
    assert r.status_code == 404


# ── Admin list (all articles incl. unpublished) ────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_empty_returns_empty(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"{BASE}/blog/admin/articles",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_admin_list_includes_drafts(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        draft = {**VALID_ARTICLE, "slug": "my-draft", "isPublished": False}
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=draft,
            headers=entetes_admin,
        )
        r = await c.get(
            f"{BASE}/blog/admin/articles",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert any(a["slug"] == "my-draft" for a in r.json())


# ── Admin detail ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_detail_returns_html_content(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
        r = await c.get(
            f"{BASE}/blog/admin/articles/test-article",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert r.json()["htmlContent"] == "<p>Content here.</p>"


@pytest.mark.asyncio
async def test_admin_detail_draft_accessible(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        draft = {**VALID_ARTICLE, "slug": "admin-only-draft", "isPublished": False}
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=draft,
            headers=entetes_admin,
        )
        r = await c.get(
            f"{BASE}/blog/admin/articles/admin-only-draft",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert r.json()["isPublished"] is False


@pytest.mark.asyncio
async def test_admin_detail_unknown_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"{BASE}/blog/admin/articles/no-such-slug",
            headers=entetes_admin,
        )
    assert r.status_code == 404


# ── Create ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_create_returns_201(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/blog/admin/articles",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
    assert r.status_code == 201
    data = r.json()
    assert data["slug"] == "test-article"
    assert data["htmlContent"] == "<p>Content here.</p>"
    assert data["isPublished"] is True


@pytest.mark.asyncio
async def test_admin_create_missing_title_returns_422(entetes_admin):
    payload = {**VALID_ARTICLE, "title": ""}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/blog/admin/articles",
            json=payload,
            headers=entetes_admin,
        )
    assert r.status_code == 422


# ── Update ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_update_returns_updated_content(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
        updated = {
            **VALID_ARTICLE,
            "title": "Titre modifié",
            "htmlContent": "<p>Nouveau contenu.</p>",
        }
        r = await c.put(
            f"{BASE}/blog/admin/articles/test-article",
            json=updated,
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert r.json()["title"] == "Titre modifié"
    assert r.json()["htmlContent"] == "<p>Nouveau contenu.</p>"


@pytest.mark.asyncio
async def test_admin_update_unknown_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(
            f"{BASE}/blog/admin/articles/no-such-slug",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
    assert r.status_code == 404


# ── Delete ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_delete_returns_204(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
        r = await c.delete(
            f"{BASE}/blog/admin/articles/test-article",
            headers=entetes_admin,
        )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_admin_delete_then_public_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/blog/admin/articles",
            json=VALID_ARTICLE,
            headers=entetes_admin,
        )
        await c.delete(
            f"{BASE}/blog/admin/articles/test-article",
            headers=entetes_admin,
        )
        r = await c.get(f"{BASE}/blog/articles/test-article")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_delete_unknown_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(
            f"{BASE}/blog/admin/articles/no-such-slug",
            headers=entetes_admin,
        )
    assert r.status_code == 404
