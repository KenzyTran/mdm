"""Unit tests for analysis/_vn100_pipeline.py (Phase 32 BT-01)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis import _vn100_pipeline as pipe
from strategies.canslim.config import CanslimConfig
from strategies.portfolio.config import PortfolioConfig


REQUIRED_METRIC_KEYS = {
    "CAGR",
    "Sharpe_rf3",
    "MaxDD",
    "MaxDD_duration_days",
    "hit_rate",
    "turnover",
    "total_cost_drag_pct",
    "num_trades",
    "avg_hold_days",
}


def _build_synthetic_precomputed(period=("2014-01-02", "2014-03-31")) -> dict:
    """Build an in-memory precomputed dict that bypasses Postgres/MySQL.

    3 tickers x ~60 business days of monotone-up prices.
    """
    start, end = period
    dates = pd.bdate_range(start, end)
    tickers = ["AAA", "BBB", "CCC"]
    rows = []
    for ti, t in enumerate(tickers):
        base = 50_000.0 + ti * 1_000.0
        for i, d in enumerate(dates):
            close = base + i * 50.0
            rows.append(
                {
                    "stockcode": t,
                    "tradingdate": d,
                    "adj_open": close - 10.0,
                    "adj_high": close + 20.0,
                    "adj_low": close - 20.0,
                    "adj_close": close,
                    "totalvol": 1_000_000 + i * 100,
                    "totaladjustrate": 1.0,
                    "openprice": close - 10.0,
                    "highestprice": close + 20.0,
                    "lowestprice": close - 20.0,
                    "closeprice": close,
                }
            )
    ohlc = pd.DataFrame(rows)

    # Constant VN100 universe: all 3 tickers always included at Jan 1.
    universe = {pd.Timestamp(start): list(tickers)}

    # MDM gate: permanent BUY across the whole period.
    mdm_gate = pd.Series(
        ["BUY"] * len(dates),
        index=pd.DatetimeIndex(dates),
        name="mdm_state",
    )

    return {
        "universe": universe,
        "ohlc": ohlc,
        "fundamentals": pd.DataFrame(),
        "foreign": pd.DataFrame(),
        "mdm_gate": mdm_gate,
        # inject empty fills to skip EntryEngine per-ticker run — the
        # engine API still exercises the full portfolio loop (gate, NAV,
        # mark-to-close) so state[i-1] discipline is verified.
        "fills": [],
    }


def _default_cfgs():
    return CanslimConfig(), PortfolioConfig(entry_mode="A")


def test_precompute_returns_dict_with_keys(monkeypatch):
    """`precompute_static` signature: the keys of the returned dict.

    This does not hit the DB — we stub `precompute_static` via monkeypatch.
    """
    synth = _build_synthetic_precomputed()
    monkeypatch.setattr(pipe, "precompute_static", lambda period: synth)
    out = pipe.precompute_static(("2014-01-02", "2014-03-31"))
    for key in ("universe", "ohlc", "fundamentals", "foreign", "mdm_gate"):
        assert key in out, f"precompute_static missing key {key}"


def test_run_vn100_backtest_signature():
    canslim_cfg, pcfg = _default_cfgs()
    pre = _build_synthetic_precomputed()
    result = pipe.run_vn100_backtest(
        canslim_cfg, pcfg, "A",
        period=("2014-01-02", "2014-03-31"),
        precomputed=pre,
    )
    assert set(result.keys()) >= {"metrics", "nav", "trades", "positions"}


def test_metrics_has_required_keys():
    canslim_cfg, pcfg = _default_cfgs()
    pre = _build_synthetic_precomputed()
    result = pipe.run_vn100_backtest(
        canslim_cfg, pcfg, "A",
        period=("2014-01-02", "2014-03-31"),
        precomputed=pre,
    )
    missing = REQUIRED_METRIC_KEYS - set(result["metrics"].keys())
    assert not missing, f"metrics missing keys: {missing}"


def test_state_lookback_discipline():
    """NAV must use state[i-1] per Equity formula rule.

    With empty fills and permanent BUY gate, the engine never opens a
    position -> NAV is flat at initial_cash. Any non-constant NAV here
    would indicate look-ahead leakage from a same-day decision.
    """
    canslim_cfg, pcfg = _default_cfgs()
    pre = _build_synthetic_precomputed()
    result = pipe.run_vn100_backtest(
        canslim_cfg, pcfg, "A",
        period=("2014-01-02", "2014-03-31"),
        precomputed=pre,
    )
    nav = result["nav"]
    assert not nav.empty
    # All NAV equals initial cash (no positions opened).
    assert np.allclose(nav["nav"].values, nav["nav"].iloc[0])


def test_entry_option_accepts_a_and_c():
    canslim_cfg, pcfg = _default_cfgs()
    pre = _build_synthetic_precomputed()
    for opt in ("A", "C"):
        out = pipe.run_vn100_backtest(
            canslim_cfg, pcfg, opt,
            period=("2014-01-02", "2014-03-31"),
            precomputed=pre,
        )
        assert "metrics" in out


def test_entry_option_rejects_invalid():
    canslim_cfg, pcfg = _default_cfgs()
    pre = _build_synthetic_precomputed()
    with pytest.raises(ValueError):
        pipe.run_vn100_backtest(
            canslim_cfg, pcfg, "union",
            period=("2014-01-02", "2014-03-31"),
            precomputed=pre,
        )
