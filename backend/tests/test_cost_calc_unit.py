"""Unit tests — Feature #15: Calculateur coût d'une cyberattaque."""
import pytest


def _answers(size="xs", sector="retail", data="internal", backup="none", coverage="none"):
    return [
        {"key": "size",     "option_id": size},
        {"key": "sector",   "option_id": sector},
        {"key": "data",     "option_id": data},
        {"key": "backup",   "option_id": backup},
        {"key": "coverage", "option_id": coverage},
    ]


# ---------------------------------------------------------------------------
# Questions endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_questions_returns_5():
    from app.api.v1.endpoints.cost_calc import get_questions
    qs = await get_questions()
    assert len(qs) == 5


@pytest.mark.asyncio
async def test_get_questions_no_multiplier_exposed():
    from app.api.v1.endpoints.cost_calc import get_questions
    qs = await get_questions()
    for q in qs:
        for opt in q["options"]:
            assert "multiplier" not in opt


@pytest.mark.asyncio
async def test_get_questions_has_key():
    from app.api.v1.endpoints.cost_calc import get_questions
    qs = await get_questions()
    for q in qs:
        assert "key" in q
        assert "options" in q


# ---------------------------------------------------------------------------
# Cost estimation logic
# ---------------------------------------------------------------------------

def test_compute_cost_returns_positive():
    from app.api.v1.endpoints.cost_calc import _compute_cost
    result = _compute_cost({"size": "xs", "sector": "retail", "data": "internal",
                            "backup": "full", "coverage": "full"})
    assert result["estimated_eur"] > 0


def test_compute_cost_high_risk_greater_than_low_risk():
    from app.api.v1.endpoints.cost_calc import _compute_cost
    high = _compute_cost({"size": "lg", "sector": "finance", "data": "critical",
                          "backup": "none", "coverage": "none"})
    low = _compute_cost({"size": "xs", "sector": "retail", "data": "public",
                         "backup": "full", "coverage": "full"})
    assert high["estimated_eur"] > low["estimated_eur"]


def test_compute_cost_range():
    from app.api.v1.endpoints.cost_calc import _compute_cost
    result = _compute_cost({"size": "md", "sector": "health", "data": "personal",
                            "backup": "partial", "coverage": "partial"})
    assert result["low_eur"] < result["estimated_eur"] < result["high_eur"]


def test_compute_cost_breakdown_sums_to_100():
    from app.api.v1.endpoints.cost_calc import _compute_cost
    result = _compute_cost({"size": "sm", "sector": "retail", "data": "internal",
                            "backup": "basic", "coverage": "insurance"})
    total_pct = sum(b["pct"] for b in result["breakdown"])
    assert total_pct == 100


def test_compute_cost_breakdown_has_5_items():
    from app.api.v1.endpoints.cost_calc import _compute_cost
    result = _compute_cost({})
    assert len(result["breakdown"]) == 5


# ---------------------------------------------------------------------------
# Estimate endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estimate_max_risk():
    from app.api.v1.endpoints.cost_calc import estimate_cost, CostSubmit, CostAnswer
    payload = CostSubmit(answers=[
        CostAnswer(key="size", option_id="lg"),
        CostAnswer(key="sector", option_id="finance"),
        CostAnswer(key="data", option_id="critical"),
        CostAnswer(key="backup", option_id="none"),
        CostAnswer(key="coverage", option_id="none"),
    ])
    result = await estimate_cost(payload)
    assert result.estimated_eur > 100_000


@pytest.mark.asyncio
async def test_estimate_min_risk():
    from app.api.v1.endpoints.cost_calc import estimate_cost, CostSubmit, CostAnswer
    payload = CostSubmit(answers=[
        CostAnswer(key="size", option_id="xs"),
        CostAnswer(key="sector", option_id="retail"),
        CostAnswer(key="data", option_id="public"),
        CostAnswer(key="backup", option_id="full"),
        CostAnswer(key="coverage", option_id="full"),
    ])
    result = await estimate_cost(payload)
    assert result.estimated_eur < 20_000


@pytest.mark.asyncio
async def test_estimate_accepts_email():
    from app.api.v1.endpoints.cost_calc import estimate_cost, CostSubmit, CostAnswer
    payload = CostSubmit(
        answers=[CostAnswer(**a) for a in _answers()],
        email="test@example.com",
        company="Test Corp",
    )
    result = await estimate_cost(payload)
    assert result.estimated_eur > 0


@pytest.mark.asyncio
async def test_estimate_returns_breakdown():
    from app.api.v1.endpoints.cost_calc import estimate_cost, CostSubmit, CostAnswer
    payload = CostSubmit(answers=[CostAnswer(**a) for a in _answers()])
    result = await estimate_cost(payload)
    assert len(result.breakdown) == 5
    for item in result.breakdown:
        assert item["eur"] > 0


@pytest.mark.asyncio
async def test_estimate_partial_answers():
    from app.api.v1.endpoints.cost_calc import estimate_cost, CostSubmit, CostAnswer
    payload = CostSubmit(answers=[CostAnswer(key="size", option_id="md")])
    result = await estimate_cost(payload)
    assert result.estimated_eur > 0
