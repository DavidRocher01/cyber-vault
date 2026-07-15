import asyncio
import os

# Keep SQLite URL so app.core.database creates a valid engine at import time.
# All test operations go through the testcontainers PostgreSQL engine created below.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

import app.models  # noqa: F401 — register all models with Base.metadata
from app.core.database import Base, get_db
from app.main import app

BASE = "/api/v1"


# ── Session-scoped PostgreSQL container + DDL ──────────────────────────────────


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def pg_url(pg_container):
    return pg_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://", 1
    )


@pytest.fixture(scope="session", autouse=True)
def _pg_schema(pg_url):
    """Create all tables once (sync wrapper around asyncio.run so it's loop-neutral)."""

    async def _run():
        engine = create_async_engine(pg_url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_run())
    yield

    # Teardown: drop all tables
    async def _cleanup():
        engine = create_async_engine(pg_url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_cleanup())


# ── Per-test isolation ─────────────────────────────────────────────────────────


# Pre-build the TRUNCATE statement once — all table names are stable across tests.
def _truncate_sql() -> str:
    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    return f"TRUNCATE {names} RESTART IDENTITY CASCADE"


@pytest.fixture(autouse=True)
async def setup_db(pg_url):
    """Per-test: wipe all rows (TRUNCATE resets sequences and cascades),
    then wire FastAPI + background-task sessions to a fresh pool."""
    engine = create_async_engine(pg_url, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text(_truncate_sql()))

    AsyncTestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with AsyncTestSession() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Patch module-level AsyncSessionLocal so background tasks use the test DB
    import app.core.database as _db_module

    original_session_local = _db_module.AsyncSessionLocal
    _db_module.AsyncSessionLocal = AsyncTestSession

    yield

    _db_module.AsyncSessionLocal = original_session_local
    app.dependency_overrides.clear()
    try:
        await engine.dispose()
    finally:
        from app.core.limiter import limiter

        limiter._storage.reset()


# ── Awareness test helper ─────────────────────────────────────────────────────


async def get_awareness_magic_token(learner_email: str, org_id: int) -> str:
    """
    Bypass the magic-link endpoint (which no longer returns the token for security)
    and call issue_magic_link() directly to get the raw token for test use.
    """
    import app.core.database as _db_module
    from app.services.awareness_magic_link import issue_magic_link

    async with _db_module.AsyncSessionLocal() as db:
        result = await issue_magic_link(db, learner_email, org_id)
        if result is None:
            raise ValueError(f"Learner {learner_email} not found in org {org_id}")
        _, raw_token = result
        return raw_token


# ── Shared fixtures ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session(pg_url):
    """Direct AsyncSession — for seeding data and verifying DB state."""
    engine = create_async_engine(pg_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client():
    """Bare AsyncClient (no auth) — kept for backwards compatibility."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def http_client():
    """Async context-managed client (preferred for new tests)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(http_client: AsyncClient):
    """http_client pre-authenticated as user@test.com."""
    await http_client.post(
        f"{BASE}/auth/register",
        json={
            "email": "user@test.com",
            "password": "StrongPass123!",
        },
    )
    r = await http_client.post(
        f"{BASE}/auth/login",
        json={
            "email": "user@test.com",
            "password": "StrongPass123!",
        },
    )
    http_client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return http_client


async def register_and_login(
    client: AsyncClient, email: str, password: str = "StrongPass123!"
) -> dict:
    """Register a user and return auth headers."""
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": password})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


_PLAN_DEFAULTS = {
    # (name, price_eur, max_sites, scan_interval_days) — tous : sites illimités (-1) + quotidien (1)
    1: ("free", 0, -1, 1),
    2: ("starter", 1490, -1, 1),
    3: ("pro", 4900, -1, 1),
    4: ("business", 14900, -1, 1),
}


async def create_plan_and_subscription(client: AsyncClient, headers: dict, tier: int = 2) -> None:
    """Give the authenticated user an active subscription of the given tier.

    Utilisé par les tests d'intégration qui appellent des endpoints gatés par
    require_min_tier (analyse de code = tier 2, dark web = tier 3, ...). Crée le Plan
    correspondant s'il est absent (les tests TRUNCATE la table plans) + une Subscription
    active pour l'utilisateur identifié par le JWT présent dans `headers`.
    """
    from sqlalchemy import select

    import app.core.database as _db_module
    from app.core.security import decode_access_token
    from app.models.plan import Plan
    from app.models.subscription import Subscription

    token = headers["Authorization"].removeprefix("Bearer ").strip()
    user_id = int(decode_access_token(token))

    name, price, max_sites, interval = _PLAN_DEFAULTS[tier]
    async with _db_module.AsyncSessionLocal() as db:
        result = await db.execute(select(Plan).where(Plan.name == name))
        plan = result.scalar_one_or_none()
        if plan is None:
            plan = Plan(
                name=name,
                display_name=name.capitalize(),
                price_eur=price,
                max_sites=max_sites,
                scan_interval_days=interval,
                tier_level=tier,
            )
            db.add(plan)
            await db.flush()
        db.add(Subscription(user_id=user_id, plan_id=plan.id, status="active"))
        await db.commit()
