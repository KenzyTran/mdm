"""Phase 33 BT-04 — Sensitivity matrix + baselines + diem_canslim OOS comparison.

Performs 4 analysis tasks in one script:
  A) 3x3 sensitivity matrix: 3 universe modes × 3 locked configs = 9 runs
  B) CANSLIM-only baseline (no MDM gate)
  C) MDM-only-on-index baseline (simple NAV from VN30/VN-Index × MDM state)
  D) VN-Index B&H benchmark
  E) diem_canslim OOS comparison (Spearman rho + top-10 overlap per quarter)

Writes:
  - docs/audits/phase33/sensitivity_matrix.csv
  - docs/audits/phase33/baselines.json
  - docs/audits/phase33/diem_canslim_oos.json

Usage:
    uv run python analysis/sensitivity_vn100.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd

from analysis._vn100_pipeline import precompute_static, run_vn100_backtest
from strategies.canslim.config import CanslimConfig
from strategies.portfolio.config import PortfolioConfig

PERIOD: Tuple[str, str] = ("2019-01-01", "2025-12-31")
OUT_DIR = Path("docs/audits/phase33")
LOCKED_PARAMS = Path("docs/audits/phase32/locked_params_top3.json")
VNINDEX_CSV = Path("data/vnindex.csv")

UNIVERSE_MODES = ["current-vn100", "liquidity-reconstructed", "vn30-only"]

METRIC_COLS = [
    "CAGR", "Sharpe_rf3", "MaxDD", "MaxDD_duration_days",
    "hit_rate", "turnover", "total_cost_drag_pct", "num_trades", "avg_hold_days",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_locked_configs() -> List[Dict[str, Any]]:
    """Load all 3 locked configs from phase32."""
    with open(LOCKED_PARAMS) as f:
        data = json.load(f)
    return data["configs"]


def _build_canslim_cfg(cfg_dict: Dict[str, Any]) -> CanslimConfig:
    return CanslimConfig(
        c_threshold=cfg_dict["c_yoy"],
        a_threshold=cfg_dict["a_cagr"],
        n_within_high=cfg_dict["n_proximity"],
    )


def _build_portfolio_cfg(cfg_dict: Dict[str, Any]) -> PortfolioConfig:
    return PortfolioConfig(
        max_slots=cfg_dict["slots"],
        entry_mode=cfg_dict["entry_option"],
        hard_stop_pct=cfg_dict["hard_stop"],
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


def _compute_simple_metrics(
    nav: np.ndarray,
    period: Tuple[str, str],
    rf: float = 0.03,
) -> Dict[str, float]:
    """Compute CAGR, Sharpe_rf3, MaxDD from a NAV array."""
    nav = np.asarray(nav, dtype=float)
    nav = nav[np.isfinite(nav)]
    n = len(nav)
    if n < 2 or nav[0] <= 0:
        return {"CAGR": 0.0, "Sharpe_rf3": 0.0, "MaxDD": 0.0, "MaxDD_duration_days": 0}

    start_ts = pd.Timestamp(period[0])
    end_ts = pd.Timestamp(period[1])
    n_years = max((end_ts - start_ts).days / 365.25, 1e-9)
    total_ret = nav[-1] / nav[0]
    cagr = total_ret ** (1 / n_years) - 1 if total_ret > 0 else -1.0

    daily_returns = np.diff(nav) / nav[:-1]
    daily_returns = np.nan_to_num(daily_returns, nan=0.0, posinf=0.0, neginf=0.0)
    ann_vol = float(daily_returns.std(ddof=0) * math.sqrt(252))
    sharpe_rf3 = (cagr - rf) / ann_vol if ann_vol > 0 else 0.0

    peak = np.maximum.accumulate(nav)
    dd = (nav - peak) / peak
    max_dd = float(dd.min())

    underwater = nav < peak
    max_dur, cur = 0, 0
    for flag in underwater:
        if flag:
            cur += 1
            if cur > max_dur:
                max_dur = cur
        else:
            cur = 0

    return {
        "CAGR": float(cagr),
        "Sharpe_rf3": float(sharpe_rf3),
        "MaxDD": float(max_dd),
        "MaxDD_duration_days": int(max_dur),
    }


# ---------------------------------------------------------------------------
# Part A: Sensitivity matrix worker
# ---------------------------------------------------------------------------

def _run_one(args: Tuple[str, Dict[str, Any], Tuple[str, str]]) -> Dict[str, Any]:
    """Multiprocessing worker: run one (mode, config) combination."""
    import sys
    from pathlib import Path
    _REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    from analysis._vn100_pipeline import precompute_static, run_vn100_backtest
    from strategies.canslim.config import CanslimConfig
    from strategies.portfolio.config import PortfolioConfig

    mode, cfg_dict, period = args
    try:
        precomputed = precompute_static(period, mode=mode)
        canslim_cfg = CanslimConfig(
            c_threshold=cfg_dict["c_yoy"],
            a_threshold=cfg_dict["a_cagr"],
            n_within_high=cfg_dict["n_proximity"],
        )
        portfolio_cfg = PortfolioConfig(
            max_slots=cfg_dict["slots"],
            entry_mode=cfg_dict["entry_option"],
            hard_stop_pct=cfg_dict["hard_stop"],
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
        result = run_vn100_backtest(
            canslim_cfg, portfolio_cfg, cfg_dict["entry_option"], period, precomputed
        )
        return {"mode": mode, "rank": cfg_dict["rank"], **result["metrics"]}
    except Exception as e:
        print(f"  [WARN] _run_one({mode}, rank={cfg_dict['rank']}) failed: {e}")
        return {
            "mode": mode,
            "rank": cfg_dict["rank"],
            **{k: float("nan") for k in [
                "CAGR", "Sharpe_rf3", "MaxDD", "MaxDD_duration_days",
                "hit_rate", "turnover", "total_cost_drag_pct", "num_trades", "avg_hold_days",
            ]},
        }


def run_sensitivity_matrix(configs: List[Dict[str, Any]]) -> pd.DataFrame:
    """Part A: 3x3 sensitivity matrix using multiprocessing."""
    work_args = [
        (mode, cfg, PERIOD)
        for mode in UNIVERSE_MODES
        for cfg in configs
    ]
    n_workers = max(1, cpu_count() - 1)
    print(f"\n[sensitivity] Running {len(work_args)} jobs across {n_workers} workers...")

    results = []
    with Pool(n_workers) as pool:
        for row in pool.imap_unordered(_run_one, work_args):
            print(
                f"  done: mode={row['mode']}, rank={row['rank']}, "
                f"CAGR={row.get('CAGR', float('nan')):.3f}, "
                f"Sharpe={row.get('Sharpe_rf3', float('nan')):.3f}"
            )
            results.append(row)

    df = pd.DataFrame(results)
    col_order = ["mode", "rank"] + METRIC_COLS
    for col in col_order:
        if col not in df.columns:
            df[col] = float("nan")
    df = df[col_order].sort_values(["mode", "rank"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Part B: CANSLIM-only baseline (constant BUY)
# ---------------------------------------------------------------------------

def run_canslim_only_baseline(configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Part B: Run rank-1 config on current-vn100 with all-BUY gate."""
    cfg1 = configs[0]  # rank-1
    print("\n[sensitivity] Running CANSLIM-only baseline (constant BUY gate)...")
    precomputed = precompute_static(PERIOD, mode="current-vn100")

    # Override MDM gate: create periodic CASH->BUY transitions so that
    # buy windows (20 bars each) tile the entire period. Every 19th bar
    # is CASH, the next bar re-opens a new window. This gives EntryEngine
    # continuous buy eligibility — the correct semantic for "no MDM gate".
    all_buy = pd.Series(
        "BUY",
        index=precomputed["mdm_gate"].index,
        name="mdm_state",
    )
    # Place CASH at bar 0, then every 19 bars to re-trigger windows
    for i in range(0, len(all_buy), 19):
        all_buy.iloc[i] = "CASH"
    precomputed_override = dict(precomputed)
    precomputed_override["mdm_gate"] = all_buy

    canslim_cfg = _build_canslim_cfg(cfg1)
    portfolio_cfg = _build_portfolio_cfg(cfg1)

    result = run_vn100_backtest(
        canslim_cfg, portfolio_cfg, cfg1["entry_option"], PERIOD, precomputed_override
    )
    metrics = result["metrics"]
    print(
        f"  CANSLIM-only: CAGR={metrics['CAGR']:.3f}, "
        f"Sharpe={metrics['Sharpe_rf3']:.3f}, MaxDD={metrics['MaxDD']:.3f}"
    )
    return metrics


# ---------------------------------------------------------------------------
# Part C: MDM-only-on-index baseline
# ---------------------------------------------------------------------------

def run_mdm_only_index_baseline() -> Dict[str, Any]:
    """Part C: Simple NAV — in market when MDM=BUY, cash otherwise."""
    print("\n[sensitivity] Computing MDM-only-on-index baseline...")

    # Load VN-Index price data
    vnidx = pd.read_csv(VNINDEX_CSV)
    # Columns: stockcode, tradingdate, openindex, closeindex, highestindex, lowestindex, totalvol
    vnidx = vnidx.rename(columns={"tradingdate": "date", "closeindex": "close"})
    vnidx["date"] = pd.to_datetime(vnidx["date"])
    vnidx = vnidx.sort_values("date").reset_index(drop=True)

    # Filter to OOS period
    start_ts = pd.Timestamp(PERIOD[0])
    end_ts = pd.Timestamp(PERIOD[1])
    vnidx = vnidx[(vnidx["date"] >= start_ts) & (vnidx["date"] <= end_ts)].reset_index(drop=True)

    if vnidx.empty:
        print("  [WARN] No VN-Index data for OOS period")
        return {"CAGR": 0.0, "Sharpe_rf3": 0.0, "MaxDD": 0.0, "MaxDD_duration_days": 0}

    # Get MDM gate (cached from Part A or Part B)
    precomputed = precompute_static(PERIOD, mode="current-vn100")
    gate = precomputed["mdm_gate"]

    # Align gate to VN-Index trading dates
    idx_dates = pd.DatetimeIndex(vnidx["date"])
    gate_aligned = gate.reindex(idx_dates).ffill().fillna("CASH")

    # Build NAV: in market when BUY, flat otherwise
    closes = vnidx["close"].astype(float).values
    n = len(closes)
    nav = np.ones(n, dtype=float)
    for i in range(1, n):
        state = gate_aligned.iloc[i - 1]  # use i-1 state (no look-ahead, state[i-1] discipline)
        if state == "BUY":
            ret = closes[i] / closes[i - 1] - 1.0
        else:
            ret = 0.0
        nav[i] = nav[i - 1] * (1 + ret)

    metrics = _compute_simple_metrics(nav, PERIOD)
    print(
        f"  MDM-only-index: CAGR={metrics['CAGR']:.3f}, "
        f"Sharpe={metrics['Sharpe_rf3']:.3f}, MaxDD={metrics['MaxDD']:.3f}"
    )
    return metrics


# ---------------------------------------------------------------------------
# Part D: VN-Index B&H benchmark
# ---------------------------------------------------------------------------

def run_vnindex_bh_benchmark() -> Dict[str, Any]:
    """Part D: VN-Index Buy & Hold benchmark for OOS period."""
    print("\n[sensitivity] Computing VN-Index B&H benchmark...")

    vnidx = pd.read_csv(VNINDEX_CSV)
    vnidx = vnidx.rename(columns={"tradingdate": "date", "closeindex": "close"})
    vnidx["date"] = pd.to_datetime(vnidx["date"])
    vnidx = vnidx.sort_values("date").reset_index(drop=True)

    start_ts = pd.Timestamp(PERIOD[0])
    end_ts = pd.Timestamp(PERIOD[1])
    vnidx = vnidx[(vnidx["date"] >= start_ts) & (vnidx["date"] <= end_ts)].reset_index(drop=True)

    if vnidx.empty:
        print("  [WARN] No VN-Index data for OOS period")
        return {"CAGR": 0.0, "Sharpe_rf3": 0.0, "MaxDD": 0.0, "MaxDD_duration_days": 0}

    closes = vnidx["close"].astype(float).values
    nav = closes / closes[0]  # normalized to 1.0 at start

    metrics = _compute_simple_metrics(nav, PERIOD)
    print(
        f"  VN-Index B&H: CAGR={metrics['CAGR']:.3f}, "
        f"Sharpe={metrics['Sharpe_rf3']:.3f}, MaxDD={metrics['MaxDD']:.3f}"
    )
    return metrics


# ---------------------------------------------------------------------------
# Part E: diem_canslim OOS comparison
# ---------------------------------------------------------------------------

def run_diem_canslim_oos_comparison() -> Dict[str, Any]:
    """Part E: Spearman rho + top-10 overlap per OOS quarter (2019-2025).

    Requires live MySQL connection. On failure, returns stub with explanation.
    """
    print("\n[sensitivity] Running diem_canslim OOS comparison (Spearman rho + top-10)...")

    try:
        from scipy.stats import spearmanr
    except ImportError:
        print("  [WARN] scipy not available — using numpy fallback for Spearman rho")
        spearmanr = None  # type: ignore

    try:
        from connectors import mysql
        from strategies.canslim.baseline import (
            available_baseline_quarters,
            load_baseline_quarter,
            quarter_to_last_trading_day,
        )
        from connectors import postgres as pg_conn
        from strategies.canslim.universe import UniverseLoader
    except Exception as e:
        print(f"  [WARN] Cannot import DB connectors: {e}")
        return _diem_canslim_stub("DB connector import failed")

    try:
        mysql_engine = mysql.get_engine()
        pg_engine = pg_conn.get_engine()
    except Exception as e:
        print(f"  [WARN] DB connection failed: {e}")
        return _diem_canslim_stub(f"DB connection failed: {e}")

    # Get VN100 tickers
    try:
        loader = UniverseLoader(mode="current-vn100", pg_engine=pg_engine)
        from datetime import date as _date
        vn100_tickers = sorted(loader.get(_date(2022, 1, 1)))
    except Exception as e:
        print(f"  [WARN] Could not load universe: {e}")
        return _diem_canslim_stub(f"Universe load failed: {e}")

    # Get available baseline quarters for OOS period
    try:
        all_quarters = available_baseline_quarters(mysql_engine)
    except Exception as e:
        print(f"  [WARN] Could not query baseline quarters: {e}")
        return _diem_canslim_stub(f"Baseline quarters query failed: {e}")

    # Filter to OOS quarters: 2019 Q1 through 2025 Q4
    oos_quarters = []
    for q in all_quarters:
        try:
            parts = q.strip().split()
            qnum = int(parts[0].lstrip("Qq"))
            year = int(parts[1])
            if 2019 <= year <= 2025:
                oos_quarters.append(q)
        except Exception:
            continue

    if not oos_quarters:
        print("  [WARN] No OOS quarters found in baseline data (2019-2025)")
        return _diem_canslim_stub("No OOS quarters in baseline")

    # Load precomputed scorer data for comparison
    # We compare tong_diem ranking vs our CANSLIM score ranking
    precomputed = precompute_static(PERIOD, mode="current-vn100")
    # Use build_canslim_raw_frame to get our scores
    try:
        from analysis._vn100_pipeline import build_canslim_raw_frame

        ohlc = precomputed["ohlc"]
        panel = pd.DataFrame({
            "date": pd.to_datetime(ohlc["tradingdate"]),
            "ticker": ohlc["stockcode"].astype(str).str.strip(),
            "open": (ohlc["adj_open"] if "adj_open" in ohlc.columns else ohlc["openprice"]).astype(float),
            "high": (ohlc["adj_high"] if "adj_high" in ohlc.columns else ohlc["highestprice"]).astype(float),
            "low": (ohlc["adj_low"] if "adj_low" in ohlc.columns else ohlc["lowestprice"]).astype(float),
            "close": (ohlc["adj_close"] if "adj_close" in ohlc.columns else ohlc["closeprice"]).astype(float),
            "volume": ohlc["totalvol"].astype(float),
        }).sort_values(["ticker", "date"]).reset_index(drop=True)
        raw_frame = build_canslim_raw_frame(panel, precomputed)
    except Exception as e:
        print(f"  [WARN] build_canslim_raw_frame failed: {e}")
        return _diem_canslim_stub(f"CANSLIM raw frame build failed: {e}")

    per_quarter_results = []
    for q in oos_quarters:
        try:
            # Get last trading day in this quarter
            last_td = quarter_to_last_trading_day(pg_engine, q)
            as_of = pd.Timestamp(last_td)

            # Baseline top tickers by tong_diem
            baseline_df = load_baseline_quarter(mysql_engine, q, vn100_tickers)
            if baseline_df.empty:
                continue
            baseline_df = baseline_df.sort_values("tong_diem", ascending=False).reset_index(drop=True)
            baseline_df["baseline_rank"] = range(1, len(baseline_df) + 1)
            baseline_top10 = set(baseline_df.head(10)["mack"].str.upper().tolist())

            # Our scores on that date: use n_prox as proxy score (lower n_prox = closer to high = better)
            our_day = raw_frame[raw_frame["date"] == as_of].copy()
            if our_day.empty:
                # Try nearest available date
                available_dates = raw_frame["date"].unique()
                if len(available_dates) == 0:
                    continue
                nearest = min(available_dates, key=lambda d: abs(pd.Timestamp(d) - as_of))
                our_day = raw_frame[raw_frame["date"] == nearest].copy()

            if our_day.empty:
                continue

            our_day["ticker"] = our_day["ticker"].str.upper().str.strip()
            # Score: combine eps_yoy_q0 and eps_cagr_3y; lower n_prox = better
            # Use a composite: c_pass weight + a_pass weight + (1 - n_prox) weight
            our_day = our_day.dropna(subset=["eps_yoy_q0", "eps_cagr_3y", "n_prox"])
            if len(our_day) < 5:
                continue

            # Compute composite rank score
            our_day["our_score"] = (
                our_day["eps_yoy_q0"].clip(0, 5) * 0.4
                + our_day["eps_cagr_3y"].clip(0, 5) * 0.4
                + (1.0 - our_day["n_prox"].clip(0, 1)) * 0.2
            )
            our_day = our_day.sort_values("our_score", ascending=False).reset_index(drop=True)
            our_day["our_rank"] = range(1, len(our_day) + 1)
            our_top10 = set(our_day.head(10)["ticker"].tolist())

            # Merge on ticker
            merged = pd.merge(
                baseline_df[["mack", "baseline_rank"]].rename(columns={"mack": "ticker"}),
                our_day[["ticker", "our_rank"]],
                on="ticker",
                how="inner",
            )

            if len(merged) < 5:
                continue

            # Spearman rho
            if spearmanr is not None:
                rho_val, _ = spearmanr(merged["baseline_rank"].values, merged["our_rank"].values)
            else:
                # Fallback: manual Spearman using numpy
                x = merged["baseline_rank"].values.astype(float)
                y = merged["our_rank"].values.astype(float)
                n_obs = len(x)
                rank_x = pd.Series(x).rank().values
                rank_y = pd.Series(y).rank().values
                d2 = ((rank_x - rank_y) ** 2).sum()
                rho_val = float(1 - 6 * d2 / (n_obs * (n_obs ** 2 - 1)))

            # Top-10 overlap
            overlap = len(baseline_top10 & our_top10)

            per_quarter_results.append({
                "quarter": q,
                "rho": float(rho_val) if not math.isnan(rho_val) else 0.0,
                "overlap": int(overlap),
                "n_common": int(len(merged)),
            })
            print(f"  {q}: rho={rho_val:.3f}, overlap={overlap}/10, n_common={len(merged)}")

        except Exception as e:
            print(f"  [WARN] Quarter {q} failed: {e}")
            continue

    if not per_quarter_results:
        return _diem_canslim_stub("No quarters could be computed")

    rhos = [r["rho"] for r in per_quarter_results]
    overlaps = [r["overlap"] for r in per_quarter_results]
    median_rho = float(np.median(rhos))
    mean_overlap = float(np.mean(overlaps))

    print(f"\n  diem_canslim OOS summary:")
    print(f"    Quarters compared: {len(per_quarter_results)}")
    print(f"    Median Spearman rho: {median_rho:.3f}")
    print(f"    Mean top-10 overlap: {mean_overlap:.2f}/10")

    return {
        "period": f"{PERIOD[0][:4]}-{PERIOD[1][:4]}",
        "quarters_compared": len(per_quarter_results),
        "median_spearman_rho": median_rho,
        "mean_top10_overlap": mean_overlap,
        "per_quarter": per_quarter_results,
    }


def _diem_canslim_stub(reason: str) -> Dict[str, Any]:
    """Return a stub result when DB is unavailable."""
    print(f"  [STUB] diem_canslim comparison skipped: {reason}")
    return {
        "period": f"{PERIOD[0][:4]}-{PERIOD[1][:4]}",
        "quarters_compared": 0,
        "median_spearman_rho": float("nan"),
        "mean_top10_overlap": float("nan"),
        "per_quarter": [],
        "stub_reason": reason,
    }


# ---------------------------------------------------------------------------
# write_verdict: auto-generate docs/audits/phase33/verdict.md
# ---------------------------------------------------------------------------

def write_verdict() -> None:
    """Task 2: Write pass/fail verdict against BT-08 targets."""
    print("\n[sensitivity] Writing verdict.md...")

    oos_metrics_path = OUT_DIR / "oos_metrics.json"
    baselines_path = OUT_DIR / "baselines.json"
    matrix_path = OUT_DIR / "sensitivity_matrix.csv"
    diem_path = OUT_DIR / "diem_canslim_oos.json"

    # Load required data
    if not oos_metrics_path.exists():
        raise FileNotFoundError(f"Missing {oos_metrics_path} — run phase 33-01 first")
    with open(oos_metrics_path) as f:
        oos = json.load(f)

    if not baselines_path.exists():
        raise FileNotFoundError(f"Missing {baselines_path} — run sensitivity matrix first")
    with open(baselines_path) as f:
        baselines = json.load(f)

    matrix_df = pd.read_csv(matrix_path) if matrix_path.exists() else pd.DataFrame()

    diem_data: Dict[str, Any] = {}
    if diem_path.exists():
        with open(diem_path) as f:
            diem_data = json.load(f)

    # BT-08 pass criteria
    s_sharpe = oos["Sharpe_rf3"]
    s_maxdd = oos["MaxDD"]
    s_cagr = oos["CAGR"]

    bh = baselines.get("vnindex_bh", {})
    b_sharpe = bh.get("Sharpe_rf3", 0.0)
    b_maxdd = bh.get("MaxDD", -1.0)
    b_cagr = bh.get("CAGR", 0.0)

    sharpe_uplift = s_sharpe - b_sharpe
    maxdd_reduction = 1 - abs(s_maxdd) / abs(b_maxdd) if b_maxdd != 0 else 0.0

    sharpe_pass = sharpe_uplift > 0.20
    maxdd_pass = maxdd_reduction > 0.30
    overall_pass = sharpe_pass and maxdd_pass

    verdict_str = "PASS" if overall_pass else "FAIL"
    sharpe_verdict = "PASS" if sharpe_pass else "FAIL"
    maxdd_verdict = "PASS" if maxdd_pass else "FAIL"

    # Baselines for comparison section
    canslim_only = baselines.get("canslim_only", {})
    mdm_idx = baselines.get("mdm_only_index", {})

    # Build sensitivity pivot table
    sensitivity_section = ""
    if not matrix_df.empty:
        sensitivity_section += "\n### Sharpe_rf3 Pivot (universe mode x rank)\n\n"
        try:
            pivot = matrix_df.pivot_table(
                index="mode", columns="rank", values="Sharpe_rf3", aggfunc="first"
            )
            sensitivity_section += "| Mode | Rank 1 | Rank 2 | Rank 3 |\n"
            sensitivity_section += "|------|--------|--------|--------|\n"
            for mode in UNIVERSE_MODES:
                if mode in pivot.index:
                    r1 = pivot.loc[mode].get(1, float("nan"))
                    r2 = pivot.loc[mode].get(2, float("nan"))
                    r3 = pivot.loc[mode].get(3, float("nan"))
                    row_pass = []
                    for v in [r1, r2, r3]:
                        p = " (P)" if not math.isnan(v) and (v - b_sharpe) > 0.20 else " (F)"
                        row_pass.append(f"{v:.3f}{p}" if not math.isnan(v) else "N/A")
                    sensitivity_section += f"| {mode} | {row_pass[0]} | {row_pass[1]} | {row_pass[2]} |\n"

            sensitivity_section += "\nP = Sharpe uplift > 0.20 vs VN-Index B&H. F = fails BT-08 Sharpe target.\n"
        except Exception as e:
            sensitivity_section += f"\n(Pivot failed: {e})\n"
            # Fallback: show raw matrix
            sensitivity_section += "\n" + matrix_df[["mode", "rank", "CAGR", "Sharpe_rf3", "MaxDD"]].to_markdown(index=False) + "\n"
    else:
        sensitivity_section = "\n_(Sensitivity matrix not available)_\n"

    # diem_canslim section
    diem_section = ""
    if diem_data and diem_data.get("quarters_compared", 0) > 0:
        med_rho = diem_data.get("median_spearman_rho", float("nan"))
        mean_ol = diem_data.get("mean_top10_overlap", float("nan"))
        n_q = diem_data.get("quarters_compared", 0)
        diem_section = f"""
| Metric | OOS (2019-2025) | In-Sample (Phase 29) |
|--------|-----------------|----------------------|
| Median Spearman rho | {med_rho:.3f} | 0.280 |
| Mean top-10 overlap | {mean_ol:.2f}/10 | 2.43/10 |
| Quarters compared | {n_q} | 28 |

{"OOS rho (" + f"{med_rho:.3f}" + ") vs in-sample (0.280): " + ("OOS ranking agreement is higher — CANSLIM scorer generalizes well OOS." if med_rho > 0.280 else "OOS ranking agreement is lower than in-sample — some degradation in scorer correlation.")}"
"""
    elif diem_data.get("stub_reason"):
        diem_section = f"\n_(diem_canslim OOS comparison skipped: {diem_data['stub_reason']})_\n"
    else:
        diem_section = "\n_(diem_canslim OOS comparison data not available)_\n"

    # Failure attribution section (only if fail)
    attribution_section = ""
    if not overall_pass:
        canslim_sharpe = canslim_only.get("Sharpe_rf3", float("nan"))
        mdm_sharpe = mdm_idx.get("Sharpe_rf3", float("nan"))
        cost_drag = oos.get("total_cost_drag_pct", 0.0)

        attribution_section = "\n## 7. Failure Attribution\n\n"

        # Analysis logic per plan spec
        if not math.isnan(canslim_sharpe) and canslim_sharpe < b_sharpe:
            primary = "CANSLIM scoring"
            reason = (
                f"CANSLIM-only Sharpe ({canslim_sharpe:.3f}) is below VN-Index B&H Sharpe ({b_sharpe:.3f}), "
                f"meaning the stock selection itself does not beat the index even without MDM gating. "
                f"The CANSLIM criteria (c_yoy=0.25, a_cagr=0.20, n_prox=0.10) may be too restrictive or "
                f"the selected stocks underperform on average during the OOS period."
            )
        elif not math.isnan(canslim_sharpe) and s_sharpe < canslim_sharpe:
            primary = "MDM gate"
            reason = (
                f"Strategy Sharpe ({s_sharpe:.3f}) is lower than CANSLIM-only Sharpe ({canslim_sharpe:.3f}), "
                f"suggesting the MDM gate is reducing exposure during profitable periods. "
                f"The HybridEngine may be keeping the portfolio in CASH/SELL during VN-market bull runs "
                f"that do not match the NASDAQ-calibrated MDM patterns."
            )
        elif not math.isnan(mdm_sharpe) and mdm_sharpe > s_sharpe:
            primary = "stock selection / entry timing"
            reason = (
                f"MDM-only-on-index Sharpe ({mdm_sharpe:.3f}) exceeds strategy Sharpe ({s_sharpe:.3f}), "
                f"meaning the MDM timing is correct but stock selection or entry execution (Pocket Pivot) "
                f"is underperforming the index itself. The issue lies in stock picking quality or entry lag."
            )
        elif cost_drag > 5.0:
            primary = "transaction costs"
            reason = (
                f"Total cost drag ratio of {cost_drag:.2f} is significant relative to strategy returns ({s_cagr:.1%} CAGR). "
                f"Commission + slippage + tax costs are eroding returns materially. "
                f"Consider reducing turnover (increase avg hold days from {oos.get('avg_hold_days', 0):.0f} days) "
                f"or negotiating lower commission rates."
            )
        else:
            primary = "marginal performance"
            reason = (
                f"No single dominant component identified. Strategy Sharpe ({s_sharpe:.3f}) vs B&H ({b_sharpe:.3f}) "
                f"shows marginal underperformance. Possible joint effect: universe survivorship bias (static VN100), "
                f"MDM calibrated on NASDAQ not VN-market, and entry lag from Pocket Pivot detector."
            )

        if not sharpe_pass:
            canslim_sharpe_s = f"{canslim_sharpe:.3f}" if not math.isnan(canslim_sharpe) else "N/A"
            mdm_sharpe_s = f"{mdm_sharpe:.3f}" if not math.isnan(mdm_sharpe) else "N/A"
            attribution_section += (
                f"### Sharpe Uplift Failure\n\n"
                f"**Primary reason:** {primary}\n\n"
                f"{reason}\n\n"
                f"**Component breakdown:**\n"
                f"- Strategy Sharpe: {s_sharpe:.3f}\n"
                f"- CANSLIM-only Sharpe: {canslim_sharpe_s}\n"
                f"- MDM-only-index Sharpe: {mdm_sharpe_s}\n"
                f"- VN-Index B&H Sharpe: {b_sharpe:.3f}\n"
                f"- Cost drag (ratio): {cost_drag:.4f}\n\n"
                f"**Actionable conclusion:** The primary reason for Sharpe uplift failure is **{primary}** because {reason}\n"
            )

        if not maxdd_pass:
            s_maxdd_abs = abs(s_maxdd)
            b_maxdd_abs = abs(b_maxdd)
            attribution_section += (
                f"\n### MaxDD Reduction Failure\n\n"
                f"Strategy MaxDD ({s_maxdd:.1%}) vs VN-Index B&H MaxDD ({b_maxdd:.1%}). "
                f"Reduction = {maxdd_reduction:.1%} (target: > 30%).\n\n"
                f"The MDM gate provides {maxdd_reduction:.1%} drawdown reduction. "
                f"{'This falls short of the 30% target, suggesting MDM gating is insufficiently protective during VN-market downturns.' if not maxdd_pass else 'MaxDD target is met.'} "
                f"Possible cause: MDM signals are calibrated on NASDAQ and may lag VN-market corrections by several days.\n"
            )

    # Write the full verdict.md
    lines = [
        "# Phase 33 Plan 02: OOS Pass/Fail Verdict",
        "",
        f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d')}",
        f"**OOS Period:** {PERIOD[0]} .. {PERIOD[1]}",
        f"**Locked config:** rank-1 (c_yoy=0.25, a_cagr=0.20, n_prox=0.10, hard_stop=0.06, slots=5, entry=C)",
        "",
        "---",
        "",
        "## 1. OOS Performance (rank-1 config)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| CAGR | {s_cagr:.2%} |",
        f"| Sharpe_rf3 | {s_sharpe:.3f} |",
        f"| MaxDD | {s_maxdd:.2%} |",
        f"| MaxDD duration | {oos.get('MaxDD_duration_days', 0)} days |",
        f"| Hit rate | {oos.get('hit_rate', 0):.2%} |",
        f"| Num trades | {oos.get('num_trades', 0)} |",
        f"| Avg hold days | {oos.get('avg_hold_days', 0):.1f} |",
        f"| Turnover | {oos.get('turnover', 0):.3f} |",
        f"| Cost drag (ratio) | {oos.get('total_cost_drag_pct', 0):.4f} |",
        "",
        "---",
        "",
        "## 2. VN-Index B&H Benchmark",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| CAGR | {b_cagr:.2%} |",
        f"| Sharpe_rf3 | {b_sharpe:.3f} |",
        f"| MaxDD | {b_maxdd:.2%} |",
        f"| MaxDD duration | {bh.get('MaxDD_duration_days', 0)} days |",
        "",
        "---",
        "",
        "## 3. BT-08 Pass/Fail Verdict",
        "",
        "| Target | Threshold | Strategy | Benchmark | Delta | Verdict |",
        "|--------|-----------|----------|-----------|-------|---------|",
        f"| Sharpe uplift | > 0.20 | {s_sharpe:.3f} | {b_sharpe:.3f} | {sharpe_uplift:+.3f} | {sharpe_verdict} |",
        f"| MaxDD reduction | > 30% | {s_maxdd:.1%} | {b_maxdd:.1%} | {maxdd_reduction:.1%} | {maxdd_verdict} |",
        "",
        f"**Overall: {verdict_str}**",
        "",
        "---",
        "",
        "## 4. Sensitivity Analysis",
        "",
        f"9-run sensitivity matrix: 3 universe modes × 3 locked configs. Period: {PERIOD[0]} .. {PERIOD[1]}.",
        "",
        sensitivity_section,
        "",
        "---",
        "",
        "## 5. Baseline Comparison",
        "",
        "| Baseline | CAGR | Sharpe_rf3 | MaxDD |",
        "|----------|------|------------|-------|",
        f"| Strategy (rank-1) | {s_cagr:.2%} | {s_sharpe:.3f} | {s_maxdd:.2%} |",
        _baseline_row("CANSLIM-only (no MDM gate)", canslim_only),
        _baseline_row("MDM-only-on-index", mdm_idx),
        _baseline_row("VN-Index B&H", bh),
        "",
        "---",
        "",
        "## 6. diem_canslim Ranking Comparison (OOS)",
        "",
        diem_section,
        "",
        "---",
    ]

    if attribution_section:
        lines.append(attribution_section)

    verdict_path = OUT_DIR / "verdict.md"
    verdict_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[sensitivity] Wrote {verdict_path} ({len(verdict_path.read_text())} chars)")
    print(f"[sensitivity] Overall BT-08 verdict: {verdict_str}")


def _baseline_row(label: str, metrics: Dict[str, Any]) -> str:
    cagr = metrics.get("CAGR", float("nan"))
    sharpe = metrics.get("Sharpe_rf3", float("nan"))
    maxdd = metrics.get("MaxDD", float("nan"))
    cagr_s = f"{cagr:.2%}" if not math.isnan(cagr) else "N/A"
    sharpe_s = f"{sharpe:.3f}" if not math.isnan(sharpe) else "N/A"
    maxdd_s = f"{maxdd:.2%}" if not math.isnan(maxdd) else "N/A"
    return f"| {label} | {cagr_s} | {sharpe_s} | {maxdd_s} |"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    configs = _load_locked_configs()
    print(f"[sensitivity] Loaded {len(configs)} locked configs from {LOCKED_PARAMS}")

    # Part A: 3x3 sensitivity matrix
    print("\n" + "=" * 60)
    print("PART A: 3x3 Sensitivity Matrix")
    print("=" * 60)
    matrix_df = run_sensitivity_matrix(configs)
    matrix_path = OUT_DIR / "sensitivity_matrix.csv"
    matrix_df.to_csv(matrix_path, index=False)
    print(f"\n[sensitivity] Wrote {matrix_path} ({len(matrix_df)} rows)")
    print("\nSensitivity Matrix Summary:")
    print(matrix_df[["mode", "rank", "CAGR", "Sharpe_rf3", "MaxDD"]].to_string(index=False))

    # Part B: CANSLIM-only baseline
    print("\n" + "=" * 60)
    print("PART B: CANSLIM-only baseline")
    print("=" * 60)
    canslim_only_metrics = run_canslim_only_baseline(configs)

    # Part C: MDM-only-on-index
    print("\n" + "=" * 60)
    print("PART C: MDM-only-on-index baseline")
    print("=" * 60)
    mdm_only_metrics = run_mdm_only_index_baseline()

    # Part D: VN-Index B&H
    print("\n" + "=" * 60)
    print("PART D: VN-Index B&H benchmark")
    print("=" * 60)
    vnindex_bh_metrics = run_vnindex_bh_benchmark()

    # Save baselines
    baselines = {
        "canslim_only": canslim_only_metrics,
        "mdm_only_index": mdm_only_metrics,
        "vnindex_bh": vnindex_bh_metrics,
    }
    baselines_path = OUT_DIR / "baselines.json"
    with open(baselines_path, "w") as f:
        json.dump(baselines, f, indent=2)
    print(f"\n[sensitivity] Wrote {baselines_path}")

    # Part E: diem_canslim OOS comparison
    print("\n" + "=" * 60)
    print("PART E: diem_canslim OOS comparison")
    print("=" * 60)
    diem_result = run_diem_canslim_oos_comparison()
    diem_path = OUT_DIR / "diem_canslim_oos.json"
    with open(diem_path, "w") as f:
        json.dump(diem_result, f, indent=2, default=lambda x: None if (isinstance(x, float) and math.isnan(x)) else x)
    print(f"[sensitivity] Wrote {diem_path}")

    # Write verdict.md
    print("\n" + "=" * 60)
    print("VERDICT: Writing pass/fail verdict")
    print("=" * 60)
    write_verdict()

    print("\n[sensitivity] All done.")
    print(f"  {OUT_DIR}/sensitivity_matrix.csv")
    print(f"  {OUT_DIR}/baselines.json")
    print(f"  {OUT_DIR}/diem_canslim_oos.json")
    print(f"  {OUT_DIR}/verdict.md")


if __name__ == "__main__":
    main()
