"""Option C (Pocket Pivot) detector — ENTRY-02.

Implements D-05/D-06 from
``.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md``.

Fires on bar ``t`` iff all four clauses hold:

    1. ``adj_close[t] > adj_open[t]``                               (up bar)
    2. ``adj_close[t] >= MA(adj_close, ma_length)[t]``              (above MA50)
    3. ``totalvol[t]  > max(down_day_vols[t-pocket_lookback .. t-1])``
       — pocket-pivot volume; fail-closed when there are NO down days
       in that window (D-05 pitfall #2).
    4. ``adj_close[t] >= (1 - base_tolerance) * max(adj_high[t-ma_length .. t-1])``
       — within base tolerance of the 50-day high.

Pitfall #2 guard: ``down_vols`` masks up-day volume with ``NaN`` via
``.where(is_down_day)``. If the entire ``pocket_lookback`` window contains
no down days, pandas' rolling-max returns ``NaN``, and ``v > NaN`` is
``False``. **Do NOT ``fillna(0)``** — that converts a missing reference
into a free pass and lets any positive volume satisfy the pocket-pivot
clause (free-pass bug).
"""
from __future__ import annotations

import pandas as pd

from strategies.entry.config import EntryConfig


def detect_option_c(df: pd.DataFrame, cfg: EntryConfig) -> pd.Series:
    """Detect Option C pocket-pivot entries on a single-ticker frame.

    Args:
        df: Single-ticker adjusted OHLCV frame sorted ascending by date.
            Required columns: ``adj_open``, ``adj_high``, ``adj_low``,
            ``adj_close``, ``totalvol``.
        cfg: :class:`EntryConfig` providing ``ma_length``,
            ``pocket_lookback``, and ``base_tolerance``.

    Returns:
        ``pd.Series[bool]`` aligned to ``df.index``. ``True`` when all
        four D-05 clauses hold; ``False`` elsewhere. Explicitly
        ``False`` when the last ``pocket_lookback`` sessions contain
        zero down days (NaN propagation = fail-closed).
    """
    c = df["adj_close"]
    o = df["adj_open"]
    h = df["adj_high"]
    v = df["totalvol"]

    prev_close = c.shift(1)
    is_down_day = c < prev_close

    # Mask up-day volume with NaN. All-NaN rolling windows produce NaN,
    # which propagates False through the `>` comparison: NaN propagation
    # = fail-closed per D-05 pitfall #2. Do NOT fillna(0) here.
    down_vols = v.where(is_down_day)
    max_down_vol = (
        down_vols.shift(1).rolling(cfg.pocket_lookback, min_periods=1).max()
    )

    ma = c.rolling(cfg.ma_length).mean()
    hi_ref = h.shift(1).rolling(cfg.ma_length).max()

    cond_up_bar = c > o
    cond_above_ma = c >= ma
    cond_pocket_vol = v > max_down_vol  # NaN -> False
    cond_near_base = c >= (1.0 - cfg.base_tolerance) * hi_ref

    fires = cond_up_bar & cond_above_ma & cond_pocket_vol & cond_near_base
    return fires.fillna(False).astype(bool)
