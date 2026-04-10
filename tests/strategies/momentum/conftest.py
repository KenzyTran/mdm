"""Fixtures for momentum strategy tests (Phase 35)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_ohlc_panel() -> pd.DataFrame:
    """Deterministic price panel for 5 tickers over 300 trading days.

    Ticker trends:
        AAA: +0.1%/day (strong uptrend -- should rank highest)
        BBB: +0.05%/day (moderate uptrend)
        CCC:  0.0%/day (flat -- middle rank)
        DDD: -0.05%/day (moderate downtrend)
        EEE: -0.1%/day (strong downtrend -- should rank lowest)

    Returns long-format DataFrame with columns: stockcode, tradingdate, adj_close.
    """
    dates = pd.bdate_range("2023-01-02", periods=300)
    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    daily_returns = [0.001, 0.0005, 0.0, -0.0005, -0.001]

    frames = []
    for ticker, ret in zip(tickers, daily_returns):
        prices = 100.0 * np.cumprod(np.concatenate([[1.0], np.full(299, 1.0 + ret)]))
        frames.append(
            pd.DataFrame(
                {
                    "stockcode": ticker,
                    "tradingdate": dates,
                    "adj_close": prices,
                }
            )
        )

    return pd.concat(frames, ignore_index=True)
