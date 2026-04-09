"""Tests for liquidity rule — CANS-09."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from strategies.canslim.config import CanslimConfig
from strategies.canslim.rules import liquidity


def _mk_ohlcv(turnovers, start=date(2024, 1, 1)):
    """Build a minimal ohlcv frame from a turnover series (VND).

    closeindex fixed at 1.0 so totalvol == turnover, keeping math trivial.
    """
    rows = []
    for i, t in enumerate(turnovers):
        rows.append({
            "tradingdate": start + timedelta(days=i),
            "closeindex": 1.0,
            "totalvol": float(t),
        })
    return pd.DataFrame(rows)


def test_liquidity_module_imports():
    assert hasattr(liquidity, "compute_liq")


def test_compute_liq_all_above_threshold_passes():
    cfg = CanslimConfig()  # 5B VND default
    df = _mk_ohlcv([10_000_000_000] * 25)
    assert liquidity.compute_liq(df, df["tradingdate"].iloc[-1], cfg) is True


def test_compute_liq_all_below_threshold_fails():
    cfg = CanslimConfig()
    df = _mk_ohlcv([1_000_000_000] * 25)
    assert liquidity.compute_liq(df, df["tradingdate"].iloc[-1], cfg) is False


def test_compute_liq_insufficient_history_fails():
    cfg = CanslimConfig()
    df = _mk_ohlcv([100_000_000_000] * 10)  # plenty of turnover but <20 bars
    assert liquidity.compute_liq(df, df["tradingdate"].iloc[-1], cfg) is False


def test_compute_liq_uses_median_not_mean():
    """19 tiny bars + 1 huge bar — mean is ~6B, median is 1B → must FAIL."""
    cfg = CanslimConfig()
    df = _mk_ohlcv([1_000_000_000] * 19 + [100_000_000_000])
    assert liquidity.compute_liq(df, df["tradingdate"].iloc[-1], cfg) is False

    # Symmetric case: 10x 1B and 10x 20B → median 10.5B → passes.
    df2 = _mk_ohlcv([1_000_000_000] * 10 + [20_000_000_000] * 10)
    assert liquidity.compute_liq(df2, df2["tradingdate"].iloc[-1], cfg) is True
