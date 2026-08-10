"""Un rapport de scan disparu doit se dire, pas exploser.

LE DEFAUT, MESURE EN PRODUCTION LE 2026-08-09. Les rapports PDF etaient ecrits
sur le disque du conteneur et leur CHEMIN ABSOLU stocke en base. Or le stockage
d'une tache Fargate est EPHEMERE : chaque deploiement remplace la tache et
emporte tous les rapports, pendant que la base continue d'affirmer qu'ils
existent. Sept minutes apres un deploiement :

    GET /api/v1/scans/163/pdf -> 500
    RuntimeError: File at path /cyber-scanner/reports/clients/scan_163.pdf
                  does not exist.

Une exception non rattrapee, une alarme CloudWatch reveillee, et un utilisateur
qui n'apprend rien. On deploie plusieurs fois par jour.

CES TESTS GARDENT LES DEUX MOITIES DE LA CORRECTION : les rapports sont ranges
hors du conteneur, et ce qui a malgre tout disparu repond 404 avec une phrase
utile.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.storage import lire_rapport, ranger_rapport

from .test_scans import BASE, _headers, _site


class TestRangementDesRapports:
    def test_une_reference_n_est_pas_un_chemin_de_conteneur(self, tmp_path, monkeypatch):
        """C'est toute la distinction : un chemin ne survit pas au conteneur."""
        monkeypatch.setattr("app.services.storage.settings.S3_BUCKET_NAME", "")
        monkeypatch.setattr("app.services.storage._LOCAL_RAPPORTS_DIR", tmp_path / "rapports")

        reference = ranger_rapport(b"%PDF-1.4 contenu", "scan_1.pdf")

        assert lire_rapport(reference) == b"%PDF-1.4 contenu"

    def test_un_rapport_disparu_se_lit_comme_absent_et_ne_jette_pas(self, tmp_path):
        """LE COEUR DE LA CORRECTION. Renvoyer `None` plutot que laisser jaillir
        l'exception est ce qui permet a l'appelant de repondre 404."""
        disparu = str(tmp_path / "jamais_ecrit.pdf")

        assert lire_rapport(disparu) is None

    def test_un_chemin_absolu_d_avant_reste_lisible_s_il_existe(self, tmp_path):
        """Les lignes d'avant cette correction portent un chemin absolu. On les
        lit quand meme, plutot que de les declarer perdues sans essayer."""
        ancien = tmp_path / "scan_ancien.pdf"
        ancien.write_bytes(b"%PDF ancien")

        assert lire_rapport(str(ancien)) == b"%PDF ancien"

    def test_la_cle_reste_dans_le_prefixe_autorise_par_l_iam(self, monkeypatch):
        """CE TEST GARDE UNE ERREUR REELLEMENT COMMISE.

        La politique IAM du role de tache n'autorise que
        `cybervault-rssi-deliverables-prod/rssi-deliverables/*`. Un premier
        essai rangeait les rapports sous `rapports/` : chaque scan aurait echoue
        en production sur un AccessDenied, SANS QU'AUCUN TEST NE PUISSE LE VOIR
        — ils passent tous par le repli local, qui ne connait pas l'IAM.
        """
        from app.services.storage import _PREFIXE_RAPPORTS

        assert _PREFIXE_RAPPORTS.startswith("rssi-deliverables/"), (
            "le prefixe sort du droit accorde au role de tache ECS"
        )

    def test_sans_seau_configure_une_cle_s3_est_declaree_absente(self, monkeypatch):
        # Plutot que de tenter un appel reseau qui echouerait plus loin.
        monkeypatch.setattr("app.services.storage.settings.S3_BUCKET_NAME", "")

        assert lire_rapport("rapports/scan_42.pdf") is None


@pytest.mark.asyncio
async def test_rapport_disparu_repond_404_et_non_500():
    """LE TEST QUI COMPTE : c'est exactement la requete qui a produit le 500."""
    with (
        patch("app.api.v1.endpoints.scans.run_scan", new_callable=AsyncMock),
        patch(
            "app.api.v1.endpoints.scans.get_active_plan",
            new=AsyncMock(
                return_value=MagicMock(scan_interval_days=30, max_sites=5, price_eur=990)
            ),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "rapport-disparu@test.com")
            site_id = await _site(c, h)
            trig = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)
            scan_id = trig.json()["scan_id"]

            # On place le scan dans l'etat exact d'un rapport promis puis perdu :
            # termine, avec un chemin en base, et rien au bout.
            from sqlalchemy import update

            from app.core.database import AsyncSessionLocal
            from app.models.scan import Scan

            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Scan)
                    .where(Scan.id == scan_id)
                    .values(
                        status="done",
                        pdf_path=str(
                            Path("/cyber-scanner/reports/clients") / f"scan_{scan_id}.pdf"
                        ),
                    )
                )
                await db.commit()

            r = await c.get(f"{BASE}/scans/{scan_id}/pdf", headers=h)

    assert r.status_code == 404, f"attendu 404, obtenu {r.status_code}"
    # La phrase doit dire quoi faire, pas seulement que ca a rate.
    assert "plus disponible" in r.json()["detail"]
