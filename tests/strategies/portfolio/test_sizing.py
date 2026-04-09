"""Sizing tests — Phase 31 Plan 03, Task 2.

Covers D-09 (NAV*slot_weight), D-10 (CANSLIM desc sort + missing-score drop),
D-11 (lot floor leaves residual in cash).
"""
from __future__ import annotations

from collections import namedtuple

import pytest

from strategies.portfolio.config import PortfolioConfig
from strategies.portfolio.sizing import (
    lot_round_shares,
    sort_by_canslim,
    target_notional,
)


CFG = PortfolioConfig()
Cand = namedtuple("Cand", "ticker")


def test_target_notional():
    assert target_notional(1_000_000_000, CFG) == pytest.approx(125_000_000)


def test_lot_round_exact():
    # 125M / 25000 = 5000 shares exact
    assert lot_round_shares(125_000_000, 25_000) == 5000


def test_lot_round_floors_down():
    # 125M / 25100 = 4980.08 -> floor to 4900 (49 * 100 lots)
    shares = lot_round_shares(125_000_000, 25_100)
    assert shares == 4900
    deployed = shares * 25_100
    residual = 125_000_000 - deployed
    # Residual cash stays in book (D-11). Deployed ~ 122.99M, residual ~ 2.01M.
    assert deployed == 122_990_000
    assert residual == 2_010_000


def test_lot_round_zero_when_price_too_high():
    assert lot_round_shares(1_000, 50_000) == 0


def test_canslim_sort_desc():
    cands = [Cand("AAA"), Cand("BBB"), Cand("CCC")]
    scores = {"AAA": 80, "BBB": 90, "CCC": 70}
    kept, dropped = sort_by_canslim(cands, lambda t: scores.get(t))
    assert [c.ticker for c in kept] == ["BBB", "AAA", "CCC"]
    assert dropped == []


def test_canslim_sort_missing_score():
    cands = [Cand("AAA"), Cand("DDD"), Cand("BBB")]
    scores = {"AAA": 80, "BBB": 90}  # DDD missing
    kept, dropped = sort_by_canslim(cands, lambda t: scores.get(t))
    assert [c.ticker for c in kept] == ["BBB", "AAA"]
    assert [c.ticker for c in dropped] == ["DDD"]
