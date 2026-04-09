"""Unit tests for analysis/sweep_vn100.py (Phase 32 BT-02)."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from analysis import sweep_vn100 as sw


def test_grid_size_is_1536():
    grid = sw.build_grid()
    assert len(grid) == 1536


def test_grid_factors():
    grid = sw.build_grid()
    assert len({g["c_yoy"] for g in grid}) == 4
    assert len({g["a_cagr"] for g in grid}) == 4
    assert len({g["n_proximity"] for g in grid}) == 4
    assert len({g["hard_stop"] for g in grid}) == 4
    assert len({g["slots"] for g in grid}) == 3
    assert len({g["entry_option"] for g in grid}) == 2


def _canned_metrics(cagr: float) -> dict:
    return {
        "CAGR": cagr,
        "Sharpe_rf3": 0.5,
        "MaxDD": -0.15,
        "MaxDD_duration_days": 120,
        "hit_rate": 0.55,
        "turnover": 2.1,
        "total_cost_drag_pct": 0.04,
        "num_trades": 50,
        "avg_hold_days": 25.0,
    }


def test_worker_returns_metrics_dict(monkeypatch):
    def fake_run(canslim_cfg, portfolio_cfg, entry_option, period, precomputed=None):
        return {"metrics": _canned_metrics(0.25)}

    monkeypatch.setattr(sw, "run_vn100_backtest", fake_run)
    cfg = {
        "c_yoy": 0.10,
        "a_cagr": 0.15,
        "n_proximity": 0.10,
        "hard_stop": 0.07,
        "slots": 8,
        "entry_option": "A",
    }
    row = sw._worker((cfg, None))
    for col in sw.METRIC_COLS:
        assert col in row
    assert row["sanity_flag"] == "OK"
    assert row["error"] == ""
    assert row["c_yoy"] == 0.10
    assert row["entry_option"] == "A"


def test_sanity_flag_threshold(monkeypatch):
    def fake_run_high(canslim_cfg, portfolio_cfg, entry_option, period, precomputed=None):
        return {"metrics": _canned_metrics(3.5)}

    monkeypatch.setattr(sw, "run_vn100_backtest", fake_run_high)
    cfg = {
        "c_yoy": 0.10, "a_cagr": 0.15, "n_proximity": 0.10,
        "hard_stop": 0.07, "slots": 8, "entry_option": "A",
    }
    row = sw._worker((cfg, None))
    assert row["sanity_flag"] == "CAGR_TOO_HIGH"

    def fake_run_ok(canslim_cfg, portfolio_cfg, entry_option, period, precomputed=None):
        return {"metrics": _canned_metrics(0.25)}

    monkeypatch.setattr(sw, "run_vn100_backtest", fake_run_ok)
    row2 = sw._worker((cfg, None))
    assert row2["sanity_flag"] == "OK"


def test_worker_handles_exception(monkeypatch):
    def boom(canslim_cfg, portfolio_cfg, entry_option, period, precomputed=None):
        raise ValueError("kaboom")

    monkeypatch.setattr(sw, "run_vn100_backtest", boom)
    cfg = {
        "c_yoy": 0.10, "a_cagr": 0.15, "n_proximity": 0.10,
        "hard_stop": 0.07, "slots": 8, "entry_option": "A",
    }
    row = sw._worker((cfg, None))
    assert row["sanity_flag"] == "ERROR"
    assert "ValueError" in row["error"]
    assert "kaboom" in row["error"]
    for col in sw.METRIC_COLS:
        assert math.isnan(row[col])
