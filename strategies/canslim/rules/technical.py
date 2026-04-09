"""Technical rules N (CANS-05) and S helper (CANS-06).

Implemented by plan 29-06.

- N: close within ``config.n_within_high`` of the 252-day high.
- S: today's volume >= ``config.s_vol_mult`` * avgvol50.

Both helpers operate on a long-format OHLCV DataFrame for a single ticker
with columns ``['tradingdate', 'closeindex', 'highestindex', 'totalvol']``
sorted ascending by date. Price reads should flow through
``connectors.adjust.adjust_ohlc`` before reaching these functions (per
29-CONTEXT.md).
"""
from __future__ import annotations

import pandas as pd

from strategies.canslim.config import CanslimConfig


def compute_n(ohlcv: pd.DataFrame, as_of_date, config: CanslimConfig) -> bool:
    """N rule: close within ``config.n_within_high`` of the 252d high.

    Returns False if fewer than ``config.min_history_days`` bars at or before
    ``as_of_date``.
    """
    df = ohlcv[ohlcv["tradingdate"] <= as_of_date].tail(config.min_history_days)
    if len(df) < config.min_history_days:
        return False
    high_252 = float(df["highestindex"].max())
    close = float(df.iloc[-1]["closeindex"])
    return close >= (1.0 - config.n_within_high) * high_252


def compute_s(ohlcv: pd.DataFrame, as_of_date, config: CanslimConfig) -> bool:
    """S helper: today's volume >= ``config.s_vol_mult`` * avgvol50.

    Uses the 50 bars preceding ``as_of_date`` for the average. Returns False
    if fewer than 51 bars are available.
    """
    df = ohlcv[ohlcv["tradingdate"] <= as_of_date].tail(51)
    if len(df) < 51:
        return False
    avg50 = float(df.iloc[:-1]["totalvol"].mean())
    today_vol = float(df.iloc[-1]["totalvol"])
    return today_vol >= config.s_vol_mult * avg50


# --- Legacy stub signatures (kept for plan-01 compatibility) ---------------


def check_n_new_high(ticker: str, as_of_date, config) -> bool:
    """Legacy stub (CANS-05 entry point). Deprecated — use compute_n."""
    raise NotImplementedError("Use compute_n(ohlcv, as_of_date, config)")


def check_n_pivot_breakout(ticker: str, as_of_date, config) -> bool:
    """Legacy stub (CANS-06). Pivot breakout is handled in a later plan."""
    raise NotImplementedError("Pivot breakout implemented in a later plan")
