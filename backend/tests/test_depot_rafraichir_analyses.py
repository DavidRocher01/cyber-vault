"""Relecture de la balise GuardDuty pour les fichiers encore en analyse.

POURQUOI RELIRE PLUTOT QU'ECOUTER EventBridge. Celui-ci supposerait une cible :
une Lambda (infrastructure absente du projet), un endpoint HTTP qu'il faudrait
authentifier — sans quoi n'importe qui pourrait annoncer qu'un fichier est sain,
soit le trou meme que ce chantier ferme — ou une file SQS qu'il faudrait
interroger, donc sonder quand meme.

La relecture inverse le sens de la confiance : c'est NOUS qui allons lire, avec
nos propres identifiants IAM. Cf. `docs/DEPOT_DOCUMENTS.md`.

LE TEST QUI GARDE LA CONTRAINTE DE COUT est
`test_aucun_fichier_en_attente_aucun_appel_s3`. La contrainte posee etait « du
moment que la facture n'est pas touchee » : elle devient une assertion, pas une
intention.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.models.enums import StatutAnalyse
from app.models.fichier_depose import FichierDepose
from app.services import depot_service

MAINTENANT = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)


async def _un_utilisateur(db) -> int:
    from app.core.security import hash_password
    from app.models.user import User

    u = User(
        email=f"raf{datetime.now(UTC).timestamp()}@test.com",
        hashed_password=hash_password("StrongPass123!"),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u.id


async def _en_analyse(db, cle: str, uid: int, minutes: int = 1) -> FichierDepose:
    f = FichierDepose(
        cle_stockage=cle,
        nom_original="d.pdf",
        taille_octets=10,
        type_mime="application/pdf",
        depose_par_id=uid,
        statut_analyse=StatutAnalyse.EN_ANALYSE,
        depose_le=MAINTENANT - timedelta(minutes=minutes),
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


# ── La contrainte de cout ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_aucun_fichier_en_attente_aucun_appel_s3(db_session):
    """« Du moment que la facture n'est pas touchee. »

    La tache tourne toutes les 2 minutes. Si elle interrogeait S3 a vide, ce
    serait 21 600 appels par mois pour rien. La requete ne rendant que les
    fichiers `en_analyse`, elle n'en fait aucun.
    """
    with patch("app.services.storage.lire_balise") as lire:
        c = await depot_service.rafraichir_analyses(db_session, MAINTENANT)

    lire.assert_not_called()
    assert c == {"lus": 0, "tranches": 0, "abandonnes": 0}


@pytest.mark.asyncio
async def test_seuls_les_fichiers_en_analyse_sont_interroges(db_session):
    """Un fichier deja tranche ne doit plus jamais etre relu."""
    uid = await _un_utilisateur(db_session)
    for cle, statut in (
        ("uploads/a/sain.pdf", StatutAnalyse.SAIN),
        ("uploads/a/rejete.pdf", StatutAnalyse.REJETE),
        ("uploads/a/indetermine.pdf", StatutAnalyse.INDETERMINE),
    ):
        f = await _en_analyse(db_session, cle, uid)
        f.statut_analyse = statut
    await db_session.commit()

    with patch("app.services.storage.lire_balise") as lire:
        c = await depot_service.rafraichir_analyses(db_session, MAINTENANT)

    lire.assert_not_called()
    assert c["lus"] == 0


# ── Le verdict ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("balise", "attendu"),
    [
        ("NO_THREATS_FOUND", StatutAnalyse.SAIN),
        ("THREATS_FOUND", StatutAnalyse.REJETE),
        ("FAILED", StatutAnalyse.INDETERMINE),
    ],
)
@pytest.mark.asyncio
async def test_la_balise_est_traduite_en_statut(db_session, balise, attendu):
    uid = await _un_utilisateur(db_session)
    cle = f"uploads/a/{balise.lower()}.pdf"
    await _en_analyse(db_session, cle, uid)

    with patch("app.services.storage.lire_balise", return_value=balise):
        c = await depot_service.rafraichir_analyses(db_session, MAINTENANT)

    assert c["tranches"] == 1
    fichier = await depot_service.fichier_par_cle(db_session, cle)
    assert fichier.statut_analyse == attendu
    assert fichier.analyse_le is not None


@pytest.mark.asyncio
async def test_pas_encore_de_balise_on_attend(db_session):
    """Le scan est en cours : on ne conclut rien."""
    uid = await _un_utilisateur(db_session)
    cle = "uploads/a/en-cours.pdf"
    await _en_analyse(db_session, cle, uid, minutes=1)

    with patch("app.services.storage.lire_balise", return_value=None):
        c = await depot_service.rafraichir_analyses(db_session, MAINTENANT)

    assert c == {"lus": 1, "tranches": 0, "abandonnes": 0}
    fichier = await depot_service.fichier_par_cle(db_session, cle)
    assert fichier.statut_analyse == StatutAnalyse.EN_ANALYSE


# ── Le renoncement ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apres_le_delai_on_renonce_en_indetermine(db_session):
    """Sans ce delai, un objet jamais etiquete serait relu indefiniment.

    C'est la seule facon dont cette tache pourrait finir par couter quelque
    chose — et le fichier resterait indiscernable d'un scan en cours.
    """
    uid = await _un_utilisateur(db_session)
    cle = "uploads/a/jamais-etiquete.pdf"
    await _en_analyse(db_session, cle, uid, minutes=90)

    with patch("app.services.storage.lire_balise", return_value=None):
        c = await depot_service.rafraichir_analyses(db_session, MAINTENANT)

    assert c["abandonnes"] == 1
    fichier = await depot_service.fichier_par_cle(db_session, cle)
    assert fichier.statut_analyse == StatutAnalyse.INDETERMINE


@pytest.mark.asyncio
async def test_on_ne_renonce_jamais_vers_sain(db_session):
    """Le renoncement ne doit pas ouvrir le telechargement."""
    uid = await _un_utilisateur(db_session)
    cle = "uploads/a/abandon.pdf"
    await _en_analyse(db_session, cle, uid, minutes=1000)

    with patch("app.services.storage.lire_balise", return_value=None):
        await depot_service.rafraichir_analyses(db_session, MAINTENANT)

    fichier = await depot_service.fichier_par_cle(db_session, cle)
    assert fichier.statut_analyse != StatutAnalyse.SAIN
    assert not await depot_service.est_telechargeable(db_session, cle)


# ── Resistance a l'echec ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_echec_de_lecture_n_interrompt_pas_les_autres(db_session):
    uid = await _un_utilisateur(db_session)
    await _en_analyse(db_session, "uploads/a/ko.pdf", uid)
    await _en_analyse(db_session, "uploads/a/ok.pdf", uid)

    def lire(cle: str, nom: str) -> str:
        if cle.endswith("ko.pdf"):
            raise OSError("S3 injoignable")
        return "NO_THREATS_FOUND"

    with patch("app.services.storage.lire_balise", side_effect=lire):
        c = await depot_service.rafraichir_analyses(db_session, MAINTENANT)

    assert c["tranches"] == 1
    ko = await depot_service.fichier_par_cle(db_session, "uploads/a/ko.pdf")
    ok = await depot_service.fichier_par_cle(db_session, "uploads/a/ok.pdf")
    assert ko.statut_analyse == StatutAnalyse.EN_ANALYSE  # sera relu au prochain passage
    assert ok.statut_analyse == StatutAnalyse.SAIN
