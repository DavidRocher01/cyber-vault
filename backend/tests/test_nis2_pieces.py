"""Depot de pieces justificatives sur l'auto-evaluation NIS2 — etape 5e.

LE PARCOURS QUE CES TESTS COUVRENT : un abonne qui veut NIS2 seul, ni consultant
ni client d'un RSSI fractionne. Il n'a aucun `RssiClient`, aucun
`RssiDeliverable` — c'est precisement ce qui rendait son cas fragile, et ce que
l'etape 5c a mis d'aplomb.

CE QUI EST GARDE PAR L'ABONNEMENT, ET CE QUI NE L'EST PAS. Deposer coute du
stockage : plans payants. Retirer et telecharger ne sont PAS gardes — un abonne
qui repasse au Gratuit doit pouvoir recuperer et effacer ses propres documents.
Les mettre derriere un peage les retiendrait en otage.

Cf. `docs/DEPOT_DOCUMENTS.md`.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import create_plan_and_subscription

BASE = "/api/v1"
PDF = b"%PDF-1.4 contenu de preuve"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _piece(nom: str = "politique.pdf", contenu: bytes = PDF) -> dict:
    return {"fichier": (nom, contenu, "application/pdf")}


# ── Le depot ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deposer_une_piece_sur_un_critere():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_ok@test.com")
        r = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())

    assert r.status_code == 201, r.text
    corps = r.json()
    assert corps["nom"] == "politique.pdf"
    assert corps["taille_octets"] == len(PDF)
    assert "statut_analyse" in corps


@pytest.mark.asyncio
async def test_la_piece_apparait_sous_son_critere():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_liste@test.com")
        await c.post(f"{BASE}/nis2/me/criteres/policy/pieces", headers=h, files=_piece())
        r = await c.get(f"{BASE}/nis2/me", headers=h)

    corps = r.json()
    assert len(corps["pieces"]["policy"]) == 1
    assert corps["pieces"]["policy"][0]["nom"] == "politique.pdf"


@pytest.mark.asyncio
async def test_les_mesures_automatiques_et_les_pieces_ne_se_confondent_pas():
    """`preuves` = ce que la plateforme mesure. `pieces` = ce que l'abonne fournit.

    Les melanger laisserait croire que la plateforme a produit ce que
    l'utilisateur a lui-meme depose.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_champs@test.com")
        await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())
        r = await c.get(f"{BASE}/nis2/me", headers=h)

    corps = r.json()
    assert "rssi" in corps["pieces"]
    assert corps["preuves"] == {}


@pytest.mark.asyncio
async def test_deposer_ne_suppose_pas_d_auto_evaluation_enregistree():
    """Exiger d'avoir enregistre avant de joindre imposerait un ordre injustifie."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_sans_eval@test.com")
        r = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())
        apres = await c.get(f"{BASE}/nis2/me", headers=h)

    assert r.status_code == 201
    # Une evaluation vide rend ce que rendait son absence : rien ne change a l'ecran.
    assert apres.json()["items"] == {}
    assert apres.json()["score"] == 0


@pytest.mark.asyncio
async def test_enregistrer_l_auto_evaluation_ne_perd_pas_les_pieces():
    """Le PUT doit rendre la meme chose que le GET, sinon elles disparaissent."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_put@test.com")
        await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())
        r = await c.put(f"{BASE}/nis2/me", headers=h, json={"items": {"rssi": "compliant"}})

    assert r.status_code == 200
    assert len(r.json()["pieces"]["rssi"]) == 1


# ── Les refus ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_critere_inconnu_est_refuse():
    """Une piece sous un identifiant errone serait invisible ET imperissable."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_critere_ko@test.com")
        r = await c.post(f"{BASE}/nis2/me/criteres/nimporte_quoi/pieces", headers=h, files=_piece())

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_un_fichier_dont_le_contenu_ment_est_refuse():
    """Renommer un exécutable en .pdf ne doit pas suffire."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_signature@test.com")
        r = await c.post(
            f"{BASE}/nis2/me/criteres/rssi/pieces",
            headers=h,
            files=_piece("faux.pdf", b"MZ\x90\x00 ce n est pas un PDF"),
        )

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_un_depot_anonyme_est_refuse():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", files=_piece())

    assert r.status_code in (401, 403)


# ── L isolation entre comptes ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_ne_retire_pas_la_piece_d_un_autre():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _headers(c, "piece_iso1@test.com")
        h2 = await _headers(c, "piece_iso2@test.com")
        depot = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h1, files=_piece())
        piece_id = depot.json()["id"]

        r = await c.delete(f"{BASE}/nis2/me/pieces/{piece_id}", headers=h2)
        encore_la = await c.get(f"{BASE}/nis2/me", headers=h1)

    assert r.status_code == 404
    assert len(encore_la.json()["pieces"]["rssi"]) == 1


@pytest.mark.asyncio
async def test_on_ne_telecharge_pas_la_piece_d_un_autre():
    """Sinon connaitre un identifiant suffirait a obtenir le document d'autrui."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _headers(c, "piece_dl1@test.com")
        h2 = await _headers(c, "piece_dl2@test.com")
        depot = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h1, files=_piece())
        piece_id = depot.json()["id"]

        r = await c.get(f"{BASE}/nis2/me/pieces/{piece_id}/download", headers=h2)

    assert r.status_code == 404


# ── Retirer et telecharger : jamais derriere un peage ────────────────────────


@pytest.mark.asyncio
async def test_retirer_sa_piece():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_retrait@test.com")
        depot = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())
        r = await c.delete(f"{BASE}/nis2/me/pieces/{depot.json()['id']}", headers=h)
        apres = await c.get(f"{BASE}/nis2/me", headers=h)

    assert r.status_code == 204
    assert apres.json()["pieces"] == {}


@pytest.mark.asyncio
async def test_telecharger_sa_piece():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_dl_ok@test.com")
        depot = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())
        r = await c.get(f"{BASE}/nis2/me/pieces/{depot.json()['id']}/download", headers=h)

    assert r.status_code == 200
    assert "url" in r.json()


# ── Le gate d abonnement ─────────────────────────────────────────────────────


async def _retrograder_au_gratuit(headers: dict) -> None:
    """Bascule l'abonnement EXISTANT vers le plan Gratuit.

    On modifie la ligne en place au lieu d'en ajouter une seconde : deux
    abonnements actifs feraient lever `get_active_plan`, qui fait un
    `scalar_one_or_none()`. Le test aurait alors verifie une exception plutot
    qu'une retrogradation.
    """
    from sqlalchemy import select

    import app.core.database as _db
    from app.core.security import decode_access_token
    from app.models.plan import Plan
    from app.models.subscription import Subscription
    from app.services.subscription_service import FREE_PLAN_NAME

    user_id = int(decode_access_token(headers["Authorization"].removeprefix("Bearer ").strip()))
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
            (await db.execute(select(Subscription).where(Subscription.user_id == user_id)))
            .scalars()
            .all()
        ):
            sub.plan_id = gratuit.id
        await db.commit()


@pytest.mark.asyncio
async def test_le_plan_gratuit_ne_peut_pas_deposer():
    """La decision produit : deposer coute du stockage, donc plans payants."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_gratuit@test.com")
        await create_plan_and_subscription(c, h, tier=1)
        r = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())

    assert r.status_code == 403


@pytest.mark.asyncio
async def test_un_plan_payant_peut_deposer():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_payant@test.com")
        await create_plan_and_subscription(c, h, tier=2)
        r = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())

    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_le_gratuit_recupere_et_efface_toujours_ses_pieces():
    """CE QUI N'EST PAS GARDE, ET C'EST DELIBERE.

    Un abonne qui repasse au Gratuit doit pouvoir recuperer et retirer ce qu'il a
    depose. Mettre ses propres documents derriere un peage les retiendrait en
    otage — indefendable sur un produit qui vend de la conformite.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_downgrade@test.com")
        await create_plan_and_subscription(c, h, tier=2)
        depot = await c.post(f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece())
        piece_id = depot.json()["id"]

        await _retrograder_au_gratuit(h)

        # La garde mord bien : il ne peut plus DEPOSER.
        depot_refuse = await c.post(
            f"{BASE}/nis2/me/criteres/rssi/pieces", headers=h, files=_piece("autre.pdf")
        )
        telecharge = await c.get(f"{BASE}/nis2/me/pieces/{piece_id}/download", headers=h)
        retire = await c.delete(f"{BASE}/nis2/me/pieces/{piece_id}", headers=h)

    assert depot_refuse.status_code == 403, "la retrogradation n'a pas pris"
    assert telecharge.status_code == 200, "ses propres documents lui sont refuses"
    assert retire.status_code == 204, "il ne peut plus faire le menage"


@pytest.mark.asyncio
async def test_retirer_une_piece_inexistante_repond_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "piece_404@test.com")
        r = await c.delete(f"{BASE}/nis2/me/pieces/999999", headers=h)

    assert r.status_code == 404
