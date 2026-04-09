"""Synthetic long-form OHLCV panel fixtures for Phase 31 portfolio tests.

Generates deterministic multi-ticker panels with VN-style ceiling/floor
columns derived from previous close * (1 ± 0.07). Supports forcing
ceiling-lock or floor-lock on specific bars via the ``lock_days`` hook so
that downstream plans can unit-test the 7% price-limit guard.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


def make_panel(
    tickers: Iterable[str] = ("AAA", "BBB", "CCC"),
    n_bars: int = 60,
    seed: int = 42,
    lock_days: Optional[Dict[str, List[Tuple[int, str]]]] = None,
    start: str = "2020-01-02",
) -> pd.DataFrame:
    """Build a deterministic long-form OHLCV+ceiling/floor panel.

    Args:
        tickers: ticker symbols to generate.
        n_bars: number of business days per ticker.
        seed: numpy RNG seed for reproducibility.
        lock_days: optional ``{ticker: [(bar_idx, "ceiling"|"floor"), ...]}``
            forcing ``open == high == low == close == ceiling_or_floor`` at
            the specified bar, to simulate a VN 7% limit lock.
        start: first business date (inclusive).

    Returns:
        DataFrame with columns
        ``date, ticker, open, high, low, close, volume, ceiling, floor``.
    """
    rng = np.random.default_rng(seed)
    lock_days = lock_days or {}
    dates = pd.bdate_range(start=start, periods=n_bars)
    frames: List[pd.DataFrame] = []

    for t_idx, ticker in enumerate(tickers):
        # Seeded per-ticker walk around ~100 * (1 + t_idx * 0.1)
        base = 100.0 * (1.0 + 0.1 * t_idx)
        returns = rng.normal(loc=0.0005, scale=0.012, size=n_bars)
        closes = base * np.exp(np.cumsum(returns))
        prev_close = np.concatenate([[base], closes[:-1]])
        ceiling = np.round(prev_close * 1.07, 2)
        floor = np.round(prev_close * 0.93, 2)

        # Keep opens/highs/lows within [floor, ceiling]
        spread = np.abs(rng.normal(loc=0.0, scale=0.008, size=n_bars)) * closes
        opens = np.clip(closes - spread * 0.5, floor, ceiling)
        highs = np.clip(np.maximum(opens, closes) + spread * 0.5, floor, ceiling)
        lows = np.clip(np.minimum(opens, closes) - spread * 0.5, floor, ceiling)
        closes_clipped = np.clip(closes, floor, ceiling)
        volume = rng.integers(50_000, 500_000, size=n_bars).astype(float)

        df = pd.DataFrame(
            {
                "date": dates,
                "ticker": ticker,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes_clipped,
                "volume": volume,
                "ceiling": ceiling,
                "floor": floor,
            }
        )

        # Apply ceiling/floor locks
        for bar_idx, kind in lock_days.get(ticker, []):
            if kind == "ceiling":
                px = df.at[bar_idx, "ceiling"]
            elif kind == "floor":
                px = df.at[bar_idx, "floor"]
            else:
                raise ValueError(f"lock_days kind must be 'ceiling'|'floor', got {kind!r}")
            df.at[bar_idx, "open"] = px
            df.at[bar_idx, "high"] = px
            df.at[bar_idx, "low"] = px
            df.at[bar_idx, "close"] = px

        frames.append(df)

    return pd.concat(frames, ignore_index=True)
