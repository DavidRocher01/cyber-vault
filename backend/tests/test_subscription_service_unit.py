"""
Unit tests — app.services.subscription_service
Covers:
  1. get_active_plan — user with no subscription returns None
  2. get_active_plan — user with active subscription returns the plan
  3. get_active_plan — ignores canceled/past_due subscriptions
  4. get_active_plan — only returns own plan (auth isolation)
  5. get_effective_max_sites — user with no subscription returns 0
  6. get_effective_max_sites — returns plan.max_sites when no extra_sites
  7. get_effective_max_sites — adds extra_sites to plan.max_sites
  8. get_effective_max_sites — reflects extra_sites increment
  9. get_effective_max_sites — multiple subscription rows: only active counts
 10. transition: canceled subscription no longer counts as active
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services.subscription_service import get_active_plan, get_effective_max_sites

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_user(db: AsyncSession, email: str) -> User:
    user = User(email=email, hashed_password=hash_password("pass"))
    db.add(user)
    await db.flush()
    return user


async def _seed_plan(
    db: AsyncSession,
    *,
    name: str = "starter",
    max_sites: int = 1,
    tier_level: int = 2,
    price_eur: int = 900,
) -> Plan:
    plan = Plan(
        name=name,
        display_name=name.capitalize(),
        price_eur=price_eur,
        max_sites=max_sites,
        scan_interval_days=30,
        tier_level=tier_level,
        stripe_price_id="",
        is_active=True,
    )
    db.add(plan)
    await db.flush()
    return plan


async def _seed_subscription(
    db: AsyncSession,
    user_id: int,
    plan_id: int,
    *,
    status: str = "active",
    extra_sites: int = 0,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        status=status,
        extra_sites=extra_sites,
    )
    db.add(sub)
    await db.flush()
    return sub


# ---------------------------------------------------------------------------
# 1-4. get_active_plan
# ---------------------------------------------------------------------------


class TestGetActivePlan:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_subscription(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "plan_none@test.com")
        await db_session.commit()

        result = await get_active_plan(db_session, user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_plan_for_active_subscription(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "plan_active@test.com")
        plan = await _seed_plan(db_session, name="plan_act", max_sites=3)
        await _seed_subscription(db_session, user.id, plan.id, status="active")
        await db_session.commit()

        result = await get_active_plan(db_session, user.id)

        assert result is not None
        assert result.id == plan.id
        assert result.max_sites == 3

    @pytest.mark.asyncio
    async def test_ignores_canceled_subscription(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "plan_cancel@test.com")
        plan = await _seed_plan(db_session, name="plan_can")
        await _seed_subscription(db_session, user.id, plan.id, status="canceled")
        await db_session.commit()

        result = await get_active_plan(db_session, user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_ignores_past_due_subscription(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "plan_past@test.com")
        plan = await _seed_plan(db_session, name="plan_pastdue")
        await _seed_subscription(db_session, user.id, plan.id, status="past_due")
        await db_session.commit()

        result = await get_active_plan(db_session, user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_does_not_return_other_user_plan(self, db_session: AsyncSession):
        u1 = await _seed_user(db_session, "plan_iso1@test.com")
        u2 = await _seed_user(db_session, "plan_iso2@test.com")
        plan = await _seed_plan(db_session, name="plan_iso")
        await _seed_subscription(db_session, u1.id, plan.id, status="active")
        await db_session.commit()

        result = await get_active_plan(db_session, u2.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_correct_plan_attributes(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "plan_attrs@test.com")
        plan = await _seed_plan(
            db_session, name="plan_full", max_sites=10, tier_level=4, price_eur=7900
        )
        await _seed_subscription(db_session, user.id, plan.id, status="active")
        await db_session.commit()

        result = await get_active_plan(db_session, user.id)

        assert result.max_sites == 10
        assert result.tier_level == 4
        assert result.price_eur == 7900


# ---------------------------------------------------------------------------
# 5-9. get_effective_max_sites
# ---------------------------------------------------------------------------


class TestGetEffectiveMaxSites:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_subscription(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "ms_none@test.com")
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_plan_max_sites_when_no_extras(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "ms_base@test.com")
        plan = await _seed_plan(db_session, name="ms_plan_base", max_sites=5)
        await _seed_subscription(db_session, user.id, plan.id, status="active", extra_sites=0)
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == 5

    @pytest.mark.asyncio
    async def test_adds_extra_sites_to_plan_max(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "ms_extra@test.com")
        plan = await _seed_plan(db_session, name="ms_plan_extra", max_sites=3)
        await _seed_subscription(db_session, user.id, plan.id, status="active", extra_sites=2)
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == 5  # 3 + 2

    @pytest.mark.asyncio
    async def test_large_extra_sites(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "ms_large@test.com")
        plan = await _seed_plan(db_session, name="ms_plan_large", max_sites=1)
        await _seed_subscription(db_session, user.id, plan.id, status="active", extra_sites=99)
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == 100  # 1 + 99

    @pytest.mark.asyncio
    async def test_canceled_subscription_returns_zero(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "ms_canceled@test.com")
        plan = await _seed_plan(db_session, name="ms_plan_canceled", max_sites=5)
        await _seed_subscription(db_session, user.id, plan.id, status="canceled", extra_sites=3)
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == 0

    @pytest.mark.asyncio
    async def test_active_beats_canceled_for_same_user(self, db_session: AsyncSession):
        """If user has both a canceled and an active sub, active one counts."""
        user = await _seed_user(db_session, "ms_both@test.com")
        plan_old = await _seed_plan(db_session, name="ms_plan_old", max_sites=1)
        plan_new = await _seed_plan(db_session, name="ms_plan_new", max_sites=5)
        await _seed_subscription(db_session, user.id, plan_old.id, status="canceled", extra_sites=0)
        await _seed_subscription(db_session, user.id, plan_new.id, status="active", extra_sites=1)
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == 6  # 5 + 1 (active plan wins)


# ---------------------------------------------------------------------------
# 10. Transition: cancel an active subscription and verify it no longer counts
# ---------------------------------------------------------------------------


class TestSubscriptionStatusTransition:
    @pytest.mark.asyncio
    async def test_canceled_plan_no_longer_returned_by_get_active_plan(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session, "trans1@test.com")
        plan = await _seed_plan(db_session, name="trans_plan", max_sites=4)
        sub = await _seed_subscription(db_session, user.id, plan.id, status="active")
        await db_session.commit()

        # Sanity check: active now
        active = await get_active_plan(db_session, user.id)
        assert active is not None

        # Simulate cancellation
        sub.status = "canceled"
        await db_session.flush()

        # Should now return None
        result_after = await get_active_plan(db_session, user.id)
        assert result_after is None

    @pytest.mark.asyncio
    async def test_canceled_subscription_effective_sites_drops_to_zero(
        self, db_session: AsyncSession
    ):
        user = await _seed_user(db_session, "trans2@test.com")
        plan = await _seed_plan(db_session, name="trans_sites_plan", max_sites=5)
        sub = await _seed_subscription(db_session, user.id, plan.id, status="active", extra_sites=2)
        await db_session.commit()

        before = await get_effective_max_sites(db_session, user.id)
        assert before == 7  # 5 + 2

        sub.status = "canceled"
        await db_session.flush()

        after = await get_effective_max_sites(db_session, user.id)
        assert after == 0


# ---------------------------------------------------------------------------
# 11. Repli sur le plan Gratuit quand aucun abonnement actif (compte neuf / churn)
# ---------------------------------------------------------------------------


class TestFreePlanFallback:
    @pytest.mark.asyncio
    async def test_get_active_plan_falls_back_to_free(self, db_session: AsyncSession):
        """Aucun abonnement mais un plan 'free' semé → get_active_plan renvoie le Gratuit."""
        user = await _seed_user(db_session, "fb_plan@test.com")
        free = await _seed_plan(db_session, name="free", max_sites=1, tier_level=1, price_eur=0)
        await db_session.commit()

        result = await get_active_plan(db_session, user.id)

        assert result is not None
        assert result.id == free.id
        assert result.name == "free"

    @pytest.mark.asyncio
    async def test_get_active_plan_ignores_inactive_free(self, db_session: AsyncSession):
        """Un plan 'free' inactif ne sert pas de repli → None."""
        user = await _seed_user(db_session, "fb_inactive@test.com")
        free = await _seed_plan(db_session, name="free", max_sites=1, tier_level=1, price_eur=0)
        free.is_active = False
        await db_session.commit()

        result = await get_active_plan(db_session, user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_effective_max_sites_falls_back_to_free_quota(self, db_session: AsyncSession):
        """Sans abonnement, le quota du Gratuit s'applique au lieu de 0."""
        user = await _seed_user(db_session, "fb_sites@test.com")
        await _seed_plan(db_session, name="free", max_sites=1, tier_level=1, price_eur=0)
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == 1

    @pytest.mark.asyncio
    async def test_effective_max_sites_free_unlimited(self, db_session: AsyncSession):
        """Un Gratuit à max_sites<0 renvoie la sentinelle illimitée en repli."""
        from app.services.subscription_service import UNLIMITED_SITES

        user = await _seed_user(db_session, "fb_unlimited@test.com")
        await _seed_plan(db_session, name="free", max_sites=-1, tier_level=1, price_eur=0)
        await db_session.commit()

        result = await get_effective_max_sites(db_session, user.id)

        assert result == UNLIMITED_SITES

    @pytest.mark.asyncio
    async def test_churned_user_falls_back_to_free(self, db_session: AsyncSession):
        """Abonnement annulé + Gratuit semé → repli sur le Gratuit (pas de verrouillage)."""
        user = await _seed_user(db_session, "fb_churn@test.com")
        free = await _seed_plan(db_session, name="free", max_sites=1, tier_level=1, price_eur=0)
        paid = await _seed_plan(db_session, name="starter", max_sites=5, tier_level=2)
        await _seed_subscription(db_session, user.id, paid.id, status="canceled")
        await db_session.commit()

        plan = await get_active_plan(db_session, user.id)
        assert plan is not None
        assert plan.id == free.id

        sites = await get_effective_max_sites(db_session, user.id)
        assert sites == 1
