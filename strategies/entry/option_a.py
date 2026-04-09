"""Option A detector — 52-week-high breakout with volume surge (ENTRY-01).

Implements D-03/D-04 from
``.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md``.

Fires on bar ``t`` iff all four clauses hold:

    1. ``adj_close[t] > max(adj_close[t-high_lookback .. t-1])``  (strict new 52wk high)
    2. ``totalvol[t]  >= vol_mult * mean(totalvol[t-vol_lookback .. t-1])``
    3. ``adj_close[t] > adj_open[t]``                              (up bar)
    4. ``adj_close[t] >= (adj_high[t] + adj_low[t]) / 2``          (upper-half close)

Pitfall #1 guard: both the 52wk-high reference and the volume baseline use
``.shift(1)`` before ``.rolling(...)``. Today's own close/volume must not
contaminate the reference window — doing so would turn the strict ``>``
check into a tautological false-negative (the new high would always be the
running max, so ``>`` never fires).
"""
from __future__ import annotations

import pandas as pd

from strategies.entry.config import EntryConfig


def detect_option_a(df: pd.DataFrame, cfg: EntryConfig) -> pd.Series:
    """Detect Option A breakouts on a single-ticker adjusted OHLCV frame.

    Args:
        df: Single-ticker adjusted OHLCV frame sorted ascending by date.
            Required columns: ``adj_open``, ``adj_high``, ``adj_low``,
            ``adj_close``, ``totalvol``.
        cfg: :class:`EntryConfig` providing ``high_lookback``,
            ``vol_lookback``, and ``vol_mult``.

    Returns:
        ``pd.Series[bool]`` aligned to ``df.index``. ``True`` on bars
        where all four D-03 clauses hold; ``False`` elsewhere (including
        warmup bars where the rolling references are undefined).
    """
    c = df["adj_close"]
    o = df["adj_open"]
    h = df["adj_high"]
    lo = df["adj_low"]
    v = df["totalvol"]

    # shift(1) on BOTH: exclude today from the reference windows (pitfall #1).
    hi_ref = c.shift(1).rolling(cfg.high_lookback).max()
    avg_vol = v.shift(1).rolling(cfg.vol_lookback).mean()

    cond_new_high = c > hi_ref
    cond_volume = v >= cfg.vol_mult * avg_vol
    cond_up_bar = c > o
    cond_upper_half = c >= (h + lo) / 2.0

    fires = cond_new_high & cond_volume & cond_up_bar & cond_upper_half
    return fires.fillna(False).astype(bool)
