import os

# Override DATABASE_URL before any app module is imported,
# so database.py creates a SQLite engine instead of PostgreSQL.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — ensure all models registered with Base.metadata
from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

BASE = "/api/v1"


@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncTestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with AsyncTestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Also patch the module-level AsyncSessionLocal so background tasks
    # and endpoints that open their own session use the test DB.
    import app.core.database as _db_module
    original_session_local = _db_module.AsyncSessionLocal
    _db_module.AsyncSessionLocal = AsyncTestSession

    yield

    _db_module.AsyncSessionLocal = original_session_local
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def register_and_login(client: AsyncClient, email: str, password: str = "StrongPass123!") -> dict:
    """Register a user and return auth headers."""
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": password})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_plan_and_subscription(client: AsyncClient, headers: dict, tier: int = 2) -> None:
    """Seed a plan + active subscription for the authenticated user (direct DB workaround via seed endpoint)."""
    # Plans are seeded via seed_plans.py; in tests we insert directly via the DB override
    # Instead we use the plans endpoint (GET /plans) — plans must be pre-seeded.
    # For tests that need subscription quota we patch _get_max_sites in the service.
    pass
