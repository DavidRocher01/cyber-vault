"""Dossier NIS2 d'un client suivi, cote consultant — etape 5d.

CE QUE CES TESTS PROTEGENT EN PRIORITE : l'isolation. Un consultant detient
desormais plusieurs dossiers — le sien et un par client — et ils partagent la
meme table. Une requete qui oublierait le sujet ferait fuiter le dossier d'un
client vers un autre, ou vers l'auto-evaluation personnelle du consultant.

Cf. `docs/DEPOT_DOCUMENTS.md`, cadrage de l'etape 5.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import create_plan_and_subscription

BASE = "/api/v1"
PDF = b"%PDF-1.4 piece du dossier"


async def _consultant(c: AsyncClient, email: str) -> dict:
    """Cree un compte, le passe consultant RSSI, et rend ses en-tetes."""
    await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    entetes = {"Authorization": f"Bearer {r.json()['access_token']}"}

    from sqlalchemy import select

    import app.core.database as _db
    from app.core.security import decode_access_token
    from app.models.user import User

    uid = int(decode_access_token(entetes["Authorization"].removeprefix("Bearer ").strip()))
    async with _db.AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.id == uid))).scalar_one()
        u.is_rssi_consultant = True
        await db.commit()
    return entetes


async def _un_client(c: AsyncClient, entetes: dict, nom: str) -> int:
    r = await c.post(
        f"{BASE}/rssi/clients",
        headers=entetes,
        json={"name": nom, "status": "active"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _piece(nom: str = "pssi.pdf") -> dict:
    return {"fichier": (nom, PDF, "application/pdf")}


# ── Le dossier par client ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_consultant_tient_un_dossier_par_client():
    """Ce que le modele d'avant l'etape 5b interdisait."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_dossiers@test.com")
        a = await _un_client(c, h, "Client A")
        b = await _un_client(c, h, "Client B")

        await c.put(
            f"{BASE}/rssi/clients/{a}/nis2", headers=h, json={"items": {"rssi": "compliant"}}
        )
        await c.put(
            f"{BASE}/rssi/clients/{b}/nis2", headers=h, json={"items": {"rssi": "non_compliant"}}
        )

        da = await c.get(f"{BASE}/rssi/clients/{a}/nis2", headers=h)
        dbb = await c.get(f"{BASE}/rssi/clients/{b}/nis2", headers=h)

    assert da.json()["items"] == {"rssi": "compliant"}
    assert dbb.json()["items"] == {"rssi": "non_compliant"}


@pytest.mark.asyncio
async def test_le_dossier_client_n_ecrase_pas_l_auto_evaluation_du_consultant():
    """Le consultant a la sienne, en plus de celles qu'il monte."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_sienne@test.com")
        client_id = await _un_client(c, h, "Client")

        await c.put(f"{BASE}/nis2/me", headers=h, json={"items": {"rssi": "compliant"}})
        await c.put(
            f"{BASE}/rssi/clients/{client_id}/nis2",
            headers=h,
            json={"items": {"rssi": "non_compliant"}},
        )

        sienne = await c.get(f"{BASE}/nis2/me", headers=h)

    assert sienne.json()["items"] == {"rssi": "compliant"}


# ── L isolation entre consultants ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_ne_lit_pas_le_dossier_du_client_d_un_autre():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _consultant(c, "cons_iso1@test.com")
        h2 = await _consultant(c, "cons_iso2@test.com")
        client_id = await _un_client(c, h1, "Client de 1")

        r = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2", headers=h2)

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_on_ne_depose_pas_sur_le_client_d_un_autre():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _consultant(c, "cons_dep1@test.com")
        h2 = await _consultant(c, "cons_dep2@test.com")
        client_id = await _un_client(c, h1, "Client de 1")

        r = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h2,
            files=_piece(),
        )

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_un_non_consultant_n_accede_pas_au_dossier():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_ref@test.com")
        client_id = await _un_client(c, h, "Client")

        await c.post(
            f"{BASE}/auth/register",
            json={"email": "simple_abonne@test.com", "password": "StrongPass123!"},
        )
        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": "simple_abonne@test.com", "password": "StrongPass123!"},
        )
        hs = {"Authorization": f"Bearer {r.json()['access_token']}"}

        rep = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2", headers=hs)

    assert rep.status_code == 403


# ── Les pieces ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_joindre_une_piece_au_dossier_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_piece@test.com")
        client_id = await _un_client(c, h, "Client")

        r = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/policy/pieces",
            headers=h,
            files=_piece(),
        )
        dossier = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2", headers=h)

    assert r.status_code == 201, r.text
    assert len(dossier.json()["pieces"]["policy"]) == 1
    assert dossier.json()["pieces"]["policy"][0]["nom"] == "pssi.pdf"


@pytest.mark.asyncio
async def test_les_pieces_ne_passent_pas_d_un_client_a_l_autre():
    """LE test d'isolation : deux dossiers du MEME consultant."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_fuite@test.com")
        a = await _un_client(c, h, "Client A")
        b = await _un_client(c, h, "Client B")

        await c.post(
            f"{BASE}/rssi/clients/{a}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece("pour_a.pdf"),
        )
        dossier_b = await c.get(f"{BASE}/rssi/clients/{b}/nis2", headers=h)

    assert dossier_b.json()["pieces"] == {}


@pytest.mark.asyncio
async def test_la_piece_d_un_client_n_apparait_pas_dans_l_auto_evaluation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_melange@test.com")
        client_id = await _un_client(c, h, "Client")

        await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece("du_client.pdf"),
        )
        mienne = await c.get(f"{BASE}/nis2/me", headers=h)

    assert mienne.json()["pieces"] == {}


@pytest.mark.asyncio
async def test_retirer_puis_telecharger_une_piece():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_menage@test.com")
        client_id = await _un_client(c, h, "Client")
        depot = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece(),
        )
        pid = depot.json()["id"]

        lien = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2/pieces/{pid}/download", headers=h)
        retrait = await c.delete(f"{BASE}/rssi/clients/{client_id}/nis2/pieces/{pid}", headers=h)
        apres = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2", headers=h)

    assert lien.status_code == 200 and "url" in lien.json()
    assert retrait.status_code == 204
    assert apres.json()["pieces"] == {}


@pytest.mark.asyncio
async def test_un_critere_inconnu_est_refuse():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_critere@test.com")
        client_id = await _un_client(c, h, "Client")

        r = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/inexistant/pieces",
            headers=h,
            files=_piece(),
        )

    assert r.status_code == 422


# ── L export ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_l_export_nomme_le_client_et_non_le_cabinet():
    """Un document qui porterait le nom du cabinet designerait la mauvaise entite.

    C'est la conformite du CLIENT qui est decrite.
    """
    from unittest.mock import patch

    import app.services.nis2_auditor_pdf as auditeur

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_export@test.com")
        client_id = await _un_client(c, h, "Entreprise Cliente SA")
        await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece("preuve_client.pdf"),
        )

        with patch.object(
            auditeur, "generate_nis2_auditor_pdf", wraps=auditeur.generate_nis2_auditor_pdf
        ) as gen:
            r = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2/pdf/auditor", headers=h)

    assert r.status_code == 200
    kwargs = gen.call_args.kwargs
    assert kwargs["company_name"] == "Entreprise Cliente SA"
    assert "rssi" in kwargs["pieces"], "les pièces du client n'ont pas été transmises"


# ── La garde d abonnement (alignee le 2026-08-07) ────────────────────────────


@pytest.mark.asyncio
async def test_un_consultant_au_gratuit_ne_depose_pas():
    """ETRE CONSULTANT N IMPLIQUE AUCUN ABONNEMENT.

    `is_rssi_consultant` est un booleen a false par defaut, pose par un admin,
    sans le moindre lien avec un plan. Un compte peut donc etre consultant ET au
    Gratuit — la garde doit s'appliquer des deux cotes.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_gratuit@test.com")
        await create_plan_and_subscription(c, h, tier=1)
        client_id = await _un_client(c, h, "Client")

        r = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece(),
        )

    assert r.status_code == 403


@pytest.mark.asyncio
async def test_un_consultant_payant_depose():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_payant@test.com")
        await create_plan_and_subscription(c, h, tier=2)
        client_id = await _un_client(c, h, "Client")

        r = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece(),
        )

    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_un_consultant_au_gratuit_recupere_et_nettoie_toujours():
    """CE QUI RESTE OUVERT, ET C EST DELIBERE.

    Un consultant dont l'abonnement a lapse doit pouvoir recuperer et nettoyer
    les dossiers de ses clients, et rendre le travail deja fait. Bloquer cela
    retiendrait en otage des documents qui ne lui appartiennent meme pas.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _consultant(c, "cons_lapse@test.com")
        await create_plan_and_subscription(c, h, tier=2)
        client_id = await _un_client(c, h, "Client")
        depot = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece(),
        )
        pid = depot.json()["id"]

        await _retrograder_au_gratuit(h)

        refuse = await c.post(
            f"{BASE}/rssi/clients/{client_id}/nis2/criteres/rssi/pieces",
            headers=h,
            files=_piece("autre.pdf"),
        )
        lien = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2/pieces/{pid}/download", headers=h)
        export = await c.get(f"{BASE}/rssi/clients/{client_id}/nis2/pdf/auditor", headers=h)
        retrait = await c.delete(f"{BASE}/rssi/clients/{client_id}/nis2/pieces/{pid}", headers=h)

    assert refuse.status_code == 403, "la retrogradation n'a pas pris"
    assert lien.status_code == 200, "ses documents lui sont refuses"
    assert export.status_code == 200, "il ne peut plus rendre le travail deja fait"
    assert retrait.status_code == 204, "il ne peut plus faire le menage"


async def _retrograder_au_gratuit(headers: dict) -> None:
    """Bascule l'abonnement EXISTANT vers le Gratuit.

    On modifie la ligne en place : deux abonnements actifs feraient lever
    `get_active_plan`, qui fait un `scalar_one_or_none()`.
    """
    from sqlalchemy import select

    import app.core.database as _db
    from app.core.security import decode_access_token
    from app.models.plan import Plan
    from app.models.subscription import Subscription
    from app.services.subscription_service import FREE_PLAN_NAME

    uid = int(decode_access_token(headers["Authorization"].removeprefix("Bearer ").strip()))
    async with _db.AsyncSessionLocal() as db:
        gratuit = (
            await db.execute(select(Plan).where(Plan.name == FREE_PLAN_NAME))
        ).scalar_one_or_none()
        if gratuit is None:
            gratuit = Plan(
                name=FREE_PLAN_NAME,
                display_name="Gratuit",
                price_eur=0,
                max_sites=-1,
                scan_interval_days=1,
                tier_level=1,
                allow_conformity_export=False,
            )
            db.add(gratuit)
            await db.flush()
        for sub in (
            (await db.execute(select(Subscription).where(Subscription.user_id == uid)))
            .scalars()
            .all()
        ):
            sub.plan_id = gratuit.id
        await db.commit()
