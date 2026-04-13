"""Phase 37 BT-01 — VN100 v8.0 in-sample parameter sweep (216 configs).

Grid:
    rs_formula    x 2   ("weighted_roc", "roc126")
    rs_threshold  x 3   (60.0, 70.0, 80.0)
    n_within_high x 3   (0.10, 0.15, 0.20)
    hard_stop     x 3   (0.06, 0.07, 0.08)
    slots         x 2   (5, 8)
    entry_option  x 2   ("A", "C")
    Total: 2*3*3*3*2*2 = 216

Period: 2016-01-01 .. 2018-12-31 (in-sample, formula selection gate BT-01).

Pattern: identical to Phase 32 sweep_vn100.py — Windows-spawn-safe top-level
worker, single precompute_static call in main process, Pool(cpu_count()-1),
tqdm fallback.

Output:
    docs/audits/phase37/sweep_v8_results.csv   — 216 rows, all METRIC_COLS
    docs/audits/phase37/locked_params_v8.json  — winner by Sharpe_rf3 with
                                                 sanity gates (CAGR>=5%,
                                                 MaxDD>=-30%)

Usage:
    uv run python analysis/sweep_vn100_v8.py
"""
from __future__ import annotations

import itertools
import json
import os
import sys
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repo root on sys.path so workers can import analysis.* under
# Windows spawn-based multiprocessing.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd

from analysis._vn100_pipeline import run_v8_backtest, precompute_static
from strategies.momentum.scorer_config import MomentumScorerConfig
from strategies.portfolio.config import PortfolioConfig


PERIOD: Tuple[str, str] = ("2016-01-01", "2018-12-31")

GRID: Dict[str, List[Any]] = {
    "rs_formula":    ["weighted_roc", "roc126"],
    "rs_threshold":  [60.0, 70.0, 80.0],
    "n_within_high": [0.10, 0.15, 0.20],
    "hard_stop":     [0.06, 0.07, 0.08],
    "slots":         [5, 8],
    "entry_option":  ["A", "C"],
}
# Total: 2 * 3 * 3 * 3 * 2 * 2 = 216 configs

OUTPUT_CSV = Path("docs/audits/phase37/sweep_v8_results.csv")
LOCKED_PARAMS = Path("docs/audits/phase37/locked_params_v8.json")

# D-13 / SC5: absolute CAGR threshold above which we flag a row (soft).
SANITY_CAGR_THRESHOLD = 3.0  # 300%

METRIC_COLS: List[str] = [
    "CAGR",
    "Sharpe_rf3",
    "MaxDD",
    "MaxDD_duration_days",
    "hit_rate",
    "turnover",
    "total_cost_drag_pct",
    "num_trades",
    "avg_hold_days",
]

GRID_COLS: List[str] = [
    "rs_formula",
    "rs_threshold",
    "n_within_high",
    "hard_stop",
    "slots",
    "entry_option",
]


def build_grid() -> List[Dict[str, Any]]:
    """Cartesian product of :data:`GRID` → list of 216 config dicts."""
    keys = list(GRID.keys())
    values = [GRID[k] for k in keys]
    grid = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
    return grid


def _nan_metrics() -> Dict[str, float]:
    return {k: float("nan") for k in METRIC_COLS}


def _worker(args: Tuple[Dict[str, Any], Any]) -> Dict[str, Any]:
    """Top-level worker (picklable for Windows spawn).

    Args:
        args: ``(config_dict, precomputed_sentinel)``. ``precomputed_sentinel``
            is currently unused — the pipeline re-loads the parquet cache
            itself inside each worker process (cheap, IO-bound).

    Returns:
        Row dict with GRID_COLS + METRIC_COLS + sanity + error.
    """
    config, _precomputed = args
    try:
        momentum_cfg = MomentumScorerConfig(
            rs_threshold=float(config["rs_threshold"]),
            n_within_high=float(config["n_within_high"]),
        )
        portfolio_cfg = PortfolioConfig(
            max_slots=int(config["slots"]),
            hard_stop_pct=float(config["hard_stop"]),
        )
        result = run_v8_backtest(
            momentum_cfg,
            portfolio_cfg,
            config["entry_option"],
            PERIOD,
            precomputed=None,   # each worker fetches from parquet cache independently
            formula=config["rs_formula"],
        )
        metrics = result["metrics"]
        cagr = metrics.get("CAGR", float("nan"))
        import math
        if isinstance(cagr, (int, float)) and not math.isnan(cagr) and cagr > SANITY_CAGR_THRESHOLD:
            sanity = "CAGR_TOO_HIGH"
        else:
            sanity = "OK"
        row: Dict[str, Any] = {
            **config,
            **{k: metrics.get(k, float("nan")) for k in METRIC_COLS},
            "sanity": sanity,
            "error": "",
        }
    except Exception as exc:
        print(f"[WARN] config {config} failed: {exc}", flush=True)
        row = {**config, **_nan_metrics(), "sanity": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
    return row


def main() -> None:
    """Run the 216-config sweep and write CSV + locked_params JSON."""
    grid = build_grid()
    assert len(grid) == 216, f"grid size {len(grid)} != 216"
    print(f"[sweep_v8] {len(grid)} configs, period {PERIOD[0]}..{PERIOD[1]}", flush=True)

    # Prime cache once before spawning workers (avoids N-way DB race)
    print("[sweep_v8] Priming precompute cache...", flush=True)
    precompute_static(PERIOD)
    print("[sweep_v8] Cache primed.", flush=True)

    n_workers = max(1, cpu_count() - 1)
    print(f"[sweep_v8] launching Pool({n_workers})...", flush=True)
    args = [(cfg, None) for cfg in grid]

    try:
        from tqdm import tqdm
        with Pool(n_workers) as pool:
            rows = list(tqdm(
                pool.imap_unordered(_worker, args, chunksize=4),
                total=len(args),
                desc="sweep_v8",
            ))
    except ImportError:
        with Pool(n_workers) as pool:
            rows = pool.map(_worker, args)

    col_order = GRID_COLS + METRIC_COLS + ["sanity", "error"]
    df = pd.DataFrame(rows, columns=col_order)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    n_ok = int((df["sanity"] == "OK").sum())
    n_flag = int((df["sanity"] == "CAGR_TOO_HIGH").sum())
    n_err = int((df["sanity"] == "ERROR").sum())
    print(
        f"[sweep_v8] DONE — total={len(df)} OK={n_ok} "
        f"CAGR_TOO_HIGH={n_flag} ERROR={n_err}",
        flush=True,
    )
    print(f"[sweep_v8] saved to {OUTPUT_CSV}", flush=True)

    if n_flag > 0:
        print(
            f"[sweep_v8] WARNING: {n_flag} configs flagged CAGR_TOO_HIGH (>300%). "
            "Review before selection.",
            flush=True,
        )

    # Print top-5 per formula for comparison
    for formula in ["weighted_roc", "roc126"]:
        top = df[df["rs_formula"] == formula].sort_values("Sharpe_rf3", ascending=False).head(5)
        print(f"\n=== {formula} top-5 ===")
        print(top[["rs_threshold", "n_within_high", "hard_stop", "slots", "entry_option",
                    "CAGR", "Sharpe_rf3", "MaxDD"]].to_string(index=False))

    # Select winner: highest Sharpe_rf3 where CAGR>=5% and MaxDD>=-30%
    sane = df[(df["CAGR"] >= 0.05) & (df["MaxDD"] >= -0.30) & df["Sharpe_rf3"].notna()]
    if sane.empty:
        print("[sweep_v8] WARNING: No config passed sanity gates — using global best Sharpe", flush=True)
        sane = df[df["Sharpe_rf3"].notna()]
    best = sane.sort_values("Sharpe_rf3", ascending=False).iloc[0]
    locked = best[GRID_COLS + METRIC_COLS].to_dict()

    LOCKED_PARAMS.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCKED_PARAMS, "w") as f:
        json.dump(locked, f, indent=2, default=float)
    print(f"[sweep_v8] Locked params written to {LOCKED_PARAMS}", flush=True)
    print(
        f"[sweep_v8] Winner: formula={locked['rs_formula']}, "
        f"Sharpe_rf3={locked['Sharpe_rf3']:.3f}, "
        f"CAGR={locked['CAGR']:.1%}, "
        f"MaxDD={locked['MaxDD']:.1%}",
        flush=True,
    )


if __name__ == "__main__":
    main()
