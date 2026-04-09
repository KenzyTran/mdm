"""Phase 32 BT-01 / SC1 — single-run VN100 backtest 2014-2018.

Runs one backtest with Phase 31 defaults on the current-VN100 universe
over the in-sample period. Hard-coded period per D-09 (no CLI args —
reproducibility). Outputs three CSVs under ``docs/audits/phase32/``:
trade log, position log, daily NAV.

Usage:
    uv run python analysis/backtest_vn100.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from analysis._vn100_pipeline import run_vn100_backtest
from strategies.canslim.config import CanslimConfig
from strategies.portfolio.config import PortfolioConfig

# Hard-coded in-sample period (D-09).
PERIOD = ("2014-01-01", "2018-12-31")
OUT_DIR = Path("docs/audits/phase32")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 29 CANSLIM defaults (D-12).
    canslim_cfg = CanslimConfig(
        c_threshold=0.20,
        a_threshold=0.15,
        n_within_high=0.15,
    )

    # Phase 31 portfolio defaults (D-07..D-24).
    portfolio_cfg = PortfolioConfig(
        max_slots=8,
        entry_mode="A",
        hard_stop_pct=0.08,
        cooldown_days=5,
        rs_threshold=70.0,
        rs_streak_days=5,
        ma50_vol_mult=1.25,
        adv_mult=10.0,
        entry_commission=0.0025,
        entry_slippage=0.0010,
        exit_commission=0.0025,
        exit_tax=0.0010,
        exit_slippage=0.0010,
    )

    print(f"[phase32 BT-01] running single-run backtest {PERIOD[0]}..{PERIOD[1]}")
    result = run_vn100_backtest(
        canslim_cfg=canslim_cfg,
        portfolio_cfg=portfolio_cfg,
        entry_option="A",
        period=PERIOD,
    )

    nav_df: pd.DataFrame = result["nav"]
    trades_df: pd.DataFrame = result["trades"]
    positions_df: pd.DataFrame = result["positions"]
    metrics = result["metrics"]

    # --- write CSVs -------------------------------------------------------
    nav_path = OUT_DIR / "single_run_nav.csv"
    trades_path = OUT_DIR / "single_run_trades.csv"
    positions_path = OUT_DIR / "single_run_positions.csv"
    nav_df.to_csv(nav_path, index=False)
    trades_df.to_csv(trades_path, index=False)
    positions_df.to_csv(positions_path, index=False)

    # --- summary ----------------------------------------------------------
    print("\n[phase32 BT-01] Summary")
    print("=" * 60)
    print(f"  CAGR                  : {metrics['CAGR'] * 100:.2f}%")
    print(f"  Sharpe_rf3            : {metrics['Sharpe_rf3']:.3f}")
    print(f"  MaxDD                 : {metrics['MaxDD'] * 100:.2f}%")
    print(f"  MaxDD_duration_days   : {metrics['MaxDD_duration_days']}")
    print(f"  hit_rate              : {metrics['hit_rate'] * 100:.2f}%")
    print(f"  num_trades            : {metrics['num_trades']}")
    print(f"  avg_hold_days         : {metrics['avg_hold_days']:.1f}")
    print("\n[phase32 BT-01] Wrote:")
    print(f"  {nav_path}")
    print(f"  {trades_path}")
    print(f"  {positions_path}")


if __name__ == "__main__":
    main()
