"""Le role admin porte sur un COMPTE, plus sur un secret partage.

`ADMIN_API_KEY` etait un secret statique : aucune identite derriere, aucune
revocation possible, aucune 2FA. L'audit du 2026-07-27 l'a releve. `users.is_admin`
attache le droit a un compte, donc a quelqu'un.

La cle reste acceptee LE TEMPS DE LA BASCULE, sinon couper avant d'avoir cree un
compte admin rendrait le back-office de production inaccessible. Ces tests
verrouillent les deux voies, et surtout ce qui doit rester refuse.
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.user import User

BASE = "/api/v1"
DEPS = "app.core.deps"
CLE = "cle-admin-de-test"


async def _session():
    """Relit `AsyncSessionLocal` a CHAQUE appel : la fixture `setup_db` le
    remplace par le conteneur PostgreSQL de test. Un import au niveau module
    figerait le repli SQLite et ferait echouer tout acces base."""
    from app.core.database import AsyncSessionLocal

    return AsyncSessionLocal()


async def _compte(client: AsyncClient, email: str, admin: bool = False) -> dict:
    """Cree un compte, le promeut si demande, et rend ses en-tetes d'auth."""
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    if admin:
        async with await _session() as db:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one()
            user.is_admin = True
            await db.commit()
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Le modele ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_compte_neuf_n_est_jamais_admin(client):
    """Le droit ne s'attrape pas en s'inscrivant."""
    await client.post(
        f"{BASE}/auth/register", json={"email": "quidam@test.com", "password": "StrongPass123!"}
    )
    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "quidam@test.com"))).scalar_one()
    assert user.is_admin is False


@pytest.mark.asyncio
async def test_admin_et_consultant_sont_deux_roles_distincts(client):
    """`is_rssi_consultant` est un role CLIENT — un consultant gere ses propres
    clients, il n'administre pas la plateforme. Les confondre ouvrirait le
    back-office a tous les consultants."""
    await _compte(client, "consultant@test.com")
    async with await _session() as db:
        user = (
            await db.execute(select(User).where(User.email == "consultant@test.com"))
        ).scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
        await db.refresh(user)
    assert user.is_rssi_consultant is True
    assert user.is_admin is False


# ── require_admin : les deux voies, pendant la bascule ───────────────────────


@pytest.mark.asyncio
async def test_un_compte_admin_ouvre_le_back_office(client):
    entetes = await _compte(client, "patron@test.com", admin=True)
    r = await client.get(f"{BASE}/admin/stats", headers=entetes)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_la_cle_historique_fonctionne_encore(client):
    """Voie de repli : sans elle, la bascule couperait l'acces en production."""
    with patch(f"{DEPS}.settings") as reglages:
        reglages.ADMIN_API_KEY = CLE
        r = await client.get(f"{BASE}/admin/stats", headers={"X-Admin-Key": CLE})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_un_compte_ordinaire_reste_refuse(client):
    """Le point qui compte : etre connecte ne suffit pas."""
    entetes = await _compte(client, "client@test.com")
    r = await client.get(f"{BASE}/admin/stats", headers=entetes)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_sans_rien_c_est_refuse(client):
    r = await client.get(f"{BASE}/admin/stats")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_mauvaise_cle_refusee(client):
    with patch(f"{DEPS}.settings") as reglages:
        reglages.ADMIN_API_KEY = CLE
        r = await client.get(f"{BASE}/admin/stats", headers={"X-Admin-Key": "pas-la-bonne"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cle_non_configuree_ne_laisse_pas_passer_une_cle_vide(client):
    """Si `ADMIN_API_KEY` est vide, l'en-tete vide ne doit pas etre accepte —
    sinon une prod mal configuree ouvrirait son back-office a tout le monde."""
    with patch(f"{DEPS}.settings") as reglages:
        reglages.ADMIN_API_KEY = ""
        r = await client.get(f"{BASE}/admin/stats", headers={"X-Admin-Key": ""})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_un_compte_desactive_perd_l_acces(client):
    """Desactiver le compte doit suffire a revoquer l'administration : c'est
    precisement ce qu'un secret partage ne permettait pas."""
    entetes = await _compte(client, "revoque@test.com", admin=True)
    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "revoque@test.com"))).scalar_one()
        user.is_active = False
        await db.commit()
    r = await client.get(f"{BASE}/admin/stats", headers=entetes)
    assert r.status_code == 403


# ── get_admin_user : la voie stricte, pour les nouvelles surfaces ────────────


@pytest.mark.asyncio
async def test_la_voie_stricte_refuse_la_cle_partagee(client):
    """`get_admin_user` n'accepte QUE des comptes. Les surfaces construites
    maintenant — a commencer par l'onglet Acquisition — ne doivent pas heriter
    du secret qu'on est en train de retirer."""
    from fastapi import Depends

    from app.core.deps import get_admin_user

    @app.get("/_test_surface_stricte")
    async def _surface(admin: User = Depends(get_admin_user)):
        return {"email": admin.email}

    try:
        with patch(f"{DEPS}.settings") as reglages:
            reglages.ADMIN_API_KEY = CLE
            r = await client.get("/_test_surface_stricte", headers={"X-Admin-Key": CLE})
        assert r.status_code == 401, "la cle partagee ne doit pas ouvrir une surface stricte"

        entetes = await _compte(client, "stricte@test.com", admin=True)
        r = await client.get("/_test_surface_stricte", headers=entetes)
        assert r.status_code == 200
        assert r.json()["email"] == "stricte@test.com"

        ordinaire = await _compte(client, "ordinaire@test.com")
        r = await client.get("/_test_surface_stricte", headers=ordinaire)
        assert r.status_code == 403
    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != "/_test_surface_stricte"
        ]
