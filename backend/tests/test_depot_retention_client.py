"""Retention des documents remis par le client — etape 4b.

CE CODE DETRUIT DES DONNEES. Les tests portent donc autant sur ce qu'il efface
que sur ce qu'il DOIT epargner.

LES DEUX REGIMES, ET POURQUOI ILS SONT OPPOSES :

- Un document remis par le CLIENT releve de la sous-traitance. Article 28-3-g du
  RGPD : a la fin de la prestation, le sous-traitant efface OU RESTITUE, au
  choix du responsable de traitement. Le delai de 90 jours EST la restitution
  possible — le portail reste accessible apres la cloture, donc le client peut
  recuperer ses documents pendant toute cette periode.

- Un livrable produit par le CONSULTANT est sa preuve en cas de litige sur la
  qualite de la prestation. Prescription de droit commun : cinq ans. Le purger
  reviendrait a detruire sa propre defense.

C'est le champ `origine` qui separe les deux, et c'est toute sa raison d'etre.
Cf. `docs/DEPOT_DOCUMENTS.md`.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest

from app.models.enums import OrigineDepot
from app.models.fichier_depose import FichierDepose
from app.models.rssi_client import RssiClient
from app.models.rssi_deliverable import RssiDeliverable
from app.services import depot_service

MAINTENANT = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)


async def _un_utilisateur(db) -> int:
    from app.core.security import hash_password
    from app.models.user import User

    u = User(
        email=f"ret{datetime.now(UTC).timestamp()}@test.com",
        hashed_password=hash_password("StrongPass123!"),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u.id


async def _mission(db, uid: int, close_depuis_jours: int | None) -> RssiClient:
    """Cree un client RSSI. `close_depuis_jours=None` => mission active."""
    c = RssiClient(
        consultant_user_id=uid,
        name="Client",
        status="active" if close_depuis_jours is None else "churned",
        cloture_le=None
        if close_depuis_jours is None
        else MAINTENANT - timedelta(days=close_depuis_jours),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def _document(db, client: RssiClient, uid: int, origine: str, cle: str) -> RssiDeliverable:
    """Un livrable AVEC son fichier au registre."""
    db.add(
        FichierDepose(
            cle_stockage=cle,
            nom_original="d.pdf",
            taille_octets=100,
            type_mime="application/pdf",
            depose_par_id=uid,
            client_id=client.id,
            statut_analyse="sain",
            depose_le=MAINTENANT - timedelta(days=400),
        )
    )
    livrable = RssiDeliverable(
        client_id=client.id,
        title="Document",
        doc_type="autre",
        file_url=cle,
        delivered_at=date(2025, 1, 1),
        origine=origine,
    )
    db.add(livrable)
    await db.commit()
    await db.refresh(livrable)
    return livrable


async def _existe(db, livrable_id: int) -> bool:
    from sqlalchemy import select

    r = await db.execute(select(RssiDeliverable).where(RssiDeliverable.id == livrable_id))
    return r.scalar_one_or_none() is not None


# ── Ce qui est efface ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_document_client_efface_apres_le_delai(db_session):
    uid = await _un_utilisateur(db_session)
    mission = await _mission(db_session, uid, close_depuis_jours=120)
    doc = await _document(db_session, mission, uid, OrigineDepot.CLIENT, "cle/client-vieux.pdf")

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 1
    efface.assert_called_once_with("cle/client-vieux.pdf")
    assert not await _existe(db_session, doc.id)
    assert await depot_service.fichier_par_cle(db_session, "cle/client-vieux.pdf") is None


# ── Ce qui doit SURVIVRE — la moitie qui compte le plus ────────────────────────


@pytest.mark.asyncio
async def test_un_livrable_du_consultant_n_est_jamais_purge(db_session):
    """Sa preuve en cas de litige. Le purger detruirait sa propre defense."""
    uid = await _un_utilisateur(db_session)
    mission = await _mission(db_session, uid, close_depuis_jours=3000)  # bien au-dela
    doc = await _document(db_session, mission, uid, OrigineDepot.CONSULTANT, "cle/consultant.pdf")

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 0
    efface.assert_not_called()
    assert await _existe(db_session, doc.id)


@pytest.mark.asyncio
async def test_pendant_le_delai_le_client_peut_encore_recuperer(db_session):
    """Le delai EST la restitution : effacer avant supprimerait sans laisser le choix."""
    uid = await _un_utilisateur(db_session)
    mission = await _mission(db_session, uid, close_depuis_jours=30)
    doc = await _document(db_session, mission, uid, OrigineDepot.CLIENT, "cle/recent.pdf")

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 0
    efface.assert_not_called()
    assert await _existe(db_session, doc.id)
    assert await depot_service.est_telechargeable(db_session, "cle/recent.pdf")


@pytest.mark.asyncio
async def test_une_mission_active_n_est_jamais_purgee(db_session):
    uid = await _un_utilisateur(db_session)
    mission = await _mission(db_session, uid, close_depuis_jours=None)
    doc = await _document(db_session, mission, uid, OrigineDepot.CLIENT, "cle/active.pdf")

    with patch("app.services.storage.supprimer_fichier"):
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 0
    assert await _existe(db_session, doc.id)


@pytest.mark.asyncio
async def test_sans_date_de_cloture_on_n_invente_rien(db_session):
    """Un client au statut clos mais sans date — cas des missions d'avant l'etape 4b.

    On ne detruit pas de donnees sur la foi d'un repere fabrique.
    """
    uid = await _un_utilisateur(db_session)
    c = RssiClient(consultant_user_id=uid, name="Ancien", status="churned", cloture_le=None)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    doc = await _document(db_session, c, uid, OrigineDepot.CLIENT, "cle/sans-date.pdf")

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 0
    efface.assert_not_called()
    assert await _existe(db_session, doc.id)


# ── L'ordre, et la resistance a l'echec ────────────────────────────────────────


@pytest.mark.asyncio
async def test_si_l_objet_resiste_rien_n_est_supprime(db_session):
    """Sinon on perd la trace d'un fichier toujours present sur S3."""
    uid = await _un_utilisateur(db_session)
    mission = await _mission(db_session, uid, close_depuis_jours=120)
    doc = await _document(db_session, mission, uid, OrigineDepot.CLIENT, "cle/recalcitrant.pdf")

    with patch("app.services.storage.supprimer_fichier", side_effect=OSError("S3 injoignable")):
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 0
    assert await _existe(db_session, doc.id), "le livrable a disparu, l'objet est toujours la"
    assert await depot_service.fichier_par_cle(db_session, "cle/recalcitrant.pdf") is not None


@pytest.mark.asyncio
async def test_un_echec_n_interrompt_pas_les_autres(db_session):
    uid = await _un_utilisateur(db_session)
    mission = await _mission(db_session, uid, close_depuis_jours=120)
    ko = await _document(db_session, mission, uid, OrigineDepot.CLIENT, "cle/ko.pdf")
    ok = await _document(db_session, mission, uid, OrigineDepot.CLIENT, "cle/ok.pdf")

    def efface(cle: str) -> None:
        if cle.endswith("ko.pdf"):
            raise OSError("S3 injoignable")

    with patch("app.services.storage.supprimer_fichier", side_effect=efface):
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 1
    assert await _existe(db_session, ko.id)
    assert not await _existe(db_session, ok.id)


# ── La date de cloture, posee au bon moment ────────────────────────────────────


@pytest.mark.asyncio
async def test_la_cloture_se_pose_au_passage_en_churned(db_session):
    from app.services.rssi import client_service

    uid = await _un_utilisateur(db_session)
    c = await _mission(db_session, uid, close_depuis_jours=None)
    assert c.cloture_le is None

    await client_service.update_client(db_session, c, {"status": "churned"})
    assert c.cloture_le is not None


@pytest.mark.asyncio
async def test_la_cloture_s_efface_si_la_mission_reprend(db_session):
    """Un client repris ne doit pas voir ses documents purges sur la foi d'une
    interruption passee."""
    from app.services.rssi import client_service

    uid = await _un_utilisateur(db_session)
    c = await _mission(db_session, uid, close_depuis_jours=120)
    assert c.cloture_le is not None

    await client_service.update_client(db_session, c, {"status": "active"})
    assert c.cloture_le is None


@pytest.mark.asyncio
async def test_la_cloture_ne_se_repousse_pas_a_chaque_modification(db_session):
    """LE piege qu'evite une colonne dediee.

    Avec `updated_at`, une simple correction d'adresse aurait repousse
    l'echeance de 90 jours a chaque fois — et rien n'aurait jamais ete purge.
    """
    from app.services.rssi import client_service

    uid = await _un_utilisateur(db_session)
    c = await _mission(db_session, uid, close_depuis_jours=60)
    initiale = c.cloture_le

    await client_service.update_client(db_session, c, {"name": "Nouveau nom"})
    assert c.cloture_le == initiale


# ── Le job nocturne ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_le_job_de_retention_compte_les_documents_clients(db_session):
    from app.services.scheduler.retention import purge_expired_data

    uid = await _un_utilisateur(db_session)
    mission = await _mission(db_session, uid, close_depuis_jours=200)
    await _document(db_session, mission, uid, OrigineDepot.CLIENT, "cle/nocturne.pdf")

    with patch("app.services.storage.supprimer_fichier"):
        counts = await purge_expired_data(db_session, MAINTENANT)

    assert counts["documents_clients"] == 1
