"""Unit tests for analysis/select_top3_vn100.py (Phase 32 BT-02 SC4 / D-13).

Tests use synthetic DataFrames only — no real CSV reads.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers to build synthetic DataFrames
# ---------------------------------------------------------------------------

GRID_COLS = ["c_yoy", "a_cagr", "n_proximity", "hard_stop", "slots", "entry_option"]
METRIC_COLS = [
    "CAGR", "Sharpe_rf3", "MaxDD", "MaxDD_duration_days",
    "hit_rate", "turnover", "total_cost_drag_pct", "num_trades", "avg_hold_days",
]


def _make_row(
    rank: int,
    sharpe: float = 0.0,
    cagr: float = 0.0,
    maxdd: float = -0.15,
    sanity_flag: str = "OK",
) -> dict:
    """Return a single row dict suitable for DataFrame construction."""
    return {
        "c_yoy": 0.10 + rank * 0.01,
        "a_cagr": 0.10 + rank * 0.01,
        "n_proximity": 0.10,
        "hard_stop": 0.07,
        "slots": 8,
        "entry_option": "A",
        "CAGR": cagr,
        "Sharpe_rf3": sharpe,
        "MaxDD": maxdd,
        "MaxDD_duration_days": 200,
        "hit_rate": 0.5,
        "turnover": 3.0,
        "total_cost_drag_pct": 0.05,
        "num_trades": 40,
        "avg_hold_days": 25.0,
        "sanity_flag": sanity_flag,
        "error": "",
    }


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Lazy import so tests can run even before the module exists (RED phase)
# ---------------------------------------------------------------------------

def _import():
    from analysis import select_top3_vn100 as m
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSelectTop3:
    def test_select_top3_returns_three_rows(self):
        m = _import()
        rows = [_make_row(i, sharpe=float(i) * 0.01) for i in range(10)]
        df = _make_df(rows)
        result = m.select_top3(df)
        assert len(result) == 3

    def test_select_top3_sorted_by_sharpe_desc(self):
        m = _import()
        rows = [_make_row(i, sharpe=float(i) * 0.01) for i in range(10)]
        df = _make_df(rows)
        result = m.select_top3(df)
        sharpes = result["Sharpe_rf3"].tolist()
        assert sharpes[0] >= sharpes[1] >= sharpes[2]

    def test_tie_breaker_cagr(self):
        """When two rows share the same Sharpe, higher CAGR should win (D-12)."""
        m = _import()
        rows = [
            _make_row(0, sharpe=0.10, cagr=0.05),
            _make_row(1, sharpe=0.10, cagr=0.08),  # same sharpe, better CAGR
            _make_row(2, sharpe=0.10, cagr=0.03),
            _make_row(3, sharpe=0.10, cagr=0.02),
            _make_row(4, sharpe=0.05, cagr=0.10),  # different sharpe
        ]
        df = _make_df(rows)
        result = m.select_top3(df)
        # rank-1 should be row with sharpe=0.10, cagr=0.08
        assert result.iloc[0]["CAGR"] == pytest.approx(0.08)

    def test_tie_breaker_maxdd(self):
        """When Sharpe + CAGR tie, lower absolute MaxDD (closer to 0 = less severe) wins (D-12).

        MaxDD is stored as a negative number; -0.10 is less severe than -0.20.
        Sorting MaxDD descending (False) puts -0.10 before -0.20, which is correct.
        """
        m = _import()
        rows = [
            _make_row(0, sharpe=0.10, cagr=0.05, maxdd=-0.20),
            _make_row(1, sharpe=0.10, cagr=0.05, maxdd=-0.10),  # same sharpe+cagr, better maxdd
            _make_row(2, sharpe=0.10, cagr=0.05, maxdd=-0.15),
            _make_row(3, sharpe=0.05, cagr=0.05, maxdd=-0.05),
            _make_row(4, sharpe=0.05, cagr=0.05, maxdd=-0.05),
        ]
        df = _make_df(rows)
        result = m.select_top3(df)
        # rank-1 should be row with maxdd=-0.10
        assert result.iloc[0]["MaxDD"] == pytest.approx(-0.10)

    def test_sanity_gate_aborts(self):
        """If any top-3 row has sanity_flag != 'OK', select_top3 raises RuntimeError (D-13)."""
        m = _import()
        rows = [
            _make_row(0, sharpe=0.90, sanity_flag="CAGR_TOO_HIGH"),
            _make_row(1, sharpe=0.80),
            _make_row(2, sharpe=0.70),
            _make_row(3, sharpe=0.60),
            _make_row(4, sharpe=0.50),
        ]
        df = _make_df(rows)
        with pytest.raises(RuntimeError, match="sanity-flagged"):
            m.select_top3(df)

    def test_sanity_gate_ok_passes(self):
        """All-OK top-3 should pass through without error."""
        m = _import()
        rows = [_make_row(i, sharpe=float(i) * 0.01) for i in range(10)]
        df = _make_df(rows)
        result = m.select_top3(df)
        assert len(result) == 3
        assert all(r == "OK" for r in result["sanity_flag"])


class TestToJsonPayload:
    def test_json_schema(self, tmp_path):
        """Written JSON must match D-14 schema."""
        m = _import()
        rows = [_make_row(i, sharpe=float(i) * 0.01) for i in range(10)]
        df = _make_df(rows)
        top3 = m.select_top3(df)
        payload = m.to_json_payload(top3)

        # Top-level keys
        for key in ("selected_at", "selection_metric", "period", "universe", "configs"):
            assert key in payload, f"Missing top-level key: {key}"

        # configs list
        assert isinstance(payload["configs"], list)
        assert len(payload["configs"]) == 3

        # Per-config keys
        required_keys = {
            "rank", "c_yoy", "a_cagr", "n_proximity",
            "hard_stop", "slots", "entry_option", "metrics",
        }
        for i, cfg in enumerate(payload["configs"]):
            missing = required_keys - set(cfg.keys())
            assert not missing, f"Config {i} missing keys: {missing}"
            assert isinstance(cfg["metrics"], dict)
            assert cfg["rank"] == i + 1

        # selection_metric value
        assert payload["selection_metric"] == "sharpe_rf3"
