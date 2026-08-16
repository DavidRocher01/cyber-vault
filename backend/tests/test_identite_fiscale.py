"""Le SIREN facture doit etre un vrai SIREN.

POURQUOI CES TESTS. Le SIREN de l'acheteur devient obligatoire sur les factures
entre professionnels au 1er septembre 2027, et c'est la cle de rapprochement de
l'administration. Un numero mal saisi n'est PAS rattrapable : la facture part,
le client la classe, et l'erreur ne se decouvre qu'au controle.

La cle de Luhn est le seul filtre qui distingue une faute de frappe d'un numero
reel — d'ou l'insistance ici.
"""

import pytest

from app.services import identite_fiscale as idf

# SIREN reels, cle de Luhn correcte.
SIREN_ROCHER = "104009634"  # celui de l'emetteur, tire de son SIRET
SIREN_VALIDE = "552100554"


class TestSirenValide:
    @pytest.mark.parametrize("valeur", [SIREN_ROCHER, SIREN_VALIDE])
    def test_accepte_un_siren_reel(self, valeur):
        assert idf.siren_valide(valeur)

    @pytest.mark.parametrize(
        "valeur",
        [
            "104 009 634",  # espaces : saisie humaine courante
            "104.009.634",
            "104-009-634",
        ],
    )
    def test_accepte_les_separateurs_de_saisie(self, valeur):
        assert idf.siren_valide(valeur)

    def test_refuse_une_faute_de_frappe(self):
        """Deux chiffres intervertis : bonne longueur, mauvaise cle.

        C'est l'erreur la plus frequente et la plus invisible — sans Luhn, elle
        passe tous les autres controles.
        """
        assert not idf.siren_valide("104009643")

    @pytest.mark.parametrize(
        "valeur",
        [None, "", "12345678", "1234567890", "10400963A", "abcdefghi"],
    )
    def test_refuse_ce_qui_n_est_pas_un_siren(self, valeur):
        assert not idf.siren_valide(valeur)


class TestSirenDepuisTva:
    def test_extrait_le_siren_d_un_numero_de_tva_francais(self):
        # Cle numerique calculee : (12 + 3 * (SIREN % 97)) % 97
        cle = (12 + 3 * (int(SIREN_ROCHER) % 97)) % 97
        assert idf.siren_depuis_tva(f"FR{cle:02d}{SIREN_ROCHER}") == SIREN_ROCHER

    def test_accepte_une_cle_alphabetique(self):
        """Les numeros les plus anciens portent une cle non calculable.

        La refuser ecarterait des entreprises parfaitement en regle.
        """
        assert idf.siren_depuis_tva(f"FRAB{SIREN_ROCHER}") == SIREN_ROCHER

    def test_refuse_une_cle_numerique_fausse(self):
        cle = (12 + 3 * (int(SIREN_ROCHER) % 97)) % 97
        fausse = (cle + 1) % 97
        assert idf.siren_depuis_tva(f"FR{fausse:02d}{SIREN_ROCHER}") is None

    def test_refuse_un_siren_dont_la_cle_de_luhn_est_fausse(self):
        assert idf.siren_depuis_tva("FRAB104009643") is None

    @pytest.mark.parametrize(
        "valeur",
        [None, "", "DE123456789", "FR104009634", "FRAB12345678"],
    )
    def test_refuse_ce_qui_n_est_pas_un_numero_francais(self, valeur):
        assert idf.siren_depuis_tva(valeur) is None


class TestIdentifiantStripe:
    def test_traduit_un_eu_vat_francais(self):
        assert idf.siren_depuis_identifiant("eu_vat", f"FRAB{SIREN_ROCHER}") == SIREN_ROCHER

    def test_un_client_etranger_ne_produit_pas_de_siren_et_n_est_pas_rejete(self):
        """Un numero allemand est valide — il n'est simplement pas francais.

        Le refuser empecherait le client d'acheter, pour une obligation qui ne
        le concerne pas.
        """
        assert idf.siren_depuis_identifiant("eu_vat", "DE123456789") is None

    @pytest.mark.parametrize("type_stripe", ["gb_vat", "au_abn", None])
    def test_ignore_les_autres_types_d_identifiant(self, type_stripe):
        assert idf.siren_depuis_identifiant(type_stripe, "123456789") is None
