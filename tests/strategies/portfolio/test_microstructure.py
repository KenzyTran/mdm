"""Tests for strategies.portfolio.microstructure (D-17, D-18, D-19)."""
from strategies.portfolio.microstructure import (
    compute_ceiling,
    compute_floor,
    is_ceiling_locked,
    is_floor_locked,
    t2_earliest_sell_bar,
)


def test_ceiling_value():
    assert compute_ceiling(100) == 107.0


def test_floor_value():
    assert compute_floor(100) == 93.0


def test_ceiling_locked_true():
    assert is_ceiling_locked(107.0, 107.0, 107.0, 107.0) is True


def test_ceiling_locked_false_range():
    assert is_ceiling_locked(107.0, 107.0, 106.5, 107.0) is False


def test_ceiling_locked_false_below():
    assert is_ceiling_locked(106.0, 107.0, 105.5, 107.0) is False


def test_floor_locked_true():
    assert is_floor_locked(93.0, 93.0, 93.0, 93.0) is True


def test_floor_locked_false_range():
    assert is_floor_locked(93.0, 94.0, 93.0, 93.0) is False


def test_t2():
    assert t2_earliest_sell_bar(10, t_plus=2) == 13
