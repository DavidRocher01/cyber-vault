"""
Tests — système de facturation
Covers:
  - invoice_service : numérotation séquentielle FACT-YYYY-NNNN
  - invoice_pdf     : génération PDF (bytes non vides, structure PDF)
  - GET /invoices             — liste paginée, auth isolation
  - GET /invoices/{id}        — détail, 404 autre utilisateur
  - GET /invoices/{id}/pdf    — téléchargement PDF
  - POST /admin/invoices      — création manuelle, lien compte utilisateur
  - GET  /admin/invoices      — liste admin
  - GET  /admin/invoices/{id}/pdf
  - webhook invoice.payment_succeeded — création auto + déduplication
"""

from datetime import UTC, date, datetime
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"
WEBHOOK_URL = f"{BASE}/webhooks/stripe"
ADMIN_KEY = "test-admin-key"
ADMIN_HEADERS = {"x-admin-key": ADMIN_KEY}


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _register_login(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


_wh_counter = 0


def _make_webhook_event(event_type: str, data: dict) -> dict:
    global _wh_counter
    _wh_counter += 1
    return {
        "id": f"evt_inv_{_wh_counter}",
        "type": event_type,
        "data": {"object": data},
    }


async def _create_invoice_via_admin(client: AsyncClient, **overrides) -> dict:
    payload = {
        "client_name": "Jean Dupont",
        "client_email": "jean@dupont.fr",
        "description": "Audit Flash — exemple.com",
        "amount_cents": 29000,
        **overrides,
    }
    with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
        r = await client.post(f"{BASE}/admin/invoices", json=payload, headers=ADMIN_HEADERS)
    assert r.status_code == 201, r.text
    return r.json()


# ── invoice_service unit tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoice_sequential_numbering():
    """Deux factures la même année → séquence 0001 puis 0002."""
    import app.core.database as db_mod
    from app.services.invoice_service import create_invoice

    today = date.today()
    year = today.year

    async with db_mod.AsyncSessionLocal() as db:
        inv1 = await create_invoice(
            db,
            user_id=None,
            type="audit",
            client_name="A",
            client_email="a@a.com",
            client_address=None,
            description="Test 1",
            amount_cents=10000,
            issue_date=today,
        )
        inv2 = await create_invoice(
            db,
            user_id=None,
            type="audit",
            client_name="B",
            client_email="b@b.com",
            client_address=None,
            description="Test 2",
            amount_cents=20000,
            issue_date=today,
        )
        await db.commit()

    assert inv1.invoice_seq < inv2.invoice_seq
    assert inv1.invoice_number.startswith(f"FACT-{year}-")
    assert inv2.invoice_number.startswith(f"FACT-{year}-")
    assert inv1.invoice_number != inv2.invoice_number


@pytest.mark.asyncio
async def test_invoice_number_format():
    """Le numéro doit respecter le format FACT-YYYY-NNNN."""
    import re

    import app.core.database as db_mod
    from app.services.invoice_service import create_invoice

    async with db_mod.AsyncSessionLocal() as db:
        inv = await create_invoice(
            db,
            user_id=None,
            type="subscription",
            client_name="C",
            client_email="c@c.com",
            client_address=None,
            description="Abonnement",
            amount_cents=990,
            issue_date=date.today(),
        )
        await db.commit()

    assert re.match(r"^FACT-\d{4}-\d{4}$", inv.invoice_number)


# ── invoice_pdf unit tests ─────────────────────────────────────────────────────


def test_invoice_pdf_returns_bytes():
    """generate_invoice_pdf doit retourner des bytes non vides."""
    from app.services.invoice_pdf import generate_invoice_pdf

    pdf = generate_invoice_pdf(
        invoice_number="FACT-2026-0001",
        issue_date=date(2026, 5, 19),
        client_name="Jean Dupont",
        client_email="jean@dupont.fr",
        client_address="12 rue de la Paix, 75001 Paris",
        description="Audit Flash",
        amount_cents=29000,
    )
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


def test_invoice_pdf_is_valid_pdf():
    """Le PDF généré doit commencer par la signature %PDF."""
    from app.services.invoice_pdf import generate_invoice_pdf

    pdf = generate_invoice_pdf(
        invoice_number="FACT-2026-0002",
        issue_date=date(2026, 5, 19),
        client_name="Client Test",
        client_email="test@test.com",
        client_address=None,
        description="Abonnement Rocher Cybersécurité",
        amount_cents=990,
    )
    assert pdf[:4] == b"%PDF"


def test_invoice_pdf_no_address():
    """La génération fonctionne sans adresse client."""
    from app.services.invoice_pdf import generate_invoice_pdf

    pdf = generate_invoice_pdf(
        invoice_number="FACT-2026-0003",
        issue_date=date(2026, 5, 19),
        client_name="Sans Adresse",
        client_email="sa@test.com",
        client_address=None,
        description="Test sans adresse",
        amount_cents=5000,
    )
    assert pdf[:4] == b"%PDF"


# ── GET /invoices ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_invoices_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/invoices")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_invoices_empty_for_new_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _register_login(c, "inv_empty@test.com")
        r = await c.get(f"{BASE}/invoices", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []


@pytest.mark.asyncio
async def test_list_invoices_returns_only_own():
    """Un utilisateur ne voit que ses propres factures."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _register_login(c, "inv_own1@test.com")
        h2 = await _register_login(c, "inv_own2@test.com")

        # Crée une facture liée à user1 via admin
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            await c.post(
                f"{BASE}/admin/invoices",
                headers=ADMIN_HEADERS,
                json={
                    "client_name": "User1",
                    "client_email": "inv_own1@test.com",
                    "description": "Audit",
                    "amount_cents": 10000,
                    "user_email": "inv_own1@test.com",
                },
            )

        r1 = await c.get(f"{BASE}/invoices", headers=h1)
        r2 = await c.get(f"{BASE}/invoices", headers=h2)

    assert r1.json()["total"] == 1
    assert r2.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_invoices_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _register_login(c, "inv_page@test.com")

        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            for i in range(3):
                await c.post(
                    f"{BASE}/admin/invoices",
                    headers=ADMIN_HEADERS,
                    json={
                        "client_name": f"Client {i}",
                        "client_email": "inv_page@test.com",
                        "description": f"Audit {i}",
                        "amount_cents": 10000,
                        "user_email": "inv_page@test.com",
                    },
                )

        r = await c.get(f"{BASE}/invoices?page=1&per_page=2", headers=h)

    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


# ── GET /invoices/{id} ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_invoice_returns_correct_data():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _register_login(c, "inv_get@test.com")

        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            created = await _create_invoice_via_admin(
                c,
                user_email="inv_get@test.com",
                client_email="inv_get@test.com",
            )

        r = await c.get(f"{BASE}/invoices/{created['id']}", headers=h)

    assert r.status_code == 200
    assert r.json()["id"] == created["id"]
    assert r.json()["invoice_number"] == created["invoice_number"]


@pytest.mark.asyncio
async def test_get_invoice_other_user_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h_owner = await _register_login(c, "inv_o1@test.com")
        h_other = await _register_login(c, "inv_o2@test.com")

        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            created = await _create_invoice_via_admin(
                c,
                user_email="inv_o1@test.com",
                client_email="inv_o1@test.com",
            )

        r = await c.get(f"{BASE}/invoices/{created['id']}", headers=h_other)

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_invoice_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _register_login(c, "inv_404@test.com")
        r = await c.get(f"{BASE}/invoices/99999", headers=h)
    assert r.status_code == 404


# ── GET /invoices/{id}/pdf ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_download_invoice_pdf_returns_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _register_login(c, "inv_pdf@test.com")

        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            created = await _create_invoice_via_admin(
                c,
                user_email="inv_pdf@test.com",
                client_email="inv_pdf@test.com",
            )

        r = await c.get(f"{BASE}/invoices/{created['id']}/pdf", headers=h)

    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_download_invoice_pdf_other_user_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h_owner = await _register_login(c, "inv_pdfown@test.com")
        h_spy = await _register_login(c, "inv_pdfspy@test.com")

        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            created = await _create_invoice_via_admin(
                c,
                user_email="inv_pdfown@test.com",
                client_email="inv_pdfown@test.com",
            )

        r = await c.get(f"{BASE}/invoices/{created['id']}/pdf", headers=h_spy)

    assert r.status_code == 404


# ── POST /admin/invoices ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_create_invoice_returns_201():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            r = await c.post(
                f"{BASE}/admin/invoices",
                headers=ADMIN_HEADERS,
                json={
                    "client_name": "Société Test",
                    "client_email": "contact@societe.fr",
                    "client_address": "1 rue du Test, 75000 Paris",
                    "description": "Audit cybersécurité Flash",
                    "amount_cents": 29000,
                },
            )

    assert r.status_code == 201
    data = r.json()
    assert data["invoice_number"].startswith("FACT-")
    assert data["type"] == "audit"
    assert data["amount_cents"] == 29000
    assert data["status"] == "paid"


@pytest.mark.asyncio
async def test_admin_create_invoice_wrong_key_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            r = await c.post(
                f"{BASE}/admin/invoices",
                headers={"x-admin-key": "wrong"},
                json={
                    "client_name": "Test",
                    "client_email": "t@t.fr",
                    "description": "Test",
                    "amount_cents": 1000,
                },
            )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_invoice_links_user_account():
    """Si user_email correspond à un compte, user_id doit être renseigné."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await _register_login(c, "inv_link@test.com")

        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            r = await c.post(
                f"{BASE}/admin/invoices",
                headers=ADMIN_HEADERS,
                json={
                    "client_name": "Linked User",
                    "client_email": "inv_link@test.com",
                    "description": "Audit",
                    "amount_cents": 29000,
                    "user_email": "inv_link@test.com",
                },
            )

    assert r.status_code == 201
    assert r.json()["user_id"] is not None


@pytest.mark.asyncio
async def test_admin_create_invoice_unknown_user_email_still_creates():
    """user_email inconnu → facture créée sans user_id."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            r = await c.post(
                f"{BASE}/admin/invoices",
                headers=ADMIN_HEADERS,
                json={
                    "client_name": "Inconnu",
                    "client_email": "inconnu@test.fr",
                    "description": "Audit",
                    "amount_cents": 29000,
                    "user_email": "nope@nowhere.com",
                },
            )

    assert r.status_code == 201
    assert r.json()["user_id"] is None


# ── GET /admin/invoices ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_invoices_requires_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            r = await c.get(f"{BASE}/admin/invoices")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_invoices_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            await _create_invoice_via_admin(c)
            r = await c.get(f"{BASE}/admin/invoices", headers=ADMIN_HEADERS)

    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


# ── GET /admin/invoices/{id}/pdf ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_pdf_download_returns_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            created = await _create_invoice_via_admin(c)
            r = await c.get(f"{BASE}/admin/invoices/{created['id']}/pdf", headers=ADMIN_HEADERS)

    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_admin_pdf_unknown_invoice_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.core.config.settings.ADMIN_API_KEY", ADMIN_KEY):
            r = await c.get(f"{BASE}/admin/invoices/99999/pdf", headers=ADMIN_HEADERS)
    assert r.status_code == 404


# ── webhook invoice.payment_succeeded ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_invoice_payment_creates_invoice():
    """invoice.payment_succeeded doit créer une facture en base."""
    from sqlalchemy import select

    import app.core.database as db_mod
    from app.models.invoice import Invoice

    stripe_invoice_id = "in_test_auto_001"
    event = _make_webhook_event(
        "invoice.payment_succeeded",
        {
            "id": stripe_invoice_id,
            "customer_email": "wh_inv1@test.com",
            "customer_name": "Client Webhook",
            "amount_paid": 990,
            "created": int(datetime(2026, 5, 19, tzinfo=UTC).timestamp()),
            "lines": {"data": [{"description": "Abonnement Rocher Cybersécurité Starter"}]},
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "wh_inv1@test.com", "password": "StrongPass123!"},
        )
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})

    assert r.status_code == 200

    async with db_mod.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
        )
        inv = result.scalar_one_or_none()

    assert inv is not None
    assert inv.type == "subscription"
    assert inv.amount_cents == 990
    assert inv.status == "paid"
    assert inv.client_email == "wh_inv1@test.com"


@pytest.mark.asyncio
async def test_webhook_invoice_payment_deduplication():
    """Deux webhooks avec le même stripe_invoice_id → une seule facture créée."""
    from sqlalchemy import func, select

    import app.core.database as db_mod
    from app.models.invoice import Invoice

    stripe_invoice_id = "in_test_dedup_002"
    event = _make_webhook_event(
        "invoice.payment_succeeded",
        {
            "id": stripe_invoice_id,
            "customer_email": "wh_inv2@test.com",
            "amount_paid": 990,
            "created": int(datetime(2026, 5, 19, tzinfo=UTC).timestamp()),
            "lines": {"data": [{"description": "Abonnement Rocher Cybersécurité"}]},
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})
            await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})

    async with db_mod.AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.stripe_invoice_id == stripe_invoice_id)
        )
        count = result.scalar_one()

    assert count == 1


@pytest.mark.asyncio
async def test_webhook_invoice_zero_amount_ignored():
    """amount_paid = 0 → aucune facture créée."""
    from sqlalchemy import select

    import app.core.database as db_mod
    from app.models.invoice import Invoice

    stripe_invoice_id = "in_test_zero_003"
    event = _make_webhook_event(
        "invoice.payment_succeeded",
        {
            "id": stripe_invoice_id,
            "customer_email": "wh_inv3@test.com",
            "amount_paid": 0,
            "created": int(datetime(2026, 5, 19, tzinfo=UTC).timestamp()),
            "lines": {"data": []},
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})

    assert r.status_code == 200

    async with db_mod.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
        )
        inv = result.scalar_one_or_none()

    assert inv is None


@pytest.mark.asyncio
async def test_webhook_invoice_missing_email_ignored():
    """Pas de customer_email → aucune facture créée, pas de crash."""
    stripe_invoice_id = "in_test_noemail_004"
    event = _make_webhook_event(
        "invoice.payment_succeeded",
        {
            "id": stripe_invoice_id,
            "amount_paid": 990,
            "created": int(datetime(2026, 5, 19, tzinfo=UTC).timestamp()),
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})

    assert r.status_code == 200
