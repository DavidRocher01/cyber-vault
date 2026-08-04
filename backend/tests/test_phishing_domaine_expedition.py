"""Le domaine d'expedition des simulations doit etre separe du transactionnel.

POURQUOI CETTE REGLE. Le but d'une bonne simulation est que les salaries
SIGNALENT le message. Ces signalements remontent a Microsoft et Google et pesent
sur la reputation du domaine expediteur. L'envoyer depuis celui qui porte les
reinitialisations de mot de passe et les factures revient a leur nuire
deliberement — d'autant plus que la simulation reussit.

CE QUE CES TESTS PROTEGENT VRAIMENT. Le danger n'est pas qu'on choisisse mal le
domaine un jour donne : c'est le REPLI SILENCIEUX. `PHISHING_FROM_EMAIL or
RESEND_FROM` fait qu'une valeur absente, vide ou mal saisie renvoie au domaine
principal sans que rien ne le signale — exactement le scenario d'une migration
de domaine batclee. Ces tests verifient qu'un tel etat REFUSE d'envoyer.

Aucun nom de domaine n'est ecrit en dur ici : la garde compare deux reglages
entre eux, donc elle survit a n'importe quel changement de domaine, et ces tests
aussi. Cf. `docs/PHISHING_REDESIGN.md` 5c.
"""

import pytest

from app.services import phishing_service
from app.services.phishing_service import DomaineExpeditionInvalideError

TRANSACTIONNEL = "Marque <no-reply@exemple-transactionnel.com>"
SIMULATION = "no-reply@exemple-simulation.com"


@pytest.fixture
def reglages(monkeypatch):
    """Pose un couple coherent, que chaque test degrade a sa facon."""
    monkeypatch.setattr(phishing_service.settings, "RESEND_FROM", TRANSACTIONNEL)
    monkeypatch.setattr(phishing_service.settings, "PHISHING_FROM_EMAIL", SIMULATION)
    return monkeypatch


# ── La garde ───────────────────────────────────────────────────────────────────


def test_domaines_distincts_acceptes(reglages):
    phishing_service.verifier_domaine_expedition()  # ne leve pas


def test_meme_domaine_refuse(reglages):
    """Le cas frontal : quelqu'un pointe les simulations sur le domaine principal."""
    reglages.setattr(
        phishing_service.settings, "PHISHING_FROM_EMAIL", "no-reply@exemple-transactionnel.com"
    )
    with pytest.raises(DomaineExpeditionInvalideError, match="transactionnel"):
        phishing_service.verifier_domaine_expedition()


def test_valeur_absente_refuse(reglages):
    """LE cas qui compte : vide => repli silencieux sur le transactionnel."""
    reglages.setattr(phishing_service.settings, "PHISHING_FROM_EMAIL", "")
    with pytest.raises(DomaineExpeditionInvalideError):
        phishing_service.verifier_domaine_expedition()


def test_casse_et_espaces_ne_contournent_pas(reglages):
    """Une comparaison naive laisserait passer une majuscule ou un espace."""
    reglages.setattr(
        phishing_service.settings, "PHISHING_FROM_EMAIL", " no-reply@EXEMPLE-Transactionnel.COM "
    )
    with pytest.raises(DomaineExpeditionInvalideError):
        phishing_service.verifier_domaine_expedition()


def test_sous_domaine_accepte(reglages):
    """Un sous-domaine porte sa propre cle DKIM : la garde ne doit pas le bloquer.

    Elle protege contre l'usage du domaine transactionnel LUI-MEME, pas contre
    un choix d'isolation plus faible — c'est une decision, pas une erreur.
    """
    reglages.setattr(
        phishing_service.settings, "PHISHING_FROM_EMAIL", "no-reply@sim.exemple-transactionnel.com"
    )
    phishing_service.verifier_domaine_expedition()  # ne leve pas


def test_aucun_nom_de_domaine_en_dur_dans_la_garde():
    """Garde-fou du garde-fou : elle doit survivre a un changement de domaine.

    Si quelqu'un y ecrit un domaine en dur, elle cesse de proteger des que le
    domaine change — et personne ne s'en apercoit.
    """
    import inspect

    source = inspect.getsource(phishing_service.verifier_domaine_expedition)
    assert "rochercybersecurite" not in source
    assert "cyberscanapp" not in source


# ── Le chemin d'envoi ──────────────────────────────────────────────────────────


def test_envoi_refuse_si_domaines_confondus(reglages):
    """Seconde barriere : le planificateur ne repasse pas par l'endpoint.

    Une campagne lancee AVANT l'existence de la garde, ou une configuration
    changee depuis, doit tout de meme etre arretee.
    """
    reglages.setattr(
        phishing_service.settings, "PHISHING_FROM_EMAIL", "no-reply@exemple-transactionnel.com"
    )
    with pytest.raises(DomaineExpeditionInvalideError):
        phishing_service._send_phishing_email(
            "cible@exemple.com", "Nom <no-reply@x.com>", "Sujet", "<p>x</p>", "x"
        )


def test_l_adresse_reste_bien_formee(reglages):
    """Non-regression de l'en-tete reparee le 2026-08-03.

    `RESEND_FROM` porte un nom d'affichage, `PHISHING_FROM_EMAIL` non : melanger
    les deux formats produisait des chevrons imbriques, que `parseaddr` reduit a
    un nom vide ET une adresse vide.
    """
    from email.utils import parseaddr

    adresse = phishing_service._adresse_expediteur()
    assert "<" not in adresse and ">" not in adresse
    nom, extraite = parseaddr(f"Support Microsoft 365 <{adresse}>")
    assert nom == "Support Microsoft 365"
    assert extraite == SIMULATION
