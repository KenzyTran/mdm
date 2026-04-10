"""Phase 33 BT-03 — OOS VN100 backtest 2019-2025 with locked params.

Runs one backtest with rank-1 locked config from Phase 32 on the
out-of-sample period. Hard-coded period per D-09 (no CLI args).

Usage:
    uv run python analysis/backtest_vn100_oos.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from analysis._vn100_pipeline import run_vn100_backtest
from strategies.canslim.config import CanslimConfig
from strategies.portfolio.config import PortfolioConfig

PERIOD = ("2019-01-01", "2025-12-31")
OUT_DIR = Path("docs/audits/phase33")
LOCKED_PARAMS = Path("docs/audits/phase32/locked_params_top3.json")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load rank-1 locked config (D-02)
    with open(LOCKED_PARAMS) as f:
        top3 = json.load(f)
    cfg1 = top3["configs"][0]  # rank-1
    assert cfg1["rank"] == 1, f"Expected rank 1, got {cfg1['rank']}"

    canslim_cfg = CanslimConfig(
        c_threshold=cfg1["c_yoy"],          # 0.25
        a_threshold=cfg1["a_cagr"],         # 0.20
        n_within_high=cfg1["n_proximity"],  # 0.10
    )
    portfolio_cfg = PortfolioConfig(
        max_slots=cfg1["slots"],            # 5
        entry_mode=cfg1["entry_option"],    # "C"
        hard_stop_pct=cfg1["hard_stop"],    # 0.06
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

    print(f"[phase33 BT-03] OOS backtest {PERIOD[0]}..{PERIOD[1]}")
    print(f"  config: c_yoy={cfg1['c_yoy']}, a_cagr={cfg1['a_cagr']}, "
          f"n_prox={cfg1['n_proximity']}, hard_stop={cfg1['hard_stop']}, "
          f"slots={cfg1['slots']}, entry={cfg1['entry_option']}")

    result = run_vn100_backtest(
        canslim_cfg=canslim_cfg,
        portfolio_cfg=portfolio_cfg,
        entry_option=cfg1["entry_option"],
        period=PERIOD,
    )

    nav_df = result["nav"]
    trades_df = result["trades"]
    positions_df = result["positions"]
    metrics = result["metrics"]

    # Write CSVs
    nav_df.to_csv(OUT_DIR / "oos_nav.csv", index=False)
    trades_df.to_csv(OUT_DIR / "oos_trades.csv", index=False)
    positions_df.to_csv(OUT_DIR / "oos_positions.csv", index=False)

    # Write metrics JSON for downstream consumption
    with open(OUT_DIR / "oos_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Summary
    print(f"\n[phase33 BT-03] OOS Summary")
    print("=" * 60)
    for k in ("CAGR", "Sharpe_rf3", "MaxDD", "MaxDD_duration_days",
              "hit_rate", "num_trades", "avg_hold_days", "turnover",
              "total_cost_drag_pct"):
        v = metrics.get(k, "N/A")
        if isinstance(v, float):
            if "pct" in k or k in ("CAGR", "MaxDD", "hit_rate"):
                print(f"  {k:25s}: {v * 100:.2f}%")
            else:
                print(f"  {k:25s}: {v:.3f}")
        else:
            print(f"  {k:25s}: {v}")

    print(f"\n[phase33 BT-03] Wrote:")
    for p in ("oos_nav.csv", "oos_trades.csv", "oos_positions.csv", "oos_metrics.json"):
        print(f"  {OUT_DIR / p}")


if __name__ == "__main__":
    main()
