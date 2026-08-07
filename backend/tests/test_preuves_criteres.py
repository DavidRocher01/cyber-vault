"""Pieces justificatives rattachees aux criteres NIS2 — etape 5c.

CE QUE CES TESTS PROTEGENT. Rattacher une piece a un critere change son sort
vis-a-vis de DEUX purges qui tournent toutes les nuits, et l'une d'elles aurait
efface la piece d'un abonne direct au bout de SEPT JOURS — parce qu'elle ne
considerait comme reference que ce qui figure dans `RssiDeliverable.file_url`, ce
dont un abonne hors RSSI n'a par construction aucun.

L'exemption a une limite, et un test la fixe : elle protege des purges liees au
TEMPS, pas du droit a l'effacement. Rattacher une piece ne doit pas devenir un
moyen de retenir des donnees malgre une demande de suppression de compte.

Cf. `docs/DEPOT_DOCUMENTS.md`, cadrage de l'etape 5.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.enums import OrigineDepot
from app.models.fichier_depose import FichierDepose
from app.models.preuve_critere import PreuveCritere
from app.models.rssi_client import RssiClient
from app.models.rssi_deliverable import RssiDeliverable
from app.services import depot_service, nis2_service, preuve_service

MAINTENANT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)


async def _un_utilisateur(db) -> int:
    from app.core.security import hash_password
    from app.models.user import User

    u = User(
        email=f"preuve{datetime.now(UTC).timestamp()}@test.com",
        hashed_password=hash_password("StrongPass123!"),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u.id


async def _un_client(db, uid: int, close_depuis_jours: int | None = None) -> RssiClient:
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


async def _un_fichier(db, uid: int, cle: str, *, client_id=None, taille=100, age_jours=30):
    f = FichierDepose(
        cle_stockage=cle,
        nom_original="preuve.pdf",
        taille_octets=taille,
        type_mime="application/pdf",
        depose_par_id=uid,
        client_id=client_id,
        statut_analyse="sain",
        depose_le=MAINTENANT - timedelta(days=age_jours),
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


async def _une_evaluation(db, uid: int, client_id=None):
    return await nis2_service.upsert_assessment(
        db, uid, items={"rssi": "compliant"}, score=50, now=MAINTENANT, client_id=client_id
    )


async def _existe_fichier(db, cle: str) -> bool:
    r = await db.execute(select(FichierDepose).where(FichierDepose.cle_stockage == cle))
    return r.scalar_one_or_none() is not None


# ── La purge des orphelins : LE piege du parcours abonne direct ────────────────


@pytest.mark.asyncio
async def test_une_piece_rattachee_n_est_pas_orpheline(db_session):
    """SANS CE COMPORTEMENT, LE PARCOURS ABONNE DIRECT EST IMPOSSIBLE.

    Il n'a aucun `RssiDeliverable` : sa piece etait orpheline des le depot, et
    cette purge l'aurait effacee au bout de sept jours.
    """
    uid = await _un_utilisateur(db_session)
    fichier = await _un_fichier(db_session, uid, "cle/preuve-b2c.pdf", age_jours=60)
    evaluation = await _une_evaluation(db_session, uid)
    await preuve_service.rattacher(
        db_session,
        assessment_id=evaluation.id,
        item_id="rssi",
        fichier_id=fichier.id,
        now=MAINTENANT,
    )

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_orphelins(db_session, MAINTENANT)

    assert n == 0
    efface.assert_not_called()
    assert await _existe_fichier(db_session, "cle/preuve-b2c.pdf")


@pytest.mark.asyncio
async def test_un_fichier_sans_rattachement_reste_purge(db_session):
    """La garde ne doit pas epargner tout le monde au passage."""
    uid = await _un_utilisateur(db_session)
    await _un_fichier(db_session, uid, "cle/vraiment-orphelin.pdf", age_jours=60)

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_orphelins(db_session, MAINTENANT)

    assert n == 1
    efface.assert_called_once_with("cle/vraiment-orphelin.pdf")
    assert not await _existe_fichier(db_session, "cle/vraiment-orphelin.pdf")


# ── La retention a 90 jours : une preuve change de finalite ───────────────────


async def _livrable_client(db, client, cle: str | None) -> RssiDeliverable:
    livrable = RssiDeliverable(
        client_id=client.id,
        title="Document",
        doc_type="autre",
        file_url=cle,
        delivered_at=date(2025, 1, 1),
        origine=OrigineDepot.CLIENT,
    )
    db.add(livrable)
    await db.commit()
    await db.refresh(livrable)
    return livrable


@pytest.mark.asyncio
async def test_une_piece_rattachee_echappe_a_la_purge_des_90_jours(db_session):
    """Rattacher change la finalite : la piece devient un element du dossier."""
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, close_depuis_jours=200)
    fichier = await _un_fichier(db_session, uid, "cle/preuve-client.pdf", client_id=client.id)
    await _livrable_client(db_session, client, "cle/preuve-client.pdf")

    evaluation = await _une_evaluation(db_session, uid, client_id=client.id)
    await preuve_service.rattacher(
        db_session,
        assessment_id=evaluation.id,
        item_id="policy",
        fichier_id=fichier.id,
        now=MAINTENANT,
    )

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 0
    efface.assert_not_called()
    assert await _existe_fichier(db_session, "cle/preuve-client.pdf")


@pytest.mark.asyncio
async def test_un_document_client_non_rattache_reste_purge(db_session):
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, close_depuis_jours=200)
    await _un_fichier(db_session, uid, "cle/ordinaire.pdf", client_id=client.id)
    await _livrable_client(db_session, client, "cle/ordinaire.pdf")

    with patch("app.services.storage.supprimer_fichier") as efface:
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 1
    efface.assert_called_once_with("cle/ordinaire.pdf")


@pytest.mark.asyncio
async def test_un_livrable_sans_fichier_reste_purge(db_session):
    """LE PIEGE SQL QUE `exists()` EVITE.

    Avec un `not_in`, un `file_url` a NULL aurait rendu NULL — donc ni vrai ni
    faux — et le livrable aurait ete epargne par accident, sans que personne ne
    l'ait decide.
    """
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, close_depuis_jours=200)
    livrable = await _livrable_client(db_session, client, None)

    with patch("app.services.storage.supprimer_fichier"):
        n = await depot_service.purger_documents_clients_clos(db_session, MAINTENANT)

    assert n == 1
    r = await db_session.execute(select(RssiDeliverable).where(RssiDeliverable.id == livrable.id))
    assert r.scalar_one_or_none() is None


# ── Le quota : un abonne direct n en avait aucun ──────────────────────────────


@pytest.mark.asyncio
async def test_le_quota_compte_ce_que_l_abonne_depose_pour_lui_meme(db_session):
    uid = await _un_utilisateur(db_session)
    await _un_fichier(db_session, uid, "cle/q1.pdf", taille=400)

    assert await depot_service.octets_deposes_par_compte(db_session, uid) == 400


@pytest.mark.asyncio
async def test_le_stockage_des_clients_ne_pese_pas_sur_le_quota_du_consultant(db_session):
    """Sinon l'activite de ses clients bloquerait son propre depot."""
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid)
    await _un_fichier(db_session, uid, "cle/sien.pdf", taille=100)
    await _un_fichier(db_session, uid, "cle/du-client.pdf", client_id=client.id, taille=9000)

    assert await depot_service.octets_deposes_par_compte(db_session, uid) == 100


@pytest.mark.asyncio
async def test_le_quota_par_compte_refuse_au_dela_du_plafond(db_session):
    from app.core.config import settings

    uid = await _un_utilisateur(db_session)
    await _un_fichier(db_session, uid, "cle/plein.pdf", taille=settings.QUOTA_DEPOT_CLIENT_OCTETS)

    with pytest.raises(depot_service.QuotaDepassementError):
        await depot_service.verifier_quota(db_session, 1, user_id=uid)


@pytest.mark.asyncio
async def test_le_perimetre_du_quota_doit_etre_explicite(db_session):
    """Ni deux perimetres, ni aucun : le deviner produirait un plafond faux."""
    with pytest.raises(ValueError):
        await depot_service.verifier_quota(db_session, 1)
    with pytest.raises(ValueError):
        await depot_service.verifier_quota(db_session, 1, client_id=1, user_id=1)


# ── La suppression de compte : la limite de l exemption ───────────────────────


@pytest.mark.asyncio
async def test_supprimer_un_compte_efface_ses_objets_stockes(db_session):
    """La cascade de la base ne sait rien de S3."""
    from app.models.user import User
    from app.services import user_service

    uid = await _un_utilisateur(db_session)
    await _un_fichier(db_session, uid, "cle/a-moi.pdf")
    user = await db_session.get(User, uid)

    with patch("app.services.storage.supprimer_fichier") as efface:
        await user_service.delete_account(db_session, user)

    efface.assert_called_once_with("cle/a-moi.pdf")
    assert not await _existe_fichier(db_session, "cle/a-moi.pdf")


@pytest.mark.asyncio
async def test_supprimer_un_compte_efface_les_fichiers_de_ses_clients(db_session):
    """`consultant_user_id` est en CASCADE : sans cela, plus rien ne les designe."""
    from app.models.user import User
    from app.services import user_service

    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid)
    await _un_fichier(db_session, uid, "cle/du-suivi.pdf", client_id=client.id)
    user = await db_session.get(User, uid)

    with patch("app.services.storage.supprimer_fichier") as efface:
        await user_service.delete_account(db_session, user)

    efface.assert_any_call("cle/du-suivi.pdf")
    assert not await _existe_fichier(db_session, "cle/du-suivi.pdf")


@pytest.mark.asyncio
async def test_une_piece_rattachee_n_echappe_pas_au_droit_a_l_effacement(db_session):
    """LA LIMITE DE L'EXEMPTION, ET ELLE EST ESSENTIELLE.

    L'exemption protege les preuves des purges liees au TEMPS. Si elle valait
    aussi contre une demande de suppression de compte, rattacher une piece
    deviendrait un moyen de retenir des donnees malgre l'exercice d'un droit.
    """
    from app.models.user import User
    from app.services import user_service

    uid = await _un_utilisateur(db_session)
    fichier = await _un_fichier(db_session, uid, "cle/preuve-a-effacer.pdf")
    evaluation = await _une_evaluation(db_session, uid)
    await preuve_service.rattacher(
        db_session,
        assessment_id=evaluation.id,
        item_id="rssi",
        fichier_id=fichier.id,
        now=MAINTENANT,
    )
    user = await db_session.get(User, uid)

    with patch("app.services.storage.supprimer_fichier") as efface:
        await user_service.delete_account(db_session, user)

    efface.assert_called_once_with("cle/preuve-a-effacer.pdf")
    assert not await _existe_fichier(db_session, "cle/preuve-a-effacer.pdf")


@pytest.mark.asyncio
async def test_si_l_objet_resiste_la_ligne_est_conservee(db_session):
    """Perdre la trace d'un fichier qu'on n'a pas su effacer le condamne a rester."""
    from app.models.user import User
    from app.services import user_service

    uid = await _un_utilisateur(db_session)
    await _un_fichier(db_session, uid, "cle/recalcitrant.pdf")
    user = await db_session.get(User, uid)

    with patch("app.services.storage.supprimer_fichier", side_effect=OSError("S3 injoignable")):
        await user_service.delete_account(db_session, user)

    assert await _existe_fichier(db_session, "cle/recalcitrant.pdf")


# ── Le rattachement lui-meme ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_critere_inconnu_est_refuse(db_session):
    """Sans ce controle, la piece serait invisible ET imperissable."""
    uid = await _un_utilisateur(db_session)
    fichier = await _un_fichier(db_session, uid, "cle/x.pdf")
    evaluation = await _une_evaluation(db_session, uid)

    with pytest.raises(preuve_service.CritereInconnuError):
        await preuve_service.rattacher(
            db_session,
            assessment_id=evaluation.id,
            item_id="critere_qui_n_existe_pas",
            fichier_id=fichier.id,
            now=MAINTENANT,
        )


@pytest.mark.asyncio
async def test_rattacher_deux_fois_ne_leve_pas(db_session):
    """Un double-clic ne doit pas produire une erreur ininterpretable."""
    uid = await _un_utilisateur(db_session)
    fichier = await _un_fichier(db_session, uid, "cle/y.pdf")
    evaluation = await _une_evaluation(db_session, uid)

    a = await preuve_service.rattacher(
        db_session,
        assessment_id=evaluation.id,
        item_id="rssi",
        fichier_id=fichier.id,
        now=MAINTENANT,
    )
    b = await preuve_service.rattacher(
        db_session,
        assessment_id=evaluation.id,
        item_id="rssi",
        fichier_id=fichier.id,
        now=MAINTENANT,
    )
    assert a.id == b.id


@pytest.mark.asyncio
async def test_on_ne_detache_pas_une_piece_du_dossier_d_un_autre(db_session):
    """Sinon connaitre un identifiant suffirait a defaire le dossier d'autrui."""
    uid = await _un_utilisateur(db_session)
    autre = await _un_utilisateur(db_session)
    fichier = await _un_fichier(db_session, uid, "cle/z.pdf")
    evaluation = await _une_evaluation(db_session, uid)
    evaluation_autre = await _une_evaluation(db_session, autre)

    preuve = await preuve_service.rattacher(
        db_session,
        assessment_id=evaluation.id,
        item_id="rssi",
        fichier_id=fichier.id,
        now=MAINTENANT,
    )

    assert not await preuve_service.detacher(
        db_session, assessment_id=evaluation_autre.id, preuve_id=preuve.id
    )
    reste = await db_session.execute(select(PreuveCritere).where(PreuveCritere.id == preuve.id))
    assert reste.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_detacher_ne_supprime_pas_le_fichier(db_session):
    """Detacher dit « cette piece ne justifie pas ce critere », pas « effacez-la »."""
    uid = await _un_utilisateur(db_session)
    fichier = await _un_fichier(db_session, uid, "cle/w.pdf")
    evaluation = await _une_evaluation(db_session, uid)
    preuve = await preuve_service.rattacher(
        db_session,
        assessment_id=evaluation.id,
        item_id="rssi",
        fichier_id=fichier.id,
        now=MAINTENANT,
    )

    assert await preuve_service.detacher(
        db_session, assessment_id=evaluation.id, preuve_id=preuve.id
    )
    assert await _existe_fichier(db_session, "cle/w.pdf")


@pytest.mark.asyncio
async def test_les_preuves_sont_regroupees_par_critere(db_session):
    uid = await _un_utilisateur(db_session)
    evaluation = await _une_evaluation(db_session, uid)
    for i, critere in enumerate(("rssi", "rssi", "policy")):
        f = await _un_fichier(db_session, uid, f"cle/g{i}.pdf")
        await preuve_service.rattacher(
            db_session,
            assessment_id=evaluation.id,
            item_id=critere,
            fichier_id=f.id,
            now=MAINTENANT,
        )

    groupes = await preuve_service.preuves_par_critere(db_session, evaluation.id)
    assert len(groupes["rssi"]) == 2
    assert len(groupes["policy"]) == 1
    assert groupes["rssi"][0]["statut_analyse"] == "sain"
