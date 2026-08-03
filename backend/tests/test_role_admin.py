"""Le droit d'administration porte sur un COMPTE.

`ADMIN_API_KEY` etait un secret partage statique : aucune identite derriere,
aucune revocation possible, aucune 2FA. L'audit du 2026-07-27 l'a releve.

La bascule s'est faite en deux temps — d'abord la cle neutralisee en production
(retiree de l'injection de secrets), puis le code du repli supprime le
2026-08-02. Il ne reste qu'une porte : `users.is_admin`.

Ces tests verrouillent surtout ce qui doit RESTER refuse.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.user import User

BASE = "/api/v1"


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


# ── La seule porte ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_compte_admin_ouvre_le_back_office(client):
    entetes = await _compte(client, "patron@test.com", admin=True)
    r = await client.get(f"{BASE}/admin/stats", headers=entetes)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_un_compte_ordinaire_reste_refuse(client):
    """Le point qui compte : etre connecte ne suffit pas."""
    entetes = await _compte(client, "client@test.com")
    r = await client.get(f"{BASE}/admin/stats", headers=entetes)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_sans_authentification_401(client):
    """Il n'y a plus de porte anonyme : c'est une identite qui manque, pas une
    cle. Le code passe donc de 403 a 401."""
    r = await client.get(f"{BASE}/admin/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_l_ancienne_cle_n_ouvre_plus_rien(client):
    """Non-regression de la bascule : presenter un en-tete `X-Admin-Key`, quelle
    qu'en soit la valeur, ne doit plus avoir le moindre effet."""
    r = await client.get(f"{BASE}/admin/stats", headers={"X-Admin-Key": "n-importe-quoi"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_un_compte_desactive_perd_l_acces(client):
    """Desactiver le compte suffit a revoquer l'administration : c'est
    precisement ce qu'un secret partage ne permettait pas."""
    entetes = await _compte(client, "revoque@test.com", admin=True)
    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "revoque@test.com"))).scalar_one()
        user.is_active = False
        await db.commit()
    r = await client.get(f"{BASE}/admin/stats", headers=entetes)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_le_droit_est_auditable(client):
    """Un droit qu'on ne peut pas lire est mal outille. Son absence de la liste
    avait fait conclure a tort qu'une promotion en production avait echoue."""
    entetes = await _compte(client, "auditeur@test.com", admin=True)
    r = await client.get(f"{BASE}/admin/users", headers=entetes)
    assert r.status_code == 200
    fiche = next(u for u in r.json() if u["email"] == "auditeur@test.com")
    assert fiche["is_admin"] is True
    assert fiche["totp_enabled"] is False
