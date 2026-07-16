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


async def _make_consultant(client: AsyncClient, email: str) -> tuple[dict, int]:
    """Crée un user consultant (is_rssi_consultant=True) et retourne (headers, id)."""
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.user import User

    headers = await register_and_login(client, email)
    uid = await _user_id(headers)
    async with _db.AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == uid))).scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return headers, uid


async def _consultant_client_with_email(consultant_id: int, name: str, email: str) -> int:
    """Crée un RssiClient (avec email) appartenant au consultant, PAS encore lié à un compte."""
    import app.core.database as _db
    from app.models.rssi_client import RssiClient

    async with _db.AsyncSessionLocal() as db:
        rc = RssiClient(consultant_user_id=consultant_id, name=name, email=email, status="active")
        db.add(rc)
        await db.flush()
        cid = rc.id
        await db.commit()
    return cid


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
    _, consultant = await _make_consultant(http_client, "portal_consult@test.com")
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
    _, consultant = await _make_consultant(http_client, "portal_consult2@test.com")
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
    _, consultant = await _make_consultant(http_client, "portal_consult3@test.com")
    hA, _, _ = await _make_client(http_client, "portal_A2@test.com", consultant, "Client A")
    _, _, deliv_b = await _make_client(
        http_client, "portal_B2@test.com", consultant, "Client B", deliverable="Audit B"
    )
    # A tente de télécharger le livrable de B -> 404 (isolation)
    r = await http_client.get(f"{BASE}/portal/deliverables/{deliv_b}/download", headers=hA)
    assert r.status_code == 404


# ── Invitation ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invite_creates_and_links_account(http_client: AsyncClient):
    from unittest.mock import patch

    ch, cid_consult = await _make_consultant(http_client, "inv_consult@test.com")
    client_id = await _consultant_client_with_email(cid_consult, "Acme", "newclient@test.com")

    with patch("app.services.email_service.send_portal_invitation") as mock_email:
        r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/invite", headers=ch)
    assert r.status_code == 200
    assert r.json()["account_created"] is True
    mock_email.assert_called_once()

    # Le client est bien rattaché à un compte + ce compte peut accéder au portail.
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.rssi_client import RssiClient

    async with _db.AsyncSessionLocal() as db:
        rc = (await db.execute(select(RssiClient).where(RssiClient.id == client_id))).scalar_one()
        assert rc.client_user_id is not None


@pytest.mark.asyncio
async def test_invite_without_email_returns_422(http_client: AsyncClient):
    ch, cid_consult = await _make_consultant(http_client, "inv_consult2@test.com")
    # client sans email
    import app.core.database as _db
    from app.models.rssi_client import RssiClient

    async with _db.AsyncSessionLocal() as db:
        rc = RssiClient(consultant_user_id=cid_consult, name="NoEmail", status="active")
        db.add(rc)
        await db.flush()
        client_id = rc.id
        await db.commit()

    r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/invite", headers=ch)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invite_isolation_other_consultant(http_client: AsyncClient):
    _, cid_a = await _make_consultant(http_client, "inv_consultA@test.com")
    chB, _ = await _make_consultant(http_client, "inv_consultB@test.com")
    client_of_a = await _consultant_client_with_email(cid_a, "Client de A", "clienta@test.com")

    # B tente d'inviter le client de A -> 404 (isolation consultant)
    r = await http_client.post(f"{BASE}/rssi/clients/{client_of_a}/invite", headers=chB)
    assert r.status_code == 404


# ── Parcours complet consultant -> client ─────────────────────────────────────


@pytest.mark.asyncio
async def test_full_journey_consultant_to_client(http_client: AsyncClient):
    """De bout en bout : le consultant crée un client, remplit la mission, l'invite ;
    le client définit son mot de passe, se connecte et voit SON espace rempli."""
    from unittest.mock import patch

    ch, _ = await _make_consultant(http_client, "journey_consult@test.com")

    # 1. Créer le client via l'API consultant
    r = await http_client.post(
        f"{BASE}/rssi/clients",
        headers=ch,
        json={"name": "Journey SAS", "email": "journeyclient@test.com", "formula": "premium"},
    )
    assert r.status_code == 201, r.text
    client_id = r.json()["id"]

    # 2. Plan d'action : 2 actions, dont 1 terminée
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/actions",
        headers=ch,
        json={"title": "Activer le MFA", "priority": "high"},
    )
    assert r.status_code == 201, r.text
    action_id = r.json()["id"]
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/actions",
        headers=ch,
        json={"title": "Documenter le PRA", "priority": "critical"},
    )
    assert r.status_code == 201
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client_id}/actions/{action_id}",
        headers=ch,
        json={"status": "done"},
    )
    assert r.status_code == 200, r.text

    # 3. Une visite planifiée
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/visits",
        headers=ch,
        json={"scheduled_date": "2026-09-24", "visit_type": "quarterly", "location": "onsite"},
    )
    assert r.status_code == 201, r.text

    # 4. Un livrable
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/deliverables",
        headers=ch,
        json={"title": "Audit initial", "doc_type": "rapport", "delivered_at": "2026-03-12"},
    )
    assert r.status_code == 201, r.text

    # 5. Inviter le client (on capture le token brut depuis l'e-mail mocké)
    with patch("app.services.email_service.send_portal_invitation") as mock_email:
        r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/invite", headers=ch)
    assert r.status_code == 200, r.text
    invite_url = mock_email.call_args[0][1]
    token = invite_url.split("token=")[1].split("&")[0]

    # 6. Le client définit son mot de passe (vrai flux reset) puis se connecte
    r = await http_client.post(
        f"{BASE}/auth/reset-password", json={"token": token, "password": "ClientPass123!"}
    )
    assert r.status_code == 204, r.text
    r = await http_client.post(
        f"{BASE}/auth/login", json={"email": "journeyclient@test.com", "password": "ClientPass123!"}
    )
    assert r.status_code == 200, r.text
    client_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 7. Le client voit SON espace rempli
    me = (await http_client.get(f"{BASE}/portal/me", headers=client_h)).json()
    assert me["name"] == "Journey SAS"
    assert me["formula"] == "premium"
    assert me["actions_total"] == 2
    assert me["actions_done"] == 1
    assert me["progress_score"] == 50  # 1 done (2 pts) + 1 open (0) / (2*2) = 50 %
    assert me["consultant"]["email"] == "journey_consult@test.com"
    assert me["next_visit"]["visit_type"] == "quarterly"

    actions = (await http_client.get(f"{BASE}/portal/actions", headers=client_h)).json()
    assert len(actions) == 2
    deliverables = (await http_client.get(f"{BASE}/portal/deliverables", headers=client_h)).json()
    assert len(deliverables) == 1 and deliverables[0]["title"] == "Audit initial"
    visits = (await http_client.get(f"{BASE}/portal/visits", headers=client_h)).json()
    assert len(visits) == 1
