"""Shared fixtures for tests/canslim — Wave 0 scaffold."""
from __future__ import annotations

import pandas as pd
import pytest

from strategies.canslim.config import CanslimConfig


@pytest.fixture
def canslim_config() -> CanslimConfig:
    """Default CanslimConfig instance."""
    return CanslimConfig()


@pytest.fixture
def fake_ohlcv() -> pd.DataFrame:
    """30 trading days x 3 tickers of synthetic OHLCV."""
    dates = pd.date_range("2025-01-01", periods=30, freq="B")
    rows = []
    for ticker in ("AAA", "BBB", "CCC"):
        for i, d in enumerate(dates):
            base = 100 + i
            rows.append(
                {
                    "stockcode": ticker,
                    "tradingdate": d,
                    "openprice": base,
                    "highestprice": base + 1,
                    "lowestprice": base - 1,
                    "closeprice": base + 0.5,
                    "totalvol": 1_000_000 + i * 1000,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def fake_eps() -> pd.DataFrame:
    """Synthetic quarterly EPS rows with publish_date column."""
    return pd.DataFrame(
        [
            {"stockcode": "AAA", "publish_date": "2025-01-15", "eps": 1500},
            {"stockcode": "AAA", "publish_date": "2024-10-15", "eps": 1200},
            {"stockcode": "BBB", "publish_date": "2025-01-20", "eps": 800},
            {"stockcode": "CCC", "publish_date": "2025-01-25", "eps": 2000},
        ]
    )


@pytest.fixture
def fake_stock_list() -> pd.DataFrame:
    """10 tickers with sector labels."""
    return pd.DataFrame(
        [
            {"stockcode": f"T{i:02d}", "sector": "nonbank" if i % 2 else "bank"}
            for i in range(10)
        ]
    )
