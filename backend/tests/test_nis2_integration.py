"""
Tests d'intégration — API NIS2 (/api/v1/nis2).

Couvre les comportements ajoutés / corrigés récemment :
  - Sauvegarde complète (34 items via _fullItems)
  - Reset (items vide → score 0)
  - Cohérence PDF / app
  - Score après reset partiel
  - Validation des statuts
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register",
                      json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login",
                          json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _all_ids(client: AsyncClient, headers: dict) -> list[str]:
    r = await client.get(f"{BASE}/nis2/me", headers=headers)
    return [it["id"] for cat in r.json()["categories"] for it in cat["items"]]


# ── Score après reset (items vide) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_items_map_gives_score_0():
    """Sauvegarder {} (reset frontend) → score 0, non_compliant par défaut."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_reset1@test.com")
        r = await c.put(f"{BASE}/nis2/me", json={"items": {}}, headers=h)
    assert r.status_code == 200
    assert r.json()["score"] == 0


@pytest.mark.asyncio
async def test_reset_then_set_two_compliant_gives_low_score():
    """2 conformes + 32 non_compliant (défaut) → score ~ 6%, pas 100%."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_reset2@test.com")
        r = await c.put(f"{BASE}/nis2/me",
                        json={"items": {"rssi": "compliant", "policy": "compliant"}},
                        headers=h)
    score = r.json()["score"]
    assert score < 20, f"Score attendu < 20 (2 conformes / 34), got {score}"


# ── Sauvegarde des 34 items (_fullItems) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_save_full_34_items_persists_all():
    """Sauvegarder les 34 items → GET retourne exactement ces 34 items."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_full1@test.com")
        ids = await _all_ids(c, h)
        full = {id_: "partial" for id_ in ids}
        await c.put(f"{BASE}/nis2/me", json={"items": full}, headers=h)
        r = await c.get(f"{BASE}/nis2/me", headers=h)
    saved = r.json()["items"]
    assert len(saved) == 34
    assert all(v == "partial" for v in saved.values())


@pytest.mark.asyncio
async def test_save_full_34_items_score_is_50_when_all_partial():
    """34 items partiels → score 50%."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_full2@test.com")
        ids = await _all_ids(c, h)
        await c.put(f"{BASE}/nis2/me",
                    json={"items": {id_: "partial" for id_ in ids}}, headers=h)
        r = await c.get(f"{BASE}/nis2/me", headers=h)
    assert r.json()["score"] == 50


@pytest.mark.asyncio
async def test_save_full_map_then_overwrite_partial():
    """Sauvegarder 34 items puis réécrire avec items partiels → DB cohérente."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_overwrite@test.com")
        ids = await _all_ids(c, h)
        # 1ère save : tout compliant
        await c.put(f"{BASE}/nis2/me",
                    json={"items": {id_: "compliant" for id_ in ids}}, headers=h)
        # 2ème save : seulement rssi=non_compliant (reset partiel)
        await c.put(f"{BASE}/nis2/me",
                    json={"items": {"rssi": "non_compliant"}}, headers=h)
        r = await c.get(f"{BASE}/nis2/me", headers=h)
    body = r.json()
    assert body["items"]["rssi"] == "non_compliant"
    # Les autres items de la 1ère save sont effacés (nouvelle sauvegarde partielle)
    assert body["score"] == 0


# ── Cohérence score PDF / API ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pdf_generated_after_save_is_non_empty():
    """PDF généré après sauvegarde → bytes valides (> 1 KB)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_pdfcons1@test.com")
        ids = await _all_ids(c, h)
        items = {id_: "compliant" for id_ in ids[:10]}
        items.update({id_: "non_compliant" for id_ in ids[10:]})
        await c.put(f"{BASE}/nis2/me", json={"items": items}, headers=h)
        r = await c.get(f"{BASE}/nis2/me/pdf", headers=h)
    assert r.status_code == 200
    assert len(r.content) > 5_000


@pytest.mark.asyncio
async def test_pdf_with_all_na_items_is_valid():
    """PDF avec tous les items NA → généré sans erreur."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_pdfna@test.com")
        ids = await _all_ids(c, h)
        await c.put(f"{BASE}/nis2/me",
                    json={"items": {id_: "na" for id_ in ids}}, headers=h)
        r = await c.get(f"{BASE}/nis2/me/pdf", headers=h)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_pdf_with_empty_assessment_is_valid():
    """PDF sans assessment sauvegardé (nouvel utilisateur) → généré sans erreur."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_pdfempty@test.com")
        r = await c.get(f"{BASE}/nis2/me/pdf", headers=h)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


# ── Validation des statuts ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_valid_statuses_accepted():
    """Tous les statuts valides (compliant, partial, non_compliant, na) → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_valid@test.com")
        for status in ("compliant", "partial", "non_compliant", "na"):
            r = await c.put(f"{BASE}/nis2/me",
                            json={"items": {"rssi": status}}, headers=h)
            assert r.status_code == 200, f"Statut '{status}' devrait être accepté"


@pytest.mark.asyncio
async def test_unknown_item_id_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_badid2@test.com")
        r = await c.put(f"{BASE}/nis2/me",
                        json={"items": {"does_not_exist": "compliant"}}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invalid_status_value_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_badval@test.com")
        r = await c.put(f"{BASE}/nis2/me",
                        json={"items": {"rssi": "maybe"}}, headers=h)
    assert r.status_code == 422


# ── updated_at ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_updated_at_set_on_save():
    """updated_at est null avant, non-null après la première sauvegarde."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_date@test.com")
        r_before = await c.get(f"{BASE}/nis2/me", headers=h)
        assert r_before.json()["updated_at"] is None

        await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "compliant"}}, headers=h)
        r_after = await c.get(f"{BASE}/nis2/me", headers=h)
        assert r_after.json()["updated_at"] is not None


@pytest.mark.asyncio
async def test_updated_at_changes_on_second_save():
    """updated_at est différent entre deux sauvegardes successives."""
    import asyncio
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_date2@test.com")
        r1 = await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "compliant"}}, headers=h)
        await asyncio.sleep(0.01)
        r2 = await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "partial"}}, headers=h)
    assert r1.json()["updated_at"] != r2.json()["updated_at"]


# ── Catégories retournées ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_categories_always_returned_in_get():
    """GET /nis2/me retourne toujours les catégories, même sans assessment."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_cats2@test.com")
        r = await c.get(f"{BASE}/nis2/me", headers=h)
    cats = r.json()["categories"]
    assert len(cats) == 10
    assert all("items" in cat for cat in cats)


@pytest.mark.asyncio
async def test_categories_always_returned_in_put():
    """PUT /nis2/me retourne aussi les catégories dans la réponse."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_catput@test.com")
        r = await c.put(f"{BASE}/nis2/me",
                        json={"items": {"rssi": "compliant"}}, headers=h)
    assert len(r.json()["categories"]) == 10
