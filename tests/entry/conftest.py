"""Shared fixtures for ``tests/entry/`` — synthetic OHLCV + MDM state builders.

These fixture helpers are the raw material for every ENTRY-01..ENTRY-05 test.
Individual test modules copy the base frame and mutate specific bars to force
detector clauses on or off. Determinism via a fixed seed so failures are
reproducible.
"""
from __future__ import annotations

from typing import Iterable, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest


_OHLCV_COLUMNS = ["adj_open", "adj_high", "adj_low", "adj_close", "totalvol"]


def _make_ohlcv(
    n_bars: int = 260,
    start_date: str = "2020-01-01",
    seed: int = 42,
) -> pd.DataFrame:
    """Build a deterministic single-ticker adjusted OHLCV frame.

    Args:
        n_bars: Number of business-day bars. Default 260 (> 252 so the
            Option A 52-week-high window is fully populated).
        start_date: First bar date (business day coerced).
        seed: Numpy RNG seed for reproducible noise.

    Returns:
        pd.DataFrame indexed by a business-day DatetimeIndex with columns
        ``adj_open, adj_high, adj_low, adj_close, totalvol``. Close is a
        deterministic random walk starting at 100.0; OHLC is derived sanely
        (open = previous close with small noise; high/low bracket open/close
        with a tiny jitter); volume baseline is 1_000_000 with gaussian noise.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start=start_date, periods=n_bars)

    close = np.empty(n_bars)
    close[0] = 100.0
    steps = rng.normal(loc=0.0, scale=0.5, size=n_bars - 1)
    for i in range(1, n_bars):
        close[i] = max(1.0, close[i - 1] + steps[i - 1])

    open_ = np.empty(n_bars)
    open_[0] = close[0]
    open_[1:] = close[:-1] + rng.normal(0.0, 0.1, size=n_bars - 1)

    jitter_hi = np.abs(rng.normal(0.3, 0.1, size=n_bars))
    jitter_lo = np.abs(rng.normal(0.3, 0.1, size=n_bars))
    high = np.maximum(open_, close) + jitter_hi
    low = np.minimum(open_, close) - jitter_lo

    vol = rng.normal(1_000_000.0, 50_000.0, size=n_bars)
    vol = np.clip(vol, 100_000.0, None)

    df = pd.DataFrame(
        {
            "adj_open": open_,
            "adj_high": high,
            "adj_low": low,
            "adj_close": close,
            "totalvol": vol,
        },
        index=idx,
    )
    return df


@pytest.fixture
def make_ohlcv():
    """Fixture: callable that returns a synthetic OHLCV frame.

    Usage::

        def test_foo(make_ohlcv):
            df = make_ohlcv()  # or make_ohlcv(n_bars=500, seed=7)
    """
    return _make_ohlcv


def _make_buy_breakout_bar(df: pd.DataFrame, idx: int) -> pd.DataFrame:
    """Mutate bar at positional ``idx`` to satisfy all four Option A clauses.

    Sets the bar to:
        - close > max(close[t-252..t-1])  (new 52-wk high, strict)
        - volume >= 1.5 * mean(vol[t-50..t-1])
        - close > open (up bar)
        - close in upper half of range

    Returns a new DataFrame (input not mutated in-place at the caller's level
    beyond what pandas' ``.copy()`` provides).
    """
    out = df.copy()
    prev_close = out["adj_close"].iloc[:idx]
    prev_vol = out["totalvol"].iloc[max(0, idx - 50) : idx]

    new_high = float(prev_close.max()) * 1.05  # 5% above prior max
    new_vol = float(prev_vol.mean()) * 2.0     # 2x trailing avg, well above 1.5x

    bar_open = new_high * 0.98
    bar_low = new_high * 0.97
    bar_high = new_high * 1.005
    bar_close = new_high  # strictly > prior max; (high+low)/2 < close -> upper half

    out.iloc[idx, out.columns.get_loc("adj_open")] = bar_open
    out.iloc[idx, out.columns.get_loc("adj_low")] = bar_low
    out.iloc[idx, out.columns.get_loc("adj_high")] = bar_high
    out.iloc[idx, out.columns.get_loc("adj_close")] = bar_close
    out.iloc[idx, out.columns.get_loc("totalvol")] = new_vol
    return out


@pytest.fixture
def make_buy_breakout_bar():
    """Fixture: callable ``(df, idx) -> df`` that plants a valid Option A bar."""
    return _make_buy_breakout_bar


def _make_mdm_state(
    dates: pd.DatetimeIndex,
    transitions: Iterable[Tuple[pd.Timestamp, str]],
    initial: str = "CASH",
) -> pd.Series:
    """Materialize an MDM state Series from a list of (date, new_state) tuples.

    Args:
        dates: Target DatetimeIndex.
        transitions: Iterable of ``(effective_date, new_state)`` pairs. Each
            new_state must be one of ``"BUY"``, ``"CASH"``, ``"SELL"``. The
            new state applies from the effective_date forward until the next
            transition.
        initial: State before the first transition. Default ``"CASH"``.

    Returns:
        pd.Series[str] indexed by ``dates``, forward-filled between
        transition points.
    """
    valid = {"BUY", "CASH", "SELL"}
    if initial not in valid:
        raise ValueError(f"initial must be one of {valid}")
    out = pd.Series(initial, index=dates, dtype=object)
    for eff_date, new_state in transitions:
        if new_state not in valid:
            raise ValueError(f"new_state {new_state!r} must be one of {valid}")
        out.loc[out.index >= eff_date] = new_state
    return out


@pytest.fixture
def make_mdm_state():
    """Fixture: callable ``(dates, transitions, initial='CASH') -> pd.Series``."""
    return _make_mdm_state
