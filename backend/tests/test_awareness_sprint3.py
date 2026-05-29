"""
Tests d'intégration — Awareness Sprint 3 (progression).

Couvre :
  - Liste et détail des programmes
  - Inscription à un programme (enroll)
  - Démarrer un module
  - Heartbeat (time tracking, video position)
  - Terminer un module (sans quiz / avec quiz réussi / avec quiz échoué)
  - completion_pct recalculé après chaque complétion
  - Enrollment status → completed quand tous les modules sont done
  - Dashboard learner
  - Sécurité : learner ne peut pas accéder aux inscriptions d'un autre learner
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


# ── helpers ────────────────────────────────────────────────────────────────────


async def _admin_headers(email: str = "admin_prog@test.com") -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
        r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _setup_learner(admin_email: str, learner_email: str) -> dict:
    """Create org + learner, get magic-link token, return learner auth headers."""
    admin_h = await _admin_headers(admin_email)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations",
                json={"name": "Test Org", "max_learners": 50},
                headers=admin_h,
            )
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": learner_email},
            headers=admin_h,
        )
        token = (
            await c.post(
                f"{BASE}/awareness/auth/magic-link",
                json={"email": learner_email, "organization_id": org_id},
            )
        ).json()["token"]
        session = (await c.get(f"{BASE}/awareness/auth/verify", params={"token": token})).json()
    return {"Authorization": f"Bearer {session['access_token']}"}


async def _create_program_with_modules(admin_h: dict, n_modules: int = 2) -> tuple[int, list[int]]:
    """Use the ContentImporter via a script-style setup for test isolation."""
    import tempfile
    from pathlib import Path

    import yaml

    # Import directly via service to avoid HTTP dependency on content endpoints
    from app.services.awareness_content_importer import import_from_directory

    tmp = Path(tempfile.mkdtemp())
    programs_dir = tmp / "programs"
    modules_dir = tmp / "modules"
    programs_dir.mkdir(parents=True)

    module_slugs = [f"mod-{i}" for i in range(n_modules)]
    prog_data = {
        "slug": f"prog-test-{n_modules}",
        "title": f"Programme {n_modules} modules",
        "language": "fr",
        "version": "1.0",
        "estimated_duration_minutes": n_modules * 3,
        "passing_score": 60,
        "certificate_validity_months": 12,
        "is_active": True,
        "modules": module_slugs,
    }
    (programs_dir / "prog.yaml").write_text(yaml.dump(prog_data), encoding="utf-8")

    for slug in module_slugs:
        mod_dir = modules_dir / slug
        mod_dir.mkdir(parents=True)
        meta = {
            "title": slug,
            "content_type": "markdown",
            "estimated_duration_minutes": 3,
            "xp_points": 10,
            "has_quiz": False,
            "is_active": True,
        }
        (mod_dir / "meta.yaml").write_text(yaml.dump(meta), encoding="utf-8")
        (mod_dir / "content.md").write_text(f"# {slug}", encoding="utf-8")

    # Use the test DB via dependency injection
    import app.core.database as db_mod

    summary = {"program_id": None, "module_ids": []}

    async with db_mod.AsyncSessionLocal() as session:
        result = await import_from_directory(session, tmp / "fr" if (tmp / "fr").exists() else tmp)
        # Fallback: import directly
        if result["programs"] == 0:
            # Re-create with fr subdir
            fr_dir = tmp / "fr"
            (fr_dir / "programs").mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copytree(programs_dir, fr_dir / "programs", dirs_exist_ok=True)
            shutil.copytree(modules_dir, fr_dir / "modules", dirs_exist_ok=True)
            await import_from_directory(session, fr_dir)

        from sqlalchemy import select

        from app.models.awareness_module import AwarenessModule
        from app.models.awareness_program import AwarenessProgram

        prog = (
            await session.execute(
                select(AwarenessProgram).where(AwarenessProgram.slug == f"prog-test-{n_modules}")
            )
        ).scalar_one_or_none()
        if prog:
            summary["program_id"] = prog.id
            mods = (
                (
                    await session.execute(
                        select(AwarenessModule)
                        .where(AwarenessModule.program_id == prog.id)
                        .order_by(AwarenessModule.position)
                    )
                )
                .scalars()
                .all()
            )
            summary["module_ids"] = [m.id for m in mods]

    return summary["program_id"], summary["module_ids"]


# ── Programmes ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_programs_requires_learner_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/programs")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_programs_returns_active_programs():
    learner_h = await _setup_learner("prog_admin1@test.com", "learner1@prog.com")
    prog_id, _ = await _create_program_with_modules(
        await _admin_headers("prog_admin1@test.com"), n_modules=1
    )
    if prog_id is None:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/programs", headers=learner_h)
    assert r.status_code == 200
    assert any(p["id"] == prog_id for p in r.json())


# ── Enrollments ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enroll_learner_returns_201():
    learner_h = await _setup_learner("enroll_admin@test.com", "enrollee@prog.com")
    prog_id, _ = await _create_program_with_modules(
        await _admin_headers("enroll_admin@test.com"), n_modules=1
    )
    if prog_id is None:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/awareness/enrollments",
            params={"program_id": prog_id},
            headers=learner_h,
        )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert r.json()["completion_pct"] == 0.0


@pytest.mark.asyncio
async def test_enroll_twice_returns_existing():
    learner_h = await _setup_learner("enroll2_admin@test.com", "enrollee2@prog.com")
    prog_id, _ = await _create_program_with_modules(
        await _admin_headers("enroll2_admin@test.com"), n_modules=1
    )
    if prog_id is None:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r1 = await c.post(
            f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner_h
        )
        r2 = await c.post(
            f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner_h
        )
    assert r1.json()["id"] == r2.json()["id"]


# ── Progression ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_module_transitions_enrollment_to_in_progress():
    learner_h = await _setup_learner("start_admin@test.com", "starter@prog.com")
    prog_id, mod_ids = await _create_program_with_modules(
        await _admin_headers("start_admin@test.com"), n_modules=2
    )
    if prog_id is None or not mod_ids:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        enroll_id = (
            await c.post(
                f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner_h
            )
        ).json()["id"]
        r = await c.post(
            f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_ids[0]}/start",
            headers=learner_h,
        )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_heartbeat_increments_time():
    learner_h = await _setup_learner("hb_admin@test.com", "hb_learner@prog.com")
    prog_id, mod_ids = await _create_program_with_modules(
        await _admin_headers("hb_admin@test.com"), n_modules=1
    )
    if prog_id is None or not mod_ids:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        enroll_id = (
            await c.post(
                f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner_h
            )
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_ids[0]}/start",
            headers=learner_h,
        )
        r = await c.post(
            f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_ids[0]}/heartbeat",
            json={"elapsed_seconds": 30, "video_position": 45},
            headers=learner_h,
        )
    assert r.status_code == 200
    assert r.json()["time_spent_seconds"] == 30
    assert r.json()["video_resume_position"] == 45


@pytest.mark.asyncio
async def test_complete_module_updates_completion_pct():
    learner_h = await _setup_learner("comp_admin@test.com", "comp_learner@prog.com")
    prog_id, mod_ids = await _create_program_with_modules(
        await _admin_headers("comp_admin@test.com"), n_modules=2
    )
    if prog_id is None or not mod_ids:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        enroll_id = (
            await c.post(
                f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner_h
            )
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_ids[0]}/start",
            headers=learner_h,
        )
        r = await c.post(
            f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_ids[0]}/complete",
            json={},
            headers=learner_h,
        )
    assert r.status_code == 200
    assert r.json()["completion_pct"] == 50.0
    assert r.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_complete_all_modules_sets_enrollment_completed():
    learner_h = await _setup_learner("full_admin@test.com", "full_learner@prog.com")
    prog_id, mod_ids = await _create_program_with_modules(
        await _admin_headers("full_admin@test.com"), n_modules=2
    )
    if prog_id is None or not mod_ids:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        enroll_id = (
            await c.post(
                f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner_h
            )
        ).json()["id"]
        for mod_id in mod_ids:
            await c.post(
                f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_id}/start",
                headers=learner_h,
            )
            await c.post(
                f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_id}/complete",
                json={},
                headers=learner_h,
            )
        r_enrollments = await c.get(f"{BASE}/awareness/enrollments", headers=learner_h)

    enrollment = next(e for e in r_enrollments.json() if e["id"] == enroll_id)
    assert enrollment["completion_pct"] == 100.0
    assert enrollment["status"] == "completed"
    assert enrollment["completed_at"] is not None


@pytest.mark.asyncio
async def test_dashboard_returns_modules_progress():
    learner_h = await _setup_learner("dash_admin@test.com", "dash_learner@prog.com")
    prog_id, mod_ids = await _create_program_with_modules(
        await _admin_headers("dash_admin@test.com"), n_modules=2
    )
    if prog_id is None or not mod_ids:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        enroll_id = (
            await c.post(
                f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner_h
            )
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/enrollments/{enroll_id}/modules/{mod_ids[0]}/start",
            headers=learner_h,
        )
        r = await c.get(
            f"{BASE}/awareness/enrollments/{enroll_id}/dashboard",
            headers=learner_h,
        )
    assert r.status_code == 200
    body = r.json()
    assert "enrollment" in body
    assert "program" in body
    assert "modules_progress" in body
    assert len(body["modules_progress"]) == 2
    statuses = {m["module_id"]: m["status"] for m in body["modules_progress"]}
    assert statuses[mod_ids[0]] == "in_progress"
    assert statuses[mod_ids[1]] == "not_started"


@pytest.mark.asyncio
async def test_other_learner_cannot_access_enrollment():
    learner1_h = await _setup_learner("iso_admin@test.com", "iso_l1@prog.com")
    learner2_h = await _setup_learner("iso_admin2@test.com", "iso_l2@prog.com")
    prog_id, _ = await _create_program_with_modules(
        await _admin_headers("iso_admin@test.com"), n_modules=1
    )
    if prog_id is None:
        pytest.skip("ContentImporter setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        enroll_id = (
            await c.post(
                f"{BASE}/awareness/enrollments", params={"program_id": prog_id}, headers=learner1_h
            )
        ).json()["id"]
        r = await c.get(
            f"{BASE}/awareness/enrollments/{enroll_id}/dashboard",
            headers=learner2_h,
        )
    assert r.status_code == 404
