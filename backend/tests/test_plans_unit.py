"""Unit tests — direct calls to plans and nis2 endpoints to cover function bodies."""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.api.v1.endpoints.plans import list_plans


@pytest.mark.asyncio
async def test_list_plans_returns_all_active():
    plan = MagicMock()
    plan.id = 1
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = [plan]
    db.execute = AsyncMock(return_value=r)

    result = await list_plans(db=db)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_plans_empty():
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=r)

    result = await list_plans(db=db)
    assert result == []
