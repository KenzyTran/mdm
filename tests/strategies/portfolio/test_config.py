"""Tests for PortfolioConfig fail-loud validation (Phase 31 plan 01)."""
from __future__ import annotations

import pytest

from strategies.portfolio.config import PortfolioConfig


def test_default_config_instantiates_cleanly():
    cfg = PortfolioConfig()
    assert cfg.max_slots == 8
    assert cfg.slot_weight == 0.125
    assert cfg.entry_mode == "union"
    assert cfg.t_plus == 2


def test_invalid_entry_mode_raises():
    with pytest.raises(ValueError, match="entry_mode"):
        PortfolioConfig(entry_mode="X")


def test_zero_max_slots_raises():
    with pytest.raises(ValueError, match="max_slots"):
        PortfolioConfig(max_slots=0)


def test_hard_stop_out_of_range_raises():
    with pytest.raises(ValueError, match="hard_stop_pct"):
        PortfolioConfig(hard_stop_pct=1.5)


def test_negative_cost_raises():
    with pytest.raises(ValueError, match="entry_commission"):
        PortfolioConfig(entry_commission=-0.001)


def test_state_imports():
    from strategies.portfolio.state import PositionBook

    book = PositionBook(max_slots=8)
    assert book.slots.free_slots() == 8
    assert book.slots.has_open("AAA") is False
    assert book.completed_trades == []
    assert book.unfilled == []


def test_cooldown_clock():
    """D-21: earliest re-entry bar = exit_bar + cooldown_days + 1 (D+6 at 5d)."""
    from strategies.portfolio.state import CooldownRegistry

    reg = CooldownRegistry()
    reg.register("AAA", exit_bar_idx=10)
    # Bars 11..15 still cooling (cooldown_days=5 → earliest re-entry = bar 16)
    for b in range(11, 16):
        assert reg.is_cooling("AAA", current_bar_idx=b, cooldown_days=5) is True
    assert reg.is_cooling("AAA", current_bar_idx=16, cooldown_days=5) is False
    # Untracked ticker never cooling
    assert reg.is_cooling("ZZZ", current_bar_idx=0, cooldown_days=5) is False
