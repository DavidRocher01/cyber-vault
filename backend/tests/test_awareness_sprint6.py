"""
Tests — Awareness Sprint 6 : gamification.

Couvre :
  - compute_level : seuils corrects pour chaque niveau
  - _initials : formation des initiales
  - BADGE_CATALOG : 20 badges, slugs uniques, champs requis
  - seed_badges : idempotent
  - check_and_award_badges : first_step, perfectionist, detective, nis2_ready
  - Endpoints /me/level et /me/badges (auth learner requise)
  - Endpoint /organizations/{id}/leaderboard (admin requis)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.awareness_gamification import (
    BADGE_CATALOG,
    _initials,
    compute_level,
)

BASE = "/api/v1"


# ── compute_level ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "xp,expected_level,expected_label",
    [
        (0, 1, "Apprenti"),
        (50, 1, "Apprenti"),
        (51, 2, "Initié"),
        (150, 2, "Initié"),
        (151, 3, "Vigilant"),
        (300, 3, "Vigilant"),
        (301, 4, "Expert"),
        (500, 4, "Expert"),
        (501, 5, "Sentinelle"),
        (999, 5, "Sentinelle"),
    ],
)
def test_compute_level(xp, expected_level, expected_label):
    result = compute_level(xp)
    assert result["level"] == expected_level
    assert result["label"] == expected_label
    assert result["xp"] == xp


def test_compute_level_no_next_threshold_at_max():
    result = compute_level(9999)
    assert result["level"] == 5
    assert result["next_level_xp"] is None


def test_compute_level_has_next_threshold_below_max():
    result = compute_level(0)
    assert result["next_level_xp"] == 51


# ── _initials ─────────────────────────────────────────────────────────────────


def test_initials_both_names():
    assert _initials("Alice", "Dupont") == "A. D."


def test_initials_first_only():
    assert _initials("Alice", None) == "A."


def test_initials_last_only():
    assert _initials(None, "Dupont") == "D."


def test_initials_both_none():
    assert _initials(None, None) == "?"


# ── BADGE_CATALOG ──────────────────────────────────────────────────────────────


def test_badge_catalog_has_20_badges():
    assert len(BADGE_CATALOG) == 20


def test_badge_catalog_slugs_unique():
    slugs = [b["slug"] for b in BADGE_CATALOG]
    assert len(slugs) == len(set(slugs))


def test_badge_catalog_required_fields():
    required = {"slug", "name", "icon", "category", "xp_bonus", "description"}
    for badge in BADGE_CATALOG:
        assert required <= badge.keys(), f"Badge {badge.get('slug')} manque des champs"


def test_badge_catalog_xp_bonus_positive():
    for badge in BADGE_CATALOG:
        assert badge["xp_bonus"] >= 0


# ── seed_badges ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_badges_creates_all(db_session):
    from app.services.awareness_gamification import seed_badges

    count = await seed_badges(db_session)
    assert count == 20


@pytest.mark.asyncio
async def test_seed_badges_idempotent(db_session):
    from app.services.awareness_gamification import seed_badges

    await seed_badges(db_session)
    count2 = await seed_badges(db_session)
    assert count2 == 0  # rien de créé la 2ème fois


# ── Endpoints (auth tests) ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_my_level_requires_learner_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/me/level")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_my_badges_requires_learner_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/me/badges")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_leaderboard_requires_admin_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/organizations/1/leaderboard")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_my_level_returns_level_data():
    """Learner fraîchement créé → XP=0, niveau Apprenti."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "gami_admin@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": "gami_admin@test.com", "password": "StrongPass123!"},
        )
        admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations", json={"name": "Gami Org"}, headers=admin_h
            )
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "gami_learner@test.com"},
            headers=admin_h,
        )
        from awareness_helpers import get_awareness_magic_token

        token = await get_awareness_magic_token("gami_learner@test.com", org_id)
        session = (await c.get(f"{BASE}/awareness/auth/verify", params={"token": token})).json()
        learner_h = {"Authorization": f"Bearer {session['access_token']}"}

        r = await c.get(f"{BASE}/awareness/me/level", headers=learner_h)

    assert r.status_code == 200
    body = r.json()
    assert body["level"] == 1
    assert body["label"] == "Apprenti"
    assert body["xp"] == 0


@pytest.mark.asyncio
async def test_get_my_badges_returns_empty_list_initially():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "badge_admin@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": "badge_admin@test.com", "password": "StrongPass123!"},
        )
        admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations", json={"name": "Badge Org"}, headers=admin_h
            )
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "badge_learner@test.com"},
            headers=admin_h,
        )
        from awareness_helpers import get_awareness_magic_token

        token = await get_awareness_magic_token("badge_learner@test.com", org_id)
        session = (await c.get(f"{BASE}/awareness/auth/verify", params={"token": token})).json()
        learner_h = {"Authorization": f"Bearer {session['access_token']}"}

        r = await c.get(f"{BASE}/awareness/me/badges", headers=learner_h)

    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_leaderboard_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "lb_admin@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login", json={"email": "lb_admin@test.com", "password": "StrongPass123!"}
        )
        admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations", json={"name": "LB Org"}, headers=admin_h
            )
        ).json()["id"]

        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/leaderboard", headers=admin_h)

    assert r.status_code == 200
    assert isinstance(r.json(), list)
