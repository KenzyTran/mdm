"""Shared fixtures for phase 32 (VN100 backtest in-sample sweep) tests."""
from __future__ import annotations

import pandas as pd
import pytest

TICKERS = ["AAA", "BBB", "CCC"]
N_DAYS = 30


@pytest.fixture
def synthetic_ohlc() -> pd.DataFrame:
    """Tiny OHLC dataframe: 3 fake tickers x 30 trading days.

    Columns: stockcode, tradingdate, openprice, highprice, lowprice, closeprice, volume
    """
    dates = pd.bdate_range("2024-01-02", periods=N_DAYS)
    rows = []
    for ticker_idx, ticker in enumerate(TICKERS):
        base = 100.0 + 10.0 * ticker_idx
        for i, d in enumerate(dates):
            close = base + i * 0.5
            rows.append(
                {
                    "stockcode": ticker,
                    "tradingdate": d,
                    "openprice": close - 0.2,
                    "highprice": close + 0.5,
                    "lowprice": close - 0.5,
                    "closeprice": close,
                    "volume": 100_000 + i * 1_000,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic_universe() -> dict:
    """Constant VN100-like membership: {date: [stockcode,...]} for 30 days."""
    dates = pd.bdate_range("2024-01-02", periods=N_DAYS)
    return {d: list(TICKERS) for d in dates}
