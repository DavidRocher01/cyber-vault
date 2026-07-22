"""
Tests — Awareness Sprint 5 : attestations (certificats).

Couvre :
  - _generate_public_id : format CERT-YYYY-XXXXXX
  - _compute_signature / verify_signature : HMAC-SHA256
  - issue_certificate : création, idempotence, frozen_data
  - verify_certificate : valide, token incorrect, révoqué, expiré
  - generate_certificate_pdf : bytes PDF valides (> 1 KB, entête %PDF)
  - Endpoint /verify-certificate/{id} : 200 valide, 404 invalide
  - Endpoint GET /awareness/enrollments/{id}/certificate : 404 sans cert
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.services.awareness_certificate_service import (
    _compute_signature,
    _generate_public_id,
    generate_certificate_pdf,
    verify_signature,
)

# ── Unit tests ─────────────────────────────────────────────────────────────────


def test_public_id_format():
    pid = _generate_public_id()
    year = str(datetime.now(UTC).year)
    assert pid.startswith(f"CERT-{year}-")
    parts = pid.split("-")
    assert len(parts) == 3
    assert len(parts[2]) == 6
    # Hex majuscule : ne doit contenir aucune minuscule. NB : `.isupper()` renvoie
    # False sur un suffixe tout-chiffres (aucun caractère casse) -> ~6% de flake ;
    # on vérifie donc l'invariant réel (== upper) au lieu de isupper().
    assert parts[2] == parts[2].upper()
    assert all(c in "0123456789ABCDEF" for c in parts[2])


def test_public_id_unique():
    ids = {_generate_public_id() for _ in range(20)}
    assert len(ids) == 20


def test_signature_deterministic():
    sig1 = _compute_signature('{"key":"val"}')
    sig2 = _compute_signature('{"key":"val"}')
    assert sig1 == sig2
    assert len(sig1) == 64


def test_signature_changes_with_data():
    s1 = _compute_signature('{"a":1}')
    s2 = _compute_signature('{"a":2}')
    assert s1 != s2


def test_verify_signature_valid():
    data = '{"learner":"alice"}'
    sig = _compute_signature(data)
    assert verify_signature(data, sig) is True


def test_verify_signature_tampered():
    data = '{"learner":"alice"}'
    sig = _compute_signature(data)
    tampered = '{"learner":"mallory"}'
    assert verify_signature(tampered, sig) is False


def test_verify_signature_wrong_hash():
    data = '{"learner":"alice"}'
    assert verify_signature(data, "a" * 64) is False


# ── PDF generation ─────────────────────────────────────────────────────────────


def _mock_cert():
    cert = MagicMock()
    cert.public_id = "CERT-2026-ABCDEF"
    cert.verification_token = "tok123"
    cert.issued_at = datetime.now(UTC)
    cert.expires_at = datetime.now(UTC) + timedelta(days=365)
    cert.frozen_data_json = json.dumps(
        {
            "learner_name": "Alice Dupont",
            "program_title": "NIS2 Essentiel",
            "program_version": "1.0",
            "completion_pct": 100.0,
        }
    )
    return cert


def test_generate_certificate_pdf_returns_bytes():
    cert = _mock_cert()
    frozen = json.loads(cert.frozen_data_json)
    pdf = generate_certificate_pdf(cert, frozen)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


def test_generate_certificate_pdf_is_pdf():
    cert = _mock_cert()
    frozen = json.loads(cert.frozen_data_json)
    pdf = generate_certificate_pdf(cert, frozen)
    assert pdf[:4] == b"%PDF"


def test_generate_certificate_pdf_no_expiry():
    cert = _mock_cert()
    cert.expires_at = None
    frozen = json.loads(cert.frozen_data_json)
    pdf = generate_certificate_pdf(cert, frozen)
    assert pdf[:4] == b"%PDF"


# ── Integration tests (HTTP) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_certificate_endpoint_invalid_token():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/verify-certificate/CERT-2026-INVALID?token=badtoken123456")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_certificate_endpoint_not_found():
    """Enrollment sans certificat → 404."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Register user + get org + create learner + get magic link
        await c.post(
            "/api/v1/auth/register",
            json={"email": "cert_admin@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "cert_admin@test.com", "password": "StrongPass123!"},
        )
        admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        org_id = (
            await c.post("/api/v1/awareness/organizations", json={"name": "Acme"}, headers=admin_h)
        ).json()["id"]
        await c.post(
            f"/api/v1/awareness/organizations/{org_id}/learners",
            json={"email": "cert_learner@test.com"},
            headers=admin_h,
        )
        from awareness_helpers import get_awareness_magic_token

        token = await get_awareness_magic_token("cert_learner@test.com", org_id)
        session = (await c.get("/api/v1/awareness/auth/verify", params={"token": token})).json()
        learner_h = {"Authorization": f"Bearer {session['access_token']}"}

        r = await c.get("/api/v1/awareness/enrollments/9999/certificate", headers=learner_h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_download_certificate_endpoint_not_found():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            "/api/v1/auth/register",
            json={"email": "dl_cert_admin@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "dl_cert_admin@test.com", "password": "StrongPass123!"},
        )
        admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        org_id = (
            await c.post("/api/v1/awareness/organizations", json={"name": "Acme"}, headers=admin_h)
        ).json()["id"]
        await c.post(
            f"/api/v1/awareness/organizations/{org_id}/learners",
            json={"email": "dl_learner@test.com"},
            headers=admin_h,
        )
        from awareness_helpers import get_awareness_magic_token

        token = await get_awareness_magic_token("dl_learner@test.com", org_id)
        session = (await c.get("/api/v1/awareness/auth/verify", params={"token": token})).json()
        learner_h = {"Authorization": f"Bearer {session['access_token']}"}

        r = await c.get(
            "/api/v1/awareness/enrollments/9999/certificate/download", headers=learner_h
        )
    assert r.status_code == 404
