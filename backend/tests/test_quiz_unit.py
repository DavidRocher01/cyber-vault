"""Unit tests — Feature #14: Quiz maturité NIS2/ISO27001 public."""

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_d_answers():
    """Return full answers with all 'd' (max score)."""
    from app.api.v1.endpoints.quiz import QUESTIONS

    return [{"question_id": q["id"], "answer_id": "d"} for q in QUESTIONS]


def _all_a_answers():
    """Return full answers with all 'a' (min score)."""
    from app.api.v1.endpoints.quiz import QUESTIONS

    return [{"question_id": q["id"], "answer_id": "a"} for q in QUESTIONS]


# ---------------------------------------------------------------------------
# Questions endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_questions_returns_10():
    from app.api.v1.endpoints.quiz import get_questions

    result = await get_questions()
    assert len(result) == 10


@pytest.mark.asyncio
async def test_get_questions_has_required_fields():
    from app.api.v1.endpoints.quiz import get_questions

    questions = await get_questions()
    for q in questions:
        assert "id" in q
        assert "text" in q
        assert "category" in q
        assert "options" in q
        assert len(q["options"]) == 4


@pytest.mark.asyncio
async def test_get_questions_no_scores_exposed():
    from app.api.v1.endpoints.quiz import get_questions

    questions = await get_questions()
    for q in questions:
        assert "scores" not in q


# ---------------------------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_max_score():
    from app.api.v1.endpoints.quiz import QuizAnswer, QuizSubmit, submit_quiz

    payload = QuizSubmit(answers=[QuizAnswer(**a) for a in _all_d_answers()])
    result = await submit_quiz(payload)
    assert result.score == result.max_score
    assert result.percentage == 100
    assert result.level["label"] == "Avancé"


@pytest.mark.asyncio
async def test_submit_min_score():
    from app.api.v1.endpoints.quiz import QuizAnswer, QuizSubmit, submit_quiz

    payload = QuizSubmit(answers=[QuizAnswer(**a) for a in _all_a_answers()])
    result = await submit_quiz(payload)
    assert result.score == 0
    assert result.percentage == 0
    assert result.level["label"] == "Insuffisant"


@pytest.mark.asyncio
async def test_submit_partial_score():
    from app.api.v1.endpoints.quiz import QUESTIONS, QuizAnswer, QuizSubmit, submit_quiz

    # Half max: answer 'b' = 1pt each
    answers = [QuizAnswer(question_id=q["id"], answer_id="b") for q in QUESTIONS]
    payload = QuizSubmit(answers=answers)
    result = await submit_quiz(payload)
    assert result.score == len(QUESTIONS)
    assert 0 < result.percentage < 100


@pytest.mark.asyncio
async def test_submit_returns_category_scores():
    from app.api.v1.endpoints.quiz import QuizAnswer, QuizSubmit, submit_quiz

    payload = QuizSubmit(answers=[QuizAnswer(**a) for a in _all_d_answers()])
    result = await submit_quiz(payload)
    assert len(result.category_scores) > 0
    for cat in result.category_scores:
        assert "category" in cat
        assert "percentage" in cat
        assert 0 <= cat["percentage"] <= 100


@pytest.mark.asyncio
async def test_submit_returns_recommendations():
    from app.api.v1.endpoints.quiz import QuizAnswer, QuizSubmit, submit_quiz

    payload = QuizSubmit(answers=[QuizAnswer(**a) for a in _all_a_answers()])
    result = await submit_quiz(payload)
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_submit_accepts_email():
    from app.api.v1.endpoints.quiz import QuizAnswer, QuizSubmit, submit_quiz

    payload = QuizSubmit(
        answers=[QuizAnswer(**a) for a in _all_d_answers()],
        email="test@example.com",
        company="Test Corp",
    )
    result = await submit_quiz(payload)
    assert result.score == result.max_score


# ---------------------------------------------------------------------------
# Level thresholds
# ---------------------------------------------------------------------------


def test_level_advanced():
    from app.api.v1.endpoints.quiz import MAX_SCORE, _compute_level

    result = _compute_level(int(MAX_SCORE * 0.85))
    assert result["label"] == "Avancé"


def test_level_intermediate():
    from app.api.v1.endpoints.quiz import MAX_SCORE, _compute_level

    result = _compute_level(int(MAX_SCORE * 0.65))
    assert result["label"] == "Intermédiaire"


def test_level_beginner():
    from app.api.v1.endpoints.quiz import MAX_SCORE, _compute_level

    result = _compute_level(int(MAX_SCORE * 0.45))
    assert result["label"] == "Débutant"


def test_level_insufficient():
    from app.api.v1.endpoints.quiz import MAX_SCORE, _compute_level

    result = _compute_level(int(MAX_SCORE * 0.20))
    assert result["label"] == "Insuffisant"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_missing_answers_defaults_to_a():
    # Only answer first 5 questions
    from app.api.v1.endpoints.quiz import QUESTIONS, QuizAnswer, QuizSubmit, submit_quiz

    answers = [QuizAnswer(question_id=q["id"], answer_id="d") for q in QUESTIONS[:5]]
    payload = QuizSubmit(answers=answers)
    result = await submit_quiz(payload)
    # 5 * 3 = 15 for answered, 5 * 0 = 0 for missing → total 15
    assert result.score == 15


@pytest.mark.asyncio
async def test_submit_max_score_value():
    from app.api.v1.endpoints.quiz import MAX_SCORE, QuizAnswer, QuizSubmit, submit_quiz

    payload = QuizSubmit(answers=[QuizAnswer(**a) for a in _all_d_answers()])
    result = await submit_quiz(payload)
    assert result.max_score == MAX_SCORE
    assert MAX_SCORE == 30
