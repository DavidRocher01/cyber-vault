"""Mesure d'acquisition — collecte et restitution.

Conception : `docs/ANALYTICS.md`. Le principe qui gouverne tout : on enregistre
d'ou vient quelqu'un AU MOMENT ou il convertit, jamais en le suivant de page en
page. Aucun identifiant de visiteur n'existe, et ces tests verrouillent
notamment ce qui ne doit PAS etre stocke.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.source_acquisition import SourceAcquisition
from app.models.user import User
from app.services import acquisition_service

BASE = "/api/v1"


async def _session():
    from app.core.database import AsyncSessionLocal

    return AsyncSessionLocal()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Normalisation : le rempart de l'endpoint public ──────────────────────────


class TestNormalisation:
    def test_la_casse_ne_dedouble_pas_les_sources(self):
        """« LinkedIn » et « linkedin » doivent compter ensemble, sinon le
        classement par revenu se disperse sur deux lignes."""
        assert acquisition_service.normaliser("LinkedIn") == "linkedin"
        assert acquisition_service.normaliser("  LINKEDIN ") == "linkedin"

    def test_longueur_bornee(self):
        """Sans plafond, `?utm_source=<2 ko>` fait de la table un stockage gratuit."""
        assert len(acquisition_service.normaliser("x" * 5000)) == 64

    def test_caracteres_dangereux_neutralises(self):
        assert (
            acquisition_service.normaliser("<script>alert(1)</script>") == "script-alert-1-script"
        )
        assert acquisition_service.normaliser("../../etc/passwd") == "..-..-etc-passwd"

    def test_vide_devient_none(self):
        assert acquisition_service.normaliser("") is None
        assert acquisition_service.normaliser("   ") is None
        assert acquisition_service.normaliser(None) is None

    def test_le_referent_perd_sa_query_string(self):
        """Une URL referente peut porter un terme de recherche ou un identifiant
        de session — donc de la donnee personnelle dont on n'a aucun usage."""
        assert (
            acquisition_service.domaine_referent("https://www.google.com/search?q=mon+nom")
            == "google.com"
        )

    def test_la_page_perd_sa_query_string(self):
        assert acquisition_service.chemin_interne("/scan-gratuit?utm_source=x&token=abc") == (
            "/scan-gratuit"
        )


# ── Collecte ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_le_scan_gratuit_enregistre_sa_provenance(client):
    # La tache de fond lie AsyncSessionLocal a l'import : sous pytest elle
    # pointerait le repli SQLite. Meme neutralisation que test_code_scans.
    with (
        patch("app.api.v1.endpoints.public_scans.assert_no_ssrf", return_value=None),
        patch("app.api.v1.endpoints.public_scans._run_background", new_callable=AsyncMock),
    ):
        r = await client.post(
            f"{BASE}/public-scans",
            json={
                "url": "https://exemple.fr",
                "utm_source": "LinkedIn",
                "utm_campaign": "lancement-nis2",
                "page_atterrissage": "/scan-gratuit?utm_source=LinkedIn",
            },
            headers={"referer": "https://www.linkedin.com/feed/?q=prive"},
        )
    assert r.status_code == 202

    async with await _session() as db:
        ligne = (await db.execute(select(SourceAcquisition))).scalar_one()
    assert ligne.evenement == "scan_gratuit"
    assert ligne.utm_source == "linkedin"
    assert ligne.utm_campaign == "lancement-nis2"
    assert ligne.referent_domaine == "linkedin.com"
    assert ligne.page_atterrissage == "/scan-gratuit"
    assert ligne.public_scan_id is not None
    assert ligne.user_id is None


@pytest.mark.asyncio
async def test_l_inscription_est_rattachee_au_compte(client):
    r = await client.post(
        f"{BASE}/auth/register",
        json={
            "email": "venu@test.com",
            "password": "StrongPass123!",
            "utm_source": "cold-email",
        },
    )
    assert r.status_code == 201

    async with await _session() as db:
        ligne = (
            await db.execute(
                select(SourceAcquisition).where(SourceAcquisition.evenement == "inscription")
            )
        ).scalar_one()
        user = (await db.execute(select(User).where(User.email == "venu@test.com"))).scalar_one()
    assert ligne.utm_source == "cold-email"
    assert ligne.user_id == user.id


@pytest.mark.asyncio
async def test_une_inscription_sans_provenance_reste_possible(client):
    """La mesure ne doit jamais conditionner l'action : pas d'UTM, pas de refus."""
    r = await client.post(
        f"{BASE}/auth/register", json={"email": "direct@test.com", "password": "StrongPass123!"}
    )
    assert r.status_code == 201

    async with await _session() as db:
        ligne = (await db.execute(select(SourceAcquisition))).scalar_one()
    assert ligne.utm_source is None


@pytest.mark.asyncio
async def test_un_champ_inconnu_est_refuse(client):
    """`extra='forbid'` : un client ne doit pas pouvoir inventer un champ, ni
    glisser un identifiant de visiteur que la conception exclut."""
    r = await client.post(
        f"{BASE}/auth/register",
        json={
            "email": "malin@test.com",
            "password": "StrongPass123!",
            "visitor_id": "abc-123",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_une_etape_inconnue_n_est_pas_ecrite(db_session):
    """La liste des etapes est fermee. Un libelle libre finirait par tout stocker."""
    resultat = await acquisition_service.enregistrer(db_session, evenement="n-importe-quoi")
    assert resultat is None
    assert (await db_session.execute(select(SourceAcquisition))).scalars().all() == []


# ── Restitution ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_les_sources_sont_triees_par_revenu(db_session):
    """Le tri par revenu et non par trafic est le parti pris central : une source
    qui amene du monde sans amener de clients doit descendre d'elle-meme."""
    for _ in range(50):
        await acquisition_service.enregistrer(
            db_session, evenement="scan_gratuit", utm_source="seo"
        )
    await acquisition_service.enregistrer(db_session, evenement="scan_gratuit", utm_source="li")
    await acquisition_service.enregistrer(
        db_session, evenement="abonnement", utm_source="li", montant_mensuel_cents=39000
    )
    await db_session.commit()

    lignes = await acquisition_service.par_source(db_session)
    assert lignes[0]["source"] == "li", "la source qui rapporte doit passer devant"
    assert lignes[0]["mrr_cents"] == 39000
    assert lignes[1]["source"] == "seo"
    assert lignes[1]["mrr_cents"] == 0


@pytest.mark.asyncio
async def test_le_tunnel_rend_toutes_les_etapes_meme_a_zero(db_session):
    """Une etape absente doit valoir 0 et non disparaitre : un trou dans le
    tunnel se lit, une ligne manquante passe inapercue."""
    await acquisition_service.enregistrer(db_session, evenement="scan_gratuit")

    etapes = await acquisition_service.tunnel(db_session)
    assert etapes == {
        "scan_gratuit": 1,
        "email_debloque": 0,
        "inscription": 0,
        "abonnement": 0,
    }


# ── Acces : la voie stricte, jamais la cle partagee ──────────────────────────


@pytest.mark.asyncio
async def test_l_onglet_exige_un_compte_admin(client):
    """Les donnees de conversion ne doivent pas etre accessibles par le secret
    partage qu'on est en train de retirer (cf. S6_INFRA_CHECKLIST §0)."""
    with patch("app.core.deps.settings") as reglages:
        reglages.ADMIN_API_KEY = "cle-partagee"
        r = await client.get(f"{BASE}/admin/acquisition", headers={"X-Admin-Key": "cle-partagee"})
    assert r.status_code == 401

    await client.post(
        f"{BASE}/auth/register", json={"email": "chef@test.com", "password": "StrongPass123!"}
    )
    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "chef@test.com"))).scalar_one()
        user.is_admin = True
        await db.commit()
    login = await client.post(
        f"{BASE}/auth/login", json={"email": "chef@test.com", "password": "StrongPass123!"}
    )
    entetes = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = await client.get(f"{BASE}/admin/acquisition", headers=entetes)
    assert r.status_code == 200
    corps = r.json()
    assert corps["fenetre"] == "90j"
    assert set(corps["tunnel"]) == set(acquisition_service.ETAPES)
    # L'inscription ci-dessus compte : la collecte n'est donc pas vide.
    assert corps["collecte_vide"] is False


@pytest.mark.asyncio
async def test_la_fenetre_est_bornee(client):
    """Un entier libre laisserait demander 100 000 jours et balayer la table."""
    await client.post(
        f"{BASE}/auth/register", json={"email": "chef2@test.com", "password": "StrongPass123!"}
    )
    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "chef2@test.com"))).scalar_one()
        user.is_admin = True
        await db.commit()
    login = await client.post(
        f"{BASE}/auth/login", json={"email": "chef2@test.com", "password": "StrongPass123!"}
    )
    entetes = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert (
        await client.get(f"{BASE}/admin/acquisition?fenetre=99999j", headers=entetes)
    ).status_code == 422
    assert (
        await client.get(f"{BASE}/admin/acquisition?fenetre=30j", headers=entetes)
    ).status_code == 200


# ── La chaine complete : source -> revenu ────────────────────────────────────


@pytest.mark.asyncio
async def test_le_revenu_remonte_jusqu_a_la_source(client, db_session):
    """Le scenario qui justifie tout le systeme, de bout en bout.

    Marie arrive de LinkedIn, lance un scan, debloque son rapport, cree un
    compte, puis s'abonne. Le MRR doit apparaitre sous « linkedin » — jamais
    sous « direct ».
    """
    from app.services import acquisition_service as acq

    # 1. Scan gratuit, avec sa provenance.
    await acq.enregistrer(
        db_session, evenement="scan_gratuit", utm_source="linkedin", public_scan_id=None
    )

    # 2-3. Inscription puis abonnement, rattaches au compte.
    await client.post(
        f"{BASE}/auth/register", json={"email": "marie@test.com", "password": "StrongPass123!"}
    )
    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "marie@test.com"))).scalar_one()
        # La ligne du scan porte la source : on la rattache comme le ferait le
        # rattachement par e-mail.
        ligne = (
            await db.execute(
                select(SourceAcquisition).where(SourceAcquisition.evenement == "scan_gratuit")
            )
        ).scalar_one()
        ligne.user_id = user.id
        await db.commit()

    async with await _session() as db:
        await acq.enregistrer_abonnement(db, user_id=user.id, montant_mensuel_cents=14900)

    async with await _session() as db:
        lignes = await acq.par_source(db)
    par_nom = {x["source"]: x for x in lignes}
    assert "linkedin" in par_nom, "le revenu doit remonter a la source, pas tomber en direct"
    assert par_nom["linkedin"]["mrr_cents"] == 14900
    assert par_nom.get("direct", {}).get("mrr_cents", 0) == 0


@pytest.mark.asyncio
async def test_l_abonnement_herite_de_la_source_du_compte(client):
    """Le webhook Stripe connait le montant, jamais le canal. Sans heritage,
    tout le revenu atterrirait sous « direct »."""
    from app.services import acquisition_service as acq

    await client.post(
        f"{BASE}/auth/register",
        json={"email": "herite@test.com", "password": "StrongPass123!", "utm_source": "Cold-Email"},
    )
    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "herite@test.com"))).scalar_one()
        ligne = await acq.enregistrer_abonnement(db, user_id=user.id, montant_mensuel_cents=4900)
    assert ligne is not None
    assert ligne.utm_source == "cold-email"


@pytest.mark.asyncio
async def test_rattachement_par_email_et_non_par_identifiant_d_appareil(client, db_session):
    """Le lien entre le scan anonyme et le compte passe par l'adresse saisie
    deux fois, jamais par quelque chose ecrit dans le navigateur."""
    from app.models.public_scan import PublicScan
    from app.services import acquisition_service as acq

    async with await _session() as db:
        scan = PublicScan(target_url="https://x.fr", email="lien@test.com")
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        scan_id = scan.id

    async with await _session() as db:
        await acq.enregistrer(
            db, evenement="scan_gratuit", utm_source="seo", public_scan_id=scan_id
        )

    await client.post(
        f"{BASE}/auth/register", json={"email": "lien@test.com", "password": "StrongPass123!"}
    )

    async with await _session() as db:
        user = (await db.execute(select(User).where(User.email == "lien@test.com"))).scalar_one()
        source = await acq.source_du_compte(db, user_id=user.id)
    assert source["utm_source"] == "seo", "la source du scan doit suivre le compte"
