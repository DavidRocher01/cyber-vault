"""Le stockage doit se declarer inutilisable AU DEMARRAGE, pas a la premiere requete.

LE DEFAUT QUE CECI PREVIENT. Le 2026-08-10, un rangement de rapports a failli
partir avec un prefixe hors du droit accorde au role de tache ECS :

    Autorise : cybervault-rssi-deliverables-prod/rssi-deliverables/*
    Ecrit    : rapports/*

Chaque scan aurait echoue sur un AccessDenied — a la premiere requete d'un
UTILISATEUR, des heures apres la bascule, sous forme d'erreur 500. Aucun des
2600 tests backend ne pouvait le voir : ils passent tous par le repli disque,
qui ne connait ni S3 ni IAM.

TOUTE LA SUBTILITE EST DANS LA DISTINCTION que ces tests gardent : un refus de
DROIT est toujours une erreur de configuration, donc on refuse de demarrer et la
bascule ECS ramene la version precedente. Une indisponibilite PASSAGERE ne doit
jamais faire tomber le service. Confondre les deux transformerait ce garde-fou
en panne.
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.services.storage import verifier_ecriture_stockage


def _client_qui_echoue(code: str) -> MagicMock:
    client = MagicMock()
    client.put_object.side_effect = ClientError({"Error": {"Code": code}}, "PutObject")
    return client


class TestVerificationDuStockage:
    def test_sans_seau_configure_on_ne_verifie_rien(self, monkeypatch):
        """Repli disque : rien a verifier, et surtout rien a exiger."""
        monkeypatch.setattr("app.services.storage.settings.S3_BUCKET_NAME", "")

        verifier_ecriture_stockage()  # ne doit pas lever

    def test_un_stockage_ecrivable_laisse_demarrer(self, monkeypatch):
        monkeypatch.setattr("app.services.storage.settings.S3_BUCKET_NAME", "un-seau")
        client = MagicMock()

        with patch("boto3.client", return_value=client):
            verifier_ecriture_stockage()

        # On ecrit PUIS on efface : la verification ne laisse pas de trace.
        assert client.put_object.called
        assert client.delete_object.called

    @pytest.mark.parametrize(
        "code", ["AccessDenied", "AllAccessDisabled", "InvalidAccessKeyId", "NoSuchBucket"]
    )
    def test_un_refus_de_droit_empeche_le_demarrage(self, code, monkeypatch):
        """LE COEUR DU GARDE-FOU. Ces erreurs ne sont jamais passageres."""
        monkeypatch.setattr("app.services.storage.settings.S3_BUCKET_NAME", "un-seau")

        with (
            patch("boto3.client", return_value=_client_qui_echoue(code)),
            pytest.raises(RuntimeError, match="Stockage inutilisable"),
        ):
            verifier_ecriture_stockage()

    @pytest.mark.parametrize("code", ["RequestTimeout", "ServiceUnavailable", "SlowDown"])
    def test_une_indisponibilite_passagere_laisse_demarrer(self, code, monkeypatch):
        """Reseau coupe, S3 lent, jeton en renouvellement : on journalise et on
        demarre. Tomber ici transformerait le garde-fou en panne."""
        monkeypatch.setattr("app.services.storage.settings.S3_BUCKET_NAME", "un-seau")

        with patch("boto3.client", return_value=_client_qui_echoue(code)):
            verifier_ecriture_stockage()  # ne doit pas lever

    def test_la_cle_de_verification_est_dans_le_prefixe_autorise(self, monkeypatch):
        """Verifier ailleurs que la ou l'on ecrit ne prouverait rien."""
        monkeypatch.setattr("app.services.storage.settings.S3_BUCKET_NAME", "un-seau")
        client = MagicMock()

        with patch("boto3.client", return_value=client):
            verifier_ecriture_stockage()

        cle = client.put_object.call_args.kwargs["Key"]
        assert cle.startswith("rssi-deliverables/"), f"cle hors du droit accorde : {cle}"
