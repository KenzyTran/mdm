---
phase: 29-vn100-universe-canslim-scorer
plan: "05"
subsystem: strategies/canslim/rules
tags: [canslim, fundamentals, wave-2]
requires: [strategies.canslim.config, strategies.canslim.sectors, connectors.eps, schema_lock.json]
provides: [strategies.canslim.rules.fundamental.compute_fundamentals]
affects: [docs/rules_canslim.md, tests/canslim/test_rules_fundamental.py]
tech_stack:
  added: []
  patterns: [sector-branching, look-ahead-guard, schema-lock-fallback, pure-helper-split]
key_files:
  created: []
  modified:
    - strategies/canslim/rules/fundamental.py
    - tests/canslim/test_rules_fundamental.py
    - docs/rules_canslim.md
decisions:
  - "Look-ahead guard uses connectors.eps.resolve_eps_publish_date (impute from yearreport+lengthreport) instead of a DB publish_date column — schema_lock.publish_date_column is legitimately null"
  - "Bank branch falls back to non-bank EPS column when is_quarter_bank_ppop_column is null in schema_lock (documented approximation, re-introspect when real PPOP column surfaces)"
  - "A+ rule interpreted as 'last 3 rolling-TTM annuals all positive' (matches 29-CONTEXT D-12, diverges from plan-02 'ROE' stub name)"
  - "Pure helpers (compute_c / compute_c_plus / compute_a / compute_a_plus) split from the DB-touching orchestrator for standalone unit tests"
metrics:
  duration_minutes: 4
  tasks_completed: 1
  files_modified: 3
  completed_at: "2026-04-09"
requirements_closed: [CANS-01, CANS-02, CANS-03, CANS-04]
---

# Phase 29 Plan 05: CANSLIM Fundamental Rules Summary

**One-liner:** Implemented `compute_fundamentals(ticker, as_of_date, config, sector_router, mysql_engine)` with C / C+ / A / A+ rules, sector branching (bank PPOP vs non-bank EPS via `schema_lock.json`), `connectors.eps.resolve_eps_publish_date` look-ahead guard (D-11), and ctck/insurance exclusion — closing CANS-01..CANS-04 and unblocking the plan 29-08 scorer composition.

## What Was Built

### Task 1: `compute_fundamentals` + rule helpers (TDD)

**Pure helpers (no DB, no schema):**

- `compute_c(values, threshold)` — current quarter YoY vs 4 quarters ago ≥ threshold; needs ≥5 quarters.
- `compute_c_plus(values)` — current YoY growth > mean of prior two quarters' YoY growths; needs ≥7 quarters.
- `compute_a(values, threshold)` — 3yr TTM-sum CAGR ≥ threshold: `(sum(v[0:4])/sum(v[8:12]))**(1/2)-1`; needs ≥12 quarters; returns False on non-positive denominators.
- `compute_a_plus(annual_values)` — last 3 rolling-TTM annuals all strictly positive.

**Orchestrator:**

- `compute_fundamentals()`:
  - Routes via `SectorRouter.route()`; `ctck` / `insurance` short-circuit to `(False, False, False, False)` without touching the DB (D-07).
  - Reads `_schema()` (cached JSON load of `schema_lock.locked`); selects table + value column per sector.
  - Falls back to the non-bank EPS column when the locked bank PPOP column is `null` (documented approximation).
  - Calls `_load_quarters()`, which issues a single `SELECT stockcode, yearreport, lengthreport, <value_col>` query (LIMIT 32), pipes the DataFrame through `resolve_eps_publish_date`, filters `publish_date <= as_of_date`, sorts newest-first, and returns up to 16 rows.
  - Builds rolling-TTM "annuals" at offsets (0, 4, 8) and dispatches to the four pure helpers.

**Legacy shims** (`check_c_quarterly_eps_yoy`, `check_c_plus_eps_acceleration`, `check_a_annual_eps_growth`, `check_a_plus_roe`) kept so anything importing the plan-02 stub names still works — each just returns the corresponding tuple index from `compute_fundamentals`.

**Tests** (`tests/canslim/test_rules_fundamental.py`, 13 total):

- 8 pure-helper tests (C pass/fail, C+ acceleration/flat, A happy path, A insufficient history, A+ all-positive, A+ negative year).
- 5 integration tests: non-bank happy path, look-ahead guard (filters a future 2025Q2 row at `as_of_date=2025-06-30`), bank ticker routes to `is_quarter_bank` table (asserted via captured SQL), ctck exclusion skips DB entirely (monkeypatched `read_sql` raises on call), insufficient history returns False for A without exceptions.
- Autouse fixture monkeypatches `_SCHEMA_LOCK` so tests never hit disk.

**Docs sync:** `docs/rules_canslim.md` §4 rewritten — sector-branching table, formula table, schema-lock fallback note, D-11 look-ahead guard explanation, and test pointer. `_TBD — plan 29-05_` removed.

- Commit: `7778393`

## Verification

- `uv run pytest tests/canslim/test_rules_fundamental.py -x -q` → **13 passed in 0.11s**
- `grep -q "publish_date" strategies/canslim/rules/fundamental.py` → found
- `grep -q "is_quarter_bank" strategies/canslim/rules/fundamental.py` → found
- `grep -q "TTM" docs/rules_canslim.md` → found
- `grep -q "_TBD — plan 29-05" docs/rules_canslim.md` → **absent** (section filled)
- Commit `7778393` touches both `strategies/canslim/rules/fundamental.py` and `docs/rules_canslim.md` (Code-Docs Sync satisfied).

## Key Decisions

1. **Impute publish_date instead of failing** — `schema_lock.publish_date_column` is legitimately `null` (no real publish/announce column in `is_quarter_nonbank` / `is_quarter_bank`). Rather than block the plan on a schema gap, the orchestrator pipes every loaded frame through `connectors.eps.resolve_eps_publish_date`, which imputes `period_end + 45d` (quarter) / `+90d` (annual). This matches phase 28 D-08/D-09/D-10 and is the same discipline the rest of the CANSLIM layer already relies on.
2. **Bank PPOP fallback to non-bank EPS column** — `is_quarter_bank_ppop_column` is also `null` in the current schema lock (introspector note: "no PPOP-like column in is_quarter_bank"). Fallback uses the non-bank EPS column name (`loi_nhuan_gop`) against the `is_quarter_bank` table, which is a best-effort approximation. Documented in `docs/rules_canslim.md` §4 with a re-introspection note.
3. **A+ = positive annual EPS 3 yrs, not ROE** — plan-02 stub was named `check_a_plus_roe`, but 29-CONTEXT D-12 and the plan-05 must-haves specify "annual EPS positive each of last 3 years". Implemented per D-12 and left a docstring note on the legacy shim.
4. **Pure helpers split out** — keeps unit tests deterministic without any monkeypatching and lets plan 29-08 scorer call the helpers directly if it ever pre-loads a quarterly frame.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] publish_date SQL filter replaced with in-memory imputation**
- **Found during:** Task 1 planning — plan's reference implementation uses `WHERE {publish_col} <= %(d)s` in SQL, but `schema_lock.publish_date_column` is `null`.
- **Issue:** Can't filter on a column that doesn't exist; the SQL would raise at runtime.
- **Fix:** Load rows with `yearreport` + `lengthreport`, pipe through `connectors.eps.resolve_eps_publish_date` (already built in phase 28), then filter in pandas. Semantically identical to the plan intent, uses existing phase-28 infrastructure.
- **Files modified:** `strategies/canslim/rules/fundamental.py`
- **Commit:** `7778393`

**2. [Rule 3 — Blocking] Bank PPOP column fallback**
- **Found during:** Task 1 planning — `is_quarter_bank_ppop_column` is `null` in schema_lock.
- **Issue:** Bank branch would query a `NULL` column name and SQL would fail.
- **Fix:** Falls back to `is_quarter_nonbank_eps_column` name against the `is_quarter_bank` table, documented as a best-effort approximation in `docs/rules_canslim.md` §4 with a note to re-run the schema introspector.
- **Files modified:** `strategies/canslim/rules/fundamental.py`, `docs/rules_canslim.md`
- **Commit:** `7778393`

## Known Stubs

None introduced. The fallback on bank PPOP is a **data-layer approximation**, not a code stub — the module is fully wired end-to-end; plan 29-08 (scorer composition) can consume it immediately. Re-introspection of `is_quarter_bank` to find a real PPOP column is tracked as a follow-up in `docs/rules_canslim.md` §4, not a blocker.

## Self-Check: PASSED

- strategies/canslim/rules/fundamental.py FOUND (`compute_fundamentals`, `_load_quarters`, `resolve_eps_publish_date` import, schema fallback, sector branching all present)
- tests/canslim/test_rules_fundamental.py FOUND (13 tests, all pass in 0.11s)
- docs/rules_canslim.md §4 FOUND (no longer `_TBD_`, contains formula table and look-ahead guard section)
- Commit 7778393 present in git log and touches all three files
