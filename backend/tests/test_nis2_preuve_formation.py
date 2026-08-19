"""
Tests — boucle de retour entre les deux produits NIS2.

L'auto-évaluation demande « vos employés suivent-ils une formation cyber ? »
alors que la plateforme connaît déjà la réponse pour les clients qui utilisent
l'e-learning. `preuve_formation()` fournit cette mesure.

Principe testé ici autant que le calcul : la mesure ne REMPLIT PAS le
questionnaire. Une auto-évaluation remplie automatiquement n'est plus une
déclaration et perdrait sa valeur devant un auditeur.
"""

import pytest

from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization
from app.models.awareness_program import AwarenessProgram
from app.models.user import User
from app.services.awareness.nis2_report import preuve_formation


async def _user(db, email="patron@acme.fr"):
    u = User(email=email, hashed_password="x")
    db.add(u)
    await db.flush()
    return u


async def _org(db, user, nom="Acme"):
    o = AwarenessOrganization(owner_user_id=user.id, name=nom, max_learners=50)
    db.add(o)
    await db.flush()
    return o


async def _programme(db, slug="nis2-essentiel"):
    p = AwarenessProgram(
        slug=slug, title="NIS2 Essentiel", passing_score=60, certificate_validity_months=12
    )
    db.add(p)
    await db.flush()
    return p


async def _apprenant(db, org, email):
    a = AwarenessLearner(organization_id=org.id, email=email, first_name="A", last_name="B")
    db.add(a)
    await db.flush()
    return a


async def _inscription(db, apprenant, prog, org, statut):
    e = AwarenessEnrollment(
        learner_id=apprenant.id, program_id=prog.id, organization_id=org.id, status=statut
    )
    db.add(e)
    await db.flush()
    return e


@pytest.mark.asyncio
async def test_aucune_organisation_ne_produit_aucune_preuve(db_session):
    """Un utilisateur sans e-learning n'a pas de preuve « à zéro » : il n'a rien
    à mesurer. Afficher « 0 % formés » serait faux et culpabilisant."""
    u = await _user(db_session)
    assert await preuve_formation(db_session, u.id) is None


@pytest.mark.asyncio
async def test_organisation_sans_apprenant(db_session):
    u = await _user(db_session, "vide@acme.fr")
    await _org(db_session, u)
    p = await preuve_formation(db_session, u.id)
    assert p == {"organisations": 1, "apprenants": 0, "termines": 0, "pct": 0.0}


@pytest.mark.asyncio
async def test_mesure_les_apprenants_ayant_termine(db_session):
    u = await _user(db_session, "mesure@acme.fr")
    org = await _org(db_session, u)
    prog = await _programme(db_session)

    a1 = await _apprenant(db_session, org, "a1@acme.fr")
    a2 = await _apprenant(db_session, org, "a2@acme.fr")
    a3 = await _apprenant(db_session, org, "a3@acme.fr")
    a4 = await _apprenant(db_session, org, "a4@acme.fr")

    await _inscription(db_session, a1, prog, org, "completed")
    await _inscription(db_session, a2, prog, org, "completed")
    await _inscription(db_session, a3, prog, org, "in_progress")
    await _inscription(db_session, a4, prog, org, "pending")

    p = await preuve_formation(db_session, u.id)
    assert p == {"organisations": 1, "apprenants": 4, "termines": 2, "pct": 50.0}


@pytest.mark.asyncio
async def test_un_apprenant_compte_une_seule_fois(db_session):
    """On mesure des PERSONNES formées, pas des inscriptions : quelqu'un qui
    termine deux parcours ne vaut pas deux salariés formés."""
    u = await _user(db_session, "double@acme.fr")
    org = await _org(db_session, u)
    p1 = await _programme(db_session, "nis2-essentiel")
    p2 = await _programme(db_session, "nis2-technique")

    a = await _apprenant(db_session, org, "solo@acme.fr")
    await _inscription(db_session, a, p1, org, "completed")
    await _inscription(db_session, a, p2, org, "completed")

    preuve = await preuve_formation(db_session, u.id)
    assert preuve["apprenants"] == 1
    assert preuve["termines"] == 1
    assert preuve["pct"] == 100.0


@pytest.mark.asyncio
async def test_agrege_plusieurs_organisations(db_session):
    """Cas du consultant RSSI : il pilote la formation de plusieurs clients."""
    u = await _user(db_session, "consultant@rssi.fr")
    o1 = await _org(db_session, u, "Client 1")
    o2 = await _org(db_session, u, "Client 2")
    prog = await _programme(db_session)

    a1 = await _apprenant(db_session, o1, "c1@x.fr")
    a2 = await _apprenant(db_session, o2, "c2@x.fr")
    await _inscription(db_session, a1, prog, o1, "completed")
    await _inscription(db_session, a2, prog, o2, "pending")

    p = await preuve_formation(db_session, u.id)
    assert p["organisations"] == 2
    assert p["apprenants"] == 2
    assert p["termines"] == 1


@pytest.mark.asyncio
async def test_ignore_les_organisations_d_un_autre_utilisateur(db_session):
    u1 = await _user(db_session, "moi@acme.fr")
    u2 = await _user(db_session, "autre@acme.fr")
    org2 = await _org(db_session, u2, "Org de l'autre")
    prog = await _programme(db_session)
    a = await _apprenant(db_session, org2, "x@autre.fr")
    await _inscription(db_session, a, prog, org2, "completed")

    assert await preuve_formation(db_session, u1.id) is None


@pytest.mark.asyncio
async def test_la_preuve_ne_remplit_pas_le_questionnaire(db_session, http_client):
    """Garde-fou du principe : même avec 100 % de salariés formés, l'item reste
    à déclarer par l'utilisateur. Une auto-évaluation pré-remplie n'est plus une
    déclaration."""
    from tests.conftest import register_and_login

    headers = await register_and_login(http_client, "declare@acme.fr")
    me = await http_client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    import app.core.database as db_mod

    async with db_mod.AsyncSessionLocal() as s:
        org = AwarenessOrganization(owner_user_id=user_id, name="Acme", max_learners=10)
        s.add(org)
        await s.flush()
        prog = AwarenessProgram(
            slug="nis2-essentiel",
            title="NIS2",
            passing_score=60,
            certificate_validity_months=12,
        )
        s.add(prog)
        await s.flush()
        app_ = AwarenessLearner(
            organization_id=org.id, email="f@acme.fr", first_name="F", last_name="G"
        )
        s.add(app_)
        await s.flush()
        s.add(
            AwarenessEnrollment(
                learner_id=app_.id,
                program_id=prog.id,
                organization_id=org.id,
                status="completed",
            )
        )
        await s.commit()

    r = await http_client.get("/api/v1/nis2/me", headers=headers)
    corps = r.json()

    assert corps["preuves"]["awareness"]["pct"] == 100.0, "la mesure doit remonter"
    assert corps["items"] == {}, "aucun item ne doit avoir ete rempli automatiquement"
    assert corps["score"] == 0, "le score reste celui de la declaration, pas de la mesure"
