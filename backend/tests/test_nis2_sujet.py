"""Une evaluation NIS2 par SUJET, et non plus une par compte — etape 5b.

TROIS SUJETS, UN SEUL MODELE. La colonne `client_id` porte le sujet :

- `NULL` -> mon auto-evaluation. C'est l'abonne qui veut NIS2 seul, sans
  consultant ni RSSI fractionne. Comportement historique, inchange.
- `X`    -> le dossier monte pour le client X, dont un consultant detient
  autant que de clients suivis.

CE QUE CES TESTS PROTEGENT SURTOUT. Le modele d'avant garantissait une seule
ligne par compte, et quatre requetes s'appuyaient dessus avec un
`scalar_one_or_none()`. Des qu'un consultant en detient plusieurs, celles qui
n'ont pas ete rendues conscientes du sujet LEVENT — dont l'export de
portabilite RGPD (art. 20). Ces tests fixent chacune d'elles.

Cf. `docs/DEPOT_DOCUMENTS.md`, cadrage de l'etape 5.
"""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.nis2_assessment import Nis2Assessment
from app.models.rssi_client import RssiClient
from app.services import nis2_service, user_service

MAINTENANT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)


async def _un_utilisateur(db, marqueur: str = "") -> int:
    from app.core.security import hash_password
    from app.models.user import User

    u = User(
        email=f"sujet{marqueur}{datetime.now(UTC).timestamp()}@test.com",
        hashed_password=hash_password("StrongPass123!"),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u.id


async def _un_client(db, consultant_id: int, nom: str) -> RssiClient:
    c = RssiClient(consultant_user_id=consultant_id, name=nom, status="active")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


# ── LE piege : deux NULL ne sont pas distincts ─────────────────────────────────


@pytest.mark.asyncio
async def test_un_compte_ne_peut_avoir_qu_une_auto_evaluation(db_session):
    """LE test de l'etape 5b.

    PostgreSQL considere par defaut deux NULL comme distincts. Sans
    `NULLS NOT DISTINCT`, cette seconde insertion PASSERAIT, et le upsert —
    qui fait un `scalar_one_or_none()` — se mettrait a lever ensuite.
    """
    uid = await _un_utilisateur(db_session)
    db_session.add(Nis2Assessment(user_id=uid, client_id=None, items_json="{}", score=0))
    await db_session.commit()

    db_session.add(Nis2Assessment(user_id=uid, client_id=None, items_json="{}", score=0))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    total = (
        await db_session.execute(
            select(func.count(Nis2Assessment.id)).where(Nis2Assessment.user_id == uid)
        )
    ).scalar_one()
    assert total == 1


@pytest.mark.asyncio
async def test_un_meme_client_ne_peut_avoir_deux_dossiers(db_session):
    """La contrainte doit valoir aussi quand `client_id` est renseigne."""
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, "Client")

    db_session.add(Nis2Assessment(user_id=uid, client_id=client.id, items_json="{}", score=0))
    await db_session.commit()

    db_session.add(Nis2Assessment(user_id=uid, client_id=client.id, items_json="{}", score=0))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


# ── Ce que le nouveau modele rend possible ─────────────────────────────────────


@pytest.mark.asyncio
async def test_un_consultant_detient_un_dossier_par_client(db_session):
    """Ce que le modele d'avant interdisait, et qui est toute la raison de 5b."""
    uid = await _un_utilisateur(db_session)
    a = await _un_client(db_session, uid, "Client A")
    b = await _un_client(db_session, uid, "Client B")

    for client in (a, b):
        await nis2_service.upsert_assessment(
            db_session,
            uid,
            items={"rssi": "compliant"},
            score=50,
            now=MAINTENANT,
            client_id=client.id,
        )

    dossier_a = await nis2_service.get_user_assessment(db_session, uid, a.id)
    dossier_b = await nis2_service.get_user_assessment(db_session, uid, b.id)
    assert dossier_a is not None and dossier_b is not None
    assert dossier_a.id != dossier_b.id


@pytest.mark.asyncio
async def test_l_auto_evaluation_coexiste_avec_les_dossiers_clients(db_session):
    """Le consultant a la sienne, en plus de celles qu'il monte."""
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, "Client")

    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "compliant"}, score=10, now=MAINTENANT
    )
    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "na"}, score=90, now=MAINTENANT, client_id=client.id
    )

    mienne = await nis2_service.get_user_assessment(db_session, uid)
    assert mienne is not None and mienne.score == 10
    assert mienne.client_id is None


@pytest.mark.asyncio
async def test_l_upsert_ne_confond_pas_les_sujets(db_session):
    """Modifier le dossier d'un client ne doit pas ecraser sa propre evaluation."""
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, "Client")

    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "compliant"}, score=10, now=MAINTENANT
    )
    await nis2_service.upsert_assessment(
        db_session,
        uid,
        items={"rssi": "non_compliant"},
        score=99,
        now=MAINTENANT,
        client_id=client.id,
    )

    mienne = await nis2_service.get_user_assessment(db_session, uid)
    assert mienne is not None
    assert mienne.score == 10, "le dossier client a ecrase l'auto-evaluation"
    assert json.loads(mienne.items_json) == {"rssi": "compliant"}


@pytest.mark.asyncio
async def test_sans_client_id_on_retrouve_bien_l_auto_evaluation(db_session):
    """`client_id = NULL` n'est jamais vrai en SQL : il faut `IS NULL`.

    Avec `== None`, la requete ramenerait zero ligne et le upsert creerait une
    seconde auto-evaluation a chaque enregistrement.
    """
    uid = await _un_utilisateur(db_session)
    premier = await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "compliant"}, score=10, now=MAINTENANT
    )
    second = await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "partial"}, score=20, now=MAINTENANT
    )
    assert premier.id == second.id, "une seconde auto-evaluation a ete creee"


# ── Les quatre requetes qui reposaient sur « une seule ligne par compte » ──────


@pytest.mark.asyncio
async def test_l_export_rgpd_ne_casse_pas_pour_un_consultant(db_session):
    """L'EXPORT DE PORTABILITE (art. 20) faisait un `scalar_one_or_none()`.

    Il aurait leve pour tout consultant detenant plus d'une evaluation —
    c'est-a-dire pour les comptes qui se servent le plus du produit.
    """
    from app.models.user import User

    uid = await _un_utilisateur(db_session, "exp")
    user = await db_session.get(User, uid)
    a = await _un_client(db_session, uid, "Client A")
    b = await _un_client(db_session, uid, "Client B")

    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "compliant"}, score=11, now=MAINTENANT
    )
    for client in (a, b):
        await nis2_service.upsert_assessment(
            db_session, uid, items={"rssi": "na"}, score=88, now=MAINTENANT, client_id=client.id
        )

    export = await user_service.export_account_data(db_session, user)

    assert export["nis2_assessment"] is not None
    assert export["nis2_assessment"]["score"] == 11, "l'export a ramene le dossier d'un client"


@pytest.mark.asyncio
async def test_l_export_rgpd_ne_publie_pas_les_donnees_d_un_tiers(db_session):
    """Un dossier de conformite decrit l'entite du CLIENT.

    Le verser dans l'export d'un autre compte publierait les donnees d'un tiers
    dans un fichier de portabilite.
    """
    from app.models.user import User

    uid = await _un_utilisateur(db_session, "tiers")
    user = await db_session.get(User, uid)
    client = await _un_client(db_session, uid, "Client")

    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "compliant"}, score=11, now=MAINTENANT
    )
    await nis2_service.upsert_assessment(
        db_session,
        uid,
        items={"secret_du_client": "non_compliant"},
        score=88,
        now=MAINTENANT,
        client_id=client.id,
    )

    export = await user_service.export_account_data(db_session, user)
    assert "secret_du_client" not in json.dumps(export)


@pytest.mark.asyncio
async def test_le_tableau_de_bord_montre_le_score_du_consultant(db_session):
    """Pas celui d'un de ses clients."""
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, "Client")

    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "compliant"}, score=11, now=MAINTENANT
    )
    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "na"}, score=88, now=MAINTENANT, client_id=client.id
    )

    a = await user_service.get_nis2_for_user(db_session, uid)
    assert a is not None and a.score == 11


# ── Ce qui arrive quand la fiche client disparait ──────────────────────────────


@pytest.mark.asyncio
async def test_supprimer_la_fiche_client_emporte_son_dossier(db_session):
    """CASCADE et non SET NULL.

    Repasser `client_id` a NULL confondrait le dossier avec l'auto-evaluation
    personnelle du consultant — en y versant les reponses d'un tiers — et
    violerait au passage la contrainte d'unicite s'il en avait deja une.
    """
    uid = await _un_utilisateur(db_session)
    client = await _un_client(db_session, uid, "Client")
    await nis2_service.upsert_assessment(
        db_session, uid, items={"rssi": "na"}, score=88, now=MAINTENANT, client_id=client.id
    )

    await db_session.delete(client)
    await db_session.commit()

    restants = (
        await db_session.execute(
            select(func.count(Nis2Assessment.id)).where(Nis2Assessment.user_id == uid)
        )
    ).scalar_one()
    assert restants == 0
