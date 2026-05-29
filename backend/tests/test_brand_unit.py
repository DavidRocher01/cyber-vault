"""Unit tests — Feature #12: Rapport PDF Marque Blanche."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_user(uid=1):
    u = MagicMock()
    u.id = uid
    u.email = "test@example.com"
    return u


def _make_brand(user_id=1):
    b = MagicMock()
    b.id = 1
    b.user_id = user_id
    b.company_name = "Acme Corp"
    b.accent_color = "#ff5500"
    b.logo_b64 = None
    b.updated_at = datetime.now(UTC)
    return b


def _make_scan(scan_id=42, status="done", overall_status="WARNING"):
    s = MagicMock()
    s.id = scan_id
    s.site_id = 10
    s.status = status
    s.overall_status = overall_status
    s.results_json = json.dumps(
        {
            "checks": [
                {
                    "severity": "critical",
                    "title": "Open port 22",
                    "description": "SSH exposed",
                },
                {
                    "severity": "warning",
                    "title": "Missing CSP",
                    "description": "No CSP header",
                },
                {
                    "severity": "info",
                    "title": "HTTP/2",
                    "description": "HTTP/2 enabled",
                },
            ]
        }
    )
    s.finished_at = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    s.created_at = datetime(2026, 5, 1, 11, 0, 0, tzinfo=UTC)
    return s


def _make_site(url="https://acme.com"):
    si = MagicMock()
    si.url = url
    return si


# ---------------------------------------------------------------------------
# _extract_findings
# ---------------------------------------------------------------------------


def test_extract_findings_normal():
    from app.services.branded_scan_pdf import _extract_findings

    scan_json = json.dumps({"checks": [{"severity": "critical", "title": "T1"}]})
    findings = _extract_findings(scan_json)
    assert len(findings) == 1
    assert findings[0]["title"] == "T1"


def test_extract_findings_empty_json():
    from app.services.branded_scan_pdf import _extract_findings

    assert _extract_findings(None) == []
    assert _extract_findings("{}") == []


def test_extract_findings_bad_json():
    from app.services.branded_scan_pdf import _extract_findings

    assert _extract_findings("not-json") == []


# ---------------------------------------------------------------------------
# _compute_score
# ---------------------------------------------------------------------------


def test_compute_score_no_findings_ok():
    from app.services.branded_scan_pdf import _compute_score

    assert _compute_score([], "OK") == 100


def test_compute_score_no_findings_unknown():
    from app.services.branded_scan_pdf import _compute_score

    assert _compute_score([], "WARNING") == 0


def test_compute_score_with_criticals():
    from app.services.branded_scan_pdf import _compute_score

    findings = [{"severity": "critical"}] * 3
    score = _compute_score(findings, "CRITICAL")
    assert score == max(0, 100 - 3 * 15)


def test_compute_score_clamped():
    from app.services.branded_scan_pdf import _compute_score

    findings = [{"severity": "critical"}] * 10
    score = _compute_score(findings, "CRITICAL")
    assert score == 0


# ---------------------------------------------------------------------------
# generate_branded_pdf — smoke test (PDF bytes returned)
# ---------------------------------------------------------------------------


def test_generate_branded_pdf_returns_pdf():
    from app.services.branded_scan_pdf import generate_branded_pdf

    pdf = generate_branded_pdf(
        company_name="Test SA",
        accent_color="#06b6d4",
        logo_b64=None,
        domain="test.com",
        overall_status="OK",
        score_pct=85,
        scan_date="01/05/2026",
        findings=[],
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_generate_branded_pdf_with_findings():
    from app.services.branded_scan_pdf import generate_branded_pdf

    findings = [
        {
            "severity": "critical",
            "title": "SQL injection",
            "description": "Found in /login",
        },
        {"severity": "warning", "title": "Missing X-Frame", "description": ""},
    ]
    pdf = generate_branded_pdf(
        company_name="Corp",
        accent_color="#ff5500",
        logo_b64=None,
        domain="corp.io",
        overall_status="CRITICAL",
        score_pct=25,
        scan_date="01/05/2026",
        findings=findings,
    )
    assert pdf[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# GET /api/v1/brand/me — no brand
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_brand_no_profile():
    from app.api.v1.endpoints.brand import get_brand

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_brand(current_user=_make_user(), db=db)
    assert result is None


@pytest.mark.asyncio
async def test_get_brand_existing():
    from app.api.v1.endpoints.brand import get_brand

    brand = _make_brand()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = brand
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_brand(current_user=_make_user(), db=db)
    assert result is brand


# ---------------------------------------------------------------------------
# PUT /api/v1/brand/me — upsert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_brand_creates_new():
    from app.api.v1.endpoints.brand import BrandProfileIn, upsert_brand

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    payload = BrandProfileIn(company_name="New Corp", accent_color="#112233")
    result = await upsert_brand(payload=payload, current_user=_make_user(), db=db)
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_brand_updates_existing():
    from app.api.v1.endpoints.brand import BrandProfileIn, upsert_brand

    brand = _make_brand()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = brand
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    payload = BrandProfileIn(
        company_name="Updated",
        accent_color="#aabbcc",
        logo_b64="data:image/png;base64,abc",
    )
    await upsert_brand(payload=payload, current_user=_make_user(), db=db)

    assert brand.company_name == "Updated"
    assert brand.accent_color == "#aabbcc"
    assert brand.logo_b64 == "data:image/png;base64,abc"
    db.add.assert_not_called()
    db.commit.assert_called_once()
