---
phase: 29
plan: 09
subsystem: strategies/canslim
tags: [canslim, validation, baseline, sc6, phase-29]
requires:
  - strategies/canslim/scorer.py (29-08)
  - connectors/mysql.py (stocks_backend.canslim access)
provides:
  - strategies/canslim/baseline.py (canslim baseline loader)
  - scripts/canslim_baseline_compare.py (28-quarter comparison CLI)
  - docs/audits/phase29/baseline_comparison.md (raw per-quarter results)
  - docs/audits/phase29-canslim-validation.md (SC1–SC7 phase roll-up)
  - docs/rules_canslim.md §8 (baseline validation section)
affects:
  - strategies/canslim/scorer.py (bug fix: closeindex→closeprice)
  - strategies/canslim/rules/fundamental.py (bug fix: mack/thoigian schema)
  - .planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json
    (bug fix: hardcoded is_quarter_bank_ppop_column)
tech-stack:
  added: []
  patterns:
    - "End-to-end smoke test against live Postgres + MySQL before declaring SC green"
    - "Boolean-vs-percentile per-component agreement as SC6 sanity metric"
key-files:
  created:
    - strategies/canslim/baseline.py
    - scripts/canslim_baseline_compare.py
    - docs/audits/phase29/baseline_comparison.md
    - docs/audits/phase29-canslim-validation.md
  modified:
    - docs/rules_canslim.md
    - strategies/canslim/scorer.py
    - strategies/canslim/rules/fundamental.py
    - .planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json
decisions:
  - "Treat CANSLIM as an independent VN100 screen, not a replica of stocks_backend.canslim (user: Option A)"
  - "Defer composite weight calibration against any baseline to a future phase"
  - "Ship Phase 29 with SC6 FAIL vs original numeric gate, ACCEPTED by user decision"
metrics:
  tasks_completed: 3
  completed_date: 2026-04-09
requirements_closed:
  - CANS-12
---

# Phase 29 Plan 09: Baseline validation + Phase 29 ship Summary

Built an end-to-end comparison harness between `CanslimScorer` and the upstream
`stocks_backend.canslim` table across 28 quarters (Q1 2019 – Q4 2025,
VN100-restricted), discovered and fixed three latent schema bugs that had
survived all of plans 29-02…29-08 because unit tests used synthetic DataFrames,
and — after finding that the scorer's top-10 ranking diverges sharply from the
upstream baseline (median Spearman ρ = 0.280, 2.43/10 top-10 overlap) — shipped
Phase 29 with documented divergence per user decision (Option A), treating
CANSLIM as an independent screen rather than a baseline replica.

## What was built

### Task 1 — `strategies/canslim/baseline.py` (commit `197a510`)

Baseline loader retargeted from the originally-planned `rank_top_stocks.diem_canslim`
to `stocks_backend.canslim`, which is the table that actually holds the
composite and per-component percentile ranks. Exports:

- `load_canslim_quarter(mysql_engine, year, period)` — returns a frame with
  `mack`, `tong_diem`, `eps_quy_gan_nhat`, `eps_trailing_12_thang`,
  `sale_quy_gan_nhat`.
- `available_quarters(mysql_engine)` — distinct (year, period) pairs with data.

### Task 2 — `scripts/canslim_baseline_compare.py` + raw report (commit `2deab97`)

Comparison CLI that, for each quarter with ≥ N VN100 rows in both our scorer
and the baseline:

1. Maps quarter label → last trading day in `stock_eod`.
2. Runs `CanslimScorer.score(last_trading_day)`, restricts to VN100.
3. Loads baseline frame for that quarter, restricts to VN100.
4. Computes top-10 overlap, Spearman ρ on the ticker intersection, and
   per-component agreement between our boolean C / A / S passes and the
   baseline percentiles thresholded at ≥ 70.
5. Emits a Markdown report with per-quarter tables, top-10 lists, and a
   per-component aggregate table.

Raw output: `docs/audits/phase29/baseline_comparison.md`.

**Critical bug fixes discovered and committed in the same change** (Rule 3
— blocking issues — because the scorer could not execute against live DBs at
all before these fixes, and without the scorer SC6 cannot be evaluated):

1. **`scorer.py::_load_panel`** queried non-existent columns
   `closeindex` / `highestindex`. Real columns: `closeprice` / `highestprice`.
   Fixed in-place.
2. **`rules/fundamental.py::_load_quarters`** queried non-existent columns
   `stockcode`, `yearreport`, `lengthreport` on the `is_quarter_*` tables.
   Real columns: `mack` (ticker) and a single text column `thoigian`
   encoding the period. Rewrote the loader to filter on `mack` and parse
   `thoigian`.
3. **`schema_lock.json.locked.is_quarter_bank_ppop_column` was `null`**,
   causing the bank branch fallback to degenerate to an empty column name.
   Hardcoded `loi_nhuan_tu_hdkd_truoc_chi_phi_du_phong_rui_ro_tin_dung`
   pending a proper re-introspection.

None of these were caught by the existing unit tests because every test in
`tests/canslim/test_rules_fundamental.py` and `tests/canslim/test_scorer.py`
fed the loaders synthetic DataFrames rather than live DB connections.
**This is the single biggest lesson from plan 29-09.**

### Task 3 — Validation report + rules §8 (commit `961ec48`)

- `docs/audits/phase29-canslim-validation.md` — phase-level roll-up covering
  SC1–SC7, requirements traceability table, the raw SC6 numbers, the
  interpretation of why the divergence is expected, the schema bug
  post-mortem, known caveats, and the final verdict (Phase 29 SHIPPED
  with documented divergence).
- `docs/rules_canslim.md` §8 — added "Baseline Validation" section with
  methodology, results, caveats, and the Option A decision. Links back to
  the audit report.

## Raw SC6 numbers

| Metric                                 | Observed        |
| -------------------------------------- | --------------- |
| Quarters compared                      | 28              |
| Median Spearman ρ                      | **0.280**       |
| Quarters with ρ ≥ 0.5                  | **1 / 28 (4%)** |
| Mean top-10 overlap                    | **2.43 / 10**   |
| Per-component agreement — C (EPS YoY)  | 69% mean        |
| Per-component agreement — A (EPS TTM)  | 70% mean        |
| Per-component agreement — S (Sales)    | 66% mean        |

**Original gate:** Spearman ρ ≥ 0.5 on ≥ 70% of quarters → **FAIL.**
**User decision:** **ACCEPTED** as expected independent-implementation
divergence (Option A).

## Decision path — 3 checkpoints → Option A

Plan 29-09 went through three checkpoints before landing on the final
decision:

1. **Checkpoint after task 1** — baseline loader retargeted to
   `stocks_backend.canslim` after discovering `rank_top_stocks.diem_canslim`
   did not contain the expected schema. User approved the retarget.
2. **Checkpoint after task 2 (first run)** — scorer crashed immediately on
   schema mismatches (bugs #1, #2, #3 above). Classified as Rule 3 blocking
   issues and fixed in the same commit (`2deab97`). User approved the
   scoped-in bug fixes.
3. **Checkpoint after task 2 (second run)** — scorer now executed cleanly
   across all 28 quarters, but the results failed the original SC6 numeric
   gate decisively (median ρ 0.280, 1/28 quarters passing). User was
   presented with two options:
   - **Option A** — accept the divergence, ship Phase 29 with honest
     documentation, treat CANSLIM as an independent screen, defer
     calibration.
   - **Option B** — loop back to plan 29-08, tune composite weights
     against the baseline, re-run 29-09.
   User selected **Option A**. This summary and the validation report
   document that decision.

## Deviations from plan

### Rule 3 — Blocking issues auto-fixed in task 2

**[Rule 3 - Blocking] Three schema bugs in scorer / fundamental loader / schema lock**
- **Found during:** Task 2 (first execution against live DBs)
- **Issue:** Scorer could not read `stock_eod` (wrong column names), could
  not read `is_quarter_*` tables (wrong column names), and the bank PPOP
  fallback degenerated to an empty column. Plan assumed all of this worked.
- **Fix:** See bugs 1–3 in task 2 section above.
- **Files modified:** `strategies/canslim/scorer.py`,
  `strategies/canslim/rules/fundamental.py`,
  `.planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json`.
- **Commit:** `2deab97` (scoped into the task 2 commit rather than a
  separate fix commit, because without these fixes task 2's primary
  deliverable — the comparison script output — could not be produced at all).

### Plan-level deviation — baseline table retarget (task 1)

Plan 29-09 originally specified `rank_top_stocks.diem_canslim` as the
baseline. Actual schema inspection during task 1 showed the real table with
usable per-component data was `stocks_backend.canslim`. The loader and all
downstream logic were retargeted with user approval at the first
checkpoint. This did not affect any other plan's success criteria.

### SC6 acceptance — Option A

The plan's acceptance criterion ("overlap ≥ 4/10 on at least 3 of 5 sampled
dates") and the phase's SC6 gate ("Spearman ρ ≥ 0.5 on ≥ 70% of quarters")
both failed the measured results. User explicitly chose Option A (ship with
documented divergence) rather than Option B (loop back and tune). All
downstream documents (validation report, rules §8, this summary) reflect
that decision.

## Commits

| Task            | Commit    | Message                                                                  |
| --------------- | --------- | ------------------------------------------------------------------------ |
| Task 1          | `197a510` | feat(29-09): retarget baseline loader to stocks_backend.canslim          |
| Task 2          | `2deab97` | feat(29-09): baseline comparison script + fix scorer schema bugs         |
| Task 3          | `961ec48` | docs(29-09): phase 29 validation report + rules §8 baseline validation   |

## Deferred issues

- **Re-introspect `is_quarter_bank` for a proper PPOP column** instead of
  the hardcoded fallback in `schema_lock.json`. A future cleanup plan should
  run `scripts/introspect_canslim_schema.py` with an improved PPOP
  heuristic and unlock the `is_quarter_bank_ppop_column` field.
- **Composite weight calibration.** Phase 29 locks
  `0.70 * bool + 0.30 * rs` without any forward-return or baseline
  validation of that choice. A future phase should revisit calibration,
  probably against forward returns rather than against the upstream
  baseline.
- **Live-DB smoke tests for CANSLIM.** The existing unit tests all use
  synthetic DataFrames. Add at least one integration test that hits live
  Postgres + MySQL and runs the scorer end-to-end for one as-of date, so
  that future schema drift fails loudly in CI rather than during the next
  phase's execution.

## Self-Check: PASSED

- `docs/audits/phase29-canslim-validation.md` — FOUND
- `docs/audits/phase29/baseline_comparison.md` — FOUND (from task 2)
- `docs/rules_canslim.md` §8 — FOUND (added in `961ec48`)
- `strategies/canslim/baseline.py` — FOUND (from task 1, `197a510`)
- `scripts/canslim_baseline_compare.py` — FOUND (from task 2, `2deab97`)
- Commits `197a510`, `2deab97`, `961ec48` — FOUND in `git log`
