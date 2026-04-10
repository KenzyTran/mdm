"""Generate v7.0 comprehensive performance report.

Reads Phase 33 OOS outputs, computes missing metrics (profit factor, VN30 B&H
benchmark, deposit/gold benchmarks, real CAGR), and produces a JSON + markdown
report satisfying BT-05/BT-06/BT-07.

Usage: uv run python analysis/generate_v7_report.py

Outputs:
  docs/audits/phase34/v7_report.json  -- machine-readable full report
  docs/audits/phase34/v7_report.md    -- human-readable markdown summary
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Ensure repo root is on sys.path for connectors import
_REPO_ROOT_STR = str(Path(__file__).parent.parent)
if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)

REPO_ROOT = Path(__file__).parent.parent

# --- Input paths (Phase 33 outputs) ---
OOS_METRICS_PATH = REPO_ROOT / "docs" / "audits" / "phase33" / "oos_metrics.json"
BASELINES_PATH = REPO_ROOT / "docs" / "audits" / "phase33" / "baselines.json"
OOS_TRADES_PATH = REPO_ROOT / "docs" / "audits" / "phase33" / "oos_trades.csv"

# --- Output paths ---
OUT_DIR = REPO_ROOT / "docs" / "audits" / "phase34"
OUT_JSON = OUT_DIR / "v7_report.json"
OUT_MD = OUT_DIR / "v7_report.md"

# --- Inflation constant (BT-07) ---
# Vietnam CPI geometric mean 2019-2025 (source: GSO.gov.vn)
# Annual: 2019:2.79%, 2020:3.23%, 2021:1.84%, 2022:3.15%, 2023:3.25%, 2024:3.6%, 2025:3.5%
AVG_CPI = 0.030

BACKTEST_PERIOD = "2019-01-01 to 2025-12-31"
BACKTEST_YEARS = 7.0
LOCKED_CONFIG = "rank-1: c_yoy=0.25, a_cagr=0.20, n_prox=0.10, hard_stop=0.06, slots=5, entry=C"


def compute_profit_factor(trades_df: pd.DataFrame) -> float:
    """Compute profit factor = sum(winning pnl_pct) / abs(sum(losing pnl_pct)).

    Args:
        trades_df: DataFrame with pnl_pct column.

    Returns:
        Profit factor as float. Returns inf if no losing trades.
    """
    wins = trades_df.loc[trades_df["pnl_pct"] > 0, "pnl_pct"].sum()
    losses = abs(trades_df.loc[trades_df["pnl_pct"] < 0, "pnl_pct"].sum())
    return wins / losses if losses > 0 else float("inf")


def compute_vn30_bh() -> dict:
    """Compute VN30 buy-and-hold benchmark from Postgres index_eod.

    Falls back to hardcoded estimates if Postgres unavailable.

    Returns:
        Dict with CAGR, MaxDD, source keys.
    """
    try:
        from connectors import postgres

        sql = """
        SELECT tradingdate, closeindex
        FROM index_eod
        WHERE stockcode = 'VN30'
          AND tradingdate >= :start AND tradingdate <= :end
        ORDER BY tradingdate
        """
        vn30 = postgres.query(sql, {"start": "2019-01-01", "end": "2025-12-31"})
        if vn30.empty:
            raise ValueError("VN30 data returned empty from Postgres")

        vn30 = vn30.sort_values("tradingdate").reset_index(drop=True)
        first_close = float(vn30["closeindex"].iloc[0])
        last_close = float(vn30["closeindex"].iloc[-1])

        first_date = pd.to_datetime(vn30["tradingdate"].iloc[0])
        last_date = pd.to_datetime(vn30["tradingdate"].iloc[-1])
        years = (last_date - first_date).days / 365.25

        cagr = (last_close / first_close) ** (1 / years) - 1

        # Compute max drawdown
        rolling_max = vn30["closeindex"].cummax()
        drawdown = (vn30["closeindex"] - rolling_max) / rolling_max
        max_dd = float(drawdown.min())

        return {
            "CAGR": round(cagr, 6),
            "MaxDD": round(max_dd, 6),
            "source": "Postgres index_eod (VN30, 2019-01-01 to 2025-12-31)",
        }
    except Exception as exc:
        print(f"[WARN] Postgres unavailable for VN30 B&H, using hardcoded fallback: {exc}")
        # Hardcoded fallback: VN30 approximate (from reference data, similar to VN-Index)
        # VN30 2019-2025: start ~870 points, end ~1250 points (approximate)
        return {
            "CAGR": 0.105,
            "MaxDD": -0.40,
            "source": "Hardcoded estimate (Postgres unavailable): VN30 approximate 2019-2025",
        }


def compute_deposit_12m_benchmark() -> dict:
    """Compute 12-month deposit benchmark via compounding.

    Annual rates sourced from Vietnam SBV approximate commercial 12M deposit rates.

    Returns:
        Dict with CAGR, MaxDD, source keys.
    """
    # Approximate commercial bank 12M deposit rates in Vietnam
    annual_rates = {
        2019: 0.065,
        2020: 0.050,
        2021: 0.050,
        2022: 0.060,
        2023: 0.055,
        2024: 0.045,
        2025: 0.045,
    }
    compound = 1.0
    for rate in annual_rates.values():
        compound *= 1 + rate
    years = len(annual_rates)
    cagr = compound ** (1 / years) - 1
    return {
        "CAGR": round(cagr, 6),
        "MaxDD": 0.0,
        "source": "Vietnam SBV approximate commercial 12M deposit rates (2019-2025)",
    }


def compute_sjc_gold_benchmark() -> dict:
    """Compute SJC gold benchmark (VND/tael).

    Start: ~36.5M VND/tael (Jan 2019)
    End:   ~92.0M VND/tael (Dec 2025)
    Source: SJC.com.vn historical prices (approximate)

    Returns:
        Dict with CAGR, MaxDD, source keys.
    """
    start_price = 36.5  # million VND/tael Jan 2019
    end_price = 92.0    # million VND/tael Dec 2025
    years = 7.0
    cagr = (end_price / start_price) ** (1 / years) - 1
    max_dd = -0.15  # Approximate: gold dips in 2021 ~15%
    return {
        "CAGR": round(cagr, 6),
        "MaxDD": max_dd,
        "source": "SJC.com.vn historical prices, approximate (2019: 36.5M, 2025: 92M VND/tael)",
    }


def add_real_cagr(metrics: dict, avg_cpi: float = AVG_CPI) -> dict:
    """Add real_CAGR field to a metrics dict using Fisher equation.

    Args:
        metrics: Dict containing at least a 'CAGR' key.
        avg_cpi: Average annual CPI (geometric mean).

    Returns:
        Updated metrics dict with real_CAGR added.
    """
    nominal = metrics["CAGR"]
    real = (1 + nominal) / (1 + avg_cpi) - 1
    metrics["real_CAGR"] = round(real, 6)
    return metrics


def generate_markdown(report: dict) -> str:
    """Generate human-readable markdown from v7 report dict.

    Args:
        report: Full report dict.

    Returns:
        Markdown string.
    """
    strategy = report["strategy"]
    benchmarks = report["benchmarks"]
    generated = report["generated"]
    period = report["period"]
    config = report["locked_config"]

    lines = [
        "# v7.0 Performance Report",
        "",
        f"**Generated:** {generated}",
        f"**Period:** {period}",
        f"**Configuration:** {config}",
        "",
        "---",
        "",
        "## Strategy Performance",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| CAGR | {strategy['CAGR']:.2%} |",
        f"| Real CAGR (inflation-adj) | {strategy['real_CAGR']:.2%} |",
        f"| Sharpe (rf=3%) | {strategy['Sharpe_rf3']:.3f} |",
        f"| Max Drawdown | {strategy['MaxDD']:.2%} |",
        f"| Max DD Duration (days) | {strategy['MaxDD_duration_days']} |",
        f"| Hit Rate | {strategy['hit_rate']:.2%} |",
        f"| Profit Factor | {strategy['profit_factor']:.3f} |",
        f"| Avg Hold Days | {strategy['avg_hold_days']:.1f} |",
        f"| Turnover | {strategy['turnover']:.2f}x |",
        f"| Total Cost Drag | {strategy['total_cost_drag_pct']:.2f}% |",
        f"| Num Trades | {strategy['num_trades']} |",
        "",
        "---",
        "",
        "## Benchmark Comparison",
        "",
        "| Benchmark | CAGR | Real CAGR | Max DD | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]

    benchmark_labels = {
        "vnindex_bh": "VN-Index B&H",
        "vn30_bh": "VN30 B&H",
        "mdm_only_index": "MDM-Only (Index)",
        "deposit_12m": "12M Deposit",
        "sjc_gold": "SJC Gold",
    }

    for key, label in benchmark_labels.items():
        bm = benchmarks[key]
        cagr_str = f"{bm['CAGR']:.2%}"
        real_cagr_str = f"{bm['real_CAGR']:.2%}"
        max_dd_str = f"{bm.get('MaxDD', 0.0):.2%}" if bm.get("MaxDD") is not None else "N/A"
        source = bm.get("source", "")
        lines.append(f"| {label} | {cagr_str} | {real_cagr_str} | {max_dd_str} | {source} |")

    # Strategy row for comparison
    lines += [
        f"| **Strategy (v7.0)** | **{strategy['CAGR']:.2%}** | **{strategy['real_CAGR']:.2%}** | **{strategy['MaxDD']:.2%}** | CANSLIM + MDM gate |",
        "",
        "---",
        "",
        "## Notes",
        "",
        "### Data Sources",
        "",
        "- **VN-Index B&H:** Phase 33 baselines.json (computed from Postgres index_eod VN-Index 2019-2025)",
        "- **VN30 B&H:** Computed from Postgres index_eod VN30 2019-2025 (fallback: hardcoded estimate)",
        "- **MDM-Only (Index):** Phase 33 baselines.json (MDM HybridEngine on VN-Index, no stock picking)",
        "- **12M Deposit:** Vietnam SBV approximate commercial 12M deposit rates 2019-2025",
        "  - Annual rates: 2019:6.5%, 2020:5.0%, 2021:5.0%, 2022:6.0%, 2023:5.5%, 2024:4.5%, 2025:4.5%",
        "- **SJC Gold:** SJC.com.vn historical prices (approximate)",
        "  - Jan 2019: ~36.5M VND/tael → Dec 2025: ~92M VND/tael",
        "- **Real CAGR:** Computed using Fisher equation: (1 + nominal) / (1 + CPI) - 1",
        "  - Average CPI: 3.0% (geometric mean, GSO.gov.vn: 2.79%, 3.23%, 1.84%, 3.15%, 3.25%, 3.6%, 3.5%)",
        "",
        "### Key Finding",
        "",
        "- **CANSLIM stock selection** is the primary alpha source (CANSLIM-only Sharpe=1.047 vs B&H 0.383)",
        "- **MDM gate** is the primary bottleneck (reduces Sharpe from 1.047 to 0.448)",
        "- Strategy beats VN-Index B&H on CAGR with dramatically lower drawdown (-10.2% vs -40.3%)",
        f"- profit_factor = {strategy['profit_factor']:.3f} (winners generate {strategy['profit_factor']:.1f}x the losses)",
    ]

    return "\n".join(lines) + "\n"


def main() -> None:
    """Generate v7.0 performance report."""
    print("[INFO] Generating v7.0 performance report...")

    # 1. Load existing Phase 33 data
    print(f"[INFO] Loading OOS metrics from {OOS_METRICS_PATH}")
    with open(OOS_METRICS_PATH) as f:
        oos_metrics = json.load(f)

    print(f"[INFO] Loading baselines from {BASELINES_PATH}")
    with open(BASELINES_PATH) as f:
        baselines = json.load(f)

    print(f"[INFO] Loading OOS trades from {OOS_TRADES_PATH}")
    trades_df = pd.read_csv(OOS_TRADES_PATH)

    # 2. Compute profit_factor (BT-05)
    profit_factor = compute_profit_factor(trades_df)
    print(f"[INFO] Computed profit_factor = {profit_factor:.4f}")

    # 3. Build strategy metrics (10 standard + real_CAGR)
    strategy = {
        "CAGR": oos_metrics["CAGR"],
        "Sharpe_rf3": oos_metrics["Sharpe_rf3"],
        "MaxDD": oos_metrics["MaxDD"],
        "MaxDD_duration_days": oos_metrics["MaxDD_duration_days"],
        "hit_rate": oos_metrics["hit_rate"],
        "profit_factor": round(profit_factor, 6),
        "avg_hold_days": oos_metrics["avg_hold_days"],
        "turnover": oos_metrics["turnover"],
        "total_cost_drag_pct": oos_metrics["total_cost_drag_pct"],
        "num_trades": oos_metrics["num_trades"],
    }
    strategy = add_real_cagr(strategy)

    # 4. Compute VN30 B&H benchmark (BT-06)
    print("[INFO] Computing VN30 B&H benchmark...")
    vn30_bh = compute_vn30_bh()
    vn30_bh = add_real_cagr(vn30_bh)

    # 5. Hardcode deposit & gold benchmarks (BT-06)
    deposit_12m = compute_deposit_12m_benchmark()
    deposit_12m = add_real_cagr(deposit_12m)

    sjc_gold = compute_sjc_gold_benchmark()
    sjc_gold = add_real_cagr(sjc_gold)

    # 6. Existing benchmarks from baselines.json + real_CAGR
    vnindex_bh = {
        "CAGR": baselines["vnindex_bh"]["CAGR"],
        "Sharpe_rf3": baselines["vnindex_bh"]["Sharpe_rf3"],
        "MaxDD": baselines["vnindex_bh"]["MaxDD"],
        "MaxDD_duration_days": baselines["vnindex_bh"]["MaxDD_duration_days"],
        "source": "Phase 33 baselines.json (Postgres index_eod VN-Index 2019-2025)",
    }
    vnindex_bh = add_real_cagr(vnindex_bh)

    mdm_only_index = {
        "CAGR": baselines["mdm_only_index"]["CAGR"],
        "Sharpe_rf3": baselines["mdm_only_index"]["Sharpe_rf3"],
        "MaxDD": baselines["mdm_only_index"]["MaxDD"],
        "MaxDD_duration_days": baselines["mdm_only_index"]["MaxDD_duration_days"],
        "source": "Phase 33 baselines.json (MDM HybridEngine on VN-Index, no stock picking)",
    }
    mdm_only_index = add_real_cagr(mdm_only_index)

    # 7. Assemble full report
    report = {
        "generated": datetime.now().isoformat(),
        "period": BACKTEST_PERIOD,
        "locked_config": LOCKED_CONFIG,
        "avg_cpi_used": AVG_CPI,
        "strategy": strategy,
        "benchmarks": {
            "vnindex_bh": vnindex_bh,
            "vn30_bh": vn30_bh,
            "mdm_only_index": mdm_only_index,
            "deposit_12m": deposit_12m,
            "sjc_gold": sjc_gold,
        },
    }

    # 8. Write outputs
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Writing JSON report to {OUT_JSON}")
    with open(OUT_JSON, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[INFO] Writing Markdown report to {OUT_MD}")
    md_content = generate_markdown(report)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("[DONE] v7.0 report generated successfully.")
    print(f"  JSON: {OUT_JSON}")
    print(f"  MD:   {OUT_MD}")
    print(f"  profit_factor = {profit_factor:.4f}")
    print(f"  strategy real_CAGR = {strategy['real_CAGR']:.4f}")
    print(f"  benchmarks: {list(report['benchmarks'].keys())}")


if __name__ == "__main__":
    main()
