---
phase: 31-multi-stock-portfolio-engine
plan: 03
subsystem: strategies/portfolio
tags: [wave-3, exits, sizing, liquidity-gate]
requires: [31-01, 31-02]
provides:
  - strategies.portfolio.exits.evaluate_exits
  - strategies.portfolio.exits.ExitDecision
  - strategies.portfolio.exits.rs_streak_hit
  - strategies.portfolio.exits.EXIT_REASONS
  - strategies.portfolio.sizing.target_notional
  - strategies.portfolio.sizing.lot_round_shares
  - strategies.portfolio.sizing.adv20
  - strategies.portfolio.sizing.liquidity_gate_passes
  - strategies.portfolio.sizing.sort_by_canslim
affects: []
tech_added: []
patterns: [first-match-wins-exit-chain, pure-function-sizing, strict-lookahead-discipline]
key_files_created:
  - strategies/portfolio/exits.py
  - strategies/portfolio/sizing.py
  - tests/strategies/portfolio/test_exit_chain.py
  - tests/strategies/portfolio/test_sizing.py
  - tests/strategies/portfolio/test_liquidity_gate.py
key_files_modified: []
decisions:
  - "Exit chain is pure function — engine holds state, this module just decides. Deferred hard-stop (limit-down) returns deferred=True without attempting to compute next valid bar; engine re-calls on next bar."
  - "adv20 uses explicit iloc slicing (no rolling) so the state[i-1] discipline is audit-obvious per memory/feedback_equity_formula.md."
metrics:
  duration_seconds: 180
  tasks_completed: 2
  files_changed: 5
  tests_passing: 25
completed: "2026-04-09"
requirements: [GATE-02, PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-09]
---

# Phase 31 Plan 03: Exits & Sizing Summary

Built the exit priority chain (D-13 first-match-wins, D-14 T+2 block, D-19 limit-down deferral, D-16 RS NaN fail-closed) and the sizing/liquidity primitives (D-09 slot target, D-11 lot-floor residual, D-24 ADV20 gate, D-10 CANSLIM tie-break).

## One-liner

Exit chain + sizing/liquidity primitives — MDM SELL > hard stop > MA50 break > RS streak, T+2 blocks all, limit-down defers hard stop, ADV20 no-lookahead verified — 25 tests green.

## Tasks

| # | Task | Commit | Tests |
|---|------|--------|-------|
| 1 | Exit priority chain (exits.py) + 13 tests | `d0b544f` | 13 passing |
| 2 | Sizing + ADV20 liquidity gate + CANSLIM sort | `ac92e79` | 12 passing (25 total) |

## Key Files

**Created:**
- `strategies/portfolio/exits.py` — `EXIT_REASONS` tuple, `ExitDecision` dataclass, `evaluate_exits()` with explicit if/elif first-match-wins chain, `rs_streak_hit()` helper scanning from tail and fail-closing on NaN.
- `strategies/portfolio/sizing.py` — `target_notional`, `lot_round_shares` (math.floor → max 0), `adv20` (explicit iloc[-20:] slice, returns NaN if <20 prior bars), `liquidity_gate_passes` (NaN → False), `sort_by_canslim` (returns kept_desc + dropped_missing).
- `tests/strategies/portfolio/test_exit_chain.py` — 13 tests: T+2 block, priority order, hard stop, limit-down deferral, MA50 break with/without vol, RS streak hit/miss, RS fail-closed on NaN, RS continuous, MDM-beats-hard-stop, hard-stop-beats-MA50, EXIT_REASONS constants.
- `tests/strategies/portfolio/test_sizing.py` — 6 tests: target notional (1B → 125M), lot exact (5000), lot floor down (4900 shares + 2.01M residual), zero when price too high, CANSLIM sort desc, CANSLIM drops missing.
- `tests/strategies/portfolio/test_liquidity_gate.py` — 6 tests: ADV20 formula, ADV20 insufficient history NaN, gate passes, gate blocks, NaN → False, **no-lookahead** (mutate close[25] after compute → unchanged).

## Verification

```
uv run pytest tests/strategies/portfolio/test_exit_chain.py \
              tests/strategies/portfolio/test_sizing.py \
              tests/strategies/portfolio/test_liquidity_gate.py -x -q
25 passed in 0.05s
```

All acceptance criteria per plan met:
- `def evaluate_exits`, `earliest_sell_bar`, `mdm_sell`, `rs_streak_hit` present in exits.py
- `def test_priority_order`, `def test_t2_blocks_all` present in test_exit_chain.py
- `def lot_round_shares`, `def adv20`, `def liquidity_gate_passes`, `def sort_by_canslim` present in sizing.py
- `def test_lot_round_floors_down` present in test_sizing.py
- `def test_adv20_no_lookahead` present in test_liquidity_gate.py
- pytest exits 0 with 25 tests passed (≥12 required per task)

Success criteria:
- Exit chain honors D-13 first-match-wins + D-14 T+2 override ✓
- Hard-stop limit-down deferral flagged (D-19) ✓
- RS streak resets on NaN (D-16) ✓
- 100-lot floor leaves residual in cash (D-11) ✓
- ADV20 no-lookahead (SC8 precursor) ✓
- CANSLIM tie-break sorts desc, drops missing scores (D-10) ✓

## Deviations from Plan

None. Plan executed exactly as written. No Rules 1-4 triggered.

## Self-Check: PASSED

Files verified:
- strategies/portfolio/exits.py — FOUND
- strategies/portfolio/sizing.py — FOUND
- tests/strategies/portfolio/test_exit_chain.py — FOUND
- tests/strategies/portfolio/test_sizing.py — FOUND
- tests/strategies/portfolio/test_liquidity_gate.py — FOUND

Commits verified in git log:
- d0b544f — FOUND
- ac92e79 — FOUND
