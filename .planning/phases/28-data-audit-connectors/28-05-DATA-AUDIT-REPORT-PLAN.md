---
phase: 28-data-audit-connectors
plan: 05
type: execute
wave: 3
depends_on: ["28-01", "28-02", "28-03", "28-04"]
files_modified:
  - scripts/run_phase28_audit.py
  - docs/audits/phase28-data-audit.md
  - docs/audits/phase28/stockcode_coverage.csv
  - docs/audits/phase28/delisted_candidates.csv
  - docs/audits/phase28/vn100_eps_coverage.csv
  - docs/audits/phase28/foreign_eod_coverage.csv
autonomous: false
requirements: [DATA-05, DATA-06, DATA-07]
must_haves:
  truths:
    - "Audit script runs end-to-end against live Postgres + MySQL and writes one Markdown report + 4 companion CSVs"
    - "Report enumerates distinct stockcode count in stock_eod"
    - "Report lists count + first 50 stockcodes whose max(tradingdate) < 2024-01-01 (delisted candidates)"
    - "Report explicitly checks for FLC, ROS, HVN presence/absence"
    - "Report contains per-VN100 ticker quarterly EPS coverage 2014-2025"
    - "Report contains stock_foreign_eod VN100 daily coverage 2014-2026"
    - "Report references the price-adjustment convention doc from plan 03"
    - "Report references the EPS publish_date imputation rule from plan 04"
  artifacts:
    - path: scripts/run_phase28_audit.py
      provides: "End-to-end audit runner"
      min_lines: 120
    - path: docs/audits/phase28-data-audit.md
      provides: "Human-readable audit report"
      contains: "Distinct stockcode"
    - path: docs/audits/phase28/stockcode_coverage.csv
      provides: "stockcode, min_date, max_date, row_count"
    - path: docs/audits/phase28/delisted_candidates.csv
      provides: "stockcode, max_date for tickers stale before 2024-01-01"
    - path: docs/audits/phase28/vn100_eps_coverage.csv
      provides: "stockcode, n_quarters_2014_2025, first_quarter, last_quarter, gaps"
    - path: docs/audits/phase28/foreign_eod_coverage.csv
      provides: "stockcode, n_days_2014_2026, first_date, last_date"
  key_links:
    - from: scripts/run_phase28_audit.py
      to: "connectors.postgres.query"
      via: "import + call"
      pattern: "from connectors.postgres"
    - from: scripts/run_phase28_audit.py
      to: "connectors.mysql.query"
      via: "import + call"
      pattern: "from connectors.mysql"
    - from: scripts/run_phase28_audit.py
      to: "connectors.eps.resolve_eps_publish_date"
      via: "import + call"
      pattern: "resolve_eps_publish_date"
---

<objective>
Build the audit runner that pulls real numbers from Postgres + MySQL and produces the canonical phase-28 report + companion CSVs. Closes DATA-05, DATA-06, DATA-07.

Purpose: Quantify the data-quality risks the v7.0 backtest will face — delisted tickers, fundamental gaps, foreign-flow gaps — so phases 29+ can plan around them.
Output: One Markdown report + 4 CSVs under docs/audits/, plus the script that regenerates them.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/28-data-audit-connectors/28-CONTEXT.md
@.planning/phases/28-data-audit-connectors/28-RESEARCH.md
@.planning/phases/28-data-audit-connectors/28-01-SUMMARY.md
@.planning/phases/28-data-audit-connectors/28-02-SUMMARY.md
@.planning/phases/28-data-audit-connectors/28-03-SUMMARY.md
@.planning/phases/28-data-audit-connectors/28-04-SUMMARY.md
@docs/audits/phase28-price-adjustment.md
@connectors/postgres.py
@connectors/mysql.py
@connectors/eps.py
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement scripts/run_phase28_audit.py</name>
  <files>scripts/run_phase28_audit.py</files>
  <read_first>
    - connectors/postgres.py (query, load_stock_eod)
    - connectors/mysql.py (query, load_is_quarter)
    - connectors/eps.py (resolve_eps_publish_date)
    - .planning/phases/28-data-audit-connectors/28-CONTEXT.md (D-12 — required report items)
  </read_first>
  <action>
    Create `scripts/run_phase28_audit.py`. The script must:

    1. Accept `--dry-run` (skips DB calls, writes empty CSVs + skeleton report — used for CI smoke).
    2. Accept `--out-dir` (default `docs/audits/phase28`).
    3. Section A — stockcode coverage in stock_eod (Postgres):
       ```sql
       SELECT stockcode, MIN(tradingdate) AS min_date,
              MAX(tradingdate) AS max_date, COUNT(*) AS row_count
       FROM stock_eod GROUP BY stockcode
       ```
       Write to `stockcode_coverage.csv`. Compute and report:
       - Distinct stockcode count
       - Count where max_date < '2024-01-01'
       Write the delisted subset to `delisted_candidates.csv`.
       Explicitly report whether FLC, ROS, HVN appear in the delisted list.

    4. Section B — VN100 universe source. Use `stock_list` table:
       ```sql
       SELECT DISTINCT stockcode FROM stock_list WHERE nhomtop ILIKE '%VN100%'
       ```
       If empty, fall back to top-100 by max(totalvol*closeprice) over last 60 trading days. Document fallback used in the report.

    5. Section C — VN100 quarterly EPS coverage 2014-2025 (MySQL is_quarter_nonbank):
       ```sql
       SELECT stockcode, yearreport, lengthreport, eps
       FROM is_quarter_nonbank
       WHERE stockcode IN (...vn100...)
         AND yearreport BETWEEN 2014 AND 2025
       ```
       Pass through `resolve_eps_publish_date` (DATA-04 helper) to confirm it works on real data. For each VN100 ticker compute:
       - n_quarters_present (out of 48 expected: 2014Q1..2025Q4)
       - first_quarter (yearreport*10 + quarter)
       - last_quarter
       - n_gaps (48 - n_quarters_present)
       Write `vn100_eps_coverage.csv`.

    6. Section D — foreign EOD coverage 2014-2026 (Postgres `stock_foreign_eod`):
       ```sql
       SELECT stockcode, MIN(tradingdate) AS first_date,
              MAX(tradingdate) AS last_date, COUNT(*) AS n_days
       FROM stock_foreign_eod
       WHERE stockcode IN (...vn100...)
       GROUP BY stockcode
       ```
       Write `foreign_eod_coverage.csv`.

    7. Render `docs/audits/phase28-data-audit.md` with sections:
       - Executive Summary (numbers from each section)
       - Section A: stock_eod coverage + delisted candidates (link to CSV, list first 50 + FLC/ROS/HVN check)
       - Section B: VN100 universe source used
       - Section C: VN100 EPS coverage (top-10 best + bottom-10 worst by n_quarters_present)
       - Section D: stock_foreign_eod VN100 coverage (worst 10 by n_days)
       - Section E: Price adjustment convention — link to `docs/audits/phase28-price-adjustment.md`
       - Section F: EPS publish_date convention — explicit reference to `connectors/eps.py` rule (Q1-Q3 +45d, Q4/annual +90d)
       - Open risks for Phase 29+

    8. Use plain pandas + pathlib + connectors helpers; no jinja.

    Skeleton:
    ```python
    """Phase 28 data audit — DATA-05/06/07.

    Usage:
        uv run python scripts/run_phase28_audit.py
        uv run python scripts/run_phase28_audit.py --dry-run
    """
    from __future__ import annotations
    import argparse
    from pathlib import Path
    import pandas as pd

    from connectors.postgres import query as pg_query
    from connectors.mysql import query as my_query
    from connectors.eps import resolve_eps_publish_date

    REPORT_PATH = Path("docs/audits/phase28-data-audit.md")
    DEFAULT_OUT = Path("docs/audits/phase28")

    # ... section functions: section_a_stockcode_coverage, section_b_vn100,
    #     section_c_eps_coverage, section_d_foreign_eod, render_markdown ...

    def main(argv=None):
        ap = argparse.ArgumentParser()
        ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
        ap.add_argument("--dry-run", action="store_true")
        args = ap.parse_args(argv)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

        if args.dry_run:
            for name in ("stockcode_coverage","delisted_candidates",
                         "vn100_eps_coverage","foreign_eod_coverage"):
                (args.out_dir / f"{name}.csv").write_text("dry-run\n")
            REPORT_PATH.write_text("# Phase 28 Data Audit (dry-run skeleton)\n")
            return 0

        ctx = {}
        ctx["section_a"] = section_a_stockcode_coverage(args.out_dir)
        ctx["vn100"]     = section_b_vn100()
        ctx["section_c"] = section_c_eps_coverage(ctx["vn100"], args.out_dir)
        ctx["section_d"] = section_d_foreign_eod(ctx["vn100"], args.out_dir)
        REPORT_PATH.write_text(render_markdown(ctx))
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    ```

    Implement each section function fully, using pg_query/my_query and writing CSVs via `df.to_csv(path, index=False)`.

    Per D-11 (Markdown + CSVs, no notebook), D-12 (required report items), D-13 (delisted flagged not handled).
  </action>
  <verify>
    <automated>uv run python scripts/run_phase28_audit.py --dry-run && test -f docs/audits/phase28/stockcode_coverage.csv && test -f docs/audits/phase28-data-audit.md</automated>
  </verify>
  <acceptance_criteria>
    - `test -f scripts/run_phase28_audit.py`
    - `grep -q 'from connectors.postgres' scripts/run_phase28_audit.py`
    - `grep -q 'from connectors.mysql' scripts/run_phase28_audit.py`
    - `grep -q 'resolve_eps_publish_date' scripts/run_phase28_audit.py`
    - `grep -q 'stock_eod' scripts/run_phase28_audit.py`
    - `grep -q 'stock_foreign_eod' scripts/run_phase28_audit.py`
    - `grep -q 'is_quarter_nonbank' scripts/run_phase28_audit.py`
    - `grep -q 'FLC' scripts/run_phase28_audit.py`
    - `grep -q 'argparse' scripts/run_phase28_audit.py`
    - `grep -q 'dry_run' scripts/run_phase28_audit.py`
    - `--dry-run` exits 0 and writes 4 CSVs + report skeleton
  </acceptance_criteria>
  <done>Script runs `--dry-run` cleanly; section functions implemented and ready for live DB.</done>
</task>

<task type="auto">
  <name>Task 2: Run audit live + write final report</name>
  <files>
    docs/audits/phase28-data-audit.md,
    docs/audits/phase28/stockcode_coverage.csv,
    docs/audits/phase28/delisted_candidates.csv,
    docs/audits/phase28/vn100_eps_coverage.csv,
    docs/audits/phase28/foreign_eod_coverage.csv
  </files>
  <read_first>
    - scripts/run_phase28_audit.py (just-created runner)
    - docs/audits/phase28-price-adjustment.md (linked from final report)
  </read_first>
  <action>
    1. Run: `uv run python scripts/run_phase28_audit.py` (live, no --dry-run)
    2. Verify all 4 CSVs exist and are non-empty
    3. Open `docs/audits/phase28-data-audit.md`, confirm it contains real numbers (not "dry-run skeleton")
    4. Manually edit the "Open risks for Phase 29+" section at the bottom with concrete observations from the data, e.g.:
       - "X% of VN100 tickers have <40 quarterly EPS rows in 2014-2025 — survivorship bias risk for early backtest years"
       - "FLC/ROS/HVN: present/absent — survivorship handling MUST be designed in Phase 29"
       - "stock_foreign_eod missing for N VN100 tickers before 2017 — I-rule fallback required"
    5. Commit all generated artifacts.
  </action>
  <verify>
    <automated>test -s docs/audits/phase28-data-audit.md && test -s docs/audits/phase28/stockcode_coverage.csv && test -s docs/audits/phase28/vn100_eps_coverage.csv && test -s docs/audits/phase28/foreign_eod_coverage.csv && test -s docs/audits/phase28/delisted_candidates.csv</automated>
  </verify>
  <acceptance_criteria>
    - All 5 files exist and are non-empty
    - `grep -q 'Distinct stockcode' docs/audits/phase28-data-audit.md`
    - `grep -q 'FLC' docs/audits/phase28-data-audit.md`
    - `grep -q 'EPS' docs/audits/phase28-data-audit.md`
    - `grep -q 'stock_foreign_eod' docs/audits/phase28-data-audit.md`
    - `grep -q 'phase28-price-adjustment' docs/audits/phase28-data-audit.md`
    - `grep -q 'publish_date' docs/audits/phase28-data-audit.md`
    - `grep -q 'Open risks' docs/audits/phase28-data-audit.md`
    - Report does NOT contain "dry-run skeleton"
  </acceptance_criteria>
  <done>Live audit complete, all CSVs populated with real Postgres/MySQL numbers, report has narrative open-risks section.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Human read-through of audit report</name>
  <what-built>End-to-end Phase 28 data audit: connectors built, helpers tested, report + 4 CSVs published under docs/audits/phase28/.</what-built>
  <how-to-verify>
    1. Open `docs/audits/phase28-data-audit.md` and confirm it answers all 6 D-12 items:
       (a) Distinct stockcode count in stock_eod
       (b) Delisted candidate count + list (max(tradingdate) < 2024-01-01)
       (c) Explicit FLC/ROS/HVN check
       (d) Price-adjustment convention (link to phase28-price-adjustment.md)
       (e) Per-stock VN100 quarterly EPS coverage 2014-2025
       (f) stock_foreign_eod VN100 daily coverage 2014-2026
    2. Skim the 4 CSVs in `docs/audits/phase28/` — confirm they look reasonable (no all-NaN, sensible date ranges).
    3. Read the "Open risks for Phase 29+" section and confirm at least 2 concrete risks are listed with numbers.
  </how-to-verify>
  <acceptance_criteria>
    - User responds "approved" or describes missing items
  </acceptance_criteria>
  <resume-signal>Type "approved" or list issues to fix</resume-signal>
</task>

</tasks>

<verification>
- `uv run pytest tests/ -q` green (full suite, including integration if creds present)
- All artifacts under docs/audits/ committed
- DATA-05, DATA-06, DATA-07 closed
</verification>

<success_criteria>
- Report enumerates all 6 D-12 items with real numbers
- 4 companion CSVs populated from live DB
- Open risks section has concrete numbers feeding Phase 29 planning
- Human approves report contents
</success_criteria>

<output>
Create `.planning/phases/28-data-audit-connectors/28-05-SUMMARY.md` after completion.
</output>
