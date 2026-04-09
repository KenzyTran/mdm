---
phase: 28-data-audit-connectors
plan: 05
subsystem: data
tags: [postgres, mysql, audit, vn100, eps, foreign-flow, data-quality]

requires:
  - phase: 28-data-audit-connectors
    provides: Postgres + MySQL connectors, adjust_ohlc, resolve_eps_publish_date
provides:
  - scripts/run_phase28_audit.py end-to-end audit runner (--dry-run supported)
  - docs/audits/phase28-data-audit.md canonical phase-28 data audit report
  - 4 companion CSVs under docs/audits/phase28/ (stockcode_coverage, delisted_candidates, vn100_eps_coverage, foreign_eod_coverage)
  - Quantified data-quality risks for VN100 backtest (delisted set, EPS gaps, foreign-flow gaps)
affects: [29-vn100-canslim, 30-entry-confirmation, 31-portfolio-engine]

tech-stack:
  added: []
  patterns:
    - "Audit runner pattern: argparse + --dry-run + per-section functions + pandas CSV export + Markdown render"
    - "VN100 universe resolution: UNION of stock_list.nhomtop IN ('VN30','VN100') (single-tag column)"
    - "Cross-sector EPS lookup: UNION ALL of is_quarter_nonbank/bank/insurance/stock"

key-files:
  created:
    - scripts/run_phase28_audit.py
    - docs/audits/phase28-data-audit.md
    - docs/audits/phase28/stockcode_coverage.csv
    - docs/audits/phase28/delisted_candidates.csv
    - docs/audits/phase28/vn100_eps_coverage.csv
    - docs/audits/phase28/foreign_eod_coverage.csv
  modified: []

key-decisions:
  - "stock_list.nhomtop is a single-tag column; VN30 and VN100 stored separately — union both tags to get the 100-ticker VN100 universe"
  - "EPS audit must UNION all 4 is_quarter_* sector tables (nonbank/bank/insurance/stock) to cover banks and securities firms in VN100"
  - "stock_foreign_eod coverage only begins 2022-04-07 — pre-2022 foreign-flow features are unavailable for backtest and must be handled in Phase 29+"

patterns-established:
  - "Phase data-audit runner: one script regenerates report + CSVs from live DB, --dry-run for CI smoke"
  - "Audit report sections mirror requirement IDs (D-12 checklist) for traceability"

requirements-completed: [DATA-05, DATA-06, DATA-07]

duration: ~90min
completed: 2026-04-09
---

# Phase 28 Plan 05: Data Audit Report Summary

**End-to-end phase 28 data audit runner + report quantifies 2936 stockcodes, 852 delisted candidates, 100-ticker VN100 universe with 16 EPS-sparse tickers, and stock_foreign_eod starting only 2022-04-07**

## Performance

- **Duration:** ~90 min (including Rule-1 debugging across checkpoint review)
- **Tasks:** 3 (2 auto + 1 human-verify)
- **Files created:** 6

## Accomplishments

- Built `scripts/run_phase28_audit.py` — end-to-end audit runner with `--dry-run` smoke mode, live Postgres + MySQL queries, and Markdown report rendering
- Ran live audit and published `docs/audits/phase28-data-audit.md` with real numbers answering all 6 D-12 checklist items
- Quantified survivorship-bias risks for Phase 29+: 852 delisted candidates, ROS confirmed delisted, FLC/HVN active
- Verified `resolve_eps_publish_date` (from plan 28-04) works on real multi-sector data
- Discovered and documented that `stock_foreign_eod` only has data from 2022-04-07 — major constraint for pre-2022 backtest

## Task Commits

1. **Task 1: Implement scripts/run_phase28_audit.py** — `28f1842` (feat)
2. **Task 2: Run audit live + write final report** — `3e2348e` (feat)
3. **Task 3: Human read-through** — approved by user after Rule-1 fixes

**Rule-1 fixes (during checkpoint review):**
- `8988e0c` fix(28-05): include VN30 tag in VN100 universe resolution
- `cbf3e0c` fix(28-05): union all 4 sector is_quarter_* tables in VN100 EPS audit

## Key Findings (from live audit)

- **stock_eod:** 2936 distinct stockcodes, range 1861-12-31 → 2026-04-09
- **Delisted candidates (max_date < 2024-01-01):** 852 tickers
- **FLC/ROS/HVN explicit check:** FLC active, **ROS delisted**, HVN active
- **VN100 universe:** 100 tickers (source: `stock_list.nhomtop IN ('VN30','VN100')`)
- **VN100 EPS coverage:** 16 tickers have <40/48 quarters 2014-2025 (DSE, GEE, DXS, HHV, SIP, GVR, KOS, BCM, SSB, POW are the worst)
- **stock_foreign_eod:** 0 VN100 tickers missing; earliest first_date observed is 2022-04-07 (REE/VIB/KOS) — pre-2022 data not available in this table
- **`resolve_eps_publish_date` real-data check:** OK

## Files Created

- `scripts/run_phase28_audit.py` — audit runner
- `docs/audits/phase28-data-audit.md` — canonical audit report
- `docs/audits/phase28/stockcode_coverage.csv`
- `docs/audits/phase28/delisted_candidates.csv`
- `docs/audits/phase28/vn100_eps_coverage.csv`
- `docs/audits/phase28/foreign_eod_coverage.csv`

## Decisions Made

- **VN100 universe via tag union:** stock_list.nhomtop is a single-tag column where VN30 and VN100 are stored as separate rows; union both tags to reach the 100-ticker universe.
- **EPS cross-sector union:** is_quarter_nonbank alone misses banks (ACB, BID, …) and securities firms; runner now UNION ALLs all 4 sector tables.
- **Phase 29 risks flagged:** pre-2022 foreign-flow features unavailable; 16 VN100 tickers have sparse EPS history; ROS survivorship handling required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] VN100 universe query returned wrong count**
- **Found during:** Task 3 checkpoint review
- **Issue:** `stock_list.nhomtop ILIKE '%VN100%'` returned fewer than 100 tickers because nhomtop is single-tag and VN30 stocks are tagged 'VN30', not 'VN100'.
- **Fix:** Query now unions `nhomtop IN ('VN30','VN100')` to reach the full 100-ticker universe.
- **Committed in:** `8988e0c`

**2. [Rule 1 - Bug] EPS audit missed banks and securities firms**
- **Found during:** Task 3 checkpoint review
- **Issue:** `is_quarter_nonbank` alone excludes banks (ACB, BID, CTG, VCB, …) and securities firms (SSI, VND, …), producing false "zero quarters" for ~20 VN100 tickers.
- **Fix:** EPS section now UNION ALLs `is_quarter_nonbank`, `is_quarter_bank`, `is_quarter_insurance`, `is_quarter_stock` before aggregating per ticker.
- **Committed in:** `cbf3e0c`

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug). Both essential for correctness of the audit numbers. No scope creep.

## Issues Encountered

- Initial live run showed implausibly low VN100 EPS coverage and a short VN100 list → traced to the two bugs above during human checkpoint review → fixed and re-ran → numbers now consistent.

## User Setup Required

None — uses existing `.env` Postgres/MySQL credentials from phase 28-00.

## Next Phase Readiness

- Phase 29 (VN100 + CANSLIM) can proceed with documented data constraints:
  - Plan for survivorship (ROS delisted; 852 delisted candidates in full universe)
  - Handle pre-2022 foreign-flow absence (stock_foreign_eod starts 2022-04-07)
  - Decide how to treat 16 EPS-sparse VN100 tickers (drop, impute, or shorten backtest window)
- Closes DATA-05, DATA-06, DATA-07 → phase 28 data-audit requirements fully satisfied.

## Self-Check: PASSED

- scripts/run_phase28_audit.py: FOUND
- docs/audits/phase28-data-audit.md: FOUND
- docs/audits/phase28/stockcode_coverage.csv: FOUND
- docs/audits/phase28/delisted_candidates.csv: FOUND
- docs/audits/phase28/vn100_eps_coverage.csv: FOUND
- docs/audits/phase28/foreign_eod_coverage.csv: FOUND
- Commits 28f1842, 3e2348e, 8988e0c, cbf3e0c: FOUND in git log

---
*Phase: 28-data-audit-connectors*
*Completed: 2026-04-09*
