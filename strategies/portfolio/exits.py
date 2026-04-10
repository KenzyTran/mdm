"""Exit priority chain for Phase 31 portfolio engine.

Implements D-13 (first-match-wins order: MDM SELL > hard stop > MA50 break >
RS deterioration), D-14 (T+2 hard block — no exit before earliest_sell_bar),
D-16 (RS streak fail-closed on NaN — missing data resets the streak),
D-19 (limit-down deferral — hard stop on a floor-locked bar is flagged
deferred=True so the engine re-checks the next non-floor-locked bar).

All exits fill at open[bar_idx + 1] (fill_bar_idx = bar_idx + 1). The engine
is responsible for the actual fill; this module is a pure decision function.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import math

import pandas as pd

from .config import PortfolioConfig
from .state import Position


EXIT_REASONS = ("mdm_sell", "hard_stop", "ma50_break", "rs_deterioration")


@dataclass
class ExitDecision:
    reason: str
    fill_bar_idx: int
    deferred: bool
    original_trigger_bar: int


def evaluate_exits(
    position: Position,
    bar_idx: int,
    bar_ctx: dict,
    cfg: PortfolioConfig,
) -> Optional[ExitDecision]:
    """First-match-wins exit chain. Returns None when no trigger fires.

    Order (D-13):
        1. T+2 block (D-14) — checked FIRST, silences all triggers.
        2. Hard stop (-8%), with limit-down deferral (D-19).
        3. MA50 break with volume confirmation.
        4. RS deterioration (streak ≥ cfg.rs_streak_days).

    Note: MDM SELL dispatch (GATE-02) is handled by engine section (3) via RS-ranked
    partial liquidation. Positions retained by that process remain subject to these
    individual exit rules on subsequent bars.
    """
    # D-14: T+2 hard block — no exit may fire before earliest_sell_bar.
    if bar_idx < position.earliest_sell_bar:
        return None

    fill_bar = bar_idx + 1

    # 1. Hard stop (-hard_stop_pct from buy_price).
    stop_price = position.buy_price * (1.0 - cfg.hard_stop_pct)
    if bar_ctx["low"] <= stop_price:
        # D-19 limit-down deferral: bar is floor-locked (O==H==L==floor).
        o, h, l = bar_ctx["open"], bar_ctx["high"], bar_ctx["low"]
        floor = bar_ctx.get("floor")
        deferred = (
            floor is not None
            and o == h == l
            and abs(l - floor) <= 1e-6
        )
        return ExitDecision(
            reason="hard_stop",
            fill_bar_idx=fill_bar,
            deferred=deferred,
            original_trigger_bar=bar_idx,
        )

    # 3. MA50 break + volume confirmation.
    if (
        bar_ctx["close"] < bar_ctx["ma50"]
        and bar_ctx["vol"] >= cfg.ma50_vol_mult * bar_ctx["vol20_avg"]
    ):
        return ExitDecision(
            reason="ma50_break",
            fill_bar_idx=fill_bar,
            deferred=False,
            original_trigger_bar=bar_idx,
        )

    # 4. RS deterioration streak.
    if bar_ctx.get("rs_streak_count", 0) >= cfg.rs_streak_days:
        return ExitDecision(
            reason="rs_deterioration",
            fill_bar_idx=fill_bar,
            deferred=False,
            original_trigger_bar=bar_idx,
        )

    return None


def rs_streak_hit(
    rs_series: "pd.Series", threshold: float, min_streak: int
) -> bool:
    """Return True iff the tail of rs_series has min_streak consecutive values
    strictly below `threshold`, with NO missing values in that window.

    D-16 fail-closed: any NaN in the window resets the streak. Practically,
    we scan from the end backward and break on the first NaN or first value
    >= threshold.
    """
    count = 0
    for val in reversed(list(rs_series)):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            break
        if val < threshold:
            count += 1
            if count >= min_streak:
                return True
        else:
            break
    return False
