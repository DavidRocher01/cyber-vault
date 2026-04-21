"""
Unit tests — ISO 27001 endpoint (without HTTP/DB).

Covers: structure validation, score computation, save/get logic.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.api.v1.endpoints.iso27001 import (
    ALL_ITEM_IDS,
    ISO27001_CATEGORIES,
    get_assessment,
    save_assessment,
    Iso27001SaveIn,
)
from app.services.assessment_service import compute_assessment_score
from app.models.user import User
from app.models.iso27001_assessment import Iso27001Assessment


def _compute_score(items):
    return compute_assessment_score(items, ALL_ITEM_IDS)


# ── Structure ─────────────────────────────────────────────────────────────────

class TestIso27001Structure:
    def test_item_count(self):
        total = sum(len(cat["items"]) for cat in ISO27001_CATEGORIES)
        assert total == 38

    def test_category_count(self):
        assert len(ISO27001_CATEGORIES) == 10

    def test_all_item_ids_unique(self):
        ids = [it["id"] for cat in ISO27001_CATEGORIES for it in cat["items"]]
        assert len(ids) == len(set(ids))

    def test_all_item_ids_set_matches_categories(self):
        ids_from_cats = {it["id"] for cat in ISO27001_CATEGORIES for it in cat["items"]}
        assert ids_from_cats == ALL_ITEM_IDS

    def test_each_category_has_required_fields(self):
        for cat in ISO27001_CATEGORIES:
            assert "id" in cat
            assert "label" in cat
            assert "icon" in cat
            assert "items" in cat
            assert len(cat["items"]) > 0

    def test_each_item_has_required_fields(self):
        for cat in ISO27001_CATEGORIES:
            for item in cat["items"]:
                assert "id" in item
                assert "label" in item
                assert "desc" in item

    def test_expected_categories_present(self):
        cat_ids = {cat["id"] for cat in ISO27001_CATEGORIES}
        assert "risk" in cat_ids
        assert "access" in cat_ids
        assert "crypto" in cat_ids
        assert "incidents" in cat_ids

    def test_known_items_present(self):
        assert "mfa" in ALL_ITEM_IDS
        assert "tls" in ALL_ITEM_IDS
        assert "backups" in ALL_ITEM_IDS
        assert "scope" in ALL_ITEM_IDS


# ── Score computation ─────────────────────────────────────────────────────────

class TestIso27001Score:
    def test_empty_gives_0(self):
        assert _compute_score({}) == 0

    def test_all_compliant_gives_100(self):
        items = {id_: "compliant" for id_ in ALL_ITEM_IDS}
        assert _compute_score(items) == 100

    def test_all_non_compliant_gives_0(self):
        items = {id_: "non_compliant" for id_ in ALL_ITEM_IDS}
        assert _compute_score(items) == 0

    def test_all_partial_gives_50(self):
        items = {id_: "partial" for id_ in ALL_ITEM_IDS}
        assert _compute_score(items) == 50

    def test_all_na_gives_0(self):
        items = {id_: "na" for id_ in ALL_ITEM_IDS}
        assert _compute_score(items) == 0

    def test_na_excluded_from_denominator(self):
        items = {id_: "na" for id_ in ALL_ITEM_IDS}
        items["mfa"] = "compliant"
        assert _compute_score(items) == 100

    def test_half_compliant_gives_50(self):
        ids = list(ALL_ITEM_IDS)
        half = len(ids) // 2
        items = {id_: "compliant" for id_ in ids[:half]}
        items.update({id_: "non_compliant" for id_ in ids[half:]})
        assert _compute_score(items) == 50

    def test_score_is_int(self):
        assert isinstance(_compute_score({"mfa": "compliant"}), int)


# ── get_assessment endpoint logic ─────────────────────────────────────────────

class TestGetAssessment:
    @pytest.mark.asyncio
    async def test_no_assessment_returns_empty(self):
        user = MagicMock(spec=User, id=1)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await get_assessment(current_user=user, db=db)

        assert result["items"] == {}
        assert result["score"] == 0
        assert result["updated_at"] is None
        assert result["categories"] == ISO27001_CATEGORIES

    @pytest.mark.asyncio
    async def test_existing_assessment_returned(self):
        user = MagicMock(spec=User, id=1)
        assessment = MagicMock(spec=Iso27001Assessment)
        assessment.items_json = json.dumps({"mfa": "compliant"})
        assessment.score = 42
        assessment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=assessment)))

        result = await get_assessment(current_user=user, db=db)

        assert result["items"] == {"mfa": "compliant"}
        assert result["score"] == 42
        assert result["updated_at"] == assessment.updated_at


# ── save_assessment endpoint logic ────────────────────────────────────────────

class TestSaveAssessment:
    @pytest.mark.asyncio
    async def test_invalid_item_id_raises_422(self):
        from fastapi import HTTPException
        user = MagicMock(spec=User, id=1)
        db = AsyncMock()
        payload = Iso27001SaveIn(items={"nonexistent_id": "compliant"})

        with pytest.raises(HTTPException) as exc:
            await save_assessment(payload=payload, current_user=user, db=db)
        assert exc.value.status_code == 422
        assert "inconnu" in exc.value.detail

    @pytest.mark.asyncio
    async def test_invalid_status_raises_422(self):
        from fastapi import HTTPException
        user = MagicMock(spec=User, id=1)
        db = AsyncMock()
        payload = Iso27001SaveIn(items={"mfa": "invalid_status"})

        with pytest.raises(HTTPException) as exc:
            await save_assessment(payload=payload, current_user=user, db=db)
        assert exc.value.status_code == 422
        assert "Statut invalide" in exc.value.detail

    @pytest.mark.asyncio
    async def test_creates_new_assessment_when_none_exists(self):
        user = MagicMock(spec=User, id=1)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        created = {}

        def capture_add(obj):
            created["obj"] = obj

        db.add = capture_add
        db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "updated_at", datetime.now(timezone.utc)))

        payload = Iso27001SaveIn(items={"mfa": "compliant"})
        result = await save_assessment(payload=payload, current_user=user, db=db)

        assert "obj" in created
        assert result["items"] == {"mfa": "compliant"}
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_existing_assessment(self):
        user = MagicMock(spec=User, id=1)
        assessment = MagicMock(spec=Iso27001Assessment)
        assessment.items_json = json.dumps({"tls": "partial"})
        assessment.score = 10
        assessment.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=assessment)))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "updated_at", datetime.now(timezone.utc)))

        payload = Iso27001SaveIn(items={"mfa": "compliant", "tls": "compliant"})
        result = await save_assessment(payload=payload, current_user=user, db=db)

        assert assessment.items_json == json.dumps({"mfa": "compliant", "tls": "compliant"})
        db.commit.assert_called_once()
        assert result["items"] == {"mfa": "compliant", "tls": "compliant"}

    @pytest.mark.asyncio
    async def test_empty_payload_saves_score_0(self):
        user = MagicMock(spec=User, id=1)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        db.commit = AsyncMock()
        db.add = MagicMock()
        db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "updated_at", datetime.now(timezone.utc)))

        payload = Iso27001SaveIn(items={})
        result = await save_assessment(payload=payload, current_user=user, db=db)

        assert result["score"] == 0
