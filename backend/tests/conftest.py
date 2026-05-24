import asyncio
import os

# Keep SQLite URL so app.core.database creates a valid engine at import time.
# All test operations go through the testcontainers PostgreSQL engine created below.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
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

@pytest.fixture(autouse=True)
async def setup_db(pg_url):
    """Per-test: create a fresh async engine (bound to this test's event loop),
    wipe all rows, and wire FastAPI + background-task sessions."""
    engine = create_async_engine(pg_url, echo=False)

    # Truncate all tables in reverse FK order
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    AsyncTestSession = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

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
    await engine.dispose()

    from app.core.limiter import limiter
    limiter._storage.reset()


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
    await http_client.post(f"{BASE}/auth/register", json={
        "email": "user@test.com",
        "password": "StrongPass123!",
    })
    r = await http_client.post(f"{BASE}/auth/login", json={
        "email": "user@test.com",
        "password": "StrongPass123!",
    })
    http_client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return http_client


async def register_and_login(
    client: AsyncClient, email: str, password: str = "StrongPass123!"
) -> dict:
    """Register a user and return auth headers."""
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": password})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def create_plan_and_subscription(
    client: AsyncClient, headers: dict, tier: int = 2
) -> None:
    pass
