"""La facture doit retenir ce que Stripe a deja collecte.

POURQUOI CE FICHIER. Deux mentions obligatoires manquaient sur les factures
emises jusqu'au 2026-08-16 :

  - L'ADRESSE DU CLIENT. Stripe la collecte a la caisse depuis toujours
    (`billing_address_collection`), et le webhook passait `client_address=None`.
    Elle etait donc jetee a l'arrivee, sans que rien ne le signale : une facture
    sans adresse ne provoque aucune erreur, elle est juste incomplete.

  - LE SIREN DE L'ACHETEUR, qui devient obligatoire entre professionnels au
    1er septembre 2027. Contrairement au format Factur-X, qui s'ecrira le moment
    venu, un SIREN non demande au moment de la vente ne se retrouve plus.

Ces tests portent sur le chemin reel — celui du webhook — et non sur les
fonctions de validation, deja couvertes par `test_identite_fiscale.py`.
"""

import pytest

from app.api.v1.endpoints.webhooks import _adresse_postale, _handle_invoice_payment_succeeded
from app.services.stripe_webhook_service import get_invoice_by_stripe_id

SIREN = "104009634"
TVA_FR = f"FRAB{SIREN}"


def _facture_stripe(**extra) -> dict:
    base = {
        "id": "in_test_donnees_client",
        "customer_email": "client@exemple.fr",
        "customer_name": "Exemple SARL",
        "amount_paid": 4900,
        "created": 1786000000,
        "lines": {"data": [{"description": "Abonnement Standard"}]},
    }
    base.update(extra)
    return base


class TestAdressePostale:
    def test_assemble_les_lignes_renseignees(self):
        assert (
            _adresse_postale(
                {
                    "line1": "546 Montée Carriat",
                    "line2": None,
                    "postal_code": "01600",
                    "city": "Reyrieux",
                    "country": "FR",
                }
            )
            == "546 Montée Carriat\n01600 Reyrieux\nFR"
        )

    @pytest.mark.parametrize("adresse", [None, {}, {"line1": None, "city": None}])
    def test_une_adresse_vide_vaut_none(self, adresse):
        """Sans ce garde-fou, la facture porterait des lignes vides et des
        virgules orphelines."""
        assert _adresse_postale(adresse) is None


@pytest.mark.asyncio
async def test_le_siren_et_l_adresse_sont_enregistres(db_session):
    await _handle_invoice_payment_succeeded(
        _facture_stripe(
            customer_tax_ids=[{"type": "eu_vat", "value": TVA_FR}],
            customer_address={
                "line1": "12 rue des Lilas",
                "postal_code": "69000",
                "city": "Lyon",
                "country": "FR",
            },
        ),
        db_session,
    )
    facture = await get_invoice_by_stripe_id(db_session, "in_test_donnees_client")
    assert facture is not None
    assert facture.client_siren == SIREN
    assert facture.client_address is not None
    assert "Lyon" in facture.client_address


@pytest.mark.asyncio
async def test_un_client_particulier_n_a_pas_de_siren_et_la_facture_passe(db_session):
    """Le SIREN ne concerne QUE les professionnels.

    Le rendre indispensable bloquerait toute vente a un particulier — or c'est
    l'e-reporting, et non la facturation electronique, qui les couvre.
    """
    await _handle_invoice_payment_succeeded(
        _facture_stripe(id="in_test_particulier", customer_tax_ids=[]),
        db_session,
    )
    facture = await get_invoice_by_stripe_id(db_session, "in_test_particulier")
    assert facture is not None
    assert facture.client_siren is None


@pytest.mark.asyncio
async def test_un_identifiant_etranger_ne_bloque_pas_la_facture(db_session):
    """Un numero allemand est valide — il n'est simplement pas un SIREN."""
    await _handle_invoice_payment_succeeded(
        _facture_stripe(
            id="in_test_etranger",
            customer_tax_ids=[{"type": "eu_vat", "value": "DE123456789"}],
        ),
        db_session,
    )
    facture = await get_invoice_by_stripe_id(db_session, "in_test_etranger")
    assert facture is not None
    assert facture.client_siren is None
