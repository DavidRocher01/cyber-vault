"""
Unit tests for app.api.v1.endpoints.notifications — direct function calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.notifications import (
    list_notifications,
    mark_read,
    mark_all_read,
    delete_notification,
)
from app.models.notification import Notification
from app.models.user import User


def _mock_user(user_id: int = 1) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = user_id
    return u


def _mock_notif(notif_id: int = 1, read: bool = False) -> MagicMock:
    n = MagicMock(spec=Notification)
    n.id = notif_id
    n.read = read
    return n


# ─── list_notifications ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notifications_empty():
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalars.return_value.all.return_value = []
        else:
            r.scalar_one.return_value = 0
        return r

    db.execute = execute
    user = _mock_user()

    result = await list_notifications(current_user=user, db=db)
    assert result["items"] == []
    assert result["unread_count"] == 0


@pytest.mark.asyncio
async def test_list_notifications_with_items():
    notif = _mock_notif()
    call_count = {"n": 0}
    db = AsyncMock()

    async def execute(*args, **kwargs):
        r = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            r.scalars.return_value.all.return_value = [notif]
        else:
            r.scalar_one.return_value = 1
        return r

    db.execute = execute
    user = _mock_user()

    result = await list_notifications(current_user=user, db=db)
    assert len(result["items"]) == 1
    assert result["unread_count"] == 1


# ─── mark_read ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_read_not_found_raises_404():
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await mark_read(notification_id=999, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_read_success():
    notif = _mock_notif(notif_id=1, read=False)
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = notif
    db.execute = AsyncMock(return_value=r)
    db.flush = AsyncMock()
    user = _mock_user()

    result = await mark_read(notification_id=1, current_user=user, db=db)
    assert notif.read is True
    assert result == notif


# ─── mark_all_read ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_all_read_no_unread():
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=r)
    db.flush = AsyncMock()
    user = _mock_user()

    await mark_all_read(current_user=user, db=db)
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_mark_all_read_marks_notifications():
    n1 = _mock_notif(1, read=False)
    n2 = _mock_notif(2, read=False)
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = [n1, n2]
    db.execute = AsyncMock(return_value=r)
    db.flush = AsyncMock()
    user = _mock_user()

    await mark_all_read(current_user=user, db=db)
    assert n1.read is True
    assert n2.read is True


# ─── delete_notification ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_notification_not_found_raises_404():
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)
    user = _mock_user()

    with pytest.raises(HTTPException) as exc:
        await delete_notification(notification_id=999, current_user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_notification_success():
    notif = _mock_notif(notif_id=1)
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = notif
    db.execute = AsyncMock(return_value=r)
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    user = _mock_user()

    await delete_notification(notification_id=1, current_user=user, db=db)
    db.delete.assert_called_once_with(notif)
    db.flush.assert_called_once()
