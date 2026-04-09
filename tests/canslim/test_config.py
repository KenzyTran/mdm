"""Tests for CanslimConfig — CANS-11 (plan 29-02)."""
from dataclasses import asdict

import pytest

from strategies.canslim.config import CanslimConfig


def test_defaults_match_d12():
    """Test 1: CanslimConfig() returns D-12 defaults."""
    cfg = CanslimConfig()
    assert cfg.c_threshold == 0.20
    assert cfg.a_threshold == 0.15
    assert cfg.n_within_high == 0.15
    assert cfg.s_vol_mult == 1.5
    assert cfg.l_rs_threshold == 80.0
    assert cfg.i_lookback_days == 20
    assert cfg.liquidity_min_turnover_vnd == 5_000_000_000.0


def test_kwarg_override_only_affects_specified_field():
    """Test 2: only the overridden field changes."""
    cfg = CanslimConfig(c_threshold=0.30)
    assert cfg.c_threshold == 0.30
    assert cfg.a_threshold == 0.15  # default preserved


def test_negative_c_threshold_raises():
    """Test 3: negative c_threshold is rejected."""
    with pytest.raises(ValueError, match="c_threshold must be >= 0"):
        CanslimConfig(c_threshold=-0.1)


def test_n_within_high_out_of_range_raises():
    """Test 4: n_within_high > 1 is rejected."""
    with pytest.raises(ValueError, match=r"n_within_high must be in \(0, 1\]"):
        CanslimConfig(n_within_high=1.5)


def test_l_rs_threshold_out_of_range_raises():
    """Test 5: l_rs_threshold > 100 is rejected."""
    with pytest.raises(ValueError, match=r"l_rs_threshold must be in \[0, 100\]"):
        CanslimConfig(l_rs_threshold=150)


def test_s_vol_mult_below_one_raises():
    """Test 6: s_vol_mult < 1 is rejected."""
    with pytest.raises(ValueError, match="s_vol_mult must be >= 1"):
        CanslimConfig(s_vol_mult=0.5)


def test_i_lookback_days_zero_raises():
    """Test 7: i_lookback_days < 1 is rejected."""
    with pytest.raises(ValueError, match="i_lookback_days must be >= 1"):
        CanslimConfig(i_lookback_days=0)


def test_asdict_round_trip_preserves_defaults():
    """Test 8: asdict() round-trips and preserves defaults."""
    cfg = CanslimConfig()
    data = asdict(cfg)
    assert data["c_threshold"] == 0.20
    assert data["l_rs_threshold"] == 80.0
    assert data["liquidity_min_turnover_vnd"] == 5_000_000_000.0
    # Round-trip via to_dict too
    assert cfg.to_dict() == data
    # Rebuild from dict
    cfg2 = CanslimConfig(**{k: v for k, v in data.items()})
    assert cfg2.to_dict() == data


def test_config_is_mutable_not_frozen():
    """Test 9: frozen=False — sweep scripts need attribute reassignment."""
    cfg = CanslimConfig()
    cfg.c_threshold = 0.25  # should not raise
    assert cfg.c_threshold == 0.25
