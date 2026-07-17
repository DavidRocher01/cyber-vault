"""Infra / liveness : l'app repond, la DB est joignable, les migrations sont a head."""

from conftest import API


def test_health_ok_and_db_reachable(client):
    r = client.get(f"{API}/health")
    assert r.status_code == 200, f"/health injoignable: {r.status_code}"
    body = r.json()
    assert body["status"] == "ok", f"status degrade: {body}"
    assert body["database"] == "ok", f"DB KO: {body}"


def test_health_exposes_applied_migration(client):
    """La revision Alembic reellement appliquee doit etre presente (non vide) :
    signe que le migrate step du deploy a bien tourne."""
    body = client.get(f"{API}/health").json()
    assert body.get("db_revision"), f"revision Alembic absente: {body}"
    assert body.get("version"), f"version applicative absente: {body}"
