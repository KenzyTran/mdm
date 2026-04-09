"""Liquidity gate + ADV20 tests — Phase 31 Plan 03, Task 2.

Covers D-24 (ADV20 gate at 10x), and the SC8 no-lookahead precursor —
see memory/feedback_equity_formula.md (the 707% bug lived in state[i-1]
look-ahead; adv20 must consume STRICTLY bars prior to bar_idx).
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from strategies.portfolio.sizing import adv20, liquidity_gate_passes


def test_adv20_formula():
    close = pd.Series([100.0] * 25)
    vol = pd.Series([1000.0] * 25)
    # bar_idx=24: uses close[4..23] * vol[4..23] = 100*1000 = 100_000
    assert adv20(close, vol, bar_idx=24) == pytest.approx(100_000.0)


def test_adv20_insufficient_history():
    close = pd.Series([100.0] * 25)
    vol = pd.Series([1000.0] * 25)
    result = adv20(close, vol, bar_idx=10)
    assert math.isnan(result)


def test_liquidity_gate_passes():
    assert liquidity_gate_passes(1.5e9, 125_000_000, 10.0) is True


def test_liquidity_gate_blocks():
    assert liquidity_gate_passes(1.0e9, 125_000_000, 10.0) is False


def test_liquidity_gate_nan():
    assert liquidity_gate_passes(float("nan"), 125_000_000, 10.0) is False


def test_adv20_no_lookahead():
    """Critical SC8 precursor test. Mutating close[bar_idx] AFTER computing
    adv20 must NOT change the result, because adv20 only consumes
    close[bar_idx-20..bar_idx-1]. See memory/feedback_equity_formula.md.
    """
    close = pd.Series([100.0] * 30)
    vol = pd.Series([1000.0] * 30)
    result_before = adv20(close, vol, bar_idx=25)
    # Mutate bar 25 AFTER the computation
    close.iloc[25] = 999_999.0
    vol.iloc[25] = 999_999.0
    result_after = adv20(close, vol, bar_idx=25)
    assert result_before == result_after == pytest.approx(100_000.0)
