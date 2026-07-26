"""
Unit tests — app.core.deps.require_conformity_export

Vérifie le garde-fou d'export des rapports de conformité (NIS2 / ISO 27001) :
  - plan payant (allow_conformity_export=True) → autorisé
  - plan Gratuit (allow_conformity_export=False) → 403
  - repli Gratuit (aucun abonnement + Gratuit semé off) → 403
  - fail-open : aucun plan connu (Gratuit non semé) → autorisé
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_conformity_export
from app.core.security import hash_password
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User


async def _seed_user(db: AsyncSession, email: str) -> User:
    user = User(email=email, hashed_password=hash_password("pass"))
    db.add(user)
    await db.flush()
    return user


async def _seed_plan(
    db: AsyncSession,
    *,
    name: str,
    allow_export: bool,
    max_sites: int = 1,
    tier_level: int = 1,
) -> Plan:
    plan = Plan(
        name=name,
        display_name=name.capitalize(),
        price_eur=0,
        max_sites=max_sites,
        scan_interval_days=30,
        tier_level=tier_level,
        stripe_price_id="",
        is_active=True,
        allow_conformity_export=allow_export,
    )
    db.add(plan)
    await db.flush()
    return plan


async def _subscribe(db: AsyncSession, user_id: int, plan_id: int) -> None:
    db.add(Subscription(user_id=user_id, plan_id=plan_id, status="active", extra_sites=0))
    await db.flush()


@pytest.mark.asyncio
async def test_paid_plan_allows_export(db_session: AsyncSession):
    user = await _seed_user(db_session, "exp_paid@test.com")
    plan = await _seed_plan(db_session, name="starter", allow_export=True, tier_level=2)
    await _subscribe(db_session, user.id, plan.id)
    await db_session.commit()

    # Ne lève pas → autorisé
    assert await require_conformity_export(current_user=user, db=db_session) is None


@pytest.mark.asyncio
async def test_free_plan_blocks_export(db_session: AsyncSession):
    user = await _seed_user(db_session, "exp_free@test.com")
    plan = await _seed_plan(db_session, name="free", allow_export=False)
    await _subscribe(db_session, user.id, plan.id)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await require_conformity_export(current_user=user, db=db_session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_no_subscription_falls_back_to_free_and_blocks(db_session: AsyncSession):
    """Compte sans abonnement + Gratuit semé (off) → repli Gratuit → 403."""
    user = await _seed_user(db_session, "exp_nosub@test.com")
    await _seed_plan(db_session, name="free", allow_export=False)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await require_conformity_export(current_user=user, db=db_session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_fail_open_when_no_plan_seeded(db_session: AsyncSession):
    """Aucun plan connu (Gratuit non semé) → fail-open, export autorisé."""
    user = await _seed_user(db_session, "exp_failopen@test.com")
    await db_session.commit()

    assert await require_conformity_export(current_user=user, db=db_session) is None
