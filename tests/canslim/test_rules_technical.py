"""Tests for technical rules N (CANS-05) and S helper — plan 29-06."""
from datetime import date

import pandas as pd
import pytest

from strategies.canslim.config import CanslimConfig
from strategies.canslim.rules import technical
from strategies.canslim.rules.technical import compute_n, compute_s


def test_technical_module_imports():
    assert hasattr(technical, "compute_n")
    assert hasattr(technical, "compute_s")


def _ohlcv(highs, closes, vols, start="2024-01-01"):
    n = len(highs)
    dates = pd.date_range(start, periods=n, freq="B").date
    return pd.DataFrame(
        {
            "tradingdate": dates,
            "closeindex": closes,
            "highestindex": highs,
            "totalvol": vols,
        }
    )


# ----- N rule -----


def test_n_true_when_close_within_15pct_of_252d_high():
    cfg = CanslimConfig()
    highs = [100.0] * 251 + [200.0]
    closes = [100.0] * 251 + [180.0]  # 180 >= 0.85*200 = 170
    vols = [1000] * 252
    df = _ohlcv(highs, closes, vols)
    as_of = df["tradingdate"].iloc[-1]
    assert compute_n(df, as_of, cfg) is True


def test_n_false_when_close_below_threshold():
    cfg = CanslimConfig()
    highs = [100.0] * 251 + [200.0]
    closes = [100.0] * 251 + [160.0]  # 160 < 170
    vols = [1000] * 252
    df = _ohlcv(highs, closes, vols)
    as_of = df["tradingdate"].iloc[-1]
    assert compute_n(df, as_of, cfg) is False


def test_n_false_when_insufficient_history():
    cfg = CanslimConfig()
    highs = [200.0] * 100
    closes = [180.0] * 100
    vols = [1000] * 100
    df = _ohlcv(highs, closes, vols)
    as_of = df["tradingdate"].iloc[-1]
    assert compute_n(df, as_of, cfg) is False


# ----- S helper -----


def test_s_true_when_today_vol_exceeds_multiplier():
    cfg = CanslimConfig()
    highs = [100.0] * 51
    closes = [100.0] * 51
    vols = [100] * 50 + [200]  # avg50=100, today=200 >= 150
    df = _ohlcv(highs, closes, vols)
    as_of = df["tradingdate"].iloc[-1]
    assert compute_s(df, as_of, cfg) is True


def test_s_false_when_today_vol_below_multiplier():
    cfg = CanslimConfig()
    highs = [100.0] * 51
    closes = [100.0] * 51
    vols = [100] * 50 + [120]  # 120 < 150
    df = _ohlcv(highs, closes, vols)
    as_of = df["tradingdate"].iloc[-1]
    assert compute_s(df, as_of, cfg) is False


def test_s_false_when_insufficient_history():
    cfg = CanslimConfig()
    highs = [100.0] * 20
    closes = [100.0] * 20
    vols = [100] * 19 + [500]
    df = _ohlcv(highs, closes, vols)
    as_of = df["tradingdate"].iloc[-1]
    assert compute_s(df, as_of, cfg) is False
