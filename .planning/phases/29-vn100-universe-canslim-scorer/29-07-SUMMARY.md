---
phase: 29-vn100-universe-canslim-scorer
plan: "07"
subsystem: strategies/canslim/rules
tags: [canslim, flow, liquidity, wave-2, CANS-06, CANS-08, CANS-09]
requires: [strategies.canslim.config, strategies.canslim.rules.technical]
provides:
  - strategies.canslim.rules.flow.compute_i
  - strategies.canslim.rules.flow.compute_s
  - strategies.canslim.rules.liquidity.compute_liq
  - strategies.canslim.rules.flow.FOREIGN_DATA_START
affects: [docs/rules_canslim.md, tests/canslim/test_rules_flow.py, tests/canslim/test_rules_liquidity.py]
tech_stack:
  added: []
  patterns: [pre-date-fallback, median-over-mean, wrapper-delegation]
key_files:
  created: []
  modified:
    - strategies/canslim/rules/flow.py
    - strategies/canslim/rules/liquidity.py
    - tests/canslim/test_rules_flow.py
    - tests/canslim/test_rules_liquidity.py
    - docs/rules_canslim.md
decisions:
  - "I rule computes net_buy as (fbvalue - fsvalue) — schema_lock.json confirms no net_buy_value column exists; plan spec was aspirational"
  - "Pre-2022-04-07 fallback returns True unconditionally (FOREIGN_DATA_START constant) to avoid starving historical backtests"
  - "flow.compute_s is a thin wrapper delegating to technical.compute_s — single import surface for scorer, no duplicated logic"
  - "Liquidity uses MEDIAN not mean of 20d turnover — robust to fat-finger prints that otherwise drag illiquid names over threshold"
metrics:
  duration_minutes: 4
  tasks_completed: 2
  files_modified: 5
  completed_at: "2026-04-09"
---

# Phase 29 Plan 07: Flow (I) + Liquidity (Liq) Summary

**One-liner:** Closed CANS-06/08/09 — `compute_i` with explicit pre-2022-04-07 fallback, `compute_liq` 20d median-turnover gate, and a thin `compute_s` wrapper delegating to `technical.compute_s`; 13 tests green.

## What Was Built

### Task 1: compute_i (foreign net flow) with pre-2022 fallback — CANS-08 + CANS-06 wrapper

- `strategies/canslim/rules/flow.py` replaced stubs with `compute_i(ticker, as_of_date, config, pg_engine) -> bool` and `compute_s(ohlcv, as_of_date, config) -> bool`.
- Pre-2022-04-07 (`FOREIGN_DATA_START` constant) branch returns True without querying — documented fallback per 29-RESEARCH.md.
- Post-2022 SQL: `ORDER BY tradingdate DESC LIMIT :n` over `stock_foreign_eod`, computing `(fbvalue - fsvalue)` as net_buy (schema_lock.json confirms no `net_buy_value` column; the plan spec was aspirational — CLAUDE.md requires reading locked schema rather than guessing).
- Strict `> 0` comparison — zero and negative sums both fail.
- Empty result (no rows for post-2022 ticker) fails.
- 7 tests in `tests/canslim/test_rules_flow.py` monkeypatching `pd.read_sql`: imports + FOREIGN_DATA_START sentinel, pre-2022 fallback (no DB call via `m.assert_not_called()`), positive sum, negative sum, exactly-zero (strict check), empty frame, LIMIT parameter binding, wrapper delegation.
- `compute_s` wrapper delegates to `technical.compute_s` (plan 29-06), unit-tested via `patch("flow.technical.compute_s")`.
- `docs/rules_canslim.md` §6.1 + §6.2 populated: SQL skeleton, fallback truth table, delegation note.

Commit: `46bd0e9`

### Task 2: compute_liq (20d median turnover) — CANS-09

- `strategies/canslim/rules/liquidity.py` stub replaced with `compute_liq(ohlcv, as_of_date, config) -> bool`.
- `ohlcv[tradingdate <= as_of_date].tail(20)` → `(closeindex * totalvol).median() >= config.liquidity_min_turnover_vnd`.
- `<20` bars of history → False (no silent pass on insufficient data).
- 5 tests in `tests/canslim/test_rules_liquidity.py` using a `_mk_ohlcv` helper: imports, all-above-threshold, all-below, insufficient history, and a **median-vs-mean divergence** case (19×1B + 1×100B → mean≈6B but median=1B → False; plus symmetric 10×1B + 10×20B → median 10.5B → True).
- `docs/rules_canslim.md` §6.3 populated with formula and the "why median" rationale.

Commit: `37abe0a`

## Verification

```
$ uv run pytest tests/canslim/test_rules_flow.py tests/canslim/test_rules_liquidity.py -x -q
............. [100%]
13 passed in 0.11s
```

Acceptance grep checks:

- `grep -q "FOREIGN_DATA_START" strategies/canslim/rules/flow.py` — present
- `grep -q "2022" strategies/canslim/rules/flow.py` — present (constant + docstring)
- `grep -q "median()" strategies/canslim/rules/liquidity.py` — present
- `grep -q "5_000_000_000" docs/rules_canslim.md` — present (§6.3)
- Code-Docs Sync: Task 1 commit touches `rules/flow.py` + `docs/rules_canslim.md`; Task 2 commit touches `rules/liquidity.py` (docs §6.3 added in the Task 1 commit alongside §6.1/6.2 for atomicity).

## Key Decisions

1. **Schema deviation — `net_buy` computed, not a column.** The plan's `<action>` SQL referenced a `net_buy_value` column. `schema_lock.json` confirms `stock_foreign_eod` has only `fbvol/fbvalue/fsvol/fsvalue/froom`. Per plan note ("do not guess"), I substituted `(fbvalue - fsvalue) AS net_buy` in the locked SQL. No behavioral change — same definition, correct column names.
2. **`FOREIGN_DATA_START` as a module constant, not a magic date.** Grep-able, testable (`assert flow.FOREIGN_DATA_START == date(2022, 4, 7)`), easy to adjust if the upstream backfill ever reaches further.
3. **Wrapper vs re-implementation for S.** Per plan `<must_haves>`: "S rule (CANS-06) wrapper here delegates to technical.compute_s for consistency." Wrapper is 2 lines and exists solely to give the scorer a clean single-import surface (`from .rules import flow` for both I and S per-signal rules, while keeping N and S numeric logic together in `technical.py`).
4. **Legacy stub functions kept with `NotImplementedError`.** `check_i_foreign_net_buy` / `check_s_volume_surge` / `check_liquidity_turnover` from the scaffold are retained as deprecation shims pointing to the new API — prevents silent import errors if older scaffold code is still wired somewhere.

## Deviations from Plan

### Rule 2 — schema reality check (required by plan's "do not guess" clause)

**1. [Rule 2 - Schema] Use `(fbvalue - fsvalue)` instead of `net_buy_value`**

- **Found during:** Task 1, reading `schema_lock.json`
- **Issue:** Plan spec's SQL used `net_buy_value AS net_buy`. Locked schema has no such column.
- **Fix:** Compute `(fbvalue - fsvalue) AS net_buy` inline. Plan explicitly directed this: "read the locked name from schema_lock.json… do not guess."
- **Files:** `strategies/canslim/rules/flow.py`
- **Commit:** `46bd0e9`

Not a deviation; this is plan-directed behavior triggered at execution time. Logged here for traceability.

## Known Stubs

None introduced. Legacy `check_*` stubs in `flow.py`/`liquidity.py` are intentional deprecation shims (documented in their docstrings), not newly-added placeholders.

## Self-Check: PASSED

- `strategies/canslim/rules/flow.py` FOUND (modified in `46bd0e9`)
- `strategies/canslim/rules/liquidity.py` FOUND (modified in `37abe0a`)
- `tests/canslim/test_rules_flow.py` FOUND (7 tests pass)
- `tests/canslim/test_rules_liquidity.py` FOUND (5 tests pass)
- `docs/rules_canslim.md` §6.1/6.2/6.3 FOUND (populated, no more `_TBD_`)
- Commit `46bd0e9` present in `git log`
- Commit `37abe0a` present in `git log`
- 13/13 tests green via `uv run pytest`
