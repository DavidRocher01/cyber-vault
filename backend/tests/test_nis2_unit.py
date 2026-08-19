"""
Tests unitaires — logique NIS2 (sans HTTP, sans DB).

Couvre la fonction _compute_score() et les constantes NIS2_CATEGORIES.
Ces tests sont rapides et ne nécessitent pas de client HTTP.
"""

from app.services.assessment_service import compute_assessment_score
from app.services.nis2.catalogue import ALL_ITEM_IDS, NIS2_CATEGORIES


def _compute_score(items):
    return compute_assessment_score(items, ALL_ITEM_IDS)


# ── Structure des données ─────────────────────────────────────────────────────


class TestNis2Structure:
    def test_34_items_total(self):
        total = sum(len(cat["items"]) for cat in NIS2_CATEGORIES)
        assert total == 34

    def test_10_categories(self):
        assert len(NIS2_CATEGORIES) == 10

    def test_all_item_ids_unique(self):
        ids = [it["id"] for cat in NIS2_CATEGORIES for it in cat["items"]]
        assert len(ids) == len(set(ids)), "Des IDs d'items sont dupliqués"

    def test_all_item_ids_set_matches_categories(self):
        ids_from_cats = {it["id"] for cat in NIS2_CATEGORIES for it in cat["items"]}
        assert ids_from_cats == ALL_ITEM_IDS

    def test_each_category_has_required_fields(self):
        for cat in NIS2_CATEGORIES:
            assert "id" in cat
            assert "label" in cat
            assert "icon" in cat
            assert "items" in cat
            assert len(cat["items"]) > 0

    def test_each_item_has_required_fields(self):
        for cat in NIS2_CATEGORIES:
            for item in cat["items"]:
                assert "id" in item
                assert "label" in item
                assert "desc" in item

    def test_governance_category_exists(self):
        ids = [cat["id"] for cat in NIS2_CATEGORIES]
        assert "governance" in ids

    def test_rssi_item_exists(self):
        assert "rssi" in ALL_ITEM_IDS


# ── _compute_score() ──────────────────────────────────────────────────────────


class TestComputeScore:
    def test_empty_items_gives_0(self):
        """Items vide → tous les 34 défaut à non_compliant → score 0."""
        assert _compute_score({}) == 0

    def test_all_non_compliant_gives_0(self):
        items = dict.fromkeys(ALL_ITEM_IDS, "non_compliant")
        assert _compute_score(items) == 0

    def test_all_compliant_gives_100(self):
        items = dict.fromkeys(ALL_ITEM_IDS, "compliant")
        assert _compute_score(items) == 100

    def test_all_na_gives_0(self):
        """Tous NA → aucun item scorable → score 0."""
        items = dict.fromkeys(ALL_ITEM_IDS, "na")
        assert _compute_score(items) == 0

    def test_partial_is_1pt_compliant_is_2pt(self):
        """compliant=2pts, partial=1pt, dénominateur=(nb_scorable)*2."""
        # 1 compliant (2pts) + 1 partial (1pt) + reste non_compliant (0pt)
        # dénominateur = 34 items scorable (tous non-NA)
        # score = 3 / (34*2) * 100 = 3/68 * 100 ≈ 4
        items = {"rssi": "compliant", "policy": "partial"}
        assert _compute_score(items) == 4

    def test_na_excluded_from_denominator(self):
        """NA exclu du dénominateur — 1 compliant parmi 1 scorable = 100."""
        items = dict.fromkeys(ALL_ITEM_IDS, "na")
        items["rssi"] = "compliant"
        assert _compute_score(items) == 100

    def test_na_does_not_penalize_score(self):
        """2 conformes, reste NA → score 100 (NA non pénalisant)."""
        items = dict.fromkeys(ALL_ITEM_IDS, "na")
        items["rssi"] = "compliant"
        items["policy"] = "compliant"
        assert _compute_score(items) == 100

    def test_mixed_na_and_nc_penalizes(self):
        """2 conformes + 3 non_compliant + reste NA → score < 100."""
        items = dict.fromkeys(ALL_ITEM_IDS, "na")
        items["rssi"] = "compliant"
        items["policy"] = "compliant"
        # 3 items non_compliant
        nc_ids = list(ALL_ITEM_IDS - {"rssi", "policy"})[:3]
        for id_ in nc_ids:
            items[id_] = "non_compliant"
        # 2 conformes / 5 scorables → 4/10 = 40%
        assert _compute_score(items) == 40

    def test_unset_items_treated_as_non_compliant(self):
        """Un item non présent dans le dict compte comme non_compliant."""
        # 1 compliant parmi 34 items (33 non renseignés → non_compliant par défaut)
        assert _compute_score({"rssi": "compliant"}) == round(2 / 68 * 100)

    def test_half_compliant_gives_50(self):
        """17 conformes / 34 = 50%."""
        ids = list(ALL_ITEM_IDS)
        items = dict.fromkeys(ids[:17], "compliant")
        items.update(dict.fromkeys(ids[17:], "non_compliant"))
        assert _compute_score(items) == 50

    def test_all_partial_gives_50(self):
        """Tous partiels → 1pt chacun / 2pts max = 50%."""
        items = dict.fromkeys(ALL_ITEM_IDS, "partial")
        assert _compute_score(items) == 50

    def test_score_rounds_correctly(self):
        """Le score est bien arrondi à l'entier le plus proche."""
        score = _compute_score({"rssi": "compliant"})
        assert isinstance(score, int)

    def test_invalid_status_treated_as_0pts(self):
        """Un statut inconnu ne lève pas d'exception — contribue 0 pt."""
        items = dict.fromkeys(ALL_ITEM_IDS, "non_compliant")
        items["rssi"] = "unknown_status"
        assert _compute_score(items) == 0


# ── Remediation : lien diagnostic -> produit ──────────────────────────────────
#
# Ajoute le 2026-07-30 (fusion des deux produits NIS2). Le diagnostic pointait un
# ecart sans jamais dire par quoi le combler, alors que six items correspondent a
# des produits vendus par la plateforme.


class TestRemediation:
    """Le referentiel declare un produit pour les items qu'un produit comble."""

    _ATTENDUS = {
        "rssi": "/rssi-externalise",
        "mgmt_training": "/sensibilisation",
        "awareness": "/sensibilisation",
        "phishing_sim": "/simulation-phishing",
        "it_training": "/sensibilisation",
        "sca": "/code-scan",
    }

    def _items(self):
        return {it["id"]: it for cat in NIS2_CATEGORIES for it in cat["items"]}

    def test_les_six_items_portent_une_remediation(self):
        items = self._items()
        for item_id, route in self._ATTENDUS.items():
            assert "remediation" in items[item_id], f"{item_id} sans remediation"
            assert items[item_id]["remediation"]["route"] == route

    def test_chaque_remediation_a_un_produit_nomme(self):
        for it in self._items().values():
            rem = it.get("remediation")
            if rem:
                assert rem.get("produit"), f"{it['id']} : produit vide"

    def test_les_autres_items_n_en_ont_pas(self):
        """Pas de correspondance inventee : seuls les items reellement couverts
        par un produit en portent une."""
        items = self._items()
        avec = {i for i, it in items.items() if "remediation" in it}
        assert avec == set(self._ATTENDUS), (
            f"correspondances inattendues : {avec ^ set(self._ATTENDUS)}"
        )


class TestRemediationDansLePdf:
    """La remediation n'apparait dans le rapport que sur un ecart DECLARE."""

    def _lignes(self, items: dict) -> list[str]:
        from datetime import UTC, datetime
        from unittest.mock import patch

        import app.services.pdf_compliance as pc
        from app.services.nis2.report_pdf import generate_nis2_pdf

        captures: list[str] = []
        vrai = pc.Paragraph

        def espion(texte, *a, **k):
            captures.append(str(texte))
            return vrai(texte, *a, **k)

        with patch.object(pc, "Paragraph", espion):
            generate_nis2_pdf(NIS2_CATEGORIES, items, 42, datetime.now(UTC), "x@y.fr")
        return [t for t in captures if "combler" in t.lower()]

    def test_evaluation_vierge_ne_propose_rien(self):
        """Sans reponse, le score compte les items comme non conformes — mais on
        ne place pas six produits dans le rapport de quelqu'un qui n'a rien
        declare."""
        assert self._lignes({}) == []

    def test_ecart_declare_propose_le_produit(self):
        lignes = self._lignes({"awareness": "non_compliant"})
        assert len(lignes) == 1
        assert "Sensibilisation NIS2" in lignes[0]

    def test_ecart_partiel_propose_aussi(self):
        assert len(self._lignes({"phishing_sim": "partial"})) == 1

    def test_item_conforme_ne_propose_rien(self):
        assert self._lignes({"awareness": "compliant"}) == []


# ── Rattachement reglementaire ────────────────────────────────────────────────
#
# Ajoute le 2026-07-30. Le referentiel couvrait les bons themes mais ne citait
# AUCUN article : face a un auditeur, la tracabilite « cet item repond a telle
# exigence » est ce qui distingue un diagnostic d'un questionnaire maison.


class TestArticles:
    def _items(self):
        return [it for cat in NIS2_CATEGORIES for it in cat["items"]]

    def test_tous_les_items_citent_un_article(self):
        sans = [it["id"] for it in self._items() if not it.get("article")]
        assert sans == [], f"items sans rattachement : {sans}"

    def test_le_format_est_homogene(self):
        for it in self._items():
            assert it["article"].startswith("Art. "), f"{it['id']} : {it['article']!r}"

    def test_les_items_de_formation_pointent_l_alinea_g(self):
        """Art. 21(2)(g) — hygiene informatique de base et formation."""
        items = {it["id"]: it["article"] for it in self._items()}
        for item_id in ("awareness", "phishing_sim", "it_training"):
            assert items[item_id] == "Art. 21(2)(g)"

    def test_la_notification_pointe_l_article_23(self):
        items = {it["id"]: it["article"] for it in self._items()}
        assert items["anssi_notif"] == "Art. 23"

    def test_la_gouvernance_pointe_l_article_20(self):
        """Art. 20 traite de la responsabilite et de la formation des dirigeants,
        distinct des mesures techniques de l'article 21."""
        items = {it["id"]: it["article"] for it in self._items()}
        assert items["rssi"].startswith("Art. 20")
        assert items["mgmt_training"].startswith("Art. 20")

    def test_le_rapport_pdf_affiche_l_article(self):
        from datetime import UTC, datetime
        from unittest.mock import patch

        import app.services.pdf_compliance as pc
        from app.services.nis2.report_pdf import generate_nis2_pdf

        captures: list[str] = []
        vrai = pc.Paragraph

        def espion(texte, *a, **k):
            captures.append(str(texte))
            return vrai(texte, *a, **k)

        with patch.object(pc, "Paragraph", espion):
            generate_nis2_pdf(NIS2_CATEGORIES, {}, 0, datetime.now(UTC), "x@y.fr")

        avec_article = [t for t in captures if "Art. " in t]
        assert len(avec_article) == 34, "chaque item doit citer son article dans le rapport"
