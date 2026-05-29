"""
Unit tests for training/sensibilisation module endpoints.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.training import (
    MODULES,
    CompleteModuleIn,
    complete_module,
    get_modules,
    get_progress,
)
from app.models.user import User

# ── helpers ────────────────────────────────────────────────────────────────────


def _user(uid: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uid
    return u


def _db_no_progress():
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        r.scalar_one_or_none.return_value = None
        return r

    db.execute = execute
    return db


def _db_with_progress(module_ids: list[str]):
    db = AsyncMock()

    async def execute(q):
        r = MagicMock()
        items = []
        for mid in module_ids:
            p = MagicMock()
            p.module_id = mid
            p.completed_at = datetime.now(UTC)
            items.append(p)
        r.scalars.return_value.all.return_value = items
        r.scalar_one_or_none.return_value = items[0] if items else None
        return r

    db.execute = execute
    return db


# ── catalogue ─────────────────────────────────────────────────────────────────


def test_exactly_five_modules():
    assert len(MODULES) == 5


def test_module_ids():
    ids = {m["id"] for m in MODULES}
    assert ids == {"phishing", "passwords", "wifi_public", "usb_unknown", "mfa"}


def test_each_module_has_required_fields():
    required = {
        "id",
        "title",
        "icon",
        "color",
        "duration_min",
        "description",
        "scenario",
        "choices",
        "correct",
        "explanation",
    }
    for m in MODULES:
        assert required <= m.keys(), f"Module {m['id']} missing fields"


def test_each_module_has_four_choices():
    for m in MODULES:
        assert len(m["choices"]) == 4, f"Module {m['id']} should have 4 choices"


def test_correct_answer_is_valid_choice():
    for m in MODULES:
        choice_ids = {c["id"] for c in m["choices"]}
        assert m["correct"] in choice_ids, f"Module {m['id']} correct answer not in choices"


# ── get_modules ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_modules_returns_all_five():
    result = await get_modules(_user(), _db_no_progress())
    assert len(result) == 5


@pytest.mark.asyncio
async def test_get_modules_not_completed_by_default():
    result = await get_modules(_user(), _db_no_progress())
    assert all(not m.completed for m in result)


@pytest.mark.asyncio
async def test_get_modules_marks_completed():
    result = await get_modules(_user(), _db_with_progress(["phishing", "mfa"]))
    completed = {m.id for m in result if m.completed}
    assert "phishing" in completed
    assert "mfa" in completed


# ── complete_module ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_module_wrong_answer_returns_false():
    db = _db_no_progress()
    result = await complete_module("phishing", CompleteModuleIn(answer="a"), _user(), db)
    assert result["correct"] is False


@pytest.mark.asyncio
async def test_complete_module_correct_answer_returns_true():
    db = _db_no_progress()
    db.add = MagicMock()
    db.commit = AsyncMock()
    result = await complete_module("phishing", CompleteModuleIn(answer="b"), _user(), db)
    assert result["correct"] is True
    assert "explanation" in result
    assert result["correct_answer"] == "b"


@pytest.mark.asyncio
async def test_complete_module_not_saved_if_wrong():
    db = _db_no_progress()
    db.add = MagicMock()
    db.commit = AsyncMock()
    await complete_module("phishing", CompleteModuleIn(answer="a"), _user(), db)
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_complete_module_unknown_id_raises():
    from fastapi import HTTPException

    db = _db_no_progress()
    with pytest.raises(HTTPException) as exc:
        await complete_module("nonexistent", CompleteModuleIn(answer="a"), _user(), db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_module_not_re_recorded_if_already_done():
    db = _db_with_progress(["phishing"])
    db.add = MagicMock()
    db.commit = AsyncMock()
    await complete_module("phishing", CompleteModuleIn(answer="b"), _user(), db)
    db.add.assert_not_called()


# ── get_progress ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_progress_zero_when_no_completions():
    result = await get_progress(_user(), _db_no_progress())
    assert result.completed == 0
    assert result.total == 5
    assert result.percentage == 0


@pytest.mark.asyncio
async def test_progress_100_percent_when_all_done():
    all_ids = [m["id"] for m in MODULES]
    result = await get_progress(_user(), _db_with_progress(all_ids))
    assert result.completed == 5
    assert result.percentage == 100


@pytest.mark.asyncio
async def test_progress_partial():
    result = await get_progress(_user(), _db_with_progress(["phishing", "mfa"]))
    assert result.completed == 2
    assert result.percentage == 40
