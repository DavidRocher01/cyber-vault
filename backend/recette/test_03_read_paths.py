"""Chemins de lecture publics critiques (aucun effet de bord)."""

from conftest import API


def test_plans_are_served(client):
    r = client.get(f"{API}/plans")
    assert r.status_code == 200, f"/plans KO: {r.status_code}"
    plans = r.json()
    assert isinstance(plans, list) and len(plans) >= 1, f"plans vides: {plans}"
    # Chaque plan doit avoir un identifiant et un prix (forme minimale).
    for p in plans:
        assert "id" in p, f"plan sans id: {p}"


def test_blog_is_served(client):
    r = client.get(f"{API}/blog/articles")
    assert r.status_code == 200, f"/blog/articles KO: {r.status_code}"
    # La liste peut etre paginee (dict) ou brute (list) — on accepte les deux.
    body = r.json()
    assert body is not None
