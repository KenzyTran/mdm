---
phase: 29-vn100-universe-canslim-scorer
plan: "03"
subsystem: strategies/canslim
tags: [universe, canslim, wave-1]
requires: [strategies.canslim, schema_lock.json]
provides: [strategies.canslim.universe.UniverseLoader]
affects: [docs/rules_canslim.md, tests/canslim/test_universe.py]
tech_stack:
  added: []
  patterns: [dataclass-config, monkeypatched-read_sql-tests]
key_files:
  created: []
  modified:
    - strategies/canslim/universe.py
    - tests/canslim/test_universe.py
    - docs/rules_canslim.md
decisions:
  - "liquidity-reconstructed uses AVG(closeindex*totalvol) over ~120 calendar days ending at rebalance date as 60-trading-day ADV proxy"
  - "rebalance set frozen between Jan 1 and Jul 1 (no intra-period churn)"
  - "history filter applies AFTER mode selection, using stock_eod row count"
metrics:
  duration_minutes: 3
  tasks_completed: 1
  files_modified: 3
  completed_at: "2026-04-09"
---

# Phase 29 Plan 03: Universe Loader Summary

**One-liner:** `UniverseLoader` dataclass with three modes (current-vn100, liquidity-reconstructed, vn30-only), semi-annual Jan/Jul rebalance for liquidity mode, and a D-05 min-history filter (252 days) — 7 tests green.

## What Was Built

### Task 1: UniverseLoader (TDD RED→GREEN)
- `strategies/canslim/universe.py` rewritten from Wave 0 stub into a `@dataclass` `UniverseLoader(mode, pg_engine, min_history_days=252, adv_window_days=60)`.
- Methods: `get(as_of_date)`, `_current_vn100()`, `_vn30_only()`, `_liquidity_reconstructed(date)`, `_last_rebalance_date(date)`, `_filter_by_history(tickers, date)`.
- SQL against `stock_list.nhomtop` (current-vn100, vn30-only) and `stock_eod` (ADV ranking + history count).
- Rebalance policy: most recent Jul 1 if `d >= Jul 1`, else Jan 1 if `d >= Jan 1`, else prior Jul 1.
- Invalid mode → `ValueError`.
- Legacy `load_vn100_universe()` kept as a deprecation shim that raises `NotImplementedError`.
- Tests in `tests/canslim/test_universe.py` (7 total): unknown-mode ValueError, `_last_rebalance_date` boundaries, current-vn100 SQL assertion, vn30-only filter, liquidity-reconstructed rebalance invariance across same period + crossing Jul 1, history filter dropping short history (BBB n=100 dropped, CCC n=252 kept).
- Test strategy: monkeypatch `universe.pd.read_sql` with a router that dispatches on SQL substring — no live DB needed.
- `docs/rules_canslim.md` §1 rewritten from `_TBD_` into full spec (3 modes, rebalance policy, history filter, usage example).
- Commit: `4c199a0`

## Verification

- `uv run pytest tests/canslim/test_universe.py -x -q` → **7 passed in 0.06s**
- `grep "nhomtop IN ('VN30','VN100')" strategies/canslim/universe.py` → match
- `grep "_last_rebalance_date" strategies/canslim/universe.py` → match
- `grep "min_history_days" strategies/canslim/universe.py` → match
- `docs/rules_canslim.md §1` no longer contains `_TBD_`

## Key Decisions

1. **ADV window via calendar-day range, not exact 60 trading days** — using `rebalance - 120 days` → `rebalance` approximates 60 trading days without needing a calendar table. Plan 29-06/07 can tighten this if the ordering turns out sensitive.
2. **`nhomtop` is the VN30/VN100 flag column** — consistent with schema_lock.json introspection results. If plan 29-04 finds a different column, this is a single-line change.
3. **History filter uses `ANY(%(tickers)s)`** — Postgres-specific but matches the rest of the codebase; keeps the query to one round-trip.

## Deviations from Plan

None — plan 29-03 executed exactly as written.

## Known Stubs

None in this plan. The `load_vn100_universe()` shim still raises `NotImplementedError` but is documented as deprecated and is not called by any code in the repo.

## Self-Check: PASSED

- strategies/canslim/universe.py FOUND (UniverseLoader class + 7 methods)
- tests/canslim/test_universe.py FOUND (7 tests passing)
- docs/rules_canslim.md §1 updated (no _TBD_)
- Commit 4c199a0 present in git log
