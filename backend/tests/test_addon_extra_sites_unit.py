"""
Unit tests for extra-sites add-on feature.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.user import User
from app.services.subscription_service import get_effective_max_sites
from app.api.v1.endpoints.subscriptions import (
    get_extra_sites_info,
    purchase_extra_sites,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _user(uid: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uid
    return u


def _plan(max_sites: int = 3) -> MagicMock:
    p = MagicMock(spec=Plan)
    p.max_sites = max_sites
    return p


def _sub(extra_sites: int = 0, max_sites: int = 3) -> MagicMock:
    s = MagicMock(spec=Subscription)
    s.plan = _plan(max_sites)
    s.extra_sites = extra_sites
    s.status = "active"
    s.stripe_customer_id = "cus_test"
    return s


def _db_with_sub(sub):
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        r.scalar_one_or_none.return_value = sub
        r.scalars.return_value.all.return_value = [sub] if sub else []
        return r

    db.execute = execute
    return db


def _db_no_sub():
    return _db_with_sub(None)


# ── get_effective_max_sites ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_effective_max_sites_no_subscription():
    result = await get_effective_max_sites(_db_no_sub(), 1)
    assert result == 0


@pytest.mark.asyncio
async def test_effective_max_sites_no_extras():
    sub = _sub(extra_sites=0, max_sites=3)
    result = await get_effective_max_sites(_db_with_sub(sub), 1)
    assert result == 3


@pytest.mark.asyncio
async def test_effective_max_sites_with_extras():
    sub = _sub(extra_sites=5, max_sites=3)
    result = await get_effective_max_sites(_db_with_sub(sub), 1)
    assert result == 8


# ── get_extra_sites_info ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extra_sites_info_no_sub():
    result = await get_extra_sites_info(_user(), _db_no_sub())
    assert result["extra_sites"] == 0
    assert result["pack_size"] > 0


@pytest.mark.asyncio
async def test_extra_sites_info_with_extras():
    sub = _sub(extra_sites=10)
    result = await get_extra_sites_info(_user(), _db_with_sub(sub))
    assert result["extra_sites"] == 10


# ── purchase_extra_sites (dev mode) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_purchase_extra_sites_no_subscription_raises():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await purchase_extra_sites(_user(), _db_no_sub())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_purchase_extra_sites_dev_mode_increments():
    sub = _sub(extra_sites=0)
    db = _db_with_sub(sub)
    db.commit = AsyncMock()

    with patch("app.api.v1.endpoints.subscriptions.DEV_MODE", True):
        result = await purchase_extra_sites(_user(), db)

    assert sub.extra_sites == 5
    db.commit.assert_awaited_once()
    assert "addon=extra_sites" in result["checkout_url"]


# ── SubscriptionOut schema ────────────────────────────────────────────────────

def test_subscription_out_extra_sites_default():
    from app.schemas.cyberscan import SubscriptionOut, PlanOut
    from datetime import datetime, timezone
    plan = PlanOut(id=1, name="starter", display_name="Starter", price_eur=900,
                   max_sites=3, scan_interval_days=30, tier_level=2)
    sub = SubscriptionOut(id=1, status="active", current_period_end=None, plan=plan)
    assert sub.extra_sites == 0


def test_subscription_out_effective_max_sites():
    from app.schemas.cyberscan import SubscriptionOut, PlanOut
    plan = PlanOut(id=1, name="starter", display_name="Starter", price_eur=900,
                   max_sites=3, scan_interval_days=30, tier_level=2)
    sub = SubscriptionOut(id=1, status="active", current_period_end=None, plan=plan, extra_sites=5)
    assert sub.effective_max_sites == 8
