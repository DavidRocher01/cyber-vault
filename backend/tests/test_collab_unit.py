"""Unit tests — Feature #16: Mode audit collaboratif."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(uid=1, email="owner@example.com"):
    u = MagicMock()
    u.id = uid
    u.email = email
    return u


def _make_site(site_id=10, user_id=1, url="https://acme.com", name="Acme"):
    s = MagicMock()
    s.id = site_id
    s.user_id = user_id
    s.url = url
    s.name = name
    return s


def _make_collab(collab_id=1, site_id=10, email="guest@example.com", role="viewer", status="pending", token="tok"):
    c = MagicMock()
    c.id = collab_id
    c.site_id = site_id
    c.owner_user_id = 1
    c.email = email
    c.role = role
    c.status = status
    c.invite_token = token
    c.invited_at = datetime.now(timezone.utc)
    c.accepted_at = None
    return c


def _make_db(site=None, collab=None, collabs=None):
    db = AsyncMock()

    def side_effect_execute(stmt):
        result = MagicMock()
        if collabs is not None:
            result.scalars.return_value.all.return_value = collabs
            result.scalar_one_or_none.return_value = collabs[0] if collabs else None
        elif collab is not None:
            result.scalar_one_or_none.return_value = collab
        elif site is not None:
            result.scalar_one_or_none.return_value = site
        else:
            result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=side_effect_execute)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# list_collaborators
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_collaborators_owner_only():
    from app.api.v1.endpoints.collab import list_collaborators
    collabs = [_make_collab(), _make_collab(collab_id=2, email="b@x.com")]
    site = _make_site()

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = site
    results[1].scalars.return_value.all.return_value = collabs
    db.execute = AsyncMock(side_effect=iter(results))

    result = await list_collaborators(site_id=10, current_user=_make_user(), db=db)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_collaborators_wrong_owner_raises_404():
    from app.api.v1.endpoints.collab import list_collaborators
    from fastapi import HTTPException

    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)

    with pytest.raises(HTTPException) as exc:
        await list_collaborators(site_id=10, current_user=_make_user(), db=db)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# invite_collaborator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invite_creates_collab():
    from app.api.v1.endpoints.collab import invite_collaborator, InviteIn
    from unittest.mock import patch

    site = _make_site()
    collab = _make_collab()

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = site
    results[1].scalar_one_or_none.return_value = None  # no existing
    db.execute = AsyncMock(side_effect=iter(results))
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, 'id', 1) or setattr(obj, 'status', 'pending'))

    bg = MagicMock()
    bg.add_task = MagicMock()

    payload = InviteIn(email="guest@example.com", role="auditor")
    await invite_collaborator(site_id=10, payload=payload, background_tasks=bg,
                              current_user=_make_user(), db=db)
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_invite_duplicate_raises_409():
    from app.api.v1.endpoints.collab import invite_collaborator, InviteIn
    from fastapi import HTTPException

    site = _make_site()
    existing = _make_collab()

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = site
    results[1].scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(side_effect=iter(results))

    bg = MagicMock()
    payload = InviteIn(email="guest@example.com", role="viewer")
    with pytest.raises(HTTPException) as exc:
        await invite_collaborator(site_id=10, payload=payload, background_tasks=bg,
                                  current_user=_make_user(), db=db)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# update_collaborator_role
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_role():
    from app.api.v1.endpoints.collab import update_collaborator_role, RoleUpdateIn

    site = _make_site()
    collab = _make_collab(role="viewer")

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = site
    results[1].scalar_one_or_none.return_value = collab
    db.execute = AsyncMock(side_effect=iter(results))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    payload = RoleUpdateIn(role="manager")
    await update_collaborator_role(site_id=10, collab_id=1, payload=payload,
                                   current_user=_make_user(), db=db)
    assert collab.role == "manager"


# ---------------------------------------------------------------------------
# remove_collaborator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_remove_collaborator():
    from app.api.v1.endpoints.collab import remove_collaborator

    site = _make_site()
    collab = _make_collab()

    db = AsyncMock()
    results = [MagicMock(), MagicMock()]
    results[0].scalar_one_or_none.return_value = site
    results[1].scalar_one_or_none.return_value = collab
    db.execute = AsyncMock(side_effect=iter(results))
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    await remove_collaborator(site_id=10, collab_id=1, current_user=_make_user(), db=db)
    db.delete.assert_called_once_with(collab)
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# accept_invite
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_accept_invite_pending():
    from app.api.v1.endpoints.collab import accept_invite

    collab = _make_collab(status="pending")
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = collab
    db.execute = AsyncMock(return_value=r)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    await accept_invite(token="tok", db=db)
    assert collab.status == "accepted"
    assert collab.accepted_at is not None


@pytest.mark.asyncio
async def test_accept_invite_already_accepted():
    from app.api.v1.endpoints.collab import accept_invite

    collab = _make_collab(status="accepted")
    collab.accepted_at = datetime.now(timezone.utc)
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = collab
    db.execute = AsyncMock(return_value=r)

    result = await accept_invite(token="tok", db=db)
    assert result is collab
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_accept_invite_invalid_token():
    from app.api.v1.endpoints.collab import accept_invite
    from fastapi import HTTPException

    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)

    with pytest.raises(HTTPException) as exc:
        await accept_invite(token="bad_token", db=db)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# my_invitations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_my_invitations():
    from app.api.v1.endpoints.collab import my_invitations

    collabs = [_make_collab(status="accepted", email="me@x.com")]
    db = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = collabs
    db.execute = AsyncMock(return_value=r)

    result = await my_invitations(current_user=_make_user(email="me@x.com"), db=db)
    assert len(result) == 1
