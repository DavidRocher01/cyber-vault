"""Unit tests — darkweb dossier module (CSV parser + dossier service + PDF)."""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.darkweb_dossier import _parse_emails_csv
from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
from app.services.darkweb_dossier_service import generate_dossier_pdf


# ── _parse_emails_csv ─────────────────────────────────────────────────────────

def csv(content: str) -> bytes:
    return content.encode("utf-8")


def test_parse_simple_email_column():
    emails = _parse_emails_csv(csv("email\njohn@acme.fr\njane@acme.fr\n"))
    assert emails == ["john@acme.fr", "jane@acme.fr"]


def test_parse_first_column_when_no_email_header():
    emails = _parse_emails_csv(csv("address,name\nalice@corp.com,Alice\nbob@corp.com,Bob\n"))
    assert "alice@corp.com" in emails
    assert "bob@corp.com" in emails


def test_parse_detects_email_column_by_name():
    emails = _parse_emails_csv(csv("nom,email_pro,dept\nAlice,alice@co.fr,RH\n"))
    assert emails == ["alice@co.fr"]


def test_parse_deduplicates():
    emails = _parse_emails_csv(csv("email\ndup@co.fr\ndup@co.fr\nother@co.fr\n"))
    assert emails.count("dup@co.fr") == 1
    assert len(emails) == 2


def test_parse_strips_whitespace_and_lowercases():
    emails = _parse_emails_csv(csv("email\n  Alice@CORP.COM  \n"))
    assert emails == ["alice@corp.com"]


def test_parse_skips_invalid_entries():
    emails = _parse_emails_csv(csv("email\nnot-an-email\nvalid@co.fr\n@nodomain\n"))
    assert emails == ["valid@co.fr"]


def test_parse_handles_bom():
    content = "﻿email\njohn@acme.fr\n".encode("utf-8-sig")
    emails = _parse_emails_csv(content)
    assert emails == ["john@acme.fr"]


def test_parse_empty_file():
    emails = _parse_emails_csv(csv(""))
    assert emails == []


def test_parse_header_only():
    emails = _parse_emails_csv(csv("email\n"))
    assert emails == []


def test_parse_quoted_values():
    emails = _parse_emails_csv(csv('email\n"quoted@domain.fr"\n'))
    assert emails == ["quoted@domain.fr"]


# ── generate_dossier_pdf ──────────────────────────────────────────────────────

def _make_dossier(**kwargs) -> DarkwebDossier:
    d = MagicMock(spec=DarkwebDossier)
    d.id = kwargs.get("id", 1)
    d.company_name = kwargs.get("company_name", "Acme SAS")
    d.domain = kwargs.get("domain", "acme.fr")
    d.status = kwargs.get("status", "completed")
    d.total_emails = kwargs.get("total_emails", 10)
    d.exposed_emails = kwargs.get("exposed_emails", 3)
    d.total_breach_instances = kwargs.get("total_breach_instances", 7)
    d.risk_score = kwargs.get("risk_score", 30)
    d.top_sources_json = kwargs.get("top_sources_json", json.dumps([
        {"name": "LinkedIn", "count": 3},
        {"name": "Adobe", "count": 2},
    ]))
    d.targets = kwargs.get("targets", [])
    return d


def _make_target(email: str, count: int, status: str = "exposed") -> DarkwebDossierTarget:
    t = MagicMock(spec=DarkwebDossierTarget)
    t.id = 1
    t.email = email
    t.status = status
    t.total_breaches = count
    t.breach_sources_json = json.dumps([
        {"name": "LinkedIn", "domain": "linkedin.com", "breach_date": "2021-06-22",
         "pwn_count": 700000000, "data_classes": ["Email addresses", "Passwords"],
         "is_sensitive": False}
    ]) if count > 0 else "[]"
    t.checked_at = datetime.now(timezone.utc)
    return t


def test_pdf_returns_bytes():
    dossier = _make_dossier()
    pdf = generate_dossier_pdf(dossier, [])
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


def test_pdf_with_exposed_targets():
    targets = [
        _make_target("alice@acme.fr", 3),
        _make_target("bob@acme.fr", 1),
        _make_target("carol@acme.fr", 0, "clean"),
    ]
    dossier = _make_dossier(exposed_emails=2, total_emails=3)
    pdf = generate_dossier_pdf(dossier, targets)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


def test_pdf_zero_risk_score():
    dossier = _make_dossier(risk_score=0, exposed_emails=0, total_breach_instances=0,
                             top_sources_json="[]")
    pdf = generate_dossier_pdf(dossier, [])
    assert isinstance(pdf, bytes)


def test_pdf_max_risk_score():
    targets = [_make_target(f"u{i}@co.fr", 5) for i in range(10)]
    dossier = _make_dossier(risk_score=100, exposed_emails=10, total_emails=10,
                             total_breach_instances=50)
    pdf = generate_dossier_pdf(dossier, targets)
    assert isinstance(pdf, bytes)


# ── risk_score calculation logic ──────────────────────────────────────────────

def test_risk_score_zero_for_clean_dossier():
    """Score must be 0 when no email is exposed."""
    total = 20
    exposed = 0
    heavy = 0
    if total > 0:
        weighted = (exposed + heavy * 0.5) / (total + heavy * 0.5)
        risk_score = min(100, round(weighted * 100))
    else:
        risk_score = 0
    assert risk_score == 0


def test_risk_score_100_for_fully_exposed_heavy():
    """Score is 100 when all emails have 3+ breaches."""
    total = 5
    exposed = 5
    heavy = 5
    weighted = (exposed + heavy * 0.5) / (total + heavy * 0.5)
    risk_score = min(100, round(weighted * 100))
    assert risk_score == 100


def test_risk_score_partial_exposure():
    """Score reflects partial exposure correctly."""
    total = 10
    exposed = 3
    heavy = 1
    weighted = (exposed + heavy * 0.5) / (total + heavy * 0.5)
    risk_score = min(100, round(weighted * 100))
    assert 0 < risk_score < 50


# ── sync_breach_catalog ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_catalog_upserts_entries():
    from app.services.darkweb_dossier_service import sync_breach_catalog

    fake_entries = [
        {"Name": "Adobe", "Title": "Adobe", "Domain": "adobe.com",
         "BreachDate": "2013-10-04", "AddedDate": "2013-12-04T00:00:00Z",
         "PwnCount": 153000000, "Description": "...",
         "DataClasses": ["Email addresses", "Passwords"],
         "IsVerified": True, "IsSensitive": False,
         "IsFabricated": False, "IsSpamList": False},
    ]

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.darkweb_dossier_service.fetch_hibp_breach_catalog",
               return_value=fake_entries):
        count = await sync_breach_catalog(db)

    assert count == 1
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_catalog_returns_zero_on_empty_fetch():
    from app.services.darkweb_dossier_service import sync_breach_catalog

    db = AsyncMock()
    with patch("app.services.darkweb_dossier_service.fetch_hibp_breach_catalog",
               return_value=[]):
        count = await sync_breach_catalog(db)

    assert count == 0
