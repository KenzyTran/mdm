---
phase: 31-multi-stock-portfolio-engine
plan: 02
subsystem: strategies/portfolio
tags: [wave-2, primitives, microstructure, costs, cooldown]
requires: [31-01]
provides:
  - strategies.portfolio.microstructure.compute_ceiling
  - strategies.portfolio.microstructure.compute_floor
  - strategies.portfolio.microstructure.is_ceiling_locked
  - strategies.portfolio.microstructure.is_floor_locked
  - strategies.portfolio.microstructure.t2_earliest_sell_bar
  - strategies.portfolio.costs.apply_entry_cost
  - strategies.portfolio.costs.apply_exit_cost
  - strategies.portfolio.costs.entry_cost_basis
affects: []
tech_added: []
patterns: [pure-function-primitives, stdlib-only-microstructure, test-documents-engine-contract]
key_files_created:
  - strategies/portfolio/microstructure.py
  - strategies/portfolio/costs.py
  - tests/strategies/portfolio/test_microstructure.py
  - tests/strategies/portfolio/test_costs.py
  - tests/strategies/portfolio/test_cooldown.py
key_files_modified: []
decisions:
  - "microstructure.py is stdlib-only (no pandas) — keeps primitives trivially unit-testable in microseconds"
  - "MDM SELL cooldown exemption enforced at engine layer, not CooldownRegistry — documented via test and module docstring so the Wave-3 engine plan cannot miss the contract"
metrics:
  duration_seconds: 120
  tasks_completed: 3
  files_changed: 5
  tests_passing: 16
completed: "2026-04-09"
requirements: [GATE-03, GATE-04, PORT-05, PORT-07, PORT-08]
---

# Phase 31 Plan 02: Primitives Summary

Built the stateless primitives the exit chain and engine will compose: Vietnam microstructure helpers (T+2 earliest-sell, 7% ceiling/floor, O==H==L limit-lock detection) and the cost model (0.35% entry debit / 0.45% exit haircut / per-share cost basis), plus cooldown semantics tests locking in D+6 earliest re-entry and the MDM-SELL exemption contract.

## One-liner

Pure-function primitives for VN microstructure (T+2, ceiling/floor lock) + costs (entry 0.35% / exit 0.45%) + CooldownRegistry D+6 semantics — 16 tests green.

## Tasks

| # | Task | Commit | Tests |
|---|------|--------|-------|
| 1 | microstructure.py — T+2, ceiling/floor lock helpers | `a5f6844` | 8 passing |
| 2 | costs.py — entry/exit cost functions | `a2834b9` | 4 passing (12 total) |
| 3 | Cooldown semantics tests (PORT-07, D-20/D-21) | `b764224` | 4 passing (16 total) |

## Key Files

**Created:**
- `strategies/portfolio/microstructure.py` — 5 pure functions: `compute_ceiling`, `compute_floor` (raw prev_close × 1.07 / 0.93 with TODO about tick rounding per D-18), `is_ceiling_locked` / `is_floor_locked` (True iff open == high == low == limit within tol), `t2_earliest_sell_bar` (buy_bar + t_plus + 1, D-17). Stdlib-only, no pandas.
- `strategies/portfolio/costs.py` — 3 pure functions: `apply_entry_cost` (notional × (1 + 0.35%)), `apply_exit_cost` (gross × (1 − 0.45%)), `entry_cost_basis` (fill_price × (1 + entry_comm + entry_slip)). Per D-22/D-23.
- `tests/strategies/portfolio/test_microstructure.py` — 8 tests: ceiling/floor values, locked-true, locked-false (range mismatch and below), mirror for floor, T+2 math (buy_bar=10 → 13).
- `tests/strategies/portfolio/test_costs.py` — 4 tests: default entry (100M → 100.35M), default exit (100M → 99.55M), cost basis (25000 → 25087.5), override path (custom comm/slip).
- `tests/strategies/portfolio/test_cooldown.py` — 4 tests: D+5 blocks, D+6 allows, unknown ticker not cooling, MDM-SELL-exempt contract test (engine must not call register() for MDM SELL exits; locked into docstring + test).

## Verification

```
uv run pytest tests/strategies/portfolio/test_microstructure.py \
              tests/strategies/portfolio/test_costs.py \
              tests/strategies/portfolio/test_cooldown.py -x -q
16 passed in 0.05s
```

All acceptance criteria met:
- `def is_ceiling_locked`, `def t2_earliest_sell_bar`, `buy_bar_idx + t_plus + 1` present in microstructure.py
- `def apply_entry_cost`, `def apply_exit_cost`, `def entry_cost_basis` present in costs.py
- `def test_cooldown_allows_d_plus_6`, `MDM SELL` present in test_cooldown.py
- pytest exits 0

Numerics match D-17..D-23 exactly (entry 0.35% debit, exit 0.45% haircut, T+2 → D+3 earliest sell, cooldown → D+6 earliest re-entry).

## Deviations from Plan

None. Plan executed exactly as written. No Rules 1-4 triggered.

## Self-Check: PASSED

Files verified:
- strategies/portfolio/microstructure.py — FOUND
- strategies/portfolio/costs.py — FOUND
- tests/strategies/portfolio/test_microstructure.py — FOUND
- tests/strategies/portfolio/test_costs.py — FOUND
- tests/strategies/portfolio/test_cooldown.py — FOUND

Commits verified in git log:
- a5f6844 — FOUND
- a2834b9 — FOUND
- b764224 — FOUND
