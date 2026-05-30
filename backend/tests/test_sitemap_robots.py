"""
Tests — /sitemap.xml and /robots.txt
Covers: content-type, presence of static URLs, blog posts in sitemap,
        robots.txt disallow rules.
"""

from datetime import UTC

import pytest
from httpx import ASGITransport, AsyncClient

import app.core.database as db_mod
from app.main import app


async def _seed_blog_post(slug: str, published: bool = True) -> None:
    from datetime import datetime

    from app.models.blog_post import BlogPost

    now = datetime.now(UTC)
    async with db_mod.AsyncSessionLocal() as session:
        post = BlogPost(
            slug=slug,
            title="Test Article",
            description="Résumé du test.",
            date="2026-05-19",
            read_time=3,
            category="Sécurité",
            tags="[]",
            html_content="<p>Contenu de test.</p>",
            is_published=published,
            created_at=now,
            updated_at=now,
        )
        session.add(post)
        await session.commit()


# ── robots.txt ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_robots_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/robots.txt")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_robots_content_type_is_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/robots.txt")
    assert "text/plain" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_robots_disallows_api_and_admin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/robots.txt")
    body = r.text
    assert "Disallow: /api/" in body
    assert "Disallow: /cyberscan/admin" in body


@pytest.mark.asyncio
async def test_robots_allows_all_agents():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/robots.txt")
    assert "User-agent: *" in r.text


@pytest.mark.asyncio
async def test_robots_contains_sitemap_link():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/robots.txt")
    assert "sitemap.xml" in r.text.lower()


# ── sitemap.xml ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sitemap_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/sitemap.xml")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_sitemap_content_type_is_xml():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/sitemap.xml")
    assert "xml" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_sitemap_is_valid_xml():
    import xml.etree.ElementTree as ET

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/sitemap.xml")
    tree = ET.fromstring(r.text)
    assert tree.tag.endswith("urlset")


@pytest.mark.asyncio
async def test_sitemap_contains_homepage():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/sitemap.xml")
    assert "cyberscanapp.com</loc>" in r.text or "<loc>https://cyberscanapp.com</loc>" in r.text


@pytest.mark.asyncio
async def test_sitemap_contains_cyberscan_static_pages():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/sitemap.xml")
    body = r.text
    assert "/cyberscan/contact" in body
    assert "/cyberscan/blog" in body


@pytest.mark.asyncio
async def test_sitemap_includes_published_blog_post():
    await _seed_blog_post("test-article-publie")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/sitemap.xml")
    assert "test-article-publie" in r.text


@pytest.mark.asyncio
async def test_sitemap_excludes_unpublished_blog_post():
    await _seed_blog_post("article-non-publie", published=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/sitemap.xml")
    assert "article-non-publie" not in r.text
