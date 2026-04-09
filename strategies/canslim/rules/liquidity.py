"""Liquidity rule (CANS-09).

20-day **median** turnover (close * volume) must meet or exceed
``config.liquidity_min_turnover_vnd`` (default 5B VND). Median — not mean —
because a single fat-finger print can otherwise drag an illiquid name over
the threshold.
"""
from __future__ import annotations

import pandas as pd

from strategies.canslim.config import CanslimConfig


def compute_liq(ohlcv: pd.DataFrame, as_of_date, config: CanslimConfig) -> bool:
    """Return True iff 20d median turnover >= ``liquidity_min_turnover_vnd``.

    Args:
        ohlcv: DataFrame with ``tradingdate``, ``closeindex``, ``totalvol``.
        as_of_date: Signal date (inclusive).
        config: CanslimConfig with ``liquidity_min_turnover_vnd`` threshold.

    Returns:
        True when the most recent 20 bars have median turnover at or above
        threshold. False if fewer than 20 bars of history are available.
    """
    df = ohlcv[ohlcv["tradingdate"] <= as_of_date].tail(20)
    if len(df) < 20:
        return False
    turnover = (df["closeindex"] * df["totalvol"]).median()
    return float(turnover) >= config.liquidity_min_turnover_vnd


def check_liquidity_turnover(ticker: str, as_of_date, config) -> bool:
    """Deprecated: use :func:`compute_liq` with an ohlcv DataFrame."""
    raise NotImplementedError("Use compute_liq(ohlcv, as_of_date, config)")
