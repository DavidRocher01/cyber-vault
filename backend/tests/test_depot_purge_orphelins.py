"""Purge des fichiers deposes que plus aucun livrable ne reference.

CE QU'EST UN ORPHELIN. Le depot rend une cle de stockage, puis un second appel
cree le livrable qui la reference. Si ce second appel n'arrive jamais — onglet
ferme, erreur reseau, abandon — le fichier reste sur S3 sans finalite. C'est le
cas le plus simple de l'article 5-1-e du RGPD, et le seul des trois regimes de
retention qui ne prete a aucune discussion (cf. docs/DEPOT_DOCUMENTS.md).

CE QUE CES TESTS PROTEGENT EN PRIORITE. L'ORDRE des deux suppressions. On efface
l'objet stocke, PUIS la ligne. Si l'objet resiste, la ligne doit rester pour que
le passage suivant reessaie — sinon on perd la trace d'un fichier toujours
present sur S3, soit exactement le probleme que ce registre a ete cree pour
resoudre, reintroduit par l'autre bout.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.models.fichier_depose import FichierDepose
from app.services import depot_service

MAINTENANT = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


async def _depose(db, cle: str, jours: int, user_id: int) -> FichierDepose:
    """Insere un fichier depose il y a `jours` jours."""
    f = FichierDepose(
        cle_stockage=cle,
        nom_original="doc.pdf",
        taille_octets=1024,
        type_mime="application/pdf",
        depose_par_id=user_id,
        statut_analyse="sain",
        depose_le=MAINTENANT - timedelta(days=jours),
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


async def _un_utilisateur(db) -> int:
    from app.core.security import hash_password
    from app.models.user import User

    u = User(
        email=f"purge{datetime.now(UTC).timestamp()}@test.com",
        hashed_password=hash_password("StrongPass123!"),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u.id


# ── Ce qui est purge, ce qui ne l'est pas ──────────────────────────────────────


@pytest.mark.asyncio
async def test_orphelin_ancien_purge(db_session):
    uid = await _un_utilisateur(db_session)
    await _depose(db_session, "uploads/rssi/1/1/orphelin.pdf", jours=10, user_id=uid)

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_orphelins(db_session, MAINTENANT)

    assert n == 1
    efface.assert_called_once_with("uploads/rssi/1/1/orphelin.pdf")
    assert await depot_service.fichier_par_cle(db_session, "uploads/rssi/1/1/orphelin.pdf") is None


@pytest.mark.asyncio
async def test_orphelin_recent_conserve(db_session):
    """Le delai de grace protege le flux normal depot -> creation du livrable."""
    uid = await _un_utilisateur(db_session)
    await _depose(db_session, "uploads/rssi/1/1/frais.pdf", jours=2, user_id=uid)

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_orphelins(db_session, MAINTENANT)

    assert n == 0
    efface.assert_not_called()
    assert await depot_service.fichier_par_cle(db_session, "uploads/rssi/1/1/frais.pdf")


@pytest.mark.asyncio
async def test_fichier_reference_par_un_livrable_jamais_purge(db_session):
    """Meme tres ancien : il est rattache, donc il a une finalite."""
    from datetime import date

    from app.models.rssi_client import RssiClient
    from app.models.rssi_deliverable import RssiDeliverable

    uid = await _un_utilisateur(db_session)
    cle = "uploads/rssi/1/1/rattache.pdf"
    await _depose(db_session, cle, jours=400, user_id=uid)

    client = RssiClient(consultant_user_id=uid, name="Client", status="active")
    db_session.add(client)
    await db_session.flush()
    db_session.add(
        RssiDeliverable(
            client_id=client.id,
            title="Rapport",
            doc_type="rapport",
            file_url=cle,
            delivered_at=date(2026, 1, 1),
        )
    )
    await db_session.commit()

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_orphelins(db_session, MAINTENANT)

    assert n == 0
    efface.assert_not_called()
    assert await depot_service.fichier_par_cle(db_session, cle)


# ── L'ordre, et la resistance a l'echec ────────────────────────────────────────


@pytest.mark.asyncio
async def test_echec_de_suppression_conserve_la_ligne(db_session):
    """LE test qui compte.

    Si l'objet n'a pas pu etre efface, la ligne DOIT rester : c'est elle qui
    permettra de reessayer. La supprimer laisserait un fichier sur S3 dont plus
    rien ne garde trace.
    """
    uid = await _un_utilisateur(db_session)
    cle = "uploads/rssi/1/1/recalcitrant.pdf"
    await _depose(db_session, cle, jours=10, user_id=uid)

    with patch("app.services.storage.supprimer_fichier", side_effect=OSError("S3 injoignable")):
        n = await depot_service.purger_orphelins(db_session, MAINTENANT)

    assert n == 0
    assert await depot_service.fichier_par_cle(db_session, cle), (
        "la ligne a ete supprimee alors que l'objet est toujours la"
    )


@pytest.mark.asyncio
async def test_un_echec_n_interrompt_pas_les_autres(db_session):
    uid = await _un_utilisateur(db_session)
    await _depose(db_session, "uploads/rssi/1/1/ko.pdf", jours=10, user_id=uid)
    await _depose(db_session, "uploads/rssi/1/1/ok.pdf", jours=10, user_id=uid)

    def efface(cle: str) -> None:
        if cle.endswith("ko.pdf"):
            raise OSError("S3 injoignable")

    with patch("app.services.storage.supprimer_fichier", side_effect=efface):
        n = await depot_service.purger_orphelins(db_session, MAINTENANT)

    assert n == 1
    assert await depot_service.fichier_par_cle(db_session, "uploads/rssi/1/1/ko.pdf")
    assert await depot_service.fichier_par_cle(db_session, "uploads/rssi/1/1/ok.pdf") is None


# ── Le job nocturne ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_le_job_de_retention_compte_les_orphelins(db_session):
    from app.services.scheduler.retention import purge_expired_data

    uid = await _un_utilisateur(db_session)
    await _depose(db_session, "uploads/rssi/1/1/nocturne.pdf", jours=30, user_id=uid)

    with patch("app.services.storage.supprimer_fichier"):
        counts = await purge_expired_data(db_session, MAINTENANT)

    assert counts["fichiers_orphelins"] == 1
