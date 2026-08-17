"""Rebonds e-mail : signature, enregistrement, idempotence.

POURQUOI CE FICHIER. Rien n'ecoutait ce que Resend renvoyait : un e-mail qui
rebondit ne laissait aucune trace. Les fournisseurs de messagerie notent les
expediteurs sur ce taux, et la sanction est invisible — elle se manifeste le jour
ou les e-mails LEGITIMES partent en indesirables.

LA MOITIE DE CE FICHIER PORTE SUR LA SIGNATURE, et ce n'est pas
disproportionne : cet endpoint met des adresses en liste de suppression. Sans
verification, n'importe qui connaissant l'URL ferait cesser les envois vers
l'adresse de son choix — reinitialisation de mot de passe comprise. Un endpoint
qui accepte tout serait pire que pas d'endpoint.
"""

import base64
import hashlib
import hmac
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.services import email_suppression, signature_svix

SECRET = "whsec_" + base64.b64encode(b"secret-de-test-pour-la-signature").decode()
URL = "/api/v1/webhooks/resend"


def _signer(corps: bytes, svix_id="msg_1", horodatage=None, secret=SECRET):
    ts = str(int(horodatage if horodatage is not None else time.time()))
    cle = base64.b64decode(secret.removeprefix("whsec_"))
    contenu = f"{svix_id}.{ts}.".encode() + corps
    sig = base64.b64encode(hmac.new(cle, contenu, hashlib.sha256).digest()).decode()
    return {"svix-id": svix_id, "svix-timestamp": ts, "svix-signature": f"v1,{sig}"}


def _evenement(type_="email.bounced", to="mort@exemple.fr", reason="mailbox_not_found"):
    return json.dumps({"type": type_, "data": {"to": [to], "reason": reason}}).encode()


class TestSignature:
    def test_accepte_une_signature_valide(self):
        corps = _evenement()
        e = _signer(corps)
        assert signature_svix.verifier(
            SECRET, e["svix-id"], e["svix-timestamp"], e["svix-signature"], corps
        )

    def test_refuse_un_corps_modifie_apres_signature(self):
        """L'attaque qui compte : garder une signature valide et changer
        l'adresse visee."""
        e = _signer(_evenement(to="victime@exemple.fr"))
        autre = _evenement(to="cible@exemple.fr")
        assert not signature_svix.verifier(
            SECRET, e["svix-id"], e["svix-timestamp"], e["svix-signature"], autre
        )

    def test_refuse_une_signature_ancienne(self):
        """Sans fenetre de tolerance, une requete interceptee reste rejouable
        indefiniment."""
        corps = _evenement()
        vieux = time.time() - signature_svix.TOLERANCE_SECONDES - 60
        e = _signer(corps, horodatage=vieux)
        assert not signature_svix.verifier(
            SECRET, e["svix-id"], e["svix-timestamp"], e["svix-signature"], corps
        )

    def test_accepte_quand_plusieurs_signatures_sont_presentes(self):
        """Svix envoie plusieurs signatures pendant une rotation de secret."""
        corps = _evenement()
        e = _signer(corps)
        entete = f"v1,unesignaturequinevautrien {e['svix-signature']}"
        assert signature_svix.verifier(SECRET, e["svix-id"], e["svix-timestamp"], entete, corps)

    def test_refuse_un_secret_vide(self):
        """Tant que le secret n'est pas configure, l'endpoint doit rester ferme."""
        corps = _evenement()
        e = _signer(corps)
        assert not signature_svix.verifier(
            "", e["svix-id"], e["svix-timestamp"], e["svix-signature"], corps
        )

    @pytest.mark.parametrize("manquant", ["svix-id", "svix-timestamp", "svix-signature"])
    def test_refuse_si_un_en_tete_manque(self, manquant):
        corps = _evenement()
        e = _signer(corps)
        e[manquant] = None
        assert not signature_svix.verifier(
            SECRET, e["svix-id"], e["svix-timestamp"], e["svix-signature"], corps
        )


class TestEnregistrement:
    @pytest.mark.asyncio
    async def test_un_rebond_dur_met_l_adresse_en_suppression(self, db_session):
        await email_suppression.enregistrer(
            db_session, email="Mort@Exemple.FR", evenement="email.bounced"
        )
        # Stockee en minuscules, sinon la meme adresse saisie autrement ne
        # bloquerait rien.
        assert await email_suppression.est_supprimee(db_session, "mort@exemple.fr")

    @pytest.mark.asyncio
    async def test_le_meme_rebond_notifie_deux_fois_ne_cree_qu_une_entree(self, db_session):
        for _ in range(3):
            await email_suppression.enregistrer(
                db_session, email="double@exemple.fr", evenement="email.complained"
            )
        assert len(await email_suppression.lister(db_session)) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "evenement", ["email.delivered", "email.opened", "email.delivery_delayed"]
    )
    async def test_un_evenement_non_definitif_ne_supprime_rien(self, db_session, evenement):
        """Une boite pleine ou un retard d'acheminement n'est pas definitif.

        Bloquer sur ce motif priverait un client de son rapport de scan parce
        que sa boite etait pleine un mardi.
        """
        await email_suppression.enregistrer(
            db_session, email="vivant@exemple.fr", evenement=evenement
        )
        assert not await email_suppression.est_supprimee(db_session, "vivant@exemple.fr")


class TestEndpoint:
    @pytest.mark.asyncio
    async def test_refuse_une_requete_non_signee(self, monkeypatch):
        monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", SECRET)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(URL, content=_evenement())
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_enregistre_un_rebond_signe(self, monkeypatch, db_session):
        monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", SECRET)
        corps = _evenement(to="rebond@exemple.fr")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(URL, content=corps, headers=_signer(corps))
        assert r.status_code == 200
        assert await email_suppression.est_supprimee(db_session, "rebond@exemple.fr")

    @pytest.mark.asyncio
    async def test_un_evenement_ignore_repond_quand_meme_200(self, monkeypatch):
        """Svix rejoue les livraisons non acquittees : refuser un evenement
        qu'on ignore volontairement le ferait rejouer en boucle."""
        monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", SECRET)
        corps = _evenement(type_="email.delivered", to="ok@exemple.fr")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(URL, content=corps, headers=_signer(corps))
        assert r.status_code == 200
