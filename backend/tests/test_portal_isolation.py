"""Portail client RSSI — isolation stricte.

Chaque endpoint /portal est scopé au RssiClient rattaché au compte connecté
(client_user_id). On vérifie : accès refusé sans client lié (403), lecture de SA mission,
et surtout qu'un client ne voit JAMAIS les données d'un autre.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login

BASE = "/api/v1"


async def _user_id(headers: dict) -> int:
    from app.core.security import decode_access_token

    return int(decode_access_token(headers["Authorization"].removeprefix("Bearer ").strip()))


async def _make_consultant(client: AsyncClient, email: str) -> int:
    """Crée un user consultant (is_rssi_consultant=True) et retourne son id."""
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.user import User

    headers = await register_and_login(client, email)
    uid = await _user_id(headers)
    async with _db.AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == uid))).scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return uid


async def _make_client(
    client: AsyncClient,
    email: str,
    consultant_id: int,
    name: str,
    actions: list[tuple[str, str]] | None = None,
    deliverable: str | None = None,
) -> tuple[dict, int, int | None]:
    """Crée un compte client lié à un RssiClient (+ actions/livrable). Retourne
    (headers, rssi_client_id, deliverable_id)."""
    import app.core.database as _db
    from app.models.rssi_action import RssiAction
    from app.models.rssi_client import RssiClient
    from app.models.rssi_deliverable import RssiDeliverable

    headers = await register_and_login(client, email)
    uid = await _user_id(headers)
    deliverable_id = None
    async with _db.AsyncSessionLocal() as db:
        rc = RssiClient(
            consultant_user_id=consultant_id,
            client_user_id=uid,
            name=name,
            status="active",
        )
        db.add(rc)
        await db.flush()
        for title, st in actions or []:
            db.add(RssiAction(client_id=rc.id, title=title, priority="medium", status=st))
        if deliverable:
            from datetime import UTC, datetime

            d = RssiDeliverable(
                client_id=rc.id,
                title=deliverable,
                doc_type="rapport",
                file_url="rssi-deliverables/1/1/x.pdf",
                delivered_at=datetime.now(UTC).date(),
            )
            db.add(d)
            await db.flush()
            deliverable_id = d.id
        await db.commit()
        return headers, rc.id, deliverable_id


@pytest.mark.asyncio
async def test_portal_denied_without_linked_client(http_client: AsyncClient):
    # Un utilisateur normal (aucun RssiClient lié) est refusé.
    headers = await register_and_login(http_client, "portal_nolink@test.com")
    r = await http_client.get(f"{BASE}/portal/me", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_portal_me_returns_own_mission(http_client: AsyncClient):
    consultant = await _make_consultant(http_client, "portal_consult@test.com")
    headers, _, _ = await _make_client(
        http_client,
        "portal_clientA@test.com",
        consultant,
        "Acme SAS",
        actions=[("A1", "done"), ("A2", "open")],  # 2/(2*2) = 50 %
    )
    r = await http_client.get(f"{BASE}/portal/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Acme SAS"
    assert data["progress_score"] == 50
    assert data["actions_total"] == 2
    assert data["actions_done"] == 1


@pytest.mark.asyncio
async def test_portal_actions_only_own(http_client: AsyncClient):
    consultant = await _make_consultant(http_client, "portal_consult2@test.com")
    hA, _, _ = await _make_client(
        http_client, "portal_A@test.com", consultant, "Client A", actions=[("SECRET_A", "open")]
    )
    await _make_client(
        http_client, "portal_B@test.com", consultant, "Client B", actions=[("SECRET_B", "open")]
    )
    r = await http_client.get(f"{BASE}/portal/actions", headers=hA)
    assert r.status_code == 200
    titles = {a["title"] for a in r.json()}
    assert titles == {"SECRET_A"}  # jamais SECRET_B


@pytest.mark.asyncio
async def test_portal_cannot_download_other_client_deliverable(http_client: AsyncClient):
    consultant = await _make_consultant(http_client, "portal_consult3@test.com")
    hA, _, _ = await _make_client(http_client, "portal_A2@test.com", consultant, "Client A")
    _, _, deliv_b = await _make_client(
        http_client, "portal_B2@test.com", consultant, "Client B", deliverable="Audit B"
    )
    # A tente de télécharger le livrable de B -> 404 (isolation)
    r = await http_client.get(f"{BASE}/portal/deliverables/{deliv_b}/download", headers=hA)
    assert r.status_code == 404
