"""Phase 32 BT-02 — VN100 in-sample parameter sweep (1,536 configs).

Grid (D-03..D-13):
    c_yoy       x 4   (0.10, 0.15, 0.20, 0.25)
    a_cagr      x 4   (0.10, 0.15, 0.20, 0.25)
    n_proximity x 4   (0.05, 0.10, 0.15, 0.20)
    hard_stop   x 4   (0.06, 0.07, 0.08, 0.10)
    slots       x 3   (5, 8, 10)
    entry_option x 2  ("A", "C")
    Total: 4*4*4*4*3*2 = 1536

Period: 2014-01-01 .. 2018-12-31 (D-09).

Per D-06: multiprocessing.Pool(cpu_count()-1).
Per D-07: fail-loud per config, log crash, continue.
Per D-13: sanity_flag is SOFT (`OK` / `CAGR_TOO_HIGH`) — do not abort.

Output: ``docs/audits/phase32/sweep_results.csv``.
Plan 03 consumes this CSV for top-3 selection + report.

Usage:
    uv run python analysis/sweep_vn100.py
"""
from __future__ import annotations

import itertools
import math
import os
import sys
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repo root on sys.path so workers can import ``analysis.*`` under
# Windows spawn-based multiprocessing.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd

from analysis._vn100_pipeline import run_vn100_backtest, precompute_static
from strategies.canslim.config import CanslimConfig
from strategies.portfolio.config import PortfolioConfig


PERIOD: Tuple[str, str] = ("2014-01-01", "2018-12-31")

GRID: Dict[str, List[Any]] = {
    "c_yoy":        [0.10, 0.15, 0.20, 0.25],
    "a_cagr":       [0.10, 0.15, 0.20, 0.25],
    "n_proximity":  [0.05, 0.10, 0.15, 0.20],
    "hard_stop":    [0.06, 0.07, 0.08, 0.10],
    "slots":        [5, 8, 10],
    "entry_option": ["A", "C"],
}

OUTPUT_CSV = Path("docs/audits/phase32/sweep_results.csv")

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
    "c_yoy",
    "a_cagr",
    "n_proximity",
    "hard_stop",
    "slots",
    "entry_option",
]


def build_grid() -> List[Dict[str, Any]]:
    """Cartesian product of :data:`GRID` → list of 1,536 config dicts."""
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
        Row dict with GRID_COLS + METRIC_COLS + sanity_flag + error.
    """
    config, _precomputed = args
    try:
        canslim_cfg = CanslimConfig(
            c_threshold=float(config["c_yoy"]),
            a_threshold=float(config["a_cagr"]),
            n_within_high=float(config["n_proximity"]),
        )
        portfolio_cfg = PortfolioConfig(
            max_slots=int(config["slots"]),
            hard_stop_pct=float(config["hard_stop"]),
            entry_mode=str(config["entry_option"]),
        )
        result = run_vn100_backtest(
            canslim_cfg,
            portfolio_cfg,
            config["entry_option"],
            PERIOD,
            precomputed=None,
        )
        metrics = result["metrics"]
        row: Dict[str, Any] = {**config, **{k: metrics.get(k, float("nan")) for k in METRIC_COLS}}
        cagr = row.get("CAGR", float("nan"))
        if isinstance(cagr, (int, float)) and not math.isnan(cagr) and cagr > SANITY_CAGR_THRESHOLD:
            row["sanity_flag"] = "CAGR_TOO_HIGH"
        else:
            row["sanity_flag"] = "OK"
        row["error"] = ""
        return row
    except Exception as e:  # noqa: BLE001 — D-07 fail-loud per config, continue sweep
        row = {**config, **_nan_metrics()}
        row["sanity_flag"] = "ERROR"
        row["error"] = f"{type(e).__name__}: {e}"
        return row


def main() -> int:
    print(f"[sweep] Phase 32 BT-02 starting — period={PERIOD}")
    grid = build_grid()
    assert len(grid) == 1536, f"grid size {len(grid)} != 1536"
    print(f"[sweep] grid built: {len(grid)} configs")

    # D-05 step 1: precompute parquet cache once in the main process before
    # fanning out. Workers will lazily re-load from parquet.
    print("[sweep] priming parquet cache via precompute_static …")
    precompute_static(PERIOD)
    print("[sweep] cache primed")

    try:
        from tqdm import tqdm
    except ImportError:  # pragma: no cover — tqdm should be present
        def tqdm(it, **kwargs):
            return it

    n_workers = max(1, cpu_count() - 1)
    print(f"[sweep] launching Pool({n_workers}) …")

    results: List[Dict[str, Any]] = []
    with Pool(n_workers) as pool:
        iterator = pool.imap_unordered(
            _worker,
            [(cfg, None) for cfg in grid],
            chunksize=4,
        )
        for row in tqdm(iterator, total=len(grid), desc="sweep"):
            results.append(row)

    col_order = GRID_COLS + METRIC_COLS + ["sanity_flag", "error"]
    df = pd.DataFrame(results, columns=col_order)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    n_ok = int((df["sanity_flag"] == "OK").sum())
    n_flag = int((df["sanity_flag"] == "CAGR_TOO_HIGH").sum())
    n_err = int((df["sanity_flag"] == "ERROR").sum())
    print(
        f"[sweep] DONE — total={len(df)} OK={n_ok} "
        f"CAGR_TOO_HIGH={n_flag} ERROR={n_err}"
    )
    print(f"[sweep] wrote {OUTPUT_CSV}")
    if n_flag > 0:
        print(
            f"[sweep] WARNING: {n_flag} configs flagged CAGR_TOO_HIGH (>300%). "
            "Review before top-3 selection (D-13)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
