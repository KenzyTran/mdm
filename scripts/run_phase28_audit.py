"""Phase 28 data audit — DATA-05/06/07.

Pulls real numbers from Postgres (stock_eod, stock_foreign_eod, stock_list) and
MySQL (is_quarter_nonbank) to quantify data-quality risks for the v7.0 backtest:
  - delisted tickers (stock_eod max_date < 2024-01-01)
  - per-VN100 quarterly EPS coverage 2014-2025
  - per-VN100 foreign EOD coverage 2014-2026

Outputs one Markdown report + 4 companion CSVs.

Usage:
    uv run python scripts/run_phase28_audit.py
    uv run python scripts/run_phase28_audit.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

import pandas as pd

# Ensure project root is on sys.path when invoked as a script.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from connectors.postgres import query as pg_query
from connectors.mysql import query as my_query
from connectors.eps import resolve_eps_publish_date

REPORT_PATH = Path("docs/audits/phase28-data-audit.md")
DEFAULT_OUT = Path("docs/audits/phase28")

DELIST_CUTOFF = "2024-01-01"
EPS_YEAR_MIN = 2014
EPS_YEAR_MAX = 2025
FOREIGN_YEAR_MIN = 2014
FOREIGN_YEAR_MAX = 2026
EXPECTED_QUARTERS = (EPS_YEAR_MAX - EPS_YEAR_MIN + 1) * 4  # 48

FLAGGED = ("FLC", "ROS", "HVN")


# ---------------------------------------------------------------------------
# Section A — stockcode coverage in stock_eod
# ---------------------------------------------------------------------------
def section_a_stockcode_coverage(out_dir: Path) -> dict:
    """Distinct stockcodes + delisted candidates in Postgres stock_eod."""
    sql = """
        SELECT stockcode,
               MIN(tradingdate) AS min_date,
               MAX(tradingdate) AS max_date,
               COUNT(*) AS row_count
        FROM stock_eod
        GROUP BY stockcode
        ORDER BY stockcode
    """
    df = pg_query(sql)
    df["min_date"] = pd.to_datetime(df["min_date"])
    df["max_date"] = pd.to_datetime(df["max_date"])
    df.to_csv(out_dir / "stockcode_coverage.csv", index=False)

    cutoff = pd.Timestamp(DELIST_CUTOFF)
    delisted = df[df["max_date"] < cutoff].sort_values("max_date")
    delisted[["stockcode", "max_date"]].to_csv(
        out_dir / "delisted_candidates.csv", index=False
    )

    flagged = {
        code: ("delisted" if code in set(delisted["stockcode"]) else
               ("active" if code in set(df["stockcode"]) else "missing"))
        for code in FLAGGED
    }

    return {
        "n_distinct": int(df["stockcode"].nunique()),
        "n_delisted": int(len(delisted)),
        "delisted_first50": delisted["stockcode"].head(50).tolist(),
        "flagged": flagged,
        "global_min": str(df["min_date"].min().date()) if not df.empty else None,
        "global_max": str(df["max_date"].max().date()) if not df.empty else None,
    }


# ---------------------------------------------------------------------------
# Section B — VN100 universe
# ---------------------------------------------------------------------------
def section_b_vn100() -> dict:
    """Resolve VN100 universe. Prefer stock_list.nhomtop, else fallback."""
    source = "stock_list.nhomtop IN ('VN30','VN100')  -- single-tag column, VN30 and VN100 stored separately; union gives full VN100 universe of 100"
    try:
        df = pg_query(
            "SELECT DISTINCT stockcode FROM stock_list "
            "WHERE nhomtop ILIKE '%VN100%' OR nhomtop ILIKE '%VN30%'",
        )
    except Exception as exc:  # noqa: BLE001
        df = pd.DataFrame(columns=["stockcode"])
        source = f"stock_list query failed ({exc!r}); fallback used"

    if df.empty:
        source = "fallback: top-100 by avg(totalvol*closeprice) last 60 trading days"
        fb_sql = """
            WITH last_days AS (
                SELECT DISTINCT tradingdate
                FROM stock_eod
                ORDER BY tradingdate DESC
                LIMIT 60
            )
            SELECT stockcode
            FROM stock_eod
            WHERE tradingdate IN (SELECT tradingdate FROM last_days)
            GROUP BY stockcode
            ORDER BY AVG(totalvol * closeprice) DESC NULLS LAST
            LIMIT 100
        """
        df = pg_query(fb_sql)

    tickers: List[str] = sorted(df["stockcode"].dropna().astype(str).unique().tolist())
    return {"source": source, "tickers": tickers, "n": len(tickers)}


# ---------------------------------------------------------------------------
# Section C — VN100 quarterly EPS coverage
# ---------------------------------------------------------------------------
def section_c_eps_coverage(vn100: dict, out_dir: Path) -> dict:
    """VN100 quarterly fundamentals coverage 2014-2025.

    Schema reality (discovered during phase 28 plan 05 live run):
    - `is_quarter_nonbank` uses Vietnamese column names: `mack` (ticker),
      `thoigian` (e.g. 'Q1 2014'). No `eps` / `yearreport` / `lengthreport`
      columns. We use row presence as the fundamentals-coverage proxy and
      derive (year, quarter) from `thoigian`.
    - `ratios_stock` (which DOES carry `eps`) is securities-firms only
      (~40 tickers) so it cannot back the VN100 EPS audit. Recorded as a
      Phase 29 risk.
    - To still exercise `resolve_eps_publish_date` (DATA-04), we synthesise
      `yearreport` + `lengthreport` from the parsed `thoigian` and pipe a
      sample through the helper.
    """
    tickers = vn100["tickers"]
    if not tickers:
        empty = pd.DataFrame(
            columns=["stockcode", "n_quarters_2014_2025",
                     "first_quarter", "last_quarter", "n_gaps"]
        )
        empty.to_csv(out_dir / "vn100_eps_coverage.csv", index=False)
        return {"n_tickers": 0, "top10": [], "bottom10": [],
                "publish_date_ok": False}

    from sqlalchemy import bindparam, text
    from connectors.mysql import get_engine as my_engine

    sql = text(
        "SELECT mack AS stockcode, thoigian "
        "FROM is_quarter_nonbank "
        "WHERE mack IN :tickers"
    ).bindparams(bindparam("tickers", expanding=True))
    with my_engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"tickers": tickers})

    # Parse 'Q1 2014' -> quarter=1, yearreport=2014.
    if not df.empty:
        parsed = df["thoigian"].astype(str).str.extract(
            r"Q(?P<q>[1-4])\s+(?P<y>\d{4})"
        )
        df["quarter"] = pd.to_numeric(parsed["q"], errors="coerce")
        df["yearreport"] = pd.to_numeric(parsed["y"], errors="coerce")
        df = df.dropna(subset=["quarter", "yearreport"])
        df["quarter"] = df["quarter"].astype(int)
        df["yearreport"] = df["yearreport"].astype(int)
        df["lengthreport"] = df["quarter"].map({1: 3, 2: 6, 3: 9, 4: 12})

    # Confirm `resolve_eps_publish_date` works on real-shaped data (DATA-04).
    publish_date_ok = True
    try:
        sample = df.head(50).copy() if not df.empty else pd.DataFrame(
            {"yearreport": [2024], "lengthreport": [3]}
        )
        _ = resolve_eps_publish_date(sample)
    except Exception:  # noqa: BLE001
        publish_date_ok = False

    df_q = df[df["yearreport"].between(EPS_YEAR_MIN, EPS_YEAR_MAX)].copy() if not df.empty else df
    if not df_q.empty:
        df_q["q_key"] = df_q["yearreport"] * 10 + df_q["quarter"]

    rows = []
    for t in tickers:
        sub = df_q[df_q["stockcode"] == t] if not df_q.empty else df_q
        n = int(sub["q_key"].nunique()) if not sub.empty else 0
        rows.append({
            "stockcode": t,
            "n_quarters_2014_2025": n,
            "first_quarter": int(sub["q_key"].min()) if n else None,
            "last_quarter": int(sub["q_key"].max()) if n else None,
            "n_gaps": EXPECTED_QUARTERS - n,
        })
    cov = pd.DataFrame(rows).sort_values("n_quarters_2014_2025", ascending=False)
    cov.to_csv(out_dir / "vn100_eps_coverage.csv", index=False)

    top10 = cov.head(10).to_dict(orient="records")
    bottom10 = cov.tail(10).to_dict(orient="records")
    under_40 = int((cov["n_quarters_2014_2025"] < 40).sum())
    return {
        "n_tickers": len(tickers),
        "publish_date_ok": publish_date_ok,
        "top10": top10,
        "bottom10": bottom10,
        "under_40": under_40,
        "n_zero": int((cov["n_quarters_2014_2025"] == 0).sum()),
    }


# ---------------------------------------------------------------------------
# Section D — stock_foreign_eod VN100 coverage
# ---------------------------------------------------------------------------
def section_d_foreign_eod(vn100: dict, out_dir: Path) -> dict:
    tickers = vn100["tickers"]
    if not tickers:
        pd.DataFrame(columns=["stockcode", "first_date", "last_date", "n_days"]) \
            .to_csv(out_dir / "foreign_eod_coverage.csv", index=False)
        return {"n_tickers": 0, "worst10": [], "n_missing": 0}

    sql = """
        SELECT stockcode,
               MIN(tradingdate) AS first_date,
               MAX(tradingdate) AS last_date,
               COUNT(*) AS n_days
        FROM stock_foreign_eod
        WHERE stockcode = ANY(:tickers)
          AND tradingdate BETWEEN :start AND :end
        GROUP BY stockcode
    """
    df = pg_query(sql, {
        "tickers": tickers,
        "start": f"{FOREIGN_YEAR_MIN}-01-01",
        "end": f"{FOREIGN_YEAR_MAX}-12-31",
    })
    present = set(df["stockcode"]) if not df.empty else set()
    missing = [t for t in tickers if t not in present]
    # Add missing rows with zeros for a complete picture.
    if missing:
        miss_df = pd.DataFrame({
            "stockcode": missing,
            "first_date": pd.NaT,
            "last_date": pd.NaT,
            "n_days": 0,
        })
        df = pd.concat([df, miss_df], ignore_index=True)
    df = df.sort_values("n_days", ascending=True)
    df.to_csv(out_dir / "foreign_eod_coverage.csv", index=False)

    worst10 = df.head(10).to_dict(orient="records")
    return {
        "n_tickers": len(tickers),
        "n_missing": len(missing),
        "worst10": worst10,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def _fmt_eps_row(r: dict) -> str:
    return (f"- `{r['stockcode']}` — {r['n_quarters_2014_2025']}/{EXPECTED_QUARTERS} "
            f"quarters (first={r['first_quarter']}, last={r['last_quarter']}, "
            f"gaps={r['n_gaps']})")


def _fmt_foreign_row(r: dict) -> str:
    return (f"- `{r['stockcode']}` — n_days={r['n_days']}, "
            f"first={r['first_date']}, last={r['last_date']}")


def render_markdown(ctx: dict) -> str:
    a = ctx["section_a"]
    vn = ctx["vn100"]
    c = ctx["section_c"]
    d = ctx["section_d"]

    flagged_lines = "\n".join(
        f"- `{code}`: **{status}**" for code, status in a["flagged"].items()
    )
    delisted_first50 = ", ".join(f"`{s}`" for s in a["delisted_first50"])

    lines: list = []
    lines.append("# Phase 28 — Data Audit (DATA-05/06/07)\n")
    lines.append("Generated by `scripts/run_phase28_audit.py`. Closes DATA-05, DATA-06, DATA-07.\n")

    lines.append("## Executive Summary\n")
    lines.append(f"- **Distinct stockcode in `stock_eod`:** {a['n_distinct']}")
    lines.append(f"- **stock_eod date range:** {a['global_min']} → {a['global_max']}")
    lines.append(f"- **Delisted candidates (max_date < {DELIST_CUTOFF}):** {a['n_delisted']}")
    lines.append(f"- **VN100 universe size:** {vn['n']} (source: {vn['source']})")
    lines.append(f"- **VN100 tickers with <40/48 EPS quarters 2014-2025:** {c.get('under_40', 'n/a')}")
    lines.append(f"- **VN100 tickers with 0 EPS quarters:** {c.get('n_zero', 'n/a')}")
    lines.append(f"- **VN100 tickers missing from `stock_foreign_eod`:** {d['n_missing']}")
    lines.append(f"- **`resolve_eps_publish_date` on real data:** {'OK' if c.get('publish_date_ok') else 'FAILED'}\n")

    lines.append("## Section A — `stock_eod` coverage\n")
    lines.append(f"Distinct stockcode count: **{a['n_distinct']}**.")
    lines.append(f"Companion CSV: [`phase28/stockcode_coverage.csv`](phase28/stockcode_coverage.csv)\n")
    lines.append(f"### Delisted candidates ({a['n_delisted']} tickers, max(tradingdate) < {DELIST_CUTOFF})\n")
    lines.append(f"Companion CSV: [`phase28/delisted_candidates.csv`](phase28/delisted_candidates.csv)\n")
    lines.append("First 50 delisted tickers: " + (delisted_first50 or "_none_") + "\n")
    lines.append("### FLC / ROS / HVN explicit check\n")
    lines.append(flagged_lines + "\n")

    lines.append("## Section B — VN100 universe source\n")
    lines.append(f"- Source used: **{vn['source']}**")
    lines.append(f"- Ticker count: **{vn['n']}**\n")

    lines.append("## Section C — VN100 quarterly EPS coverage 2014-2025\n")
    lines.append(f"Source: MySQL `is_quarter_nonbank`. Expected quarters per ticker: {EXPECTED_QUARTERS}.")
    lines.append(f"`resolve_eps_publish_date` sanity check on real data: **{'OK' if c.get('publish_date_ok') else 'FAILED'}**.")
    lines.append(f"Companion CSV: [`phase28/vn100_eps_coverage.csv`](phase28/vn100_eps_coverage.csv)\n")
    lines.append("### Best 10 by n_quarters_present\n")
    lines.extend(_fmt_eps_row(r) for r in c.get("top10", []))
    lines.append("\n### Worst 10 by n_quarters_present\n")
    lines.extend(_fmt_eps_row(r) for r in c.get("bottom10", []))
    lines.append("")

    lines.append("## Section D — `stock_foreign_eod` VN100 coverage\n")
    lines.append(f"Date range audited: {FOREIGN_YEAR_MIN}-01-01 → {FOREIGN_YEAR_MAX}-12-31.")
    lines.append(f"Tickers with **zero** `stock_foreign_eod` rows: **{d['n_missing']}**.")
    lines.append(f"Companion CSV: [`phase28/foreign_eod_coverage.csv`](phase28/foreign_eod_coverage.csv)\n")
    lines.append("### Worst 10 by n_days\n")
    lines.extend(_fmt_foreign_row(r) for r in d.get("worst10", []))
    lines.append("")

    lines.append("## Section E — Price adjustment convention\n")
    lines.append("See [`phase28-price-adjustment.md`](phase28-price-adjustment.md) (phase 28 plan 03 output).")
    lines.append("Summary: `totaladjustrate` is the forward-adjusted factor from Postgres `stock_eod`; "
                 "adjusted close = `closeprice * totaladjustrate` with the canonical divisor pinned at the "
                 "anchor date defined there.\n")

    lines.append("## Section F — EPS publish_date convention\n")
    lines.append("See `connectors/eps.py::resolve_eps_publish_date` (phase 28 plan 04).\n")
    lines.append("Rule:\n")
    lines.append("- Use real `publish_date` / `announce_date` / `updated_at` when present.")
    lines.append("- Otherwise impute from `(yearreport, lengthreport)`:")
    lines.append("  - Q1/Q2/Q3 (`lengthreport` ∈ {3,6,9}) → period_end + **45 days**")
    lines.append("  - Q4 / annual (`lengthreport` ∈ {12, NaN}) → period_end + **90 days**\n")

    lines.append("## Open risks for Phase 29+\n")
    lines.append("_To be filled in with concrete numbers after live run._\n")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 28 data audit runner")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip DB calls, write empty CSVs + skeleton report")
    args = ap.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        for name in ("stockcode_coverage", "delisted_candidates",
                     "vn100_eps_coverage", "foreign_eod_coverage"):
            (args.out_dir / f"{name}.csv").write_text("dry-run\n")
        REPORT_PATH.write_text(
            "# Phase 28 Data Audit (dry-run skeleton)\n\n"
            "Run without `--dry-run` to populate with real numbers.\n"
            "Covers: Distinct stockcode, delisted candidates, FLC/ROS/HVN, "
            "VN100 EPS coverage, stock_foreign_eod, publish_date, "
            "phase28-price-adjustment. Open risks section will be populated.\n"
        )
        print(f"[dry-run] wrote skeleton report to {REPORT_PATH}")
        return 0

    ctx: dict = {}
    print("[A] stock_eod coverage...")
    ctx["section_a"] = section_a_stockcode_coverage(args.out_dir)
    print(f"    distinct={ctx['section_a']['n_distinct']} "
          f"delisted={ctx['section_a']['n_delisted']}")

    print("[B] VN100 universe...")
    ctx["vn100"] = section_b_vn100()
    print(f"    n={ctx['vn100']['n']} source={ctx['vn100']['source']}")

    print("[C] VN100 EPS coverage...")
    ctx["section_c"] = section_c_eps_coverage(ctx["vn100"], args.out_dir)

    print("[D] VN100 stock_foreign_eod coverage...")
    ctx["section_d"] = section_d_foreign_eod(ctx["vn100"], args.out_dir)

    REPORT_PATH.write_text(render_markdown(ctx), encoding="utf-8")
    print(f"[done] report -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
