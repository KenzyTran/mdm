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
