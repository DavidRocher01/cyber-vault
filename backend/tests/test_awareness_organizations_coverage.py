"""
Tests de couverture ciblés — Awareness multi-tenancy (organizations.py).

Complète test_awareness_sprint2.py en visant les chemins NON couverts :
  - list/get avec agrégation learner_count (état vide, actifs-seulement)
  - ISOLATION inter-tenant sur PATCH / enroll-all / import-csv (404)
  - enroll-all : 404, org vide, comptage enrolled/skipped, envoi email mocké,
    tolérance aux échecs d'envoi email (try/except)
  - import-csv : filename manquant, fichier trop volumineux (>2 MB)
  - validations de payload (nom vide, max_learners hors bornes)
  - accès non authentifié (401)

Mode pytest asyncio_mode=auto → `async def test_...` sans décorateur.
Aucun appel réseau réel : email + magic-link mockés.
"""

from __future__ import annotations

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select

from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_program import AwarenessProgram

BASE = "/api/v1"

# Cible des patches : les symboles importés DANS le module service qui envoie
# les magic-links (la logique enroll-all a été déplacée endpoint -> service).
_ORG_MODULE = "app.services.awareness_organization_service"


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_org(client: AsyncClient, headers: dict, **kw) -> int:
    payload = {"name": kw.pop("name", "Acme"), **kw}
    r = await client.post(f"{BASE}/awareness/organizations", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_learner(client: AsyncClient, headers: dict, org_id: int, email: str) -> int:
    r = await client.post(
        f"{BASE}/awareness/organizations/{org_id}/learners",
        json={"email": email, "first_name": email.split("@")[0]},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_program(db_session, slug: str = "cov-prog") -> int:
    prog = AwarenessProgram(slug=slug, title="Programme couverture")
    db_session.add(prog)
    await db_session.commit()
    await db_session.refresh(prog)
    return prog.id


# ── list / get : agrégation learner_count ────────────────────────────────────────


async def test_list_organizations_empty_returns_empty_list(http_client: AsyncClient):
    h = await _register(http_client, "cov_empty@test.com")
    r = await http_client.get(f"{BASE}/awareness/organizations", headers=h)
    assert r.status_code == 200
    assert r.json() == []


async def test_list_organizations_learner_count_active_only(http_client: AsyncClient):
    h = await _register(http_client, "cov_count@test.com")
    org_id = await _create_org(http_client, h, name="Counted", max_learners=50)
    active_id = await _create_learner(http_client, h, org_id, "act@c.com")
    await _create_learner(http_client, h, org_id, "act2@c.com")
    # Un learner désactivé ne doit PAS être compté (jointure filtrée is_active)
    inactive_id = await _create_learner(http_client, h, org_id, "gone@c.com")
    await http_client.patch(
        f"{BASE}/awareness/organizations/{org_id}/learners/{inactive_id}",
        json={"is_active": False},
        headers=h,
    )
    assert active_id != inactive_id

    r = await http_client.get(f"{BASE}/awareness/organizations", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["learner_count"] == 2


async def test_get_organization_returns_stats_with_learner_count(http_client: AsyncClient):
    h = await _register(http_client, "cov_getstats@test.com")
    org_id = await _create_org(http_client, h, name="Detail", max_learners=30)
    await _create_learner(http_client, h, org_id, "one@d.com")

    r = await http_client.get(f"{BASE}/awareness/organizations/{org_id}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == org_id
    assert body["learner_count"] == 1
    # Champs stats par défaut présents
    assert body["active_enrollments"] == 0
    assert body["completion_rate"] == 0.0


async def test_get_organization_nonexistent_returns_404(http_client: AsyncClient):
    h = await _register(http_client, "cov_get404@test.com")
    r = await http_client.get(f"{BASE}/awareness/organizations/999999", headers=h)
    assert r.status_code == 404


# ── ISOLATION inter-tenant (sécurité) ─────────────────────────────────────────────


async def test_patch_organization_other_tenant_404(http_client: AsyncClient):
    owner = await _register(http_client, "cov_owner_patch@test.com")
    org_id = await _create_org(http_client, owner, name="Private")
    attacker = await _register(http_client, "cov_attacker_patch@test.com")

    r = await http_client.patch(
        f"{BASE}/awareness/organizations/{org_id}",
        json={"name": "Hijacked"},
        headers=attacker,
    )
    assert r.status_code == 404

    # L'org de la victime n'a pas changé
    check = await http_client.get(f"{BASE}/awareness/organizations/{org_id}", headers=owner)
    assert check.json()["name"] == "Private"


async def test_enroll_all_other_tenant_404(http_client: AsyncClient):
    owner = await _register(http_client, "cov_owner_enr@test.com")
    org_id = await _create_org(http_client, owner, name="Victim")
    attacker = await _register(http_client, "cov_attacker_enr@test.com")

    r = await http_client.post(
        f"{BASE}/awareness/organizations/{org_id}/enroll-all",
        params={"program_id": 1},
        headers=attacker,
    )
    assert r.status_code == 404


async def test_import_csv_other_tenant_404(http_client: AsyncClient):
    owner = await _register(http_client, "cov_owner_csv@test.com")
    org_id = await _create_org(http_client, owner, name="CsvVictim")
    attacker = await _register(http_client, "cov_attacker_csv@test.com")

    r = await http_client.post(
        f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
        files={"file": ("x.csv", b"email\na@b.com\n", "text/csv")},
        headers=attacker,
    )
    # Contrôle d'accès AVANT parsing → 404, pas 200
    assert r.status_code == 404


# ── enroll-all : comportements ────────────────────────────────────────────────────


async def test_enroll_all_nonexistent_org_404(http_client: AsyncClient):
    h = await _register(http_client, "cov_enr404@test.com")
    r = await http_client.post(
        f"{BASE}/awareness/organizations/888888/enroll-all",
        params={"program_id": 1},
        headers=h,
    )
    assert r.status_code == 404


async def test_enroll_all_empty_org_returns_zeroes(http_client: AsyncClient):
    """Org sans learner actif → aucune inscription, aucun email, aucune insertion FK."""
    h = await _register(http_client, "cov_enr_empty@test.com")
    org_id = await _create_org(http_client, h, name="EmptyOrg")

    with patch(f"{_ORG_MODULE}.send_awareness_magic_link") as mock_email:
        r = await http_client.post(
            f"{BASE}/awareness/organizations/{org_id}/enroll-all",
            params={"program_id": 1},
            headers=h,
        )
    assert r.status_code == 200
    assert r.json() == {"enrolled": 0, "skipped": 0, "total": 0}
    mock_email.assert_not_called()


async def test_enroll_all_enrolls_and_sends_email(http_client: AsyncClient, db_session):
    h = await _register(http_client, "cov_enr_ok@test.com")
    org_id = await _create_org(http_client, h, name="EnrollOrg", max_learners=50)
    await _create_learner(http_client, h, org_id, "l1@e.com")
    await _create_learner(http_client, h, org_id, "l2@e.com")
    program_id = await _seed_program(db_session, slug="cov-enroll-ok")

    with patch(f"{_ORG_MODULE}.send_awareness_magic_link") as mock_email:
        r = await http_client.post(
            f"{BASE}/awareness/organizations/{org_id}/enroll-all",
            params={"program_id": program_id},
            headers=h,
        )
    assert r.status_code == 200
    body = r.json()
    # 2 learners actifs, aucun déjà inscrit → 2 nouveaux inscrits, 2 emails
    assert body == {"enrolled": 2, "skipped": 0, "total": 2}
    assert mock_email.call_count == 2


async def test_enroll_all_skips_already_enrolled(http_client: AsyncClient, db_session):
    """Deuxième appel : learners déjà inscrits → skipped, pas de nouvel email."""
    h = await _register(http_client, "cov_enr_skip@test.com")
    org_id = await _create_org(http_client, h, name="SkipOrg", max_learners=50)
    await _create_learner(http_client, h, org_id, "s1@e.com")
    program_id = await _seed_program(db_session, slug="cov-enroll-skip")

    with patch(f"{_ORG_MODULE}.send_awareness_magic_link"):
        await http_client.post(
            f"{BASE}/awareness/organizations/{org_id}/enroll-all",
            params={"program_id": program_id},
            headers=h,
        )

    with patch(f"{_ORG_MODULE}.send_awareness_magic_link") as mock_email:
        r = await http_client.post(
            f"{BASE}/awareness/organizations/{org_id}/enroll-all",
            params={"program_id": program_id},
            headers=h,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["enrolled"] == 0
    assert body["skipped"] == 1
    mock_email.assert_not_called()


async def test_enroll_all_email_failure_is_swallowed(http_client: AsyncClient, db_session):
    """L'échec d'envoi d'email ne doit PAS faire échouer l'inscription (try/except)."""
    h = await _register(http_client, "cov_enr_mailfail@test.com")
    org_id = await _create_org(http_client, h, name="MailFailOrg", max_learners=50)
    await _create_learner(http_client, h, org_id, "mf@e.com")
    program_id = await _seed_program(db_session, slug="cov-enroll-mailfail")

    with patch(
        f"{_ORG_MODULE}.send_awareness_magic_link",
        side_effect=RuntimeError("SMTP down"),
    ) as mock_email:
        r = await http_client.post(
            f"{BASE}/awareness/organizations/{org_id}/enroll-all",
            params={"program_id": program_id},
            headers=h,
        )
    assert r.status_code == 200
    assert r.json()["enrolled"] == 1
    mock_email.assert_called_once()

    # L'inscription a bien été committée malgré l'échec email
    rows = (
        (
            await db_session.execute(
                select(AwarenessLearner).where(AwarenessLearner.organization_id == org_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


# ── import-csv : validations de fichier ───────────────────────────────────────────


async def test_import_csv_missing_filename_rejected(http_client: AsyncClient):
    h = await _register(http_client, "cov_csv_noname@test.com")
    org_id = await _create_org(http_client, h, name="NoNameCsv")
    # Nom de fichier vide → not file.filename → 422
    r = await http_client.post(
        f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
        files={"file": ("", b"email\na@b.com\n", "text/csv")},
        headers=h,
    )
    assert r.status_code == 422


async def test_import_csv_too_large_rejected(http_client: AsyncClient):
    h = await _register(http_client, "cov_csv_big@test.com")
    org_id = await _create_org(http_client, h, name="BigCsv")
    big = b"email\n" + (b"x@y.com\n" * 300_000)  # > 2 MB
    assert len(big) > 2 * 1024 * 1024
    r = await http_client.post(
        f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
        files={"file": ("big.csv", big, "text/csv")},
        headers=h,
    )
    assert r.status_code == 422
    assert "volumineux" in r.json()["detail"]


# ── validations de payload (create) ───────────────────────────────────────────────


async def test_create_organization_empty_name_422(http_client: AsyncClient):
    h = await _register(http_client, "cov_badname@test.com")
    r = await http_client.post(f"{BASE}/awareness/organizations", json={"name": ""}, headers=h)
    assert r.status_code == 422


async def test_create_organization_max_learners_out_of_bounds_422(http_client: AsyncClient):
    h = await _register(http_client, "cov_badquota@test.com")
    r = await http_client.post(
        f"{BASE}/awareness/organizations",
        json={"name": "Ok", "max_learners": 0},
        headers=h,
    )
    assert r.status_code == 422

    r2 = await http_client.post(
        f"{BASE}/awareness/organizations",
        json={"name": "Ok", "max_learners": 100_000},
        headers=h,
    )
    assert r2.status_code == 422


# ── authentification requise ──────────────────────────────────────────────────────


async def test_create_organization_requires_auth(http_client: AsyncClient):
    r = await http_client.post(f"{BASE}/awareness/organizations", json={"name": "NoAuth"})
    assert r.status_code in (401, 403)


async def test_list_organizations_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/awareness/organizations")
    assert r.status_code in (401, 403)
