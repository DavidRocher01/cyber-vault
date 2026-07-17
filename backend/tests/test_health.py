"""Integration test — GET /api/v1/health (sonde publique de la recette)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


@pytest.mark.asyncio
async def test_health_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"]
    # db_revision est best-effort : le schema de test est construit depuis les
    # modeles (pas de table alembic_version), donc il peut etre None ici. Contre
    # une instance migree (prod), la recette test_01 en exige la presence.
    assert "db_revision" in body
