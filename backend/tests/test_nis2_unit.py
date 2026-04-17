"""
Tests unitaires — logique NIS2 (sans HTTP, sans DB).

Couvre la fonction _compute_score() et les constantes NIS2_CATEGORIES.
Ces tests sont rapides et ne nécessitent pas de client HTTP.
"""

import pytest

from app.api.v1.endpoints.nis2 import (
    ALL_ITEM_IDS,
    NIS2_CATEGORIES,
)
from app.services.assessment_service import compute_assessment_score

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
        items = {id: "non_compliant" for id in ALL_ITEM_IDS}
        assert _compute_score(items) == 0

    def test_all_compliant_gives_100(self):
        items = {id: "compliant" for id in ALL_ITEM_IDS}
        assert _compute_score(items) == 100

    def test_all_na_gives_0(self):
        """Tous NA → aucun item scorable → score 0."""
        items = {id: "na" for id in ALL_ITEM_IDS}
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
        items = {id: "na" for id in ALL_ITEM_IDS}
        items["rssi"] = "compliant"
        assert _compute_score(items) == 100

    def test_na_does_not_penalize_score(self):
        """2 conformes, reste NA → score 100 (NA non pénalisant)."""
        items = {id: "na" for id in ALL_ITEM_IDS}
        items["rssi"] = "compliant"
        items["policy"] = "compliant"
        assert _compute_score(items) == 100

    def test_mixed_na_and_nc_penalizes(self):
        """2 conformes + 3 non_compliant + reste NA → score < 100."""
        items = {id: "na" for id in ALL_ITEM_IDS}
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
        items = {id_: "compliant" for id_ in ids[:17]}
        items.update({id_: "non_compliant" for id_ in ids[17:]})
        assert _compute_score(items) == 50

    def test_all_partial_gives_50(self):
        """Tous partiels → 1pt chacun / 2pts max = 50%."""
        items = {id: "partial" for id in ALL_ITEM_IDS}
        assert _compute_score(items) == 50

    def test_score_rounds_correctly(self):
        """Le score est bien arrondi à l'entier le plus proche."""
        score = _compute_score({"rssi": "compliant"})
        assert isinstance(score, int)

    def test_invalid_status_treated_as_0pts(self):
        """Un statut inconnu ne lève pas d'exception — contribue 0 pt."""
        items = {id: "non_compliant" for id in ALL_ITEM_IDS}
        items["rssi"] = "unknown_status"
        assert _compute_score(items) == 0
