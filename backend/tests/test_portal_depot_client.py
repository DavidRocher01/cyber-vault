"""Le client remet un document a son consultant — etape 3 du depot.

C'est le besoin d'origine du chantier : jusqu'ici le portail etait en LECTURE
SEULE, le flux allait a sens unique du consultant vers le client. Il n'a pu etre
ouvert qu'une fois l'antivirus en service.

CE QUE CES TESTS PROTEGENT, PAR ORDRE D'IMPORTANCE :

1. L'ISOLATION. Un client ne depose que pour LUI. C'est la garantie qui tient
   tout le portail, et le depot est le premier point d'ECRITURE qu'il ait.
2. LE QUOTA. Sans plafond, la plateforme devient un espace de stockage — ce que
   `docs/DEPOT_DOCUMENTS.md` interdit explicitement.
3. L'ORDRE DES CONTROLES. Rien n'est ecrit sur S3 avant que tout soit valide :
   un refus apres stockage laisserait un objet orphelin en annoncant un echec.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.models.enums import OrigineDepot, StatutAnalyse

BASE = "/api/v1"
_PDF = b"%PDF-1.4 document du client"


async def _client_du_portail(http_client: AsyncClient, email: str) -> tuple[dict, int]:
    """Cree un consultant, un client RSSI, et le compte client rattache."""
    from sqlalchemy import select

    import app.core.database as _db
    from app.core.security import decode_access_token
    from app.models.rssi_client import RssiClient
    from app.models.user import User
    from tests.conftest import register_and_login

    consultant_h = await register_and_login(http_client, f"consult_{email}")
    cid = int(decode_access_token(consultant_h["Authorization"].removeprefix("Bearer ").strip()))
    async with _db.AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.id == cid))).scalar_one()
        u.is_rssi_consultant = True
        await db.commit()

    client_h = await register_and_login(http_client, email)
    uid = int(decode_access_token(client_h["Authorization"].removeprefix("Bearer ").strip()))
    async with _db.AsyncSessionLocal() as db:
        rc = RssiClient(
            consultant_user_id=cid, client_user_id=uid, name="Client portail", status="active"
        )
        db.add(rc)
        await db.flush()
        rid = rc.id
        await db.commit()
    return client_h, rid


# ── Le depot fonctionne ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_le_client_peut_deposer(http_client: AsyncClient):
    h, _ = await _client_du_portail(http_client, "depot_ok@test.com")
    r = await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("politique.pdf", _PDF, "application/pdf")},
        data={"titre": "Politique de securite relue"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["title"] == "Politique de securite relue"
    assert d["origine"] == OrigineDepot.CLIENT
    assert d["has_file"] is True


@pytest.mark.asyncio
async def test_le_depot_apparait_dans_sa_liste_avec_son_origine(http_client: AsyncClient):
    h, _ = await _client_du_portail(http_client, "depot_liste@test.com")
    await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("inventaire.pdf", _PDF, "application/pdf")},
        data={"titre": "Inventaire"},
        headers=h,
    )
    r = await http_client.get(f"{BASE}/portal/deliverables", headers=h)
    assert r.status_code == 200
    ligne = next(d for d in r.json() if d["title"] == "Inventaire")
    assert ligne["origine"] == OrigineDepot.CLIENT
    assert ligne["statut_analyse"] == StatutAnalyse.SAIN  # antivirus inactif en test


@pytest.mark.asyncio
async def test_le_consultant_voit_le_depot_de_son_client(http_client: AsyncClient):
    """Sinon la fonctionnalite ne sert a rien : remettre sans que personne ne recoive."""
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.rssi_deliverable import RssiDeliverable

    h, rid = await _client_du_portail(http_client, "depot_vu@test.com")
    await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("preuve.pdf", _PDF, "application/pdf")},
        data={"titre": "Preuve de mise en oeuvre"},
        headers=h,
    )
    async with _db.AsyncSessionLocal() as db:
        livrables = (
            (await db.execute(select(RssiDeliverable).where(RssiDeliverable.client_id == rid)))
            .scalars()
            .all()
        )
    assert len(livrables) == 1
    assert livrables[0].origine == OrigineDepot.CLIENT


@pytest.mark.asyncio
async def test_le_client_retelecharge_son_propre_depot(http_client: AsyncClient):
    h, _ = await _client_du_portail(http_client, "depot_dl@test.com")
    dep = await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("doc.pdf", _PDF, "application/pdf")},
        data={"titre": "Doc"},
        headers=h,
    )
    r = await http_client.get(f"{BASE}/portal/deliverables/{dep.json()['id']}/download", headers=h)
    assert r.status_code == 200
    assert r.json()["url"]


# ── L'isolation, la garantie qui tient tout le portail ─────────────────────────


@pytest.mark.asyncio
async def test_un_compte_sans_client_lie_ne_peut_pas_deposer(http_client: AsyncClient):
    from tests.conftest import register_and_login

    h = await register_and_login(http_client, "depot_orphelin@test.com")
    r = await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("x.pdf", _PDF, "application/pdf")},
        data={"titre": "X"},
        headers=h,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_le_depot_atterrit_chez_le_bon_client(http_client: AsyncClient):
    """Le client_id ne vient JAMAIS de la requete : il est resolu par la dependance."""
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.rssi_deliverable import RssiDeliverable

    hA, ridA = await _client_du_portail(http_client, "depot_a@test.com")
    _, ridB = await _client_du_portail(http_client, "depot_b@test.com")

    await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("a.pdf", _PDF, "application/pdf")},
        # Tentative d'injection : ces champs ne sont pas lus par l'endpoint.
        data={"titre": "Depot de A", "client_id": str(ridB), "origine": "consultant"},
        headers=hA,
    )
    async with _db.AsyncSessionLocal() as db:
        chez_b = (
            (await db.execute(select(RssiDeliverable).where(RssiDeliverable.client_id == ridB)))
            .scalars()
            .all()
        )
        chez_a = (
            (await db.execute(select(RssiDeliverable).where(RssiDeliverable.client_id == ridA)))
            .scalars()
            .all()
        )
    assert len(chez_b) == 0, "le depot a atterri chez un autre client"
    assert len(chez_a) == 1
    assert chez_a[0].origine == OrigineDepot.CLIENT, "l'origine a ete forcee par la requete"


# ── Les controles, et leur ordre ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_fichier_deguise_est_refuse(http_client: AsyncClient):
    h, _ = await _client_du_portail(http_client, "depot_deguise@test.com")
    r = await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("piege.pdf", b"<!DOCTYPE html><script>", "application/pdf")},
        data={"titre": "Piege"},
        headers=h,
    )
    assert r.status_code == 422
    assert "ne correspond pas" in r.json()["detail"]


@pytest.mark.asyncio
async def test_un_titre_vide_est_refuse(http_client: AsyncClient):
    h, _ = await _client_du_portail(http_client, "depot_sanstitre@test.com")
    r = await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("x.pdf", _PDF, "application/pdf")},
        data={"titre": "   "},
        headers=h,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_rien_n_est_ecrit_sur_s3_si_un_controle_refuse(http_client: AsyncClient):
    """L'ordre des controles : refuser APRES stockage laisserait un orphelin."""
    h, _ = await _client_du_portail(http_client, "depot_ordre@test.com")
    with patch("app.services.storage.upload_file") as ecrit:
        r = await http_client.post(
            f"{BASE}/portal/deliverables",
            files={"fichier": ("piege.pdf", b"MZ\x90\x00", "application/pdf")},
            data={"titre": "Piege"},
            headers=h,
        )
    assert r.status_code == 422
    ecrit.assert_not_called()


# ── Le quota ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_le_quota_refuse_le_depot_de_trop(http_client: AsyncClient, monkeypatch):
    """Sans plafond, la plateforme devient un espace de stockage."""
    from app.services import depot_service

    h, _ = await _client_du_portail(http_client, "depot_quota@test.com")
    # Quota volontairement minuscule : un PDF passe, le second non.
    monkeypatch.setattr(depot_service.settings, "QUOTA_DEPOT_CLIENT_OCTETS", len(_PDF) + 10)

    premier = await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("un.pdf", _PDF, "application/pdf")},
        data={"titre": "Un"},
        headers=h,
    )
    assert premier.status_code == 201

    second = await http_client.post(
        f"{BASE}/portal/deliverables",
        files={"fichier": ("deux.pdf", _PDF, "application/pdf")},
        data={"titre": "Deux"},
        headers=h,
    )
    assert second.status_code == 413
    assert "Quota" in second.json()["detail"]


@pytest.mark.asyncio
async def test_le_quota_est_verifie_avant_d_ecrire(http_client: AsyncClient, monkeypatch):
    from app.services import depot_service

    h, _ = await _client_du_portail(http_client, "depot_quota_ordre@test.com")
    monkeypatch.setattr(depot_service.settings, "QUOTA_DEPOT_CLIENT_OCTETS", 1)

    with patch("app.services.storage.upload_file") as ecrit:
        r = await http_client.post(
            f"{BASE}/portal/deliverables",
            files={"fichier": ("gros.pdf", _PDF, "application/pdf")},
            data={"titre": "Gros"},
            headers=h,
        )
    assert r.status_code == 413
    ecrit.assert_not_called()
