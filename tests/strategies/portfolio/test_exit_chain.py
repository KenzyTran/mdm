"""Exit priority chain tests — Phase 31 Plan 03, Task 1.

Covers D-13 (first-match-wins exit priority), D-14 (T+2 hard block),
D-16 (RS streak fail-closed on NaN), D-19 (limit-down hard-stop deferral).
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from strategies.portfolio.config import PortfolioConfig
from strategies.portfolio.exits import (
    EXIT_REASONS,
    ExitDecision,
    evaluate_exits,
    rs_streak_hit,
)
from strategies.portfolio.state import Position


def make_position(earliest_sell_bar: int = 0, buy_price: float = 100.0) -> Position:
    return Position(
        ticker="AAA",
        buy_bar=0,
        buy_date=pd.Timestamp("2023-01-03"),
        buy_price=buy_price,
        shares=1000,
        cost_basis=buy_price,
        earliest_sell_bar=earliest_sell_bar,
    )


def make_bar(**overrides):
    bar = dict(
        mdm_state="BUY",
        low=100.0,
        high=100.0,
        open=100.0,
        close=100.0,
        ma50=90.0,
        vol=1000.0,
        vol20_avg=1000.0,
        rs_streak_count=0,
        floor=92.0,
    )
    bar.update(overrides)
    return bar


CFG = PortfolioConfig()


def test_t2_blocks_all():
    pos = make_position(earliest_sell_bar=13)
    bar = make_bar(mdm_state="SELL", low=50.0, close=50.0, vol=10000.0, rs_streak_count=99)
    assert evaluate_exits(pos, bar_idx=11, bar_ctx=bar, cfg=CFG) is None


def test_priority_order():
    pos = make_position(earliest_sell_bar=0)
    bar = make_bar(
        mdm_state="SELL",
        low=50.0,
        close=50.0,
        ma50=100.0,
        vol=5000.0,
        rs_streak_count=10,
    )
    d = evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG)
    assert d is not None
    assert d.reason == "mdm_sell"
    assert d.fill_bar_idx == 21


def test_hard_stop():
    pos = make_position(buy_price=100.0)
    bar = make_bar(low=92.0, high=95.0, open=94.0, close=93.0)
    d = evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG)
    assert d is not None
    assert d.reason == "hard_stop"
    assert d.fill_bar_idx == 21
    assert d.deferred is False


def test_hard_stop_limit_down():
    pos = make_position(buy_price=100.0)
    bar = make_bar(low=92.0, high=92.0, open=92.0, close=92.0, floor=92.0)
    d = evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG)
    assert d is not None
    assert d.reason == "hard_stop"
    assert d.deferred is True


def test_ma50_break():
    pos = make_position()
    bar = make_bar(close=89.0, ma50=90.0, vol=1300.0, vol20_avg=1000.0)
    d = evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG)
    assert d is not None
    assert d.reason == "ma50_break"


def test_ma50_break_vol_insufficient():
    pos = make_position()
    bar = make_bar(close=89.0, ma50=90.0, vol=1100.0, vol20_avg=1000.0)
    assert evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG) is None


def test_rs_streak_hit_trigger():
    pos = make_position()
    bar = make_bar(rs_streak_count=5)
    d = evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG)
    assert d is not None
    assert d.reason == "rs_deterioration"


def test_rs_streak_not_yet():
    pos = make_position()
    bar = make_bar(rs_streak_count=4)
    assert evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG) is None


def test_rs_streak_resets_on_nan():
    s = pd.Series([60, 60, float("nan"), 60, 60, 60])
    assert rs_streak_hit(s, threshold=70, min_streak=5) is False


def test_rs_streak_continuous():
    s = pd.Series([60, 60, 60, 60, 60])
    assert rs_streak_hit(s, threshold=70, min_streak=5) is True


def test_mdm_sell_beats_hard_stop():
    pos = make_position(buy_price=100.0)
    bar = make_bar(mdm_state="SELL", low=80.0, close=80.0)
    d = evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG)
    assert d.reason == "mdm_sell"


def test_hard_stop_beats_ma50():
    pos = make_position(buy_price=100.0)
    bar = make_bar(low=90.0, close=89.0, ma50=90.0, vol=2000.0, vol20_avg=1000.0)
    d = evaluate_exits(pos, bar_idx=20, bar_ctx=bar, cfg=CFG)
    assert d.reason == "hard_stop"


def test_exit_reasons_constants():
    assert set(EXIT_REASONS) == {"mdm_sell", "hard_stop", "ma50_break", "rs_deterioration"}
