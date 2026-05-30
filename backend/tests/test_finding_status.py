"""
Tests for finding-status endpoints: GET and PUT /scans/site/{site_id}/finding-status.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.scans import (
    list_finding_statuses,
    upsert_finding_status,
)
from app.models.finding_status import FindingStatus
from app.models.site import Site
from app.models.user import User

# ── helpers ────────────────────────────────────────────────────────────────────


def _user(uid: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uid
    return u


def _site(sid: int = 10) -> MagicMock:
    s = MagicMock(spec=Site)
    s.id = sid
    return s


def _fs(site_id=10, module_key="ssl", status="todo", note=None) -> MagicMock:
    fs = MagicMock(spec=FindingStatus)
    fs.site_id = site_id
    fs.module_key = module_key
    fs.status = status
    fs.note = note
    fs.updated_at = datetime(2024, 6, 1, tzinfo=UTC)
    return fs


def _db_returning(*rows_per_call):
    """AsyncMock db whose execute() returns successive results."""
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        val = rows_per_call[n] if n < len(rows_per_call) else None
        r.scalar_one_or_none.return_value = val
        r.scalars.return_value.all.return_value = (
            val if isinstance(val, list) else ([] if val is None else [val])
        )
        call_count["n"] += 1
        return r

    db.execute = execute
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


# ── list_finding_statuses ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_empty_when_no_statuses():
    site = _site()
    db = _db_returning(site, [])
    result = await list_finding_statuses(site_id=10, current_user=_user(), db=db)
    assert result == []


@pytest.mark.asyncio
async def test_list_returns_mapped_rows():
    site = _site()
    fs1 = _fs(module_key="ssl", status="resolved")
    fs2 = _fs(module_key="ports", status="in_progress", note="WIP")
    db = _db_returning(site, [fs1, fs2])
    result = await list_finding_statuses(site_id=10, current_user=_user(), db=db)
    assert len(result) == 2
    assert result[0]["module_key"] == "ssl"
    assert result[0]["status"] == "resolved"
    assert result[1]["module_key"] == "ports"
    assert result[1]["note"] == "WIP"


@pytest.mark.asyncio
async def test_list_raises_404_for_unowned_site():
    db = _db_returning(None)
    with pytest.raises(HTTPException) as exc:
        await list_finding_statuses(site_id=99, current_user=_user(), db=db)
    assert exc.value.status_code == 404


# ── upsert_finding_status ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_creates_new_row_when_none_exists():
    site = _site()
    db = _db_returning(site, None)  # site found, no existing FindingStatus row
    result = await upsert_finding_status(
        site_id=10,
        module_key="ssl",
        status="resolved",
        note="Fixed cert",
        current_user=_user(),
        db=db,
    )
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.module_key == "ssl"
    assert added.status == "resolved"
    assert added.note == "Fixed cert"


@pytest.mark.asyncio
async def test_upsert_updates_existing_row():
    site = _site()
    existing = _fs(module_key="ports", status="todo")
    db = _db_returning(site, existing)
    result = await upsert_finding_status(
        site_id=10,
        module_key="ports",
        status="in_progress",
        note="In progress",
        current_user=_user(),
        db=db,
    )
    assert existing.status == "in_progress"
    assert existing.note == "In progress"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_returns_correct_fields():
    site = _site()
    existing = _fs(module_key="headers", status="todo")
    db = _db_returning(site, existing)
    result = await upsert_finding_status(
        site_id=10,
        module_key="headers",
        status="accepted_risk",
        note=None,
        current_user=_user(),
        db=db,
    )
    assert result["module_key"] == "headers"
    assert result["status"] == "accepted_risk"
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_upsert_raises_422_for_invalid_status():
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await upsert_finding_status(
            site_id=10,
            module_key="ssl",
            status="invalid_value",
            note=None,
            current_user=_user(),
            db=db,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_upsert_raises_404_for_unowned_site():
    db = _db_returning(None)
    with pytest.raises(HTTPException) as exc:
        await upsert_finding_status(
            site_id=99,
            module_key="ssl",
            status="resolved",
            note=None,
            current_user=_user(),
            db=db,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["todo", "in_progress", "resolved", "accepted_risk"])
async def test_upsert_accepts_all_valid_statuses(status):
    site = _site()
    db = _db_returning(site, None)
    result = await upsert_finding_status(
        site_id=10,
        module_key="ssl",
        status=status,
        note=None,
        current_user=_user(),
        db=db,
    )
    added = db.add.call_args[0][0]
    assert added.status == status


@pytest.mark.asyncio
async def test_upsert_null_note_is_stored():
    site = _site()
    db = _db_returning(site, None)
    await upsert_finding_status(
        site_id=10,
        module_key="cors",
        status="todo",
        note=None,
        current_user=_user(),
        db=db,
    )
    added = db.add.call_args[0][0]
    assert added.note is None


@pytest.mark.asyncio
async def test_upsert_updated_at_is_set():
    site = _site()
    db = _db_returning(site, None)
    await upsert_finding_status(
        site_id=10,
        module_key="ssl",
        status="resolved",
        note=None,
        current_user=_user(),
        db=db,
    )
    added = db.add.call_args[0][0]
    assert added.updated_at is not None
