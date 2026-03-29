---
phase: 15-advanced-features
plan: 02
subsystem: mdm-hybrid
tags: [contextual-transitions, state-history, favor-cash, adv-01, tdd]
dependency_graph:
  requires: [indicator_filter.py, mdm_hybrid_engine.py, config.py]
  provides: [state_history, contextual_threshold, favor_cash_logic]
  affects: [mdm_hybrid_engine.py, test_hybrid_engine.py]
tech_stack:
  added: []
  patterns: [contextual-modifier, temporary-filter-instance, state-history-append-on-change]
key_files:
  created: []
  modified:
    - strategies/mdm_hybrid/mdm_hybrid_engine.py
    - tests/test_hybrid_engine.py
decisions:
  - "State history only grows on state CHANGES, not every day (no memory leak)"
  - "Contextual threshold uses temporary IndicatorFilter to keep filter stateless"
  - "Only 2 contextual rules to avoid overfitting on 95 post-2019 signals"
  - "BUY from long Cash (>10d) or Cash-from-Sell (>5d) requires unanimous agreement (1.0)"
metrics:
  duration: 48min
  completed: "2026-03-29T13:49:40Z"
---

# Phase 15 Plan 02: Contextual State Transitions Summary

State history tracking with contextual majority_threshold adjustment implementing Dr. K's 'favor cash positions' philosophy via 2 simple rules that make BUY confirmations harder in bearish context.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 072362b | test | Add failing tests for state history and contextual threshold (TDD RED) |
| 415f8b3 | feat | Implement state history tracking and contextual threshold (TDD GREEN) |

## Changes Made

### Task 1: State History Tracking + Contextual Threshold (TDD)

**HybridEngine.__init__** (mdm_hybrid_engine.py):
- Added `self.state_history = []` list tracking completed state periods
- Added `self._current_state_name`, `self._current_state_start`, `self._days_in_current_state` tracking vars
- Reset method clears all state history fields

**State history update** (mdm_hybrid_engine.py run() loop):
- After final state determined (post two-phase commit), checks if state changed
- On state change: appends completed state `{state, entered_date, duration}` to `state_history`
- On same state: increments `_days_in_current_state`
- History only grows on state CHANGES, not every day

**_get_contextual_threshold()** (mdm_hybrid_engine.py):
- Returns base `majority_threshold` for non-BUY proposals (SELL/CASH unaffected)
- Rule 1: If in CASH for > `cash_deterioration_days` (default 10), returns 1.0 for BUY
- Rule 2: If in CASH entered from SELL and > 5 days, returns 1.0 for BUY
- Otherwise returns default threshold (2/3)

**Contextual threshold wiring** (mdm_hybrid_engine.py run() loop):
- Before evaluate() call, computes `ctx_threshold = self._get_contextual_threshold(proposal)`
- If threshold differs from default, creates temporary `IndicatorFilter` with adjusted `FilterConfig`
- Keeps IndicatorFilter stateless per Phase 12 design

**Tests** (test_hybrid_engine.py):
- `test_state_history_tracking`: Verifies {state, entered_date, duration} entries on NASDAQ data
- `test_state_history_only_on_changes`: History length < total days, <= transition count
- `test_contextual_cash_from_sell_stickier`: CASH from SELL (6 days) requires 1.0
- `test_contextual_long_cash_raises_threshold`: CASH for 11 days requires 1.0
- `test_contextual_normal_does_not_modify`: Short CASH from BUY keeps 2/3
- `test_contextual_only_affects_buy_proposals`: SELL/CASH proposals unaffected

## Verification Results

- `uv run pytest tests/test_hybrid_engine.py -k "test_state_history or test_contextual"`: 6 passed
- `uv run pytest tests/test_hybrid_engine.py tests/test_indicator_filter.py -x`: 72 passed (full regression)
- State history grows only on state changes (not 13K+ entries)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functionality is fully wired.

## Self-Check: PASSED

- All 2 modified files exist in worktree
- All 2 commits (072362b, 415f8b3) found in git log
- Acceptance criteria keywords verified in source files
