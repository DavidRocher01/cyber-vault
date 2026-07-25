"""Unit tests — logique de badges gamification (streak + bonus XP)."""

from datetime import date

from app.services.awareness_gamification import (
    _BADGE_XP_BONUS,
    BADGE_CATALOG,
    _longest_consecutive_run,
)


def test_xp_bonus_map_covers_all_badges():
    assert set(_BADGE_XP_BONUS) == {b["slug"] for b in BADGE_CATALOG}
    assert all(v > 0 for v in _BADGE_XP_BONUS.values())


def test_longest_consecutive_run_empty():
    assert _longest_consecutive_run(set()) == 0


def test_longest_consecutive_run_single():
    assert _longest_consecutive_run({date(2026, 7, 1)}) == 1


def test_longest_consecutive_run_seven_consecutive():
    days = {date(2026, 7, d) for d in range(1, 8)}
    assert _longest_consecutive_run(days) == 7


def test_longest_consecutive_run_with_gap():
    # 3 consecutifs, trou, 2 consecutifs -> meilleure serie = 3
    days = {
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
        date(2026, 7, 10),
        date(2026, 7, 11),
    }
    assert _longest_consecutive_run(days) == 3


def test_longest_consecutive_run_unordered_input():
    days = {date(2026, 7, 5), date(2026, 7, 3), date(2026, 7, 4)}
    assert _longest_consecutive_run(days) == 3
