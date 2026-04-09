"""Round-trip tests for strategies.portfolio.ab_report (Phase 31, D-27)."""
from __future__ import annotations

import pandas as pd
import pytest

from strategies.portfolio.ab_report import (
    NAV_COLS,
    POSITIONS_COLS,
    TRADES_COLS,
    UNFILLED_COLS,
    write_all,
)
from strategies.portfolio.engine import PortfolioResult
from strategies.portfolio.state import Trade


def _make_result_with_data() -> PortfolioResult:
    trade = Trade(
        ticker="VNM",
        buy_date=pd.Timestamp("2024-01-05"),
        buy_price=70000.0,
        buy_cost_vnd=100_350_000.0,
        sell_date=pd.Timestamp("2024-02-10"),
        sell_price=75000.0,
        sell_cost_vnd=106_762_500.0,
        pnl_vnd=6_412_500.0,
        pnl_pct=0.064,
        exit_reason="mdm_sell",
    )
    nav_daily = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2024-01-05"),
                "nav": 1_000_000_000.0,
                "cash": 899_650_000.0,
                "deployed_pct": 0.1003,
                "open_slots": 1,
            },
            {
                "date": pd.Timestamp("2024-01-08"),
                "nav": 1_003_000_000.0,
                "cash": 899_650_000.0,
                "deployed_pct": 0.103,
                "open_slots": 1,
            },
        ]
    )
    positions_daily = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2024-01-05"),
                "ticker": "VNM",
                "shares": 1400,
                "mark_price": 70000.0,
                "mark_value": 98_000_000.0,
            },
            {
                "date": pd.Timestamp("2024-01-08"),
                "ticker": "VNM",
                "shares": 1400,
                "mark_price": 71000.0,
                "mark_value": 99_400_000.0,
            },
        ]
    )
    unfilled = [
        {
            "bar_idx": 12,
            "date": pd.Timestamp("2024-01-05"),
            "ticker": "HPG",
            "reason": "ceiling_lock",
            "ceiling_px": 28500.0,
        }
    ]
    return PortfolioResult(
        trades=[trade],
        nav_daily=nav_daily,
        positions_daily=positions_daily,
        unfilled=unfilled,
    )


def test_round_trip(tmp_path):
    result = _make_result_with_data()
    paths = write_all(result, tmp_path)

    assert set(paths.keys()) == {"trades", "positions", "nav", "unfilled"}
    for p in paths.values():
        assert p.exists(), f"{p} not written"

    trades = pd.read_csv(paths["trades"])
    positions = pd.read_csv(paths["positions"])
    nav = pd.read_csv(paths["nav"])
    unfilled = pd.read_csv(paths["unfilled"])

    assert set(trades.columns) == set(TRADES_COLS)
    assert list(trades.columns) == TRADES_COLS
    assert len(trades) == 1
    assert trades.iloc[0]["ticker"] == "VNM"
    assert trades.iloc[0]["exit_reason"] == "mdm_sell"

    assert set(positions.columns) == set(POSITIONS_COLS)
    assert list(positions.columns) == POSITIONS_COLS
    assert len(positions) == 2

    assert set(nav.columns) == set(NAV_COLS)
    assert list(nav.columns) == NAV_COLS
    assert len(nav) == 2

    assert set(unfilled.columns) == set(UNFILLED_COLS)
    assert list(unfilled.columns) == UNFILLED_COLS
    assert len(unfilled) == 1
    assert unfilled.iloc[0]["reason"] == "ceiling_lock"
    assert "ceiling_px=28500" in str(unfilled.iloc[0]["detail"])


def test_empty_result(tmp_path):
    result = PortfolioResult()
    paths = write_all(result, tmp_path / "empty_out")

    for p in paths.values():
        assert p.exists()

    trades = pd.read_csv(paths["trades"])
    positions = pd.read_csv(paths["positions"])
    nav = pd.read_csv(paths["nav"])
    unfilled = pd.read_csv(paths["unfilled"])

    assert list(trades.columns) == TRADES_COLS
    assert list(positions.columns) == POSITIONS_COLS
    assert list(nav.columns) == NAV_COLS
    assert list(unfilled.columns) == UNFILLED_COLS
    assert len(trades) == 0
    assert len(positions) == 0
    assert len(nav) == 0
    assert len(unfilled) == 0
