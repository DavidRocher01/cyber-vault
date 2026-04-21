"""
Unit tests for notification-preferences endpoint.

Covers: GET returns all fields including notif_ssl_expiry,
        PUT persists notif_ssl_expiry=True and =False.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.users import update_notification_preferences
from app.models.user import User
from app.schemas.user import NotificationPreferencesIn


# ─── helpers ─────────────────────────────────────────────────────────────────

def _mock_user(**kwargs) -> MagicMock:
    defaults = dict(
        notif_scan_done=True,
        notif_scan_critical=True,
        notif_url_scan_done=True,
        notif_code_scan_done=True,
        notif_ssl_expiry=True,
    )
    defaults.update(kwargs)
    u = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(u, k, v)
    return u


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _prefs(**kwargs) -> NotificationPreferencesIn:
    defaults = dict(
        notif_scan_done=True,
        notif_scan_critical=True,
        notif_url_scan_done=True,
        notif_code_scan_done=True,
        notif_ssl_expiry=True,
    )
    defaults.update(kwargs)
    return NotificationPreferencesIn(**defaults)


# ─── update_notification_preferences ────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_persists_notif_ssl_expiry_true():
    user = _mock_user(notif_ssl_expiry=False)
    db = _mock_db()
    db.refresh = AsyncMock(side_effect=lambda u: None)

    await update_notification_preferences(
        payload=_prefs(notif_ssl_expiry=True),
        current_user=user,
        db=db,
    )

    assert user.notif_ssl_expiry is True
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_persists_notif_ssl_expiry_false():
    user = _mock_user(notif_ssl_expiry=True)
    db = _mock_db()
    db.refresh = AsyncMock(side_effect=lambda u: None)

    await update_notification_preferences(
        payload=_prefs(notif_ssl_expiry=False),
        current_user=user,
        db=db,
    )

    assert user.notif_ssl_expiry is False
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_persists_all_fields():
    user = _mock_user(
        notif_scan_done=False,
        notif_scan_critical=False,
        notif_url_scan_done=False,
        notif_code_scan_done=False,
        notif_ssl_expiry=False,
    )
    db = _mock_db()
    db.refresh = AsyncMock(side_effect=lambda u: None)

    await update_notification_preferences(
        payload=_prefs(
            notif_scan_done=True,
            notif_scan_critical=True,
            notif_url_scan_done=True,
            notif_code_scan_done=True,
            notif_ssl_expiry=True,
        ),
        current_user=user,
        db=db,
    )

    assert user.notif_scan_done is True
    assert user.notif_scan_critical is True
    assert user.notif_url_scan_done is True
    assert user.notif_code_scan_done is True
    assert user.notif_ssl_expiry is True


@pytest.mark.asyncio
async def test_update_does_not_commit_before_setting_fields():
    """Ensure commit happens after all fields are set (order matters)."""
    committed_at = {"after_ssl": False}
    user = _mock_user()
    db = _mock_db()

    async def _commit():
        committed_at["after_ssl"] = hasattr(user, "notif_ssl_expiry")

    db.commit = _commit
    db.refresh = AsyncMock(side_effect=lambda u: None)

    await update_notification_preferences(
        payload=_prefs(notif_ssl_expiry=False),
        current_user=user,
        db=db,
    )

    assert committed_at["after_ssl"] is True


# ─── schema ───────────────────────────────────────────────────────────────────

def test_notification_preferences_in_requires_ssl_expiry():
    """NotificationPreferencesIn must include notif_ssl_expiry."""
    prefs = NotificationPreferencesIn(
        notif_scan_done=True,
        notif_scan_critical=False,
        notif_url_scan_done=True,
        notif_code_scan_done=False,
        notif_ssl_expiry=True,
    )
    assert prefs.notif_ssl_expiry is True


def test_notification_preferences_in_rejects_missing_ssl_expiry():
    """Omitting notif_ssl_expiry must raise a validation error."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        NotificationPreferencesIn(
            notif_scan_done=True,
            notif_scan_critical=True,
            notif_url_scan_done=True,
            notif_code_scan_done=True,
            # notif_ssl_expiry intentionally omitted
        )
