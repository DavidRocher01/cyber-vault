"""Le back-office doit annoncer le plan EFFECTIF — corrige le 2026-08-07.

LE DEFAUT, TROUVE EN PRODUCTION. La liste `/admin/users` joignait les abonnements
sur `Subscription.status == "active"` ET RIEN D'AUTRE, alors que
`get_active_plan` — qui commande tous les acces — exige EN PLUS que la periode ne
soit pas echue au-dela de la marge de grace.

Un abonnement expire s'affichait donc « Business / Actif » au back-office pendant
que la plateforme traitait deja le compte en Gratuit. Les deux disaient vrai
selon leur propre regle, et c'est ce qui rendait le defaut couteux : il faisait
conclure a tort sur les droits d'un client. Vu sur un compte reel, dont le
tableau de bord annoncait « Plan Gratuit » avec un badge Business en face.

CE QUE CES TESTS FIXENT :
1. la liste rend le plan EFFECTIF, pas celui de la ligne d'abonnement ;
2. elle rend aussi de quoi COMPRENDRE l'ecart — sans quoi l'administrateur
   verrait « Gratuit » sur un compte qu'il a lui-meme passe en Business, sans
   aucune explication ;
3. les deux lectures s'accordent : ce que la liste annonce est ce que
   `get_active_plan` applique.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _un_admin(c: AsyncClient, email: str) -> dict:
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.user import User

    await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    entetes = {"Authorization": f"Bearer {r.json()['access_token']}"}

    async with _db.AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.email == email))).scalar_one()
        u.is_admin = True
        await db.commit()
    return entetes


async def _plan(nom: str, tier: int, export: bool):
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.plan import Plan

    async with _db.AsyncSessionLocal() as db:
        existant = (await db.execute(select(Plan).where(Plan.name == nom))).scalar_one_or_none()
        if existant:
            return existant.id
        p = Plan(
            name=nom,
            display_name=nom.capitalize(),
            price_eur=0,
            max_sites=-1,
            scan_interval_days=1,
            tier_level=tier,
            stripe_price_id="",
            is_active=True,
            allow_conformity_export=export,
        )
        db.add(p)
        await db.commit()
        return p.id


async def _abonner(user_id: int, plan_id: int, *, fin: datetime | None):
    """Pose un abonnement au statut `active`, avec l'echeance voulue."""
    import app.core.database as _db
    from app.models.subscription import Subscription

    async with _db.AsyncSessionLocal() as db:
        db.add(
            Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status="active",
                current_period_end=fin,
            )
        )
        await db.commit()


async def _id_de(c: AsyncClient, entetes: dict, email: str) -> int:
    r = await c.get(f"{BASE}/admin/users", headers=entetes)
    return next(u["id"] for u in r.json() if u["email"] == email)


async def _ligne(c: AsyncClient, entetes: dict, email: str) -> dict:
    r = await c.get(f"{BASE}/admin/users", headers=entetes)
    return next(u for u in r.json() if u["email"] == email)


# ── LE cas qui a mordu en production ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_abonnement_expire_n_est_plus_annonce_comme_payant():
    """LE test de ce correctif.

    Statut `active` en base, mais periode echue depuis 3 mois : la plateforme
    traite le compte en Gratuit. Le back-office doit dire la meme chose.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _un_admin(c, "adm_expire@test.com")
        await _plan("free", 1, False)
        biz = await _plan("business", 4, True)

        await c.post(
            f"{BASE}/auth/register",
            json={"email": "expire@test.com", "password": "StrongPass123!"},
        )
        uid = await _id_de(c, h, "expire@test.com")
        await _abonner(uid, biz, fin=datetime.now(UTC) - timedelta(days=90))

        ligne = await _ligne(c, h, "expire@test.com")

    assert ligne["plan_name"] == "free", "le back-office annonce encore le plan payant"
    assert ligne["plan"] == "Free"


@pytest.mark.asyncio
async def test_l_ecart_est_explique_et_pas_seulement_corrige():
    """Sans le « pourquoi », l'administrateur verrait « Gratuit » sur un compte
    qu'il a lui-meme passe en Business, sans aucun moyen de comprendre."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _un_admin(c, "adm_pourquoi@test.com")
        await _plan("free", 1, False)
        biz = await _plan("business", 4, True)
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "pourquoi@test.com", "password": "StrongPass123!"},
        )
        uid = await _id_de(c, h, "pourquoi@test.com")
        echeance = datetime.now(UTC) - timedelta(days=90)
        await _abonner(uid, biz, fin=echeance)

        ligne = await _ligne(c, h, "pourquoi@test.com")

    assert ligne["subscription_perimee"] is True
    assert ligne["subscription_period_end"] is not None, "l'echeance doit etre visible"
    assert ligne["subscription_status"] == "active", "le statut brut reste consultable"


# ── Ce qui ne doit PAS changer ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_abonnement_valide_reste_annonce_tel_quel():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _un_admin(c, "adm_valide@test.com")
        await _plan("free", 1, False)
        biz = await _plan("business", 4, True)
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "valide@test.com", "password": "StrongPass123!"},
        )
        uid = await _id_de(c, h, "valide@test.com")
        await _abonner(uid, biz, fin=datetime.now(UTC) + timedelta(days=365))

        ligne = await _ligne(c, h, "valide@test.com")

    assert ligne["plan_name"] == "business"
    assert ligne["subscription_perimee"] is False


@pytest.mark.asyncio
async def test_une_echeance_nulle_vaut_sans_expiration():
    """Plans manuels, overrides admin : `current_period_end` a NULL ne perime pas."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _un_admin(c, "adm_nulle@test.com")
        await _plan("free", 1, False)
        biz = await _plan("business", 4, True)
        await c.post(
            f"{BASE}/auth/register", json={"email": "nulle@test.com", "password": "StrongPass123!"}
        )
        uid = await _id_de(c, h, "nulle@test.com")
        await _abonner(uid, biz, fin=None)

        ligne = await _ligne(c, h, "nulle@test.com")

    assert ligne["plan_name"] == "business"
    assert ligne["subscription_perimee"] is False


@pytest.mark.asyncio
async def test_la_marge_de_grace_est_respectee():
    """Echu d'un jour : encore dans la marge, donc encore valide."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _un_admin(c, "adm_grace@test.com")
        await _plan("free", 1, False)
        biz = await _plan("business", 4, True)
        await c.post(
            f"{BASE}/auth/register", json={"email": "grace@test.com", "password": "StrongPass123!"}
        )
        uid = await _id_de(c, h, "grace@test.com")
        await _abonner(uid, biz, fin=datetime.now(UTC) - timedelta(days=1))

        ligne = await _ligne(c, h, "grace@test.com")

    assert ligne["plan_name"] == "business", "la marge de grace n'est pas appliquee"


@pytest.mark.asyncio
async def test_un_compte_sans_abonnement_reste_au_gratuit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _un_admin(c, "adm_sans@test.com")
        await _plan("free", 1, False)
        await c.post(
            f"{BASE}/auth/register", json={"email": "sans@test.com", "password": "StrongPass123!"}
        )

        ligne = await _ligne(c, h, "sans@test.com")

    assert ligne["plan_name"] == "free"
    assert ligne["subscription_perimee"] is False, "sans abonnement, il n'y a rien de perime"


# ── Les deux lectures doivent s'accorder ─────────────────────────────────────


@pytest.mark.asyncio
async def test_le_back_office_dit_ce_que_la_plateforme_applique(db_session):
    """LA GARANTIE DE FOND : une seule regle, deux lectures qui concordent.

    C'est ce que le defaut du 2026-08-07 violait — chacune avait la sienne.
    """
    from app.services.subscription_service import get_active_plan

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _un_admin(c, "adm_accord@test.com")
        await _plan("free", 1, False)
        biz = await _plan("business", 4, True)
        await c.post(
            f"{BASE}/auth/register", json={"email": "accord@test.com", "password": "StrongPass123!"}
        )
        uid = await _id_de(c, h, "accord@test.com")
        await _abonner(uid, biz, fin=datetime.now(UTC) - timedelta(days=90))

        ligne = await _ligne(c, h, "accord@test.com")

    applique = await get_active_plan(db_session, uid)
    assert applique is not None
    assert ligne["plan_name"] == applique.name, (
        f"le back-office annonce {ligne['plan_name']}, la plateforme applique {applique.name}"
    )
