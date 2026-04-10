"""Tests for momentum RS computation (Phase 35, MOM-01/MOM-02).

Task 1 (RED): RSConfig validation tests pass; compute_rs_panel tests fail.
Task 2 (GREEN): All tests pass after implementation.
"""
from __future__ import annotations

import pytest

from strategies.momentum.config import RSConfig


# --- RSConfig validation tests ---


def test_rsconfig_defaults():
    cfg = RSConfig()
    assert cfg.roc_days == (63, 126, 189, 252)
    assert cfg.roc_weights == (0.4, 0.2, 0.2, 0.2)
    assert cfg.min_history_days == 252


def test_rsconfig_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="roc_weights must sum to 1.0"):
        RSConfig(roc_days=(63,), roc_weights=(0.5,))


def test_rsconfig_days_weights_length_mismatch():
    with pytest.raises(ValueError, match="roc_days and roc_weights must align"):
        RSConfig(roc_days=(63, 126), roc_weights=(0.5,))


# --- compute_rs_panel placeholder tests (RED — expected to fail until Task 2) ---


def test_weighted_roc_placeholder(synthetic_ohlc_panel):
    """Import compute_rs_panel and call with formula='weighted_roc'."""
    from strategies.momentum.rs import compute_rs_panel

    result = compute_rs_panel(synthetic_ohlc_panel, formula="weighted_roc")
    assert hasattr(result, "columns")  # is a DataFrame


def test_roc126_placeholder(synthetic_ohlc_panel):
    """Import compute_rs_panel and call with formula='roc126'."""
    from strategies.momentum.rs import compute_rs_panel

    result = compute_rs_panel(synthetic_ohlc_panel, formula="roc126")
    assert hasattr(result, "columns")  # is a DataFrame
