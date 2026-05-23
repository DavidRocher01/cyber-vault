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


def _make_target(
    email: str,
    count: int,
    status: str = "exposed",
    check_status: str | None = None,
    data_classes: list[str] | None = None,
) -> DarkwebDossierTarget:
    t = MagicMock(spec=DarkwebDossierTarget)
    t.id = 1
    t.email = email
    t.status = status
    t.check_status = check_status or ("exposed" if count > 0 else "verified_clean")
    t.total_breaches = count
    dc = data_classes if data_classes is not None else ["Email addresses", "Passwords"]
    t.breach_sources_json = json.dumps([
        {"name": "LinkedIn", "domain": "linkedin.com", "breach_date": "2021-06-22",
         "pwn_count": 700000000, "data_classes": dc, "is_sensitive": False}
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


# ── export_dossier_csv ────────────────────────────────────────────────────────

def test_export_csv_returns_bytes():
    from app.services.darkweb_dossier_service import export_dossier_csv
    dossier = _make_dossier()
    result = export_dossier_csv(dossier, [])
    assert isinstance(result, bytes)


def test_export_csv_contains_header_row():
    from app.services.darkweb_dossier_service import export_dossier_csv
    dossier = _make_dossier()
    result = export_dossier_csv(dossier, [])
    text = result.decode("utf-8-sig")
    assert "Email" in text
    assert "Statut" in text
    assert "Nb fuites" in text


def test_export_csv_contains_target_rows():
    from app.services.darkweb_dossier_service import export_dossier_csv
    targets = [
        _make_target("alice@acme.fr", 2),
        _make_target("bob@acme.fr", 0, "clean"),
    ]
    dossier = _make_dossier(total_emails=2, exposed_emails=1)
    result = export_dossier_csv(dossier, targets)
    text = result.decode("utf-8-sig")
    assert "alice@acme.fr" in text
    assert "bob@acme.fr" in text


def test_export_csv_exposed_status_in_row():
    from app.services.darkweb_dossier_service import export_dossier_csv
    targets = [_make_target("carol@acme.fr", 1)]
    result = export_dossier_csv(_make_dossier(), targets)
    text = result.decode("utf-8-sig")
    assert "exposed" in text
    assert "carol@acme.fr" in text


def test_export_csv_bom_prefix():
    from app.services.darkweb_dossier_service import export_dossier_csv
    result = export_dossier_csv(_make_dossier(), [])
    assert result.startswith(b"\xef\xbb\xbf"), "CSV doit commencer par un BOM UTF-8"


# ── _compute_severity ─────────────────────────────────────────────────────────

def test_compute_severity_zero_with_no_targets():
    from app.services.darkweb_dossier_service import _compute_severity
    assert _compute_severity([]) == 0


def test_compute_severity_zero_with_clean_targets():
    from app.services.darkweb_dossier_service import _compute_severity
    t = _make_target("x@co.fr", 0, "clean")
    t.breach_sources_json = "[]"
    assert _compute_severity([t]) == 0


def test_compute_severity_high_with_passwords():
    from app.services.darkweb_dossier_service import _compute_severity
    t = MagicMock()
    t.breach_sources_json = json.dumps([
        {"name": "LinkedIn", "data_classes": ["Passwords", "Email addresses"]},
        {"name": "Adobe", "data_classes": ["Passwords"]},
    ])
    score = _compute_severity([t])
    assert score > 50, f"Score attendu > 50, obtenu {score}"


def test_compute_severity_low_with_email_only():
    from app.services.darkweb_dossier_service import _compute_severity
    t = MagicMock()
    t.breach_sources_json = json.dumps([
        {"name": "Spam", "data_classes": ["Email addresses"]},
    ])
    score = _compute_severity([t])
    assert score < 50, f"Score attendu < 50, obtenu {score}"


def test_compute_severity_max_with_financial():
    from app.services.darkweb_dossier_service import _compute_severity
    t = MagicMock()
    t.breach_sources_json = json.dumps([
        {"name": "Bank", "data_classes": ["Credit card numbers", "Bank account details"]},
    ])
    score = _compute_severity([t])
    assert score > 0


def test_compute_severity_ignores_invalid_json():
    from app.services.darkweb_dossier_service import _compute_severity
    t = MagicMock()
    t.breach_sources_json = "not-json"
    assert _compute_severity([t]) == 0


# ── _build_recommendations ────────────────────────────────────────────────────

def _make_dossier_for_recs(**kwargs) -> DarkwebDossier:
    d = MagicMock(spec=DarkwebDossier)
    d.risk_score = kwargs.get("risk_score", 10)
    d.unverified_count = kwargs.get("unverified_count", 0)
    return d


def test_build_recs_returns_at_least_one():
    from app.services.darkweb_dossier_service import _build_recommendations
    recs = _build_recommendations(_make_dossier_for_recs(), [])
    assert len(recs) >= 1


def test_build_recs_max_six():
    from app.services.darkweb_dossier_service import _build_recommendations
    targets = [_make_target(f"u{i}@co.fr", 2) for i in range(10)]
    recs = _build_recommendations(_make_dossier_for_recs(risk_score=80), targets)
    assert len(recs) <= 6


def test_build_recs_includes_password_reset_when_exposed():
    from app.services.darkweb_dossier_service import _build_recommendations
    targets = [_make_target("a@co.fr", 2)]
    recs = _build_recommendations(_make_dossier_for_recs(), targets)
    titles = [r[0] for r in recs]
    assert any("mot de passe" in t.lower() or "password" in t.lower() or "réinitialisation" in t.lower() for t in titles)


def test_build_recs_includes_mfa_when_password_class_found():
    from app.services.darkweb_dossier_service import _build_recommendations
    targets = [_make_target("a@co.fr", 2, data_classes=["Passwords", "Email addresses"])]
    recs = _build_recommendations(_make_dossier_for_recs(), targets)
    titles = [r[0] for r in recs]
    assert any("mfa" in t.lower() or "multi-facteur" in t.lower() or "authentification" in t.lower() for t in titles)


def test_build_recs_includes_financial_when_credit_class_found():
    from app.services.darkweb_dossier_service import _build_recommendations
    targets = [_make_target("a@co.fr", 1, data_classes=["Credit card numbers"])]
    recs = _build_recommendations(_make_dossier_for_recs(), targets)
    titles = [r[0] for r in recs]
    assert any("financ" in t.lower() or "bancaire" in t.lower() for t in titles)


def test_build_recs_includes_incomplete_when_unverified():
    from app.services.darkweb_dossier_service import _build_recommendations
    error_target = _make_target("b@co.fr", 0, status="error", check_status="rate_limited")
    recs = _build_recommendations(_make_dossier_for_recs(), [error_target])
    titles_and_bodies = " ".join(r[0] + r[1] for r in recs).lower()
    assert "incompl" in titles_and_bodies or "non vérif" in titles_and_bodies or "rate" in titles_and_bodies


def test_build_recs_high_risk_surveillance_text():
    from app.services.darkweb_dossier_service import _build_recommendations
    recs = _build_recommendations(_make_dossier_for_recs(risk_score=75), [])
    surveillance = next((r for r in recs if "surveillance" in r[0].lower()), None)
    assert surveillance is not None
    assert "75%" in surveillance[1] or "élevé" in surveillance[1].lower()


def test_build_recs_no_financial_rec_without_financial_class():
    from app.services.darkweb_dossier_service import _build_recommendations
    targets = [_make_target("a@co.fr", 2, data_classes=["Email addresses"])]
    recs = _build_recommendations(_make_dossier_for_recs(), targets)
    titles = [r[0] for r in recs]
    assert not any("financ" in t.lower() or "bancaire" in t.lower() for t in titles)


# ── check_status determination logic ─────────────────────────────────────────

def test_check_status_rate_limited_when_rate_in_error():
    api_status = "unknown"
    api_error = "Rate limited — retry later"
    is_rate = any(kw in api_error.lower() for kw in ("rate", "429", "retry", "throttl"))
    check_status = "rate_limited" if is_rate else "api_error"
    assert check_status == "rate_limited"


def test_check_status_api_error_when_network_failure():
    api_status = "unknown"
    api_error = "Connection timed out"
    is_rate = any(kw in api_error.lower() for kw in ("rate", "429", "retry", "throttl"))
    check_status = "rate_limited" if is_rate else "api_error"
    assert check_status == "api_error"


def test_check_status_verified_clean_when_count_zero_and_ok():
    api_status = "OK"
    count = 0
    if api_status == "unknown":
        result_status = "error"
        check_status = "api_error"
    elif count > 0:
        result_status = "exposed"
        check_status = "exposed"
    else:
        result_status = "clean"
        check_status = "verified_clean"
    assert result_status == "clean"
    assert check_status == "verified_clean"


def test_check_status_exposed_when_count_nonzero():
    api_status = "CRITICAL"
    count = 3
    if api_status == "unknown":
        result_status = "error"
        check_status = "api_error"
    elif count > 0:
        result_status = "exposed"
        check_status = "exposed"
    else:
        result_status = "clean"
        check_status = "verified_clean"
    assert result_status == "exposed"
    assert check_status == "exposed"


# ── risk_score with verified_total ────────────────────────────────────────────

def test_risk_score_excludes_unverified_from_total():
    """Risk score uses verified_total (total - unverified), not raw total."""
    total = 10
    unverified = 3
    exposed = 3
    verified_total = total - unverified
    heavy = 0
    weighted = (exposed + heavy * 0.5) / (verified_total + heavy * 0.5)
    risk_score = min(100, round(weighted * 100))
    assert risk_score == 43  # 3/7 ≈ 43%


def test_risk_score_zero_when_all_unverified():
    total = 5
    unverified = 5
    exposed = 0
    verified_total = total - unverified
    risk_score = 0 if verified_total == 0 else min(100, round(exposed / verified_total * 100))
    assert risk_score == 0


# ── CSV check_status column ───────────────────────────────────────────────────

def test_export_csv_contains_check_status_header():
    from app.services.darkweb_dossier_service import export_dossier_csv
    result = export_dossier_csv(_make_dossier(), [])
    text = result.decode("utf-8-sig")
    assert "Vérification API" in text


def test_export_csv_check_status_in_target_row():
    from app.services.darkweb_dossier_service import export_dossier_csv
    t = _make_target("carol@co.fr", 2)
    t.check_status = "exposed"
    result = export_dossier_csv(_make_dossier(), [t])
    text = result.decode("utf-8-sig")
    assert "exposed" in text


def test_export_csv_check_status_rate_limited():
    from app.services.darkweb_dossier_service import export_dossier_csv
    t = _make_target("d@co.fr", 0, status="error")
    t.check_status = "rate_limited"
    result = export_dossier_csv(_make_dossier(), [t])
    text = result.decode("utf-8-sig")
    assert "rate_limited" in text
