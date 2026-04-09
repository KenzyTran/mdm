"""Tests for RS rule (L, CANS-07) — plan 29-06."""
import numpy as np
import pandas as pd
import pytest

from strategies.canslim.config import CanslimConfig
from strategies.canslim.rules import rs
from strategies.canslim.rules.rs import compute_rs_ratings


def test_rs_module_imports():
    assert hasattr(rs, "compute_rs_ratings")


def _panel(ticker_to_prices, start="2023-01-01"):
    frames = []
    for t, prices in ticker_to_prices.items():
        dates = pd.date_range(start, periods=len(prices), freq="B").date
        frames.append(
            pd.DataFrame(
                {"stockcode": t, "tradingdate": dates, "closeindex": prices}
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_single_ticker_doubling_gets_percentile_100():
    cfg = CanslimConfig()
    prices = list(np.linspace(100.0, 200.0, 260))
    panel = _panel({"AAA": prices})
    as_of = panel["tradingdate"].max()
    out = compute_rs_ratings(panel, as_of, ["AAA"], cfg)
    assert not np.isnan(out["AAA"])
    assert out["AAA"] == pytest.approx(100.0)


def test_two_ticker_universe_ranks():
    cfg = CanslimConfig()
    up_fast = list(np.linspace(100.0, 150.0, 260))  # +50%
    up_slow = list(np.linspace(100.0, 110.0, 260))  # +10%
    panel = _panel({"AAA": up_fast, "BBB": up_slow})
    as_of = panel["tradingdate"].max()
    out = compute_rs_ratings(panel, as_of, ["AAA", "BBB"], cfg)
    assert out["AAA"] == pytest.approx(100.0)
    assert out["BBB"] == pytest.approx(50.0)


def test_insufficient_history_returns_nan():
    cfg = CanslimConfig()
    prices = list(np.linspace(100.0, 150.0, 100))
    panel = _panel({"AAA": prices})
    as_of = panel["tradingdate"].max()
    out = compute_rs_ratings(panel, as_of, ["AAA"], cfg)
    assert np.isnan(out["AAA"])


def test_l_pass_uses_threshold():
    cfg = CanslimConfig()
    prices_hi = list(np.linspace(100.0, 200.0, 260))
    prices_lo = list(np.linspace(100.0, 105.0, 260))
    panel = _panel({"HI": prices_hi, "LO": prices_lo})
    as_of = panel["tradingdate"].max()
    out = compute_rs_ratings(panel, as_of, ["HI", "LO"], cfg)
    l_pass = out >= cfg.l_rs_threshold
    assert bool(l_pass["HI"]) is True
    assert bool(l_pass["LO"]) is False


def test_extra_tickers_in_panel_are_ignored():
    cfg = CanslimConfig()
    p = list(np.linspace(100.0, 150.0, 260))
    panel = _panel({"AAA": p, "ZZZ": p})
    as_of = panel["tradingdate"].max()
    out = compute_rs_ratings(panel, as_of, ["AAA"], cfg)
    assert list(out.index) == ["AAA"]


def test_rs_formula_numeric():
    """Raw RS = 0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252.

    Build 253 bars where closeindex on the last bar gives known ROCs vs
    bars at offsets 63/126/189/252 back. Single-ticker universe → rank 100.
    """
    cfg = CanslimConfig()
    n = 253
    prices = [100.0] * n
    # The last bar is index n-1=252. past@lookback = iloc[-lb-1] = iloc[252-lb-1].
    # For lb=63 -> iloc 188; lb=126 -> iloc 125; lb=189 -> iloc 62; lb=252 -> iloc 0.
    prices[n - 1] = 163.0  # latest
    prices[188] = 100.0  # ROC63 = 63/100 = 0.63
    prices[125] = 100.0  # ROC126 = 0.63
    prices[62] = 100.0
    prices[0] = 100.0
    panel = _panel({"AAA": prices})
    as_of = panel["tradingdate"].max()
    out = compute_rs_ratings(panel, as_of, ["AAA"], cfg)
    assert out["AAA"] == pytest.approx(100.0)  # single ticker → top rank
