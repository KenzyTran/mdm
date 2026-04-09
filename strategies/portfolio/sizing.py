"""Sizing, ADV20 liquidity gate, and CANSLIM tie-break sort.

Phase 31 Plan 03, Task 2. Pure functions, no state.

Key invariants:
- adv20 uses STRICTLY close[t-20..t-1] and vol[t-20..t-1] — NO look-ahead
  (per memory feedback_equity_formula.md: equity formula bug was caused
  by using state[i] instead of state[i-1], a 707% vs 93% look-ahead bug).
- lot_round_shares floors down to lot_size units — any residual stays in
  cash (D-11).
- liquidity_gate_passes fails closed on NaN adv20.
- sort_by_canslim drops candidates with missing score into a separate list
  (engine logs them as unfilled/canslim_score_missing per D-10).
"""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Tuple

import pandas as pd

from .config import PortfolioConfig


def target_notional(nav_prev: float, cfg: PortfolioConfig) -> float:
    """Target VND notional for one slot = NAV[t-1] * slot_weight (D-09)."""
    return nav_prev * cfg.slot_weight


def lot_round_shares(
    target_notional_vnd: float, fill_price: float, lot_size: int = 100
) -> int:
    """Floor target notional to whole 100-lot shares (D-09/D-11).

    Never returns negative. Residual cash stays in book.
    """
    if fill_price <= 0 or target_notional_vnd <= 0:
        return 0
    raw_shares = target_notional_vnd / fill_price
    lots = math.floor(raw_shares / lot_size)
    return max(0, lots * lot_size)


def adv20(close_series: pd.Series, vol_series: pd.Series, bar_idx: int) -> float:
    """Average Daily Value over the 20 bars STRICTLY before bar_idx.

    Formula: mean(close[bar_idx-20..bar_idx-1] * vol[bar_idx-20..bar_idx-1]).
    Returns NaN if fewer than 20 prior bars are available.

    NO LOOK-AHEAD: bar `bar_idx` itself is NOT consumed (see
    memory/feedback_equity_formula.md — the 707% bug lived here).
    """
    if bar_idx < 20:
        return float("nan")
    c_slice = close_series.iloc[bar_idx - 20 : bar_idx]
    v_slice = vol_series.iloc[bar_idx - 20 : bar_idx]
    if len(c_slice) < 20 or len(v_slice) < 20:
        return float("nan")
    return float((c_slice.values * v_slice.values).mean())


def liquidity_gate_passes(
    adv20_value: float, target_notional_vnd: float, adv_mult: float
) -> bool:
    """True iff ADV20 >= adv_mult * target_notional (D-24). NaN → False."""
    if adv20_value is None:
        return False
    if isinstance(adv20_value, float) and math.isnan(adv20_value):
        return False
    return adv20_value >= adv_mult * target_notional_vnd


def sort_by_canslim(
    candidates: List,
    score_lookup: Callable[[str], Optional[float]],
) -> Tuple[list, list]:
    """Sort candidates by CANSLIM score descending (D-10).

    Candidates with None/NaN score are moved to a `dropped_missing` list so
    the engine can log them as `unfilled/canslim_score_missing`.

    Returns (kept_sorted_desc, dropped_missing).
    """
    kept: list = []
    dropped: list = []
    for c in candidates:
        score = score_lookup(c.ticker)
        if score is None or (isinstance(score, float) and math.isnan(score)):
            dropped.append(c)
        else:
            kept.append((score, c))
    kept.sort(key=lambda pair: pair[0], reverse=True)
    return [c for _, c in kept], dropped
