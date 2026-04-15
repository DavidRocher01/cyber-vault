"""
Direct unit tests for nis2 endpoint bodies not covered by integration tests.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.nis2 import get_assessment
from app.models.user import User


def _mock_user(user_id: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    return u


@pytest.mark.asyncio
async def test_get_assessment_no_existing_record_returns_defaults():
    """When no assessment exists, returns empty items, score=0."""
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    result = await get_assessment(current_user=user, db=db)
    assert result["score"] == 0
    assert result["items"] == {}
    assert result["updated_at"] is None
    assert "categories" in result


@pytest.mark.asyncio
async def test_get_assessment_with_existing_record():
    """When assessment exists, returns its data."""
    from datetime import datetime, timezone

    assessment = MagicMock()
    assessment.items_json = json.dumps({"rssi": "compliant"})
    assessment.score = 42
    assessment.updated_at = datetime(2024, 6, 1, tzinfo=timezone.utc)

    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = assessment
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    result = await get_assessment(current_user=user, db=db)
    assert result["score"] == 42
    assert result["items"] == {"rssi": "compliant"}
    assert result["updated_at"] is not None
