"""
Unit tests for app.api.v1.endpoints.sites — direct function calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.sites import (
    list_sites,
    add_site,
    delete_site,
)
from app.services.subscription_service import get_active_plan
from app.models.site import Site
from app.models.user import User


def _mock_user(user_id: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    return u


def _mock_site(site_id: int = 1, url: str = "https://example.com") -> MagicMock:
    s = MagicMock(spec=Site)
    s.id = site_id
    s.url = url
    s.name = "Test"
    s.is_active = True
    return s


def _payload(url: str = "https://example.com", name: str = "Test") -> MagicMock:
    p = MagicMock()
    p.url = url
    p.name = name
    return p


# ─── get_active_plan ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_active_plan_no_plan_returns_none():
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)

    result = await get_active_plan(db, user_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_get_active_plan_with_plan():
    plan = MagicMock()
    plan.max_sites = 5
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = plan
    db.execute = AsyncMock(return_value=r)

    result = await get_active_plan(db, user_id=1)
    assert result.max_sites == 5


# ─── list_sites ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sites_returns_active_sites():
    site = _mock_site()
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = [site]
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    result = await list_sites(current_user=user, db=db)
    assert len(result) == 1
    assert result[0].id == 1


@pytest.mark.asyncio
async def test_list_sites_empty():
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    result = await list_sites(current_user=user, db=db)
    assert result == []


# ─── add_site ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_site_no_subscription_raises_403():
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None  # no plan → max_sites=0
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await add_site(payload=_payload(), current_user=user, db=db)
    assert exc.value.status_code == 403
    assert "Abonnement" in exc.value.detail


@pytest.mark.asyncio
async def test_add_site_limit_reached_raises_403():
    plan = MagicMock()
    plan.max_sites = 2
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = plan
        else:
            r.scalar.return_value = 2  # already at limit
        return r

    db.execute = execute
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await add_site(payload=_payload(), current_user=user, db=db)
    assert exc.value.status_code == 403
    assert "Limite" in exc.value.detail


@pytest.mark.asyncio
async def test_add_site_invalid_protocol_raises_422():
    plan = MagicMock()
    plan.max_sites = 5
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = plan
        else:
            r.scalar.return_value = 0
        return r

    db.execute = execute
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await add_site(payload=_payload(url="ftp://example.com"), current_user=user, db=db)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_add_site_auto_adds_https():
    """URLs without scheme get https:// prepended."""
    plan = MagicMock()
    plan.max_sites = 5
    site = _mock_site(url="https://example.com")
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = plan
        else:
            r.scalar.return_value = 0
        return r

    db.execute = execute
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    user = _mock_user()

    # Should not raise — url without scheme
    added_sites = []

    def fake_add(obj):
        added_sites.append(obj)

    db.add = fake_add

    await add_site(payload=_payload(url="example.com"), current_user=user, db=db)
    assert len(added_sites) == 1
    assert added_sites[0].url.startswith("https://")


@pytest.mark.asyncio
async def test_add_site_success():
    plan = MagicMock()
    plan.max_sites = 5
    site = _mock_site()
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalar_one_or_none.return_value = plan
        else:
            r.scalar.return_value = 1
        return r

    db.execute = execute
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    user = _mock_user()

    result = await add_site(payload=_payload(), current_user=user, db=db)
    db.commit.assert_called_once()


# ─── delete_site ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_site_not_found_raises_404():
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await delete_site(site_id=999, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_site_soft_deletes():
    site = _mock_site()
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = site
    db.execute = AsyncMock(return_value=r)
    db.commit = AsyncMock()
    user = _mock_user()

    await delete_site(site_id=1, current_user=user, db=db)
    assert site.is_active is False
    db.commit.assert_called_once()
