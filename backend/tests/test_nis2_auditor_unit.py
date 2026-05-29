"""Unit tests — Feature #18: Export NIS2 prêt-à-déposer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CATEGORIES = [
    {
        "label": "Gouvernance",
        "items": [
            {"id": "mgmt_policy", "label": "Politique de sécurité"},
            {"id": "mgmt_roles", "label": "Rôles et responsabilités"},
        ],
    },
    {
        "label": "Gestion des risques",
        "items": [
            {"id": "risk_assess", "label": "Évaluation des risques"},
            {"id": "risk_treat", "label": "Traitement des risques"},
        ],
    },
]


def _items_all_compliant():
    return {
        "mgmt_policy": "compliant",
        "mgmt_roles": "compliant",
        "risk_assess": "compliant",
        "risk_treat": "compliant",
    }


def _items_mixed():
    return {
        "mgmt_policy": "compliant",
        "mgmt_roles": "partial",
        "risk_assess": "non_compliant",
        "risk_treat": "na",
    }


# ---------------------------------------------------------------------------
# _domain_scores
# ---------------------------------------------------------------------------


def test_domain_scores_all_compliant():
    from app.services.nis2_auditor_pdf import _domain_scores

    result = _domain_scores(_CATEGORIES, _items_all_compliant())
    for _, pct in result:
        assert pct == 100


def test_domain_scores_mixed():
    from app.services.nis2_auditor_pdf import _domain_scores

    result = _domain_scores(_CATEGORIES, _items_mixed())
    scores = dict(result)
    assert scores["Gouvernance"] < 100
    assert scores["Gestion des risques"] == 0


def test_domain_scores_empty_items():
    from app.services.nis2_auditor_pdf import _domain_scores

    result = _domain_scores(_CATEGORIES, {})
    for _, pct in result:
        assert pct == 0


# ---------------------------------------------------------------------------
# generate_nis2_auditor_pdf — smoke tests
# ---------------------------------------------------------------------------


def test_generate_auditor_pdf_returns_pdf_bytes():
    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    pdf = generate_nis2_auditor_pdf(
        categories=_CATEGORIES,
        items=_items_all_compliant(),
        score=100,
        user_email="test@example.com",
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        company_name="Test Corp",
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_generate_auditor_pdf_with_nc_items():
    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    pdf = generate_nis2_auditor_pdf(
        categories=_CATEGORIES,
        items=_items_mixed(),
        score=40,
        user_email="admin@corp.fr",
        updated_at=None,
        company_name="",
    )
    assert pdf[:4] == b"%PDF"


def test_generate_auditor_pdf_no_company():
    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    pdf = generate_nis2_auditor_pdf(
        categories=_CATEGORIES,
        items={},
        score=0,
        user_email="nobody@example.com",
        updated_at=None,
        company_name="",
    )
    assert pdf[:4] == b"%PDF"


def test_generate_auditor_pdf_all_na():
    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    items = {item["id"]: "na" for cat in _CATEGORIES for item in cat["items"]}
    pdf = generate_nis2_auditor_pdf(
        categories=_CATEGORIES,
        items=items,
        score=0,
        user_email="user@test.com",
        updated_at=datetime.now(UTC),
        company_name="Corp SA",
    )
    assert pdf[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Endpoint — GET /nis2/me/pdf/auditor
# ---------------------------------------------------------------------------


def _make_user(uid=1):
    u = MagicMock()
    u.id = uid
    u.email = "owner@example.com"
    return u


@pytest.mark.asyncio
async def test_export_auditor_pdf_no_assessment():
    from app.api.v1.endpoints.nis2 import export_auditor_pdf

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = None  # no assessment
    results[1].scalar_one_or_none.return_value = None  # no brand
    db.execute = AsyncMock(side_effect=iter(results))

    response = await export_auditor_pdf(current_user=_make_user(), db=db)
    assert response.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_export_auditor_pdf_with_assessment():
    import json

    from app.api.v1.endpoints.nis2 import export_auditor_pdf

    assessment = MagicMock()
    assessment.items_json = json.dumps({"mgmt_policy": "compliant"})
    assessment.score = 50
    assessment.updated_at = datetime(2026, 5, 1, tzinfo=UTC)

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = assessment
    results[1].scalar_one_or_none.return_value = None  # no brand
    db.execute = AsyncMock(side_effect=iter(results))

    response = await export_auditor_pdf(current_user=_make_user(), db=db)
    assert response.media_type == "application/pdf"
    assert "pret_a_deposer" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_auditor_pdf_with_brand():
    import json

    from app.api.v1.endpoints.nis2 import export_auditor_pdf

    assessment = MagicMock()
    assessment.items_json = json.dumps({})
    assessment.score = 60
    assessment.updated_at = datetime.now(UTC)

    brand = MagicMock()
    brand.company_name = "Acme Corp"

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = assessment
    results[1].scalar_one_or_none.return_value = brand
    db.execute = AsyncMock(side_effect=iter(results))

    response = await export_auditor_pdf(current_user=_make_user(), db=db)
    assert response.media_type == "application/pdf"
