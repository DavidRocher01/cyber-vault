"""
Tests de couverture ciblée — Awareness learners CRUD & magic-link.

Complète test_awareness_sprint2.py en visant les chemins NON couverts de
app/api/v1/endpoints/awareness/learners.py :
  - create_learner : org 404 (owner différent / org inexistante), non authentifié,
    email invalide (422 validation), échec envoi email (branche try/except),
    issue_magic_link renvoyant None (learner désactivé côté service).
  - list_learners : org 404, active_only=False (inclut inactifs).
  - update_learner : org 404, learner 404 (id inexistant), learner d'une AUTRE
    organisation non accessible (isolation multi-tenant).
  - request_magic_link : org introuvable → fallback nom, branche échec envoi.
  - verify_magic_link_token : token trop court (422 validation).

asyncio_mode=auto → pas de décorateur, fixtures async standard.
"""

from __future__ import annotations

from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


# ── helpers ────────────────────────────────────────────────────────────────────


async def _headers(email: str) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
        r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_org(
    c: AsyncClient, headers: dict, name: str = "Org", max_learners: int = 50
) -> int:
    r = await c.post(
        f"{BASE}/awareness/organizations",
        json={"name": name, "max_learners": max_learners},
        headers=headers,
    )
    return r.json()["id"]


async def _create_learner(c: AsyncClient, headers: dict, org_id: int, email: str) -> int:
    r = await c.post(
        f"{BASE}/awareness/organizations/{org_id}/learners",
        json={"email": email},
        headers=headers,
    )
    return r.json()["id"]


# ── create_learner : chemins d'erreur ───────────────────────────────────────────


async def test_create_learner_org_not_owned_returns_404():
    """Un utilisateur ne peut pas ajouter de learner à l'org d'un autre (isolation)."""
    owner = await _headers("cl_owner@test.com")
    intruder = await _headers("cl_intruder@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, owner, "Owned")
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "x@acme.com"},
            headers=intruder,
        )
    assert r.status_code == 404


async def test_create_learner_org_nonexistent_returns_404():
    h = await _headers("cl_ghostorg@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/awareness/organizations/999999/learners",
            json={"email": "x@acme.com"},
            headers=h,
        )
    assert r.status_code == 404


async def test_create_learner_unauthenticated_401():
    """Sans header Authorization → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/awareness/organizations/1/learners",
            json={"email": "x@acme.com"},
        )
    assert r.status_code == 401


async def test_create_learner_invalid_email_422():
    h = await _headers("cl_bademail@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h)
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "not-an-email"},
            headers=h,
        )
    assert r.status_code == 422


async def test_create_learner_email_send_failure_still_201():
    """Si l'envoi du magic-link échoue, la création réussit quand même (try/except)."""
    h = await _headers("cl_sendfail@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h)
        with patch(
            "app.api.v1.endpoints.awareness.learners.send_awareness_magic_link",
            side_effect=RuntimeError("smtp down"),
        ):
            r = await c.post(
                f"{BASE}/awareness/organizations/{org_id}/learners",
                json={"email": "resilient@acme.com", "first_name": "Res"},
                headers=h,
            )
    assert r.status_code == 201
    assert r.json()["email"] == "resilient@acme.com"


async def test_create_learner_issue_magic_link_none_still_201():
    """issue_magic_link renvoie None (magic_result falsy) → pas d'email, 201 OK."""
    h = await _headers("cl_nolink@test.com")

    async def _none(*args, **kwargs):
        return None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h)
        with (
            patch(
                "app.api.v1.endpoints.awareness.learners.issue_magic_link",
                side_effect=_none,
            ),
            patch("app.api.v1.endpoints.awareness.learners.send_awareness_magic_link") as send_mock,
        ):
            r = await c.post(
                f"{BASE}/awareness/organizations/{org_id}/learners",
                json={"email": "nolink@acme.com"},
                headers=h,
            )
    assert r.status_code == 201
    send_mock.assert_not_called()


# ── list_learners ────────────────────────────────────────────────────────────────


async def test_list_learners_org_not_owned_404():
    owner = await _headers("ll_owner@test.com")
    intruder = await _headers("ll_intruder@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, owner)
        r = await c.get(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            headers=intruder,
        )
    assert r.status_code == 404


async def test_list_learners_active_only_false_includes_inactive():
    """active_only=False → les learners désactivés apparaissent aussi."""
    h = await _headers("ll_inactive@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h)
        learner_id = await _create_learner(c, h, org_id, "dormant@acme.com")
        await c.patch(
            f"{BASE}/awareness/organizations/{org_id}/learners/{learner_id}",
            json={"is_active": False},
            headers=h,
        )
        r_default = await c.get(f"{BASE}/awareness/organizations/{org_id}/learners", headers=h)
        r_all = await c.get(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            params={"active_only": "false"},
            headers=h,
        )
    assert r_default.status_code == 200
    assert all(lr["is_active"] for lr in r_default.json())
    assert r_all.status_code == 200
    emails = {lr["email"] for lr in r_all.json()}
    assert "dormant@acme.com" in emails
    assert any(lr["is_active"] is False for lr in r_all.json())


async def test_list_learners_empty_org_returns_empty_list():
    h = await _headers("ll_empty@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h)
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/learners", headers=h)
    assert r.status_code == 200
    assert r.json() == []


# ── update_learner ───────────────────────────────────────────────────────────────


async def test_update_learner_org_not_owned_404():
    owner = await _headers("ul_owner@test.com")
    intruder = await _headers("ul_intruder@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, owner)
        learner_id = await _create_learner(c, owner, org_id, "victim@acme.com")
        r = await c.patch(
            f"{BASE}/awareness/organizations/{org_id}/learners/{learner_id}",
            json={"department": "hacked"},
            headers=intruder,
        )
    assert r.status_code == 404


async def test_update_learner_nonexistent_id_404():
    h = await _headers("ul_ghost@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h)
        r = await c.patch(
            f"{BASE}/awareness/organizations/{org_id}/learners/424242",
            json={"department": "RH"},
            headers=h,
        )
    assert r.status_code == 404


async def test_update_learner_wrong_org_isolation_404():
    """Un learner de l'org A n'est pas atteignable via l'URL de l'org B (même owner)."""
    h = await _headers("ul_multitenant@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_a = await _create_org(c, h, "OrgA")
        org_b = await _create_org(c, h, "OrgB")
        learner_a = await _create_learner(c, h, org_a, "insidea@acme.com")
        # Tenter de modifier le learner de A via l'URL de B
        r = await c.patch(
            f"{BASE}/awareness/organizations/{org_b}/learners/{learner_a}",
            json={"department": "leak"},
            headers=h,
        )
    assert r.status_code == 404


# ── request_magic_link : branches ────────────────────────────────────────────────


async def test_magic_link_send_failure_still_202():
    """Échec d'envoi d'email lors du magic-link → toujours 202 (try/except)."""
    h = await _headers("ml_sendfail@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h)
        await _create_learner(c, h, org_id, "sendfail@acme.com")
        with patch(
            "app.api.v1.endpoints.awareness.learners.send_awareness_magic_link",
            side_effect=RuntimeError("smtp down"),
        ):
            r = await c.post(
                f"{BASE}/awareness/auth/magic-link",
                json={"email": "sendfail@acme.com", "organization_id": org_id},
            )
    assert r.status_code == 202
    assert "message" in r.json()


async def test_magic_link_known_learner_sends_email_with_org_name():
    """Learner connu → issue_magic_link OK, org résolue, send appelé avec org_name."""
    h = await _headers("ml_orgname@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = await _create_org(c, h, "Rocher SA")
        await _create_learner(c, h, org_id, "known@acme.com")
        with patch(
            "app.api.v1.endpoints.awareness.learners.send_awareness_magic_link"
        ) as send_mock:
            r = await c.post(
                f"{BASE}/awareness/auth/magic-link",
                json={"email": "known@acme.com", "organization_id": org_id},
            )
    assert r.status_code == 202
    send_mock.assert_called_once()
    # L'org existe → son nom réel est transmis (pas le fallback).
    assert send_mock.call_args.kwargs["org_name"] == "Rocher SA"


# ── verify_magic_link_token : validation ─────────────────────────────────────────


async def test_verify_token_too_short_422():
    """token < min_length=10 → 422 validation avant d'atteindre le service."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/auth/verify", params={"token": "short"})
    assert r.status_code == 422


async def test_verify_token_missing_param_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/auth/verify")
    assert r.status_code == 422
