"""Integration tests — /api/v1/darkweb-dossier (B2B dossier endpoints)."""
import io
import json
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import register_and_login

BASE = "/api/v1"
ENDPOINT = f"{BASE}/darkweb-dossier"

_MOCK_BREACH = {
    "email": "test@acme.fr",
    "breaches": [{"name": "LinkedIn", "domain": "linkedin.com",
                  "breach_date": "2012-05-05", "pwn_count": 164611595,
                  "data_classes": ["Email addresses", "Passwords"],
                  "is_sensitive": False}],
    "total": 1, "status": "WARNING", "provider": "leakcheck", "error": None,
}
_MOCK_CLEAN = {
    "email": "clean@acme.fr", "breaches": [], "total": 0,
    "status": "OK", "provider": "leakcheck", "error": None,
}


def _csv(emails: list[str]) -> bytes:
    lines = ["email"] + emails
    return "\n".join(lines).encode()


def _upload(emails: list[str]):
    return {"emails_csv": ("emails.csv", io.BytesIO(_csv(emails)), "text/csv")}


# ── Auth guards ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_no_auth_returns_401(http_client: AsyncClient):
    r = await http_client.get(ENDPOINT)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_no_auth_returns_401(http_client: AsyncClient):
    r = await http_client.post(ENDPOINT, data={"company_name": "Acme", "domain": "acme.fr"},
                               files=_upload(["a@acme.fr"]))
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_sync_catalog_no_auth_returns_403(http_client: AsyncClient):
    r = await http_client.post(f"{ENDPOINT}/catalog/sync")
    assert r.status_code == 403


# ── Create dossier ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_dossier_returns_201(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier1@test.com")
    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_BREACH):
        r = await http_client.post(
            ENDPOINT,
            data={"company_name": "Acme SAS", "domain": "acme.fr"},
            files=_upload(["alice@acme.fr"]),
            headers=headers,
        )
    assert r.status_code == 201
    data = r.json()
    assert data["company_name"] == "Acme SAS"
    assert data["domain"] == "acme.fr"
    assert data["status"] in ("pending", "processing", "completed")
    assert data["total_emails"] == 1


@pytest.mark.asyncio
async def test_create_dossier_strips_www(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier2@test.com")
    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        r = await http_client.post(
            ENDPOINT,
            data={"company_name": "Corp", "domain": "www.corp.io"},
            files=_upload(["bob@corp.io"]),
            headers=headers,
        )
    assert r.status_code == 201
    assert r.json()["domain"] == "corp.io"


@pytest.mark.asyncio
async def test_create_dossier_empty_csv_returns_400(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier3@test.com")
    r = await http_client.post(
        ENDPOINT,
        data={"company_name": "Acme", "domain": "acme.fr"},
        files={"emails_csv": ("empty.csv", io.BytesIO(b"email\n"), "text/csv")},
        headers=headers,
    )
    assert r.status_code == 400
    assert "email" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_dossier_no_valid_emails_returns_400(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier4@test.com")
    r = await http_client.post(
        ENDPOINT,
        data={"company_name": "Acme", "domain": "acme.fr"},
        files={"emails_csv": ("bad.csv", io.BytesIO(b"email\nnot-an-email\n@nodomain\n"), "text/csv")},
        headers=headers,
    )
    assert r.status_code == 400


# ── List dossiers ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_dossiers_empty_for_new_user(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier5@test.com")
    r = await http_client.get(ENDPOINT, headers=headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_dossiers_only_own(http_client: AsyncClient):
    h1 = await register_and_login(http_client, "dossier6@test.com")
    h2 = await register_and_login(http_client, "dossier7@test.com")

    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        await http_client.post(ENDPOINT, data={"company_name": "A", "domain": "a.fr"},
                               files=_upload(["a@a.fr"]), headers=h1)

    r = await http_client.get(ENDPOINT, headers=h2)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_dossiers_returns_created(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier8@test.com")
    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        await http_client.post(ENDPOINT, data={"company_name": "Corp X", "domain": "corpx.io"},
                               files=_upload(["x@corpx.io"]), headers=headers)

    r = await http_client.get(ENDPOINT, headers=headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["company_name"] == "Corp X"


# ── Get dossier detail ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_dossier_detail(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier9@test.com")
    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_BREACH):
        create_r = await http_client.post(
            ENDPOINT,
            data={"company_name": "Detail Corp", "domain": "detail.fr"},
            files=_upload(["alice@detail.fr"]),
            headers=headers,
        )
    dossier_id = create_r.json()["id"]

    r = await http_client.get(f"{ENDPOINT}/{dossier_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == dossier_id


@pytest.mark.asyncio
async def test_get_dossier_other_user_returns_404(http_client: AsyncClient):
    h1 = await register_and_login(http_client, "dossier10@test.com")
    h2 = await register_and_login(http_client, "dossier11@test.com")

    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        create_r = await http_client.post(
            ENDPOINT,
            data={"company_name": "Private", "domain": "private.fr"},
            files=_upload(["x@private.fr"]),
            headers=h1,
        )
    dossier_id = create_r.json()["id"]

    r = await http_client.get(f"{ENDPOINT}/{dossier_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_dossier_not_found_returns_404(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier12@test.com")
    r = await http_client.get(f"{ENDPOINT}/99999", headers=headers)
    assert r.status_code == 404


# ── Delete dossier ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_dossier(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier13@test.com")
    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        create_r = await http_client.post(
            ENDPOINT,
            data={"company_name": "ToDelete", "domain": "del.fr"},
            files=_upload(["d@del.fr"]),
            headers=headers,
        )
    dossier_id = create_r.json()["id"]

    del_r = await http_client.delete(f"{ENDPOINT}/{dossier_id}", headers=headers)
    assert del_r.status_code == 204

    get_r = await http_client.get(f"{ENDPOINT}/{dossier_id}", headers=headers)
    assert get_r.status_code == 404


@pytest.mark.asyncio
async def test_delete_dossier_other_user_returns_404(http_client: AsyncClient):
    h1 = await register_and_login(http_client, "dossier14@test.com")
    h2 = await register_and_login(http_client, "dossier15@test.com")

    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        create_r = await http_client.post(
            ENDPOINT,
            data={"company_name": "Other", "domain": "other.fr"},
            files=_upload(["o@other.fr"]),
            headers=h1,
        )
    dossier_id = create_r.json()["id"]

    r = await http_client.delete(f"{ENDPOINT}/{dossier_id}", headers=h2)
    assert r.status_code == 404


# ── Per-user limit ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_dossier_limit_enforced(http_client: AsyncClient):
    """Enforce max 20 dossiers per user."""
    from app.api.v1.endpoints import darkweb_dossier as ep_module
    original_limit = ep_module._MAX_DOSSIERS_PER_USER
    ep_module._MAX_DOSSIERS_PER_USER = 2

    headers = await register_and_login(http_client, "dossier_limit@test.com")

    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        for i in range(2):
            r = await http_client.post(
                ENDPOINT,
                data={"company_name": f"Corp {i}", "domain": f"corp{i}.fr"},
                files=_upload([f"u{i}@corp{i}.fr"]),
                headers=headers,
            )
            assert r.status_code == 201

        # Third dossier must be rejected
        r = await http_client.post(
            ENDPOINT,
            data={"company_name": "Extra", "domain": "extra.fr"},
            files=_upload(["e@extra.fr"]),
            headers=headers,
        )
    assert r.status_code == 400
    assert "Limite" in r.json()["detail"]

    ep_module._MAX_DOSSIERS_PER_USER = original_limit


# ── PDF endpoint ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_pdf_returns_pdf_bytes(http_client: AsyncClient):
    headers = await register_and_login(http_client, "dossier_pdf@test.com")
    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_BREACH):
        create_r = await http_client.post(
            ENDPOINT,
            data={"company_name": "PDF Corp", "domain": "pdf.fr"},
            files=_upload(["p@pdf.fr"]),
            headers=headers,
        )
    dossier_id = create_r.json()["id"]

    r = await http_client.get(f"{ENDPOINT}/{dossier_id}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 1000


@pytest.mark.asyncio
async def test_get_pdf_other_user_returns_404(http_client: AsyncClient):
    h1 = await register_and_login(http_client, "dossier_pdf2@test.com")
    h2 = await register_and_login(http_client, "dossier_pdf3@test.com")

    with patch("app.services.darkweb_dossier_service.check_email_breaches", return_value=_MOCK_CLEAN):
        create_r = await http_client.post(
            ENDPOINT,
            data={"company_name": "Private PDF", "domain": "ppdf.fr"},
            files=_upload(["q@ppdf.fr"]),
            headers=h1,
        )
    dossier_id = create_r.json()["id"]

    r = await http_client.get(f"{ENDPOINT}/{dossier_id}/pdf", headers=h2)
    assert r.status_code == 404
