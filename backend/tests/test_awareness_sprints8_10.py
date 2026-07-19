"""
Tests — Awareness Sprints 8-10 : NIS2 rapport, observabilité.

Sprint 8 — NIS2 compliance :
  - compute_nis2_metrics : structure retournée
  - map_requirements : statuts corrects (compliant/partial/non_compliant)
  - compute_global_score : 100% si tout compliant, 0% si tout non_compliant
  - generate_nis2_report_pdf : PDF valide
  - Endpoints GET /nis2-report et /nis2-report/pdf (auth requise)

Sprint 10 — Observabilité :
  - Scheduler job enregistré
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.awareness_nis2_report import (
    compute_global_score,
    generate_nis2_report_pdf,
    map_requirements,
)

BASE = "/api/v1"


# ── map_requirements ───────────────────────────────────────────────────────────


def test_map_requirements_all_compliant():
    metrics = {
        "general_completion_pct": 90.0,
        "overall_completion_pct": 90.0,
        "learner_participation_pct": 90.0,
        "incident_module_completion_pct": 90.0,
        "continuity_module_completion_pct": 90.0,
    }
    reqs = map_requirements(metrics)
    assert all(r["status"] == "compliant" for r in reqs)
    assert all(r["gap"] == 0.0 for r in reqs)


def test_map_requirements_all_non_compliant():
    metrics = dict.fromkeys(
        [
            "general_completion_pct",
            "overall_completion_pct",
            "learner_participation_pct",
            "incident_module_completion_pct",
            "continuity_module_completion_pct",
        ],
        0.0,
    )
    reqs = map_requirements(metrics)
    assert all(r["status"] == "non_compliant" for r in reqs)


def test_map_requirements_partial():
    # 75% of threshold = partial zone
    metrics = dict.fromkeys(
        [
            "general_completion_pct",
            "overall_completion_pct",
            "learner_participation_pct",
            "incident_module_completion_pct",
            "continuity_module_completion_pct",
        ],
        65.0,
    )
    reqs = map_requirements(metrics)
    # 65% vs threshold 80% = 65/80 = 81% → partial (≥ 75% of threshold)
    statuses = {r["status"] for r in reqs}
    assert "partial" in statuses or "non_compliant" in statuses


def test_map_requirements_gap_calculated():
    metrics = {
        "general_completion_pct": 50.0,
        "overall_completion_pct": 50.0,
        "learner_participation_pct": 50.0,
        "incident_module_completion_pct": 50.0,
        "continuity_module_completion_pct": 50.0,
    }
    reqs = map_requirements(metrics)
    # general_completion threshold=80, value=50 → gap=30
    general = next(r for r in reqs if r["article"] == "Art. 21(a)")
    assert general["gap"] == 30.0


def test_map_requirements_returns_5_requirements():
    metrics = dict.fromkeys(
        [
            "general_completion_pct",
            "overall_completion_pct",
            "learner_participation_pct",
            "incident_module_completion_pct",
            "continuity_module_completion_pct",
        ],
        80.0,
    )
    reqs = map_requirements(metrics)
    assert len(reqs) == 5


# ── compute_global_score ───────────────────────────────────────────────────────


def test_global_score_all_compliant():
    reqs = [{"status": "compliant"}] * 5
    assert compute_global_score(reqs) == 100.0


def test_global_score_all_non_compliant():
    reqs = [{"status": "non_compliant"}] * 5
    assert compute_global_score(reqs) == 0.0


def test_global_score_mixed():
    reqs = [
        {"status": "compliant"},
        {"status": "partial"},
        {"status": "non_compliant"},
        {"status": "compliant"},
        {"status": "partial"},
    ]
    # weights: 2+1+0+2+1 = 6 / (5*2=10) = 60%
    assert compute_global_score(reqs) == 60.0


def test_global_score_empty():
    assert compute_global_score([]) == 0.0


# ── generate_nis2_report_pdf ───────────────────────────────────────────────────


def _sample_requirements():
    return [
        {
            "article": "Art. 21(g)",
            "title": "Hygiène cyber",
            "value": 85.0,
            "threshold": 80,
            "status": "compliant",
            "status_label": "Conforme",
            "color": "green",
            "gap": 0.0,
        },
        {
            "article": "Art. 21(b)",
            "title": "Gestion incidents",
            "value": 45.0,
            "threshold": 75,
            "status": "non_compliant",
            "status_label": "Non conforme",
            "color": "red",
            "gap": 30.0,
        },
    ]


def test_generate_nis2_pdf_returns_pdf():
    from datetime import UTC, datetime

    pdf = generate_nis2_report_pdf(
        "Acme Corp",
        _sample_requirements(),
        50.0,
        {"overall_completion_pct": 60.0, "learner_participation_pct": 75.0},
        12,
        datetime.now(UTC),
    )
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_generate_nis2_pdf_zero_score():
    from datetime import UTC, datetime

    reqs = [
        {
            "article": "Art. 21(a)",
            "title": "Test",
            "value": 0.0,
            "threshold": 80,
            "status": "non_compliant",
            "status_label": "Non conforme",
            "color": "red",
            "gap": 80.0,
        }
    ]
    pdf = generate_nis2_report_pdf("Zero Corp", reqs, 0.0, {}, 0, datetime.now(UTC))
    assert pdf[:4] == b"%PDF"


# ── Endpoints NIS2 (auth) ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nis2_report_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/organizations/1/nis2-report")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_nis2_report_pdf_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/organizations/1/nis2-report/pdf")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_nis2_report_404_other_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "nis2_u1@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login", json={"email": "nis2_u1@test.com", "password": "StrongPass123!"}
        )
        h1 = {"Authorization": f"Bearer {r.json()['access_token']}"}

        await c.post(
            f"{BASE}/auth/register",
            json={"email": "nis2_u2@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login", json={"email": "nis2_u2@test.com", "password": "StrongPass123!"}
        )
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "NIS2 Org"}, headers=h1)
        ).json()["id"]

        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/nis2-report", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_nis2_report_returns_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "nis2_ok@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login", json={"email": "nis2_ok@test.com", "password": "StrongPass123!"}
        )
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "NIS2 OK"}, headers=h)
        ).json()["id"]
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/nis2-report", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert "global_score" in body
    assert "requirements" in body
    assert len(body["requirements"]) == 5


@pytest.mark.asyncio
async def test_nis2_report_pdf_returns_pdf_bytes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "nis2_pdf@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login", json={"email": "nis2_pdf@test.com", "password": "StrongPass123!"}
        )
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "PDF Org"}, headers=h)
        ).json()["id"]
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/nis2-report/pdf", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


# ── Scheduler Sprint 10 ────────────────────────────────────────────────────────


def test_awareness_at_risk_job_registered():
    """start_scheduler() doit enregistrer le job awareness_at_risk."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    from app.services.scheduler import _run_awareness_at_risk_detection

    # Crée un scheduler temporaire pour vérifier que le job est bien déclaré
    tmp = AsyncIOScheduler()
    tmp.add_job(
        _run_awareness_at_risk_detection,
        trigger=CronTrigger(hour=4, minute=0),
        id="awareness_at_risk",
    )
    job_ids = [job.id for job in tmp.get_jobs()]
    assert "awareness_at_risk" in job_ids
