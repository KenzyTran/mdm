"""MDM BUY window tracker (ENTRY-03).

Implements D-07..D-10 and D-20 from
``.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md``.

A *BUY window* is a contiguous range of trading bars during which an
Option A / Option C signal is eligible to convert to an actual entry.
Each window is anchored to a CASH/SELL -> BUY state transition and lasts
``window_days`` trading bars **inclusive** — the transition bar itself is
day 1, and the terminal bar is day ``window_days``.

Locked behavior (30-01-NOTES.md §3): if the MDM state Series begins
already in ``"BUY"`` with no prior observable ``"CASH"``/``"SELL"`` bar,
that is **NOT** a transition and does NOT open a window. The fail-closed
default is implemented naturally via ``.shift(1)``: the NaN at index 0
evaluates ``False`` in ``isin(["CASH", "SELL"])``.

Pitfall #3 guard: day-1 inclusive means the window is ``[t, t+window_days-1]``
where ``t`` is the transition bar — not ``[t+1, t+window_days]``. A naive
``t+1`` offset would strand same-day signals and double-count day 20.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd


def compute_buy_windows(
    state: pd.Series,
    window_days: int = 20,
) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """Return one ``(start, end_inclusive)`` window per CASH/SELL -> BUY transition.

    Args:
        state: ``pd.Series`` indexed by trading-day timestamps with values
            in ``{"BUY", "CASH", "SELL"}``. Must be sorted ascending.
        window_days: Window length in trading bars. The transition bar is
            day 1; the terminal bar is day ``window_days`` (inclusive).
            Default 20 per D-07/D-20.

    Returns:
        List of ``(start_date, end_date_inclusive)`` tuples, one per
        observed CASH/SELL -> BUY transition. Continuous BUY does NOT
        extend an existing window; a series that starts in BUY without
        a prior CASH/SELL bar produces NO initial window (locked decision
        per 30-01-NOTES.md §3). Overlapping windows are kept independent
        if a new transition happens mid-window.
    """
    if window_days < 1:
        raise ValueError("window_days must be >= 1")

    prev = state.shift(1)
    is_transition = (state == "BUY") & (prev.isin(["CASH", "SELL"]))

    idx = state.index
    n = len(idx)
    windows: List[Tuple[pd.Timestamp, pd.Timestamp]] = []
    for t in idx[is_transition]:
        i = idx.get_loc(t)
        j = min(i + window_days - 1, n - 1)
        windows.append((idx[i], idx[j]))
    return windows


def is_in_any_window(
    signal_date: pd.Timestamp,
    windows: List[Tuple[pd.Timestamp, pd.Timestamp]],
    trading_days_index: Optional[pd.DatetimeIndex] = None,
) -> Tuple[bool, Optional[int]]:
    """Check whether ``signal_date`` falls within any BUY window.

    Args:
        signal_date: Candidate entry-signal bar.
        windows: Output of :func:`compute_buy_windows`.
        trading_days_index: Optional trading-day index used to compute
            the 1-indexed ``days_since_buy`` offset as a count of bars
            between the window start and ``signal_date``. When omitted,
            offset is computed as ``(signal_date - start).days + 1``,
            which is only correct if the state series is contiguous
            trading days without gaps; callers that care should pass the
            engine's trading-day index.

    Returns:
        ``(True, days_since_buy)`` where ``days_since_buy`` is 1-indexed
        (1 = transition bar itself, ``window_days`` = terminal bar) if
        ``signal_date`` falls within any window. ``(False, None)``
        otherwise.
    """
    signal_ts = pd.Timestamp(signal_date)
    for start, end in windows:
        if start <= signal_ts <= end:
            if trading_days_index is not None:
                i = trading_days_index.get_loc(start)
                j = trading_days_index.get_loc(signal_ts)
                return True, j - i + 1
            # Fallback: count business days inclusive between start and
            # signal_date. This matches the trading-day cadence assumed by
            # the MDM state series in the common case where it is built on
            # ``pd.bdate_range``. Callers that use a non-bday trading
            # calendar (e.g. HOSE with holidays) should pass
            # ``trading_days_index`` for exact offsets.
            return True, len(pd.bdate_range(start, signal_ts))
    return False, None


# Alias for the name used in the 30-02-PLAN interfaces section.
find_window = is_in_any_window
