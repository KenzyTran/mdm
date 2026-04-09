"""Baseline comparison: CanslimScorer vs stocks_backend.canslim (CANS-12).

Iterates all quarters in the ``canslim`` baseline table where VN100 coverage
is meaningful (>= ``--min-tickers`` rows), and for each quarter:

  1. Maps the quarter label to the last trading day in Postgres stock_eod.
  2. Runs :class:`CanslimScorer` for that as_of_date and restricts to VN100.
  3. Loads the baseline ``canslim`` frame for that quarter, also VN100-only.
  4. Computes three agreement metrics:
     a. **Top-10 overlap:** |our_top10 ∩ baseline_top10| (0..10).
     b. **Composite Spearman ρ:** rank correlation between our ``score`` and
        baseline ``tong_diem`` over tickers present in both frames.
     c. **Per-component agreement rates:** for each of our boolean rules, map
        to a baseline percentile column (threshold :data:`BASELINE_PCTL_GATE`,
        default 70) and compute agreement = (both True + both False) / total.

Emits:
  - ``--output`` Markdown report (per-quarter tables + aggregate summary)
  - PASS / FAIL verdict based on: Spearman ρ ≥ 0.5 on ≥ 70% of quarters.

Usage:
    uv run python scripts/canslim_baseline_compare.py \
        --start 2023 --min-tickers 50 \
        --output docs/audits/phase29/baseline_comparison.md

**Honesty clause:** If the acceptance gate fails, the script still writes the
full report with raw per-quarter numbers so the user can inspect WHY.  We do
NOT fudge thresholds to force a PASS.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

# Allow running as a script from project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from connectors import mysql, postgres  # noqa: E402
from strategies.canslim.baseline import (  # noqa: E402
    available_baseline_quarters,
    load_baseline_quarter,
    quarter_to_last_trading_day,
    _quarter_sort_key,
)
from strategies.canslim.config import CanslimConfig  # noqa: E402
from strategies.canslim.scorer import CanslimScorer  # noqa: E402
from strategies.canslim.sectors import SectorRouter  # noqa: E402
from strategies.canslim.universe import UniverseLoader  # noqa: E402

# Threshold used to map a baseline percentile column to a boolean "top decile"
# gate. 70 = "top 30% of the screening universe" — documented as a judgment
# call in docs/audits/phase29-canslim-validation.md.
BASELINE_PCTL_GATE = 70.0

# Mapping from our scorer boolean columns to baseline percentile columns.
# Each entry: our_col -> (baseline_col, description).
# Notes:
#   * c_pass (quarterly EPS YoY >= 20%) <-> eps_quy_gan_nhat (quarterly EPS pctl)
#   * c_plus_pass (EPS accel) — no direct analog; we reuse eps_quy_gan_nhat
#     as a loose proxy (documented caveat).
#   * a_pass (3y TTM CAGR) <-> eps_trailing_12_thang (TTM EPS pctl)
#   * a_plus_pass (positive TTM) — no clean analog; dropped from agreement
#     analysis.
#   * s_pass (supply/turnover tech) <-> sale_quy_gan_nhat as a weak proxy
#     (baseline has no direct supply metric). We report this but flag it.
#   * roe has no scorer boolean — we compute its "baseline-implied" pass-rate
#     for reference only.
BOOLEAN_RULE_MAP: Dict[str, Tuple[str, str]] = {
    "c_pass": ("eps_quy_gan_nhat", "quarterly EPS YoY >= threshold"),
    "a_pass": ("eps_trailing_12_thang", "3y TTM EPS growth"),
    # s_pass is weakly analogous; baseline measures sales not supply:
    # we include it to expose the divergence honestly.
    "s_pass": ("sale_quy_gan_nhat", "sales momentum (loose proxy for S)"),
}


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


def top_overlap(our_top: Sequence[str], baseline_top: Sequence[str]) -> int:
    return len(set(our_top) & set(baseline_top))


def spearman_rho(our: pd.Series, base: pd.Series) -> float:
    """Spearman rank correlation on the intersection of their indices.

    Implemented without scipy: rank both, then Pearson on ranks.
    """
    common = our.index.intersection(base.index)
    if len(common) < 3:
        return float("nan")
    a = our.loc[common].rank()
    b = base.loc[common].rank()
    if a.std(ddof=0) == 0 or b.std(ddof=0) == 0:
        return float("nan")
    return float(np.corrcoef(a.values, b.values)[0, 1])


def component_agreement(
    ours: pd.DataFrame,
    base: pd.DataFrame,
    our_col: str,
    base_col: str,
    gate: float = BASELINE_PCTL_GATE,
) -> Tuple[int, int, int, int]:
    """Return (n_total, both_pass, both_fail, disagree) for one rule mapping.

    ``ours`` indexed by ticker with a bool column ``our_col``.
    ``base`` indexed by ticker with a numeric percentile column ``base_col``.
    Baseline pass := ``base_col >= gate``.
    """
    common = ours.index.intersection(base.index)
    if len(common) == 0:
        return (0, 0, 0, 0)
    a = ours.loc[common, our_col].astype(bool)
    b = base.loc[common, base_col] >= gate
    both_pass = int(((a) & (b)).sum())
    both_fail = int(((~a) & (~b)).sum())
    disagree = int(len(common) - both_pass - both_fail)
    return (int(len(common)), both_pass, both_fail, disagree)


# --------------------------------------------------------------------------- #
# Per-quarter runner
# --------------------------------------------------------------------------- #


def compare_quarter(
    quarter: str,
    scorer: CanslimScorer,
    mysql_engine,
    pg_engine,
    vn100: List[str],
) -> Dict:
    """Run the full comparison for a single quarter; return a result dict."""
    try:
        as_of = quarter_to_last_trading_day(pg_engine, quarter)
    except RuntimeError as e:
        return {"quarter": quarter, "error": str(e)}

    base = load_baseline_quarter(mysql_engine, quarter, vn100)
    if base.empty:
        return {"quarter": quarter, "as_of": as_of, "error": "empty baseline"}
    base = base.set_index("mack")

    try:
        ours = scorer.score(as_of)
    except Exception as e:  # noqa: BLE001 — want to surface any scorer error
        return {"quarter": quarter, "as_of": as_of, "error": f"scorer: {e!r}"}
    if ours.empty:
        return {"quarter": quarter, "as_of": as_of, "error": "empty scorer"}
    ours = ours.copy()
    ours["ticker"] = ours["ticker"].str.upper()
    # Restrict to VN100 (scorer already restricts via universe_loader, but
    # this is belt-and-braces in case of mode drift).
    ours = ours[ours["ticker"].isin(vn100)].set_index("ticker")

    # Top-10 sets
    our_top10 = ours.sort_values("score", ascending=False).head(10).index.tolist()
    base_top10 = base.sort_values("tong_diem", ascending=False).head(10).index.tolist()
    overlap = top_overlap(our_top10, base_top10)

    # Composite rank correlation
    rho = spearman_rho(ours["score"], base["tong_diem"])

    # Per-component agreements
    components = {}
    for our_col, (base_col, _desc) in BOOLEAN_RULE_MAP.items():
        n, bp, bf, dg = component_agreement(ours, base, our_col, base_col)
        agree_rate = (bp + bf) / n if n else float("nan")
        components[our_col] = {
            "n": n,
            "both_pass": bp,
            "both_fail": bf,
            "disagree": dg,
            "agree_rate": agree_rate,
            "base_col": base_col,
        }

    return {
        "quarter": quarter,
        "as_of": as_of,
        "n_ours": int(len(ours)),
        "n_base": int(len(base)),
        "n_common": int(len(ours.index.intersection(base.index))),
        "our_top10": our_top10,
        "base_top10": base_top10,
        "overlap": overlap,
        "spearman": rho,
        "components": components,
    }


# --------------------------------------------------------------------------- #
# Report writer
# --------------------------------------------------------------------------- #


def write_report(
    results: List[Dict],
    out_path: Path,
    acceptance_rho: float,
    acceptance_pct_quarters: float,
) -> Tuple[bool, Dict]:
    """Write the Markdown report and return (passed, summary_dict)."""
    good = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]

    if good:
        rhos = [r["spearman"] for r in good if not np.isnan(r["spearman"])]
        n_quarters = len(good)
        n_pass_rho = sum(1 for r in good if not np.isnan(r["spearman"]) and r["spearman"] >= acceptance_rho)
        pct_pass = n_pass_rho / n_quarters if n_quarters else 0.0
        median_rho = float(np.median(rhos)) if rhos else float("nan")
        mean_overlap = float(np.mean([r["overlap"] for r in good]))
    else:
        n_quarters = 0
        n_pass_rho = 0
        pct_pass = 0.0
        median_rho = float("nan")
        mean_overlap = float("nan")

    passed = pct_pass >= acceptance_pct_quarters and not np.isnan(median_rho)

    lines: List[str] = []
    lines.append("# Phase 29 Baseline Comparison — `canslim` table\n")
    lines.append(
        "Compares `CanslimScorer` output against the upstream MySQL "
        "`stocks_backend.canslim` table (composite `tong_diem` + component "
        "percentiles), VN100-restricted.\n"
    )
    lines.append("## Methodology\n")
    lines.append(
        "- For each quarter in `canslim` with ≥ `min-tickers` VN100 rows:\n"
        "  - Map quarter label → last trading day in `stock_eod`.\n"
        "  - Run `CanslimScorer.score(last_trading_day)`, restrict to VN100.\n"
        "  - Load baseline `canslim` frame for that quarter, restrict to VN100.\n"
        "- **Top-10 overlap:** count intersection of top-10 by composite score.\n"
        "- **Spearman ρ:** rank correlation between our `score` and baseline "
        "`tong_diem` on ticker intersection.\n"
        "- **Per-component agreement:** map our booleans to baseline percentile "
        f"columns with gate ≥ {BASELINE_PCTL_GATE:.0f}; report "
        "(both_pass + both_fail) / total.\n"
    )
    lines.append(
        f"**Acceptance gate:** Spearman ρ ≥ {acceptance_rho} on ≥ "
        f"{acceptance_pct_quarters:.0%} of quarters.\n"
    )
    lines.append(
        "**Quarterly-vs-daily caveat:** baseline is QUARTERLY; scorer is daily. "
        "We use the last trading day of the quarter as the `as_of_date` proxy "
        "so any intra-quarter drift in daily features (N, S, RS, I, Liq) is "
        "visible to the scorer but not to the baseline. Some divergence is "
        "EXPECTED here — especially on the technical rules.\n"
    )

    lines.append("## Verdict\n")
    lines.append(f"- Quarters compared: **{n_quarters}**")
    lines.append(f"- Errors: {len(errors)}")
    lines.append(f"- Median Spearman ρ: **{median_rho:.3f}**")
    lines.append(
        f"- Quarters with ρ ≥ {acceptance_rho}: **{n_pass_rho}/{n_quarters} "
        f"({pct_pass:.0%})**"
    )
    lines.append(f"- Mean top-10 overlap: {mean_overlap:.2f} / 10")
    lines.append(f"- **Result: {'PASS' if passed else 'FAIL'}**\n")

    # Per-quarter table
    lines.append("## Per-quarter metrics\n")
    lines.append(
        "| quarter | as_of | n_ours | n_base | n_common | top10_overlap | "
        "spearman | c_agree | a_agree | s_agree |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in good:
        comp = r["components"]
        def _fmt(col):
            ar = comp[col]["agree_rate"]
            return f"{ar:.0%}" if not np.isnan(ar) else "n/a"
        lines.append(
            f"| {r['quarter']} | {r['as_of']} | {r['n_ours']} | {r['n_base']} "
            f"| {r['n_common']} | {r['overlap']}/10 | {r['spearman']:.3f} "
            f"| {_fmt('c_pass')} | {_fmt('a_pass')} | {_fmt('s_pass')} |"
        )
    lines.append("")

    # Per-quarter top-10 detail
    lines.append("## Per-quarter top-10 lists\n")
    for r in good:
        lines.append(
            f"### {r['quarter']} ({r['as_of']}) — overlap {r['overlap']}/10, ρ={r['spearman']:.3f}"
        )
        lines.append(f"- ours: `{', '.join(r['our_top10'])}`")
        lines.append(f"- base: `{', '.join(r['base_top10'])}`")
        overlap_set = sorted(set(r["our_top10"]) & set(r["base_top10"]))
        lines.append(f"- overlap: `{', '.join(overlap_set) if overlap_set else '(none)'}`")
        lines.append("")

    # Per-component aggregate
    lines.append("## Per-component aggregate agreement\n")
    lines.append("| our_rule | baseline_col | mean_agree_rate | n_quarters |")
    lines.append("|---|---|---|---|")
    for our_col, (base_col, _desc) in BOOLEAN_RULE_MAP.items():
        rates = [
            r["components"][our_col]["agree_rate"]
            for r in good
            if not np.isnan(r["components"][our_col]["agree_rate"])
        ]
        mean_rate = float(np.mean(rates)) if rates else float("nan")
        lines.append(
            f"| {our_col} | {base_col} | "
            f"{mean_rate:.0%} | {len(rates)} |"
        )
    lines.append("")

    # Errors
    if errors:
        lines.append("## Errors\n")
        for r in errors:
            lines.append(f"- {r['quarter']}: {r.get('error')}")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "n_quarters": n_quarters,
        "median_rho": median_rho,
        "n_pass_rho": n_pass_rho,
        "pct_pass": pct_pass,
        "mean_overlap": mean_overlap,
        "passed": passed,
    }
    return passed, summary


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=int, default=2019, help="Min year (default 2019)")
    ap.add_argument("--min-tickers", type=int, default=50)
    ap.add_argument("--acceptance-rho", type=float, default=0.5)
    ap.add_argument("--acceptance-pct", type=float, default=0.70)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("docs/audits/phase29/baseline_comparison.md"),
    )
    ap.add_argument(
        "--sector-column",
        type=str,
        default="nhom",
        help="stock_list sector column name (per schema_lock)",
    )
    ap.add_argument("--limit-quarters", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    pg = postgres.get_engine()
    mx = mysql.get_engine()

    # VN100 ticker universe (snapshot — matches scorer's current-vn100 mode).
    vn100 = (
        pd.read_sql(
            "SELECT stockcode FROM stock_list WHERE nhomtop IN ('VN30','VN100')",
            pg,
        )["stockcode"]
        .str.upper()
        .tolist()
    )
    print(f"[info] VN100 size: {len(vn100)}")

    # Eligible quarters: all in canslim >= args.start year with enough VN100 rows.
    all_quarters = available_baseline_quarters(mx)
    coverage = pd.read_sql(
        "SELECT thoigian, COUNT(*) AS n FROM canslim "
        "WHERE mack IN %(t)s GROUP BY thoigian",
        mx,
        params={"t": tuple(vn100)},
    )
    cov_map = dict(zip(coverage["thoigian"], coverage["n"]))
    quarters = [
        q for q in all_quarters
        if _quarter_sort_key(q)[0] >= args.start
        and cov_map.get(q, 0) >= args.min_tickers
    ]
    if args.limit_quarters:
        quarters = quarters[: args.limit_quarters]
    print(f"[info] Eligible quarters: {len(quarters)} (start={args.start})")

    # Build scorer
    router = SectorRouter.from_postgres(pg, args.sector_column)
    universe_loader = UniverseLoader(mode="current-vn100", pg_engine=pg)
    scorer = CanslimScorer(
        config=CanslimConfig(),
        universe_loader=universe_loader,
        sector_router=router,
        pg_engine=pg,
        mysql_engine=mx,
    )

    results: List[Dict] = []
    for i, q in enumerate(quarters, 1):
        print(f"[run] {i}/{len(quarters)} {q} ...", flush=True)
        r = compare_quarter(q, scorer, mx, pg, vn100)
        if "error" in r:
            print(f"       ERROR: {r['error']}")
        else:
            print(
                f"       overlap={r['overlap']}/10 rho={r['spearman']:.3f} "
                f"n_common={r['n_common']}"
            )
        results.append(r)

    passed, summary = write_report(
        results,
        args.output,
        acceptance_rho=args.acceptance_rho,
        acceptance_pct_quarters=args.acceptance_pct,
    )
    print()
    print(f"[summary] {summary}")
    print(f"[summary] Report: {args.output}")
    print(f"[summary] Verdict: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
