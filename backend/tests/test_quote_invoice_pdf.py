"""Unit tests — quote_pdf and invoice_pdf generators."""

from datetime import date

from app.services.invoice_pdf import (
    _date as invoice_date,
)
from app.services.invoice_pdf import (
    _fmt as invoice_fmt,
)
from app.services.invoice_pdf import (
    generate_invoice_pdf,
)
from app.services.quote_pdf import (
    _date as quote_date,
)
from app.services.quote_pdf import (
    _fmt as quote_fmt,
)
from app.services.quote_pdf import (
    generate_quote_pdf,
)

# ── _fmt ──────────────────────────────────────────────────────────────────────


def test_quote_fmt_zero():
    assert quote_fmt(0) == "0.00 €"


def test_quote_fmt_round_euros():
    assert quote_fmt(10000) == "100.00 €"


def test_quote_fmt_cents():
    result = quote_fmt(1234)
    assert "12" in result
    assert "34" in result


def test_invoice_fmt_zero():
    assert invoice_fmt(0) == "0.00 €"


def test_invoice_fmt_round_euros():
    assert invoice_fmt(50000) == "500.00 €"


# ── _date ─────────────────────────────────────────────────────────────────────


def test_quote_date_january():
    d = date(2026, 1, 15)
    assert "janvier" in quote_date(d)
    assert "2026" in quote_date(d)


def test_quote_date_december():
    d = date(2026, 12, 31)
    assert "décembre" in quote_date(d)


def test_invoice_date_all_months():
    months_fr = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    for i, name in enumerate(months_fr, 1):
        assert name in invoice_date(date(2026, i, 1))


# ── generate_quote_pdf ────────────────────────────────────────────────────────


def _quote_items():
    return [
        {"description": "Audit de sécurité", "quantity": 1, "unit_price_cents": 120000},
        {"description": "Rapport PDF", "quantity": 1, "unit_price_cents": 30000},
    ]


def test_generate_quote_pdf_returns_pdf():
    pdf = generate_quote_pdf(
        quote_number="DEV-2026-001",
        issue_date=date(2026, 5, 1),
        validity_days=30,
        client_name="Acme Corp",
        client_email="contact@acme.fr",
        client_address="12 rue de la Paix, 75001 Paris",
        subject="Mission de conseil cybersécurité",
        items=_quote_items(),
        total_cents=150000,
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_generate_quote_pdf_no_address():
    pdf = generate_quote_pdf(
        quote_number="DEV-2026-002",
        issue_date=date(2026, 5, 1),
        validity_days=15,
        client_name="Dupont SAS",
        client_email="dupont@example.fr",
        client_address=None,
        subject="Pentest",
        items=[{"description": "Pentest web", "quantity": 1, "unit_price_cents": 80000}],
        total_cents=80000,
    )
    assert pdf[:4] == b"%PDF"


def test_generate_quote_pdf_empty_items():
    pdf = generate_quote_pdf(
        quote_number="DEV-2026-003",
        issue_date=date(2026, 6, 15),
        validity_days=45,
        client_name="Solo Client",
        client_email="solo@example.com",
        client_address=None,
        subject="À définir",
        items=[],
        total_cents=0,
    )
    assert pdf[:4] == b"%PDF"


def test_generate_quote_pdf_many_items():
    items = [
        {"description": f"Prestation {i}", "quantity": i, "unit_price_cents": i * 10000}
        for i in range(1, 12)
    ]
    pdf = generate_quote_pdf(
        quote_number="DEV-2026-004",
        issue_date=date(2026, 3, 1),
        validity_days=30,
        client_name="Big Client SA",
        client_email="big@client.fr",
        client_address="42 avenue des Champs",
        subject="Contrat cadre",
        items=items,
        total_cents=sum(i * i * 10000 for i in range(1, 12)),
    )
    assert pdf[:4] == b"%PDF"


def test_generate_quote_pdf_non_standard_validity():
    pdf = generate_quote_pdf(
        quote_number="DEV-2026-005",
        issue_date=date(2026, 12, 1),
        validity_days=7,
        client_name="Express Client",
        client_email="express@test.com",
        client_address=None,
        subject="Mission urgente",
        items=[{"description": "Intervention", "quantity": 1, "unit_price_cents": 50000}],
        total_cents=50000,
    )
    assert pdf[:4] == b"%PDF"


# ── generate_invoice_pdf ───────────────────────────────────────────────────────


def test_generate_invoice_pdf_returns_pdf():
    pdf = generate_invoice_pdf(
        invoice_number="FAC-2026-001",
        issue_date=date(2026, 5, 1),
        client_name="Acme Corp",
        client_email="billing@acme.fr",
        client_address="12 rue de la Paix, 75001 Paris",
        description="Audit de sécurité — Mai 2026",
        amount_cents=150000,
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_generate_invoice_pdf_no_address():
    pdf = generate_invoice_pdf(
        invoice_number="FAC-2026-002",
        issue_date=date(2026, 6, 1),
        client_name="Dupont SAS",
        client_email="dupont@example.fr",
        client_address=None,
        description="Pentest application web",
        amount_cents=80000,
    )
    assert pdf[:4] == b"%PDF"


def test_generate_invoice_pdf_zero_amount():
    pdf = generate_invoice_pdf(
        invoice_number="FAC-2026-003",
        issue_date=date(2026, 1, 1),
        client_name="Test Corp",
        client_email="test@corp.fr",
        client_address=None,
        description="Prestation offerte",
        amount_cents=0,
    )
    assert pdf[:4] == b"%PDF"


def test_generate_invoice_pdf_large_amount():
    pdf = generate_invoice_pdf(
        invoice_number="FAC-2026-004",
        issue_date=date(2026, 11, 15),
        client_name="Enterprise SA",
        client_email="finance@enterprise.fr",
        client_address="100 boulevard Haussmann, 75008 Paris",
        description="Contrat annuel de cybersécurité managée",
        amount_cents=1200000,
    )
    assert pdf[:4] == b"%PDF"


def test_generate_invoice_pdf_long_description():
    desc = "Prestation de conseil " + "en cybersécurité " * 20
    pdf = generate_invoice_pdf(
        invoice_number="FAC-2026-005",
        issue_date=date(2026, 7, 1),
        client_name="Verbeux SARL",
        client_email="contact@verbeux.fr",
        client_address=None,
        description=desc,
        amount_cents=99900,
    )
    assert pdf[:4] == b"%PDF"
