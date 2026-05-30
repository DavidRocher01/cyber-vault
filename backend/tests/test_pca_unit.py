"""
Unit tests for PCA Light module.
"""

from unittest.mock import MagicMock

import pytest

from app.api.v1.endpoints.pca import (
    PcaCompany,
    PcaRequest,
    PcaSystem,
    PcaTeamMember,
    generate_pca,
)
from app.models.user import User
from app.services.pca_pdf import generate_pca_pdf


def _user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = 1
    return u


def _basic_payload() -> PcaRequest:
    return PcaRequest(
        company=PcaCompany(name="Acme", sector="Industrie", contact="Jean Dupont", email="j@a.fr"),
        critical_systems=[
            PcaSystem(
                name="ERP",
                description="Gestion des stocks",
                rto_hours=4,
                rpo_hours=1,
                responsible="Alice",
            ),
        ],
        response_team=[
            PcaTeamMember(name="Bob", role="DSI", phone="06 00 00 00 00", email="bob@a.fr"),
        ],
        communication_plan="Informer les clients sous 24h.",
    )


# ── endpoint ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_pca_returns_streaming_response():
    from fastapi.responses import StreamingResponse

    result = await generate_pca(_basic_payload(), _user())
    assert isinstance(result, StreamingResponse)
    assert result.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_generate_pca_filename_uses_company_name():
    result = await generate_pca(_basic_payload(), _user())
    disposition = result.headers.get("content-disposition", "")
    assert "acme" in disposition.lower()


@pytest.mark.asyncio
async def test_generate_pca_empty_systems():
    payload = PcaRequest(company=PcaCompany(name="Corp"))
    result = await generate_pca(payload, _user())
    from fastapi.responses import StreamingResponse

    assert isinstance(result, StreamingResponse)


# ── PDF generation ────────────────────────────────────────────────────────────


def test_pdf_is_non_empty_bytes():
    data = {
        "company": {"name": "Test", "sector": ""},
        "critical_systems": [],
        "response_team": [],
    }
    pdf = generate_pca_pdf(data)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


def test_pdf_starts_with_pdf_header():
    data = {"company": {"name": "Test"}, "critical_systems": [], "response_team": []}
    pdf = generate_pca_pdf(data)
    assert pdf[:4] == b"%PDF"


def test_pdf_with_systems():
    data = {
        "company": {"name": "SAS Demo", "sector": "Tech"},
        "critical_systems": [
            {
                "name": "CRM",
                "description": "Gestion clients",
                "rto_hours": 2,
                "rpo_hours": 1,
                "responsible": "Alice",
            },
            {
                "name": "ERP",
                "description": "Comptabilité",
                "rto_hours": 8,
                "rpo_hours": 4,
                "responsible": "Bob",
            },
        ],
        "response_team": [],
    }
    pdf = generate_pca_pdf(data)
    assert len(pdf) > 1000


def test_pdf_with_full_team():
    data = {
        "company": {"name": "SAS Demo"},
        "critical_systems": [],
        "response_team": [
            {"name": "Alice", "role": "DSI", "phone": "06 00", "email": "alice@co.fr"},
            {"name": "Bob", "role": "RSSI", "phone": "06 01", "email": "bob@co.fr"},
        ],
        "communication_plan": "Notifier les clients dans les 24h.",
    }
    pdf = generate_pca_pdf(data)
    assert len(pdf) > 1000


# ── schema validation ─────────────────────────────────────────────────────────


def test_pca_system_defaults():
    s = PcaSystem(name="DB")
    assert s.rto_hours == 4
    assert s.rpo_hours == 1


def test_pca_request_empty_lists():
    r = PcaRequest(company=PcaCompany(name="X"))
    assert r.critical_systems == []
    assert r.response_team == []


def test_pca_company_required_name():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PcaCompany()
