"""Phase 37 BT-02/BT-03 — OOS VN100 v8.0 backtest 2019-2025 with locked formula.

Runs one backtest using the formula and config locked by Phase 37 Plan 02 sweep.
Hard-coded period (no CLI args). Produces oos_metrics_v8.json, oos_nav_v8.csv,
oos_trades_v8.csv, and comparison_table.json (v8.0 vs v7.0 vs VN-Index B&H).

Usage:
    uv run python analysis/backtest_vn100_v8_oos.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis._vn100_pipeline import run_v8_backtest
from strategies.momentum.scorer_config import MomentumScorerConfig
from strategies.portfolio.config import PortfolioConfig

PERIOD = ("2019-01-01", "2025-12-31")
LOCKED_PARAMS = Path("docs/audits/phase37/locked_params_v8.json")
OUT_DIR = Path("docs/audits/phase37")

# v7.0 baseline — locked from docs/audits/phase33/oos_metrics.json
V7_BASELINE = {
    "label": "v7.0 (CANSLIM+MDM)",
    "CAGR": 0.10182,
    "Sharpe_rf3": 0.81335,
    "MaxDD": -0.16309,
    "MaxDD_duration_days": 938,
    "hit_rate": 0.305,
    "num_trades": 59,
    "avg_hold_days": 41.25,
}

# VN-Index B&H — locked from docs/audits/phase33/baselines.json
VNINDEX_BH = {
    "label": "VN-Index B&H",
    "CAGR": 0.10421,
    "Sharpe_rf3": 0.38349,
    "MaxDD": -0.40343,
    "MaxDD_duration_days": None,
    "hit_rate": None,
    "num_trades": None,
    "avg_hold_days": None,
}


def main() -> None:
    """Run OOS backtest with locked formula and produce comparison table."""
    # Load locked params from in-sample sweep
    if not LOCKED_PARAMS.exists():
        raise FileNotFoundError(f"Run sweep first: {LOCKED_PARAMS}")
    with open(LOCKED_PARAMS) as f:
        best = json.load(f)

    print(f"Locked formula: {best['rs_formula']}")
    print(
        f"Locked params: rs_threshold={best['rs_threshold']}, "
        f"n_within_high={best['n_within_high']}, "
        f"hard_stop={best['hard_stop']}, "
        f"slots={int(best['slots'])}, "
        f"entry={best['entry_option']}"
    )

    momentum_cfg = MomentumScorerConfig(
        rs_threshold=float(best["rs_threshold"]),
        n_within_high=float(best["n_within_high"]),
    )
    portfolio_cfg = PortfolioConfig(
        max_slots=int(best["slots"]),
        hard_stop_pct=float(best["hard_stop"]),
    )

    print(f"Running OOS backtest {PERIOD[0]}..{PERIOD[1]} ...", flush=True)
    result = run_v8_backtest(
        momentum_cfg,
        portfolio_cfg,
        best["entry_option"],
        PERIOD,
        formula=best["rs_formula"],
    )

    metrics = result["metrics"]

    # Write OOS artifacts
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "oos_metrics_v8.json", "w") as f:
        json.dump(metrics, f, indent=2, default=float)
    result["nav"].to_csv(OUT_DIR / "oos_nav_v8.csv", index=False)
    result["trades"].to_csv(OUT_DIR / "oos_trades_v8.csv", index=False)
    print(f"OOS artifacts written to {OUT_DIR}")

    # Build comparison table
    v8_row = {
        "label": f"v8.0 (RS+N+MDM, {best['rs_formula']})",
        "CAGR": metrics["CAGR"],
        "Sharpe_rf3": metrics["Sharpe_rf3"],
        "MaxDD": metrics["MaxDD"],
        "MaxDD_duration_days": metrics.get("MaxDD_duration_days"),
        "hit_rate": metrics.get("hit_rate"),
        "num_trades": metrics.get("num_trades"),
        "avg_hold_days": metrics.get("avg_hold_days"),
    }
    comparison = [v8_row, V7_BASELINE, VNINDEX_BH]
    with open(OUT_DIR / "comparison_table.json", "w") as f:
        json.dump(comparison, f, indent=2, default=float)

    # Print human-readable comparison to console
    print("\n=== v8.0 OOS Validation (2019-2025) ===")
    header = f"{'Model':<32} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'Trades':>7} {'AvgHold':>8}"
    print(header)
    print("-" * len(header))
    for row in comparison:
        cagr = f"{row['CAGR']:.1%}" if row["CAGR"] is not None else "—"
        sharpe = f"{row['Sharpe_rf3']:.3f}" if row["Sharpe_rf3"] is not None else "—"
        maxdd = f"{row['MaxDD']:.1%}" if row["MaxDD"] is not None else "—"
        trades = str(int(row["num_trades"])) if row.get("num_trades") is not None else "—"
        hold = f"{row['avg_hold_days']:.1f}d" if row.get("avg_hold_days") is not None else "—"
        print(f"{row['label']:<32} {cagr:>8} {sharpe:>8} {maxdd:>8} {trades:>7} {hold:>8}")

    v7_sharpe = V7_BASELINE["Sharpe_rf3"]
    v8_sharpe = metrics["Sharpe_rf3"]
    delta = v8_sharpe - v7_sharpe
    direction = "BEATS" if delta > 0 else "TRAILS"
    print(f"\nv8.0 {direction} v7.0 by Sharpe_rf3 delta={delta:+.3f}")
    print(f"Comparison table written to {OUT_DIR / 'comparison_table.json'}")


if __name__ == "__main__":
    main()
