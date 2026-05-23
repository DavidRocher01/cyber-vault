import os
import tempfile

# Override DATABASE_URL before any app module is imported,
# so database.py creates a SQLite engine instead of PostgreSQL.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — ensure all models registered with Base.metadata
from app.core.database import Base, get_db
from app.main import app

BASE = "/api/v1"


@pytest_asyncio.fixture
async def test_engine():
    """Per-test SQLite file engine with all tables created."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp.name}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest.fixture(autouse=True)
async def setup_db(test_engine):
    """Wire the FastAPI app and AsyncSessionLocal to the per-test SQLite DB."""
    AsyncTestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

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
    app.dependency_overrides.clear()

    # Reset rate limiter storage so each test starts with a clean slate
    from app.core.limiter import limiter
    limiter._storage.reset()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Direct AsyncSession on the test DB — for seeding data and verifying state."""
    Session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session


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
