"""Vietnam microstructure primitives for Phase 31 portfolio engine.

Pure stdlib functions. Covers:
- D-17: T+2.5 earliest sellable bar = buy_bar + t_plus + 1 (= buy_bar + 3).
- D-18: ceiling/floor daily limits (default 7% of prev close).
- D-19: ceiling-lock / floor-lock bar detection (open == high == low == limit).
"""
from __future__ import annotations


def compute_ceiling(prev_close: float, pct: float = 0.07) -> float:
    # TODO: replace raw *1.07 with VN tick-rounding helper (per CONTEXT D-18).
    return prev_close * (1.0 + pct)


def compute_floor(prev_close: float, pct: float = 0.07) -> float:
    return prev_close * (1.0 - pct)


def is_ceiling_locked(
    open_: float, high: float, low: float, ceiling: float, tol: float = 1e-6
) -> bool:
    """True iff bar opened at ceiling and never traded below (O==H==L==ceiling)."""
    if abs(open_ - ceiling) > tol:
        return False
    return abs(high - open_) <= tol and abs(low - open_) <= tol


def is_floor_locked(
    open_: float, high: float, low: float, floor: float, tol: float = 1e-6
) -> bool:
    if abs(open_ - floor) > tol:
        return False
    return abs(high - open_) <= tol and abs(low - open_) <= tol


def t2_earliest_sell_bar(buy_bar_idx: int, t_plus: int = 2) -> int:
    """Earliest sellable bar index under T+2.5 settlement (D-17).

    Returns buy_bar_idx + t_plus + 1 (== buy_bar + 3 when t_plus=2).
    """
    return buy_bar_idx + t_plus + 1
