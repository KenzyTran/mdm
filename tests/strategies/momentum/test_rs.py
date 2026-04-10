"""Tests for momentum RS computation (Phase 35, MOM-01/MOM-02).

Task 1 (RED): RSConfig validation tests pass; compute_rs_panel tests fail.
Task 2 (GREEN): All tests pass after implementation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategies.momentum.config import RSConfig
from strategies.momentum.rs import compute_rs_panel


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


# --- compute_rs_panel tests (GREEN) ---


def test_weighted_roc(synthetic_ohlc_panel):
    """weighted_roc formula: AAA (strongest uptrend) ranks highest, EEE lowest."""
    result = compute_rs_panel(synthetic_ohlc_panel, formula="weighted_roc")
    assert isinstance(result, pd.DataFrame)

    last_date = result["date"].max()
    last = result[result["date"] == last_date].set_index("ticker")

    assert last.loc["AAA", "rs_rank"] > last.loc["EEE", "rs_rank"]
    assert last.loc["AAA", "rs_rank"] > last.loc["CCC", "rs_rank"]


def test_roc126(synthetic_ohlc_panel):
    """roc126 formula: ranking order AAA > BBB > CCC > DDD > EEE on last date."""
    result = compute_rs_panel(synthetic_ohlc_panel, formula="roc126")

    last_date = result["date"].max()
    last = result[result["date"] == last_date].set_index("ticker")

    ranks = [last.loc[t, "rs_rank"] for t in ["AAA", "BBB", "CCC", "DDD", "EEE"]]
    # Each should be strictly greater than the next
    for i in range(len(ranks) - 1):
        assert ranks[i] > ranks[i + 1], f"Rank order violated at position {i}"


def test_rank_range(synthetic_ohlc_panel):
    """All rs_rank values must be in [0, 100]."""
    result = compute_rs_panel(synthetic_ohlc_panel, formula="weighted_roc")
    assert (result["rs_rank"] >= 0).all()
    assert (result["rs_rank"] <= 100).all()


def test_nan_insufficient_history(synthetic_ohlc_panel):
    """Ticker with only 100 days of data should NOT appear (dropped by dropna)."""
    # Add a short-history ticker
    dates = pd.bdate_range("2024-01-02", periods=100)
    short_ticker = pd.DataFrame(
        {
            "stockcode": "FFF",
            "tradingdate": dates,
            "adj_close": np.linspace(100, 110, 100),
        }
    )
    panel = pd.concat([synthetic_ohlc_panel, short_ticker], ignore_index=True)

    result = compute_rs_panel(panel, formula="weighted_roc")
    # FFF should not have any ranked rows (insufficient history for 252-day ROC)
    fff_rows = result[result["ticker"] == "FFF"]
    assert len(fff_rows) == 0, f"FFF should have no ranked rows but got {len(fff_rows)}"


def test_unknown_formula(synthetic_ohlc_panel):
    """Unknown formula raises ValueError."""
    with pytest.raises(ValueError, match="Unknown formula"):
        compute_rs_panel(synthetic_ohlc_panel, formula="bad")


def test_output_columns(synthetic_ohlc_panel):
    """Result has exactly columns [date, ticker, rs_raw, rs_rank]."""
    result = compute_rs_panel(synthetic_ohlc_panel, formula="roc126")
    assert list(result.columns) == ["date", "ticker", "rs_raw", "rs_rank"]
