"""Etat d'analyse antivirus des fichiers deposes (etape 2 du depot de documents).

La regle tenue par ces tests : UN FICHIER N'EST DELIVRE QUE S'IL EST REPUTE SAIN.

Elle a deux bords qui comptent autant que la regle elle-meme :

- un fichier ANTERIEUR au registre reste telechargeable, sans quoi la mise en
  production rendrait indisponible d'un coup tous les livrables deja deposes ;
- tant que l'antivirus n'est pas en service, un depot est enregistre sain — le
  marquer `en_analyse` fermerait une porte qu'aucune cle n'ouvre, personne ne
  rendant de verdict.

Cf. `docs/DEPOT_DOCUMENTS.md`.
"""

import pytest
from httpx import AsyncClient

from app.models.enums import StatutAnalyse

BASE = "/api/v1"
_PDF = b"%PDF-1.4 contenu de test"


async def _auth_consultant(http_client: AsyncClient, email: str) -> dict:
    from sqlalchemy import select

    import app.core.database as _db_mod
    from app.models.user import User

    await http_client.post(
        f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"}
    )
    r = await http_client.post(
        f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"}
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    async with _db_mod.AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return headers


async def _client_et_depot(http_client: AsyncClient, headers: dict) -> tuple[int, str, int]:
    """Cree un client RSSI, depose un PDF, rattache un livrable.

    Renvoie (client_id, cle_stockage, deliverable_id).
    """
    c = await http_client.post(f"{BASE}/rssi/clients", json={"name": "Client AV"}, headers=headers)
    client_id = c.json()["id"]
    up = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/deliverables/upload",
        files={"file": ("rapport.pdf", _PDF, "application/pdf")},
        headers=headers,
    )
    assert up.status_code == 200, up.text
    cle = up.json()["key"]
    d = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/deliverables",
        json={
            "title": "Rapport",
            "doc_type": "rapport",
            "delivered_at": "2026-05-01",
            "file_url": cle,
        },
        headers=headers,
    )
    return client_id, cle, d.json()["id"]


# ── Le registre se remplit ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_depot_entre_au_registre(http_client: AsyncClient):
    from sqlalchemy import select

    import app.core.database as _db_mod
    from app.models.fichier_depose import FichierDepose

    h = await _auth_consultant(http_client, "av_registre@test.com")
    _, cle, _ = await _client_et_depot(http_client, h)

    async with _db_mod.AsyncSessionLocal() as db:
        fichier = (
            await db.execute(select(FichierDepose).where(FichierDepose.cle_stockage == cle))
        ).scalar_one()
    assert fichier.nom_original == "rapport.pdf"
    assert fichier.taille_octets == len(_PDF)
    assert fichier.type_mime == "application/pdf"


@pytest.mark.asyncio
async def test_sans_antivirus_le_depot_est_enregistre_sain(http_client: AsyncClient):
    """Sinon la porte se ferme sans que personne ne detienne la cle."""
    h = await _auth_consultant(http_client, "av_sain@test.com")
    up_json = None
    c = await http_client.post(f"{BASE}/rssi/clients", json={"name": "C"}, headers=h)
    up = await http_client.post(
        f"{BASE}/rssi/clients/{c.json()['id']}/deliverables/upload",
        files={"file": ("x.pdf", _PDF, "application/pdf")},
        headers=h,
    )
    up_json = up.json()
    assert up_json["statut_analyse"] == StatutAnalyse.SAIN


# ── La regle de delivrance ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fichier_sain_telechargeable(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "av_dl_ok@test.com")
    client_id, _, deliverable_id = await _client_et_depot(http_client, h)
    r = await http_client.get(
        f"{BASE}/rssi/clients/{client_id}/deliverables/{deliverable_id}/download", headers=h
    )
    assert r.status_code == 200
    assert r.json()["url"]


@pytest.mark.asyncio
async def test_fichier_en_analyse_refuse(http_client: AsyncClient):
    import app.core.database as _db_mod
    from app.services import depot_service

    h = await _auth_consultant(http_client, "av_encours@test.com")
    client_id, cle, deliverable_id = await _client_et_depot(http_client, h)

    async with _db_mod.AsyncSessionLocal() as db:
        fichier = await depot_service.fichier_par_cle(db, cle)
        fichier.statut_analyse = StatutAnalyse.EN_ANALYSE
        await db.commit()

    r = await http_client.get(
        f"{BASE}/rssi/clients/{client_id}/deliverables/{deliverable_id}/download", headers=h
    )
    assert r.status_code == 409
    assert "analyse" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_fichier_rejete_refuse(http_client: AsyncClient):
    import app.core.database as _db_mod
    from app.services import depot_service

    h = await _auth_consultant(http_client, "av_rejete@test.com")
    client_id, cle, deliverable_id = await _client_et_depot(http_client, h)

    async with _db_mod.AsyncSessionLocal() as db:
        await depot_service.enregistrer_verdict(db, cle_stockage=cle, sain=False)

    r = await http_client.get(
        f"{BASE}/rssi/clients/{client_id}/deliverables/{deliverable_id}/download", headers=h
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_fichier_anterieur_au_registre_reste_telechargeable(http_client: AsyncClient):
    """Le bord qui evite de casser la production.

    Un livrable dont la cle ne figure dans aucune ligne — cas de TOUS les
    fichiers deposes avant ce chantier — doit rester delivrable.
    """
    h = await _auth_consultant(http_client, "av_ancien@test.com")
    c = await http_client.post(f"{BASE}/rssi/clients", json={"name": "Ancien"}, headers=h)
    client_id = c.json()["id"]
    # Livrable pointant une cle jamais passee par le registre.
    d = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/deliverables",
        json={
            "title": "Livrable d'avant",
            "doc_type": "rapport",
            "delivered_at": "2026-01-01",
            "file_url": "uploads/rssi/1/1/cle-historique_rapport.pdf",
        },
        headers=h,
    )
    r = await http_client.get(
        f"{BASE}/rssi/clients/{client_id}/deliverables/{d.json()['id']}/download", headers=h
    )
    assert r.status_code == 200, r.text


# ── Portail client : la voie qui compte le plus ────────────────────────────────
#
# C'est le client qu'on protege quand la plateforme sert de vecteur. Un controle
# pose seulement cote consultant laisserait passer exactement ce qu'il pretend
# arreter.


async def _client_du_portail(http_client: AsyncClient, email: str, cle: str) -> tuple[dict, int]:
    """Cree un compte client rattache a un RssiClient, avec un livrable pointant
    `cle`. Renvoie (entetes du client, deliverable_id).
    """
    from datetime import UTC, datetime

    from sqlalchemy import select

    import app.core.database as _db
    from app.models.rssi_client import RssiClient
    from app.models.rssi_deliverable import RssiDeliverable
    from app.models.user import User
    from tests.conftest import register_and_login

    consultant_h = await register_and_login(http_client, f"consult_{email}")
    from app.core.security import decode_access_token

    consultant_id = int(
        decode_access_token(consultant_h["Authorization"].removeprefix("Bearer ").strip())
    )
    async with _db.AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.id == consultant_id))).scalar_one()
        u.is_rssi_consultant = True
        await db.commit()

    client_h = await register_and_login(http_client, email)
    client_uid = int(decode_access_token(client_h["Authorization"].removeprefix("Bearer ").strip()))
    async with _db.AsyncSessionLocal() as db:
        rc = RssiClient(
            consultant_user_id=consultant_id,
            client_user_id=client_uid,
            name="Client portail",
            status="active",
        )
        db.add(rc)
        await db.flush()
        d = RssiDeliverable(
            client_id=rc.id,
            title="Rapport",
            doc_type="rapport",
            file_url=cle,
            delivered_at=datetime.now(UTC).date(),
        )
        db.add(d)
        await db.flush()
        deliverable_id = d.id
        await db.commit()
    return client_h, deliverable_id


@pytest.mark.asyncio
async def test_portail_refuse_un_fichier_non_sain(http_client: AsyncClient):
    import app.core.database as _db_mod
    from app.services import depot_service

    cle = "rssi-deliverables/9/9/portail-infecte.pdf"
    client_h, deliverable_id = await _client_du_portail(http_client, "portail_av@test.com", cle)
    async with _db_mod.AsyncSessionLocal() as db:
        await depot_service.enregistrer_depot(
            db,
            cle_stockage=cle,
            nom_original="portail-infecte.pdf",
            taille_octets=10,
            type_mime="application/pdf",
            depose_par_id=1,
        )
        await depot_service.enregistrer_verdict(db, cle_stockage=cle, sain=False)

    r = await http_client.get(
        f"{BASE}/portal/deliverables/{deliverable_id}/download", headers=client_h
    )
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_portail_delivre_un_fichier_sain(http_client: AsyncClient):
    import app.core.database as _db_mod
    from app.services import depot_service

    cle = "rssi-deliverables/9/9/portail-sain.pdf"
    client_h, deliverable_id = await _client_du_portail(http_client, "portail_ok@test.com", cle)
    async with _db_mod.AsyncSessionLocal() as db:
        await depot_service.enregistrer_depot(
            db,
            cle_stockage=cle,
            nom_original="portail-sain.pdf",
            taille_octets=10,
            type_mime="application/pdf",
            depose_par_id=1,
        )

    r = await http_client.get(
        f"{BASE}/portal/deliverables/{deliverable_id}/download", headers=client_h
    )
    assert r.status_code == 200, r.text


# ── Service ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verdict_sur_cle_inconnue_ne_cree_rien(http_client: AsyncClient):
    """Un verdict portant sur un objet non enregistre ne doit pas creer de ligne.

    Ce serait accepter comme source de verite un appel dont on ne maitrise pas
    l'origine.
    """
    from sqlalchemy import func, select

    import app.core.database as _db_mod
    from app.models.fichier_depose import FichierDepose
    from app.services import depot_service

    async with _db_mod.AsyncSessionLocal() as db:
        avant = (await db.execute(select(func.count(FichierDepose.id)))).scalar_one()
        resultat = await depot_service.enregistrer_verdict(
            db, cle_stockage="cle/qui/n/existe/pas", sain=True
        )
        apres = (await db.execute(select(func.count(FichierDepose.id)))).scalar_one()
    assert resultat is None
    assert avant == apres


@pytest.mark.asyncio
async def test_verdict_horodate_l_analyse(http_client: AsyncClient):
    import app.core.database as _db_mod
    from app.services import depot_service

    h = await _auth_consultant(http_client, "av_horodate@test.com")
    _, cle, _ = await _client_et_depot(http_client, h)

    async with _db_mod.AsyncSessionLocal() as db:
        avant = await depot_service.fichier_par_cle(db, cle)
        assert avant.analyse_le is None
        apres = await depot_service.enregistrer_verdict(db, cle_stockage=cle, sain=True)
    assert apres.statut_analyse == StatutAnalyse.SAIN
    assert apres.analyse_le is not None


@pytest.mark.asyncio
async def test_somme_des_octets_par_client(http_client: AsyncClient):
    """Socle du futur quota : sans registre, rien a sommer."""
    import app.core.database as _db_mod
    from app.services import depot_service

    h = await _auth_consultant(http_client, "av_quota@test.com")
    client_id, _, _ = await _client_et_depot(http_client, h)

    async with _db_mod.AsyncSessionLocal() as db:
        total = await depot_service.octets_deposes_par_client(db, client_id)
    assert total == len(_PDF)


@pytest.mark.asyncio
async def test_antivirus_actif_met_le_depot_en_analyse(http_client: AsyncClient, monkeypatch):
    """Le reglage commande bien l'etat initial."""
    from app.services import depot_service

    monkeypatch.setattr(depot_service.settings, "ANTIVIRUS_DEPOT_ACTIF", True)
    assert depot_service.statut_a_l_enregistrement() == StatutAnalyse.EN_ANALYSE
    monkeypatch.setattr(depot_service.settings, "ANTIVIRUS_DEPOT_ACTIF", False)
    assert depot_service.statut_a_l_enregistrement() == StatutAnalyse.SAIN
