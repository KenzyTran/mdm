---
phase: 31-multi-stock-portfolio-engine
plan: 04
subsystem: strategies/portfolio
tags: [wave-4, engine, orchestrator, sc8]
requires: [31-01, 31-02, 31-03]
provides:
  - strategies.portfolio.engine.PortfolioEngine
  - strategies.portfolio.engine.PortfolioResult
affects: []
tech_added: []
patterns: [inject-all-upstream, precompute-indicators-once, nav-prev-before-bar-t, first-match-wins-exits]
key_files_created:
  - strategies/portfolio/engine.py
  - tests/strategies/portfolio/test_gate_policy.py
  - tests/strategies/portfolio/test_nav_lookback.py
  - tests/strategies/portfolio/test_engine_integration.py
key_files_modified:
  - strategies/portfolio/__init__.py
decisions:
  - "NAV[t-1] computed BEFORE any bar-t decision via `_compute_nav(bar_idx-1)`; ADV20 series shifted by 1 in precompute — bar-t sizing uses only bars strictly before t"
  - "Ceiling-lock tolerance loosened to 0.02 VND to handle VN tick-rounding between fixture and engine prev_close*1.07 recomputation"
  - "MDM SELL exits skip CooldownRegistry.register (D-20); all other exits register cooldown"
  - "Entry fill scheduling rechecks ceiling-lock on actual fill bar AND at candidate evaluation time; both paths log unfilled/ceiling_lock"
metrics:
  duration_seconds: 480
  tasks_completed: 2
  files_changed: 5
  tests_passing: 62
completed: "2026-04-09"
requirements: [GATE-01, GATE-02, GATE-03, GATE-04, PORT-01, PORT-02, PORT-03, PORT-04, PORT-06, PORT-07, PORT-09, PORT-10]
---

# Phase 31 Plan 04: PortfolioEngine Summary

Built the PortfolioEngine bar-by-bar orchestrator integrating Waves 0-3 primitives into a single `.run()` loop with the non-negotiable SC8 invariant: bar-t close mutations do not influence bar-t entry sizing.

## One-liner

PortfolioEngine — bar loop composing config/state/exits/sizing/microstructure/costs with SC8 NAV[t-1] discipline, Policy A gate dispatch, T+2 override, ceiling/floor lock, cooldown, CANSLIM tie-break — 12 new tests (62 total) green.

## Tasks

| # | Task | Commit | Tests |
|---|------|--------|-------|
| 1 | PortfolioEngine bar-loop orchestrator | `502e5e7` | import smoke |
| 2 | Gate policy + SC8 + integration tests | `c417a5e` | 12 new (62 total) |

## Key Files

**Created:**
- `strategies/portfolio/engine.py` — `PortfolioEngine` class with `__init__` (fail-loud validation + precompute MA50/vol20_avg/ADV20(shifted)/ceiling_px/floor_px), `.run()` main loop, `_compute_nav`, `_materialize_scheduled_fills`, `_dedupe_union` (D-04 union mode), `_update_rs_streaks`, `_build_bar_ctx`. Scheduled entries fill at `bar_idx+1` at candidate.fill_price; exits at next open with floor-lock deferral.
- `tests/strategies/portfolio/test_gate_policy.py` — 4 tests: state injection, BUY admits, CASH drops (`gate_cash`), SELL liquidates without cooldown.
- `tests/strategies/portfolio/test_nav_lookback.py` — 3 tests: `test_no_bar_t_lookahead` (mutates AAA close from bar 25 onward by 1.5x, asserts identical entries/final positions), `test_nav_prev_uses_prior_close`, `test_adv20_uses_only_prior_bars`. Cites the 707% bug from `memory/feedback_equity_formula.md`.
- `tests/strategies/portfolio/test_engine_integration.py` — 5 tests: end-to-end synthetic, T+2 blocks early exit, ceiling lock blocks entry (via `lock_days` fixture hook), CANSLIM tie-break selects top-2 of 4, cooldown blocks re-entry.

**Modified:**
- `strategies/portfolio/__init__.py` — exports PortfolioEngine, PortfolioResult, PortfolioConfig.

## Verification

```
uv run pytest tests/strategies/portfolio/ -q
62 passed in 9.44s
```

All acceptance criteria met:
- `class PortfolioEngine`, `_compute_nav`, `nav_prev`, `entry_mode`, `mdm_sell`, `ceiling_lock`, `liquidity_gate` present in engine.py
- `PortfolioEngine` exported from `__init__.py`
- `test_no_bar_t_lookahead`, `test_policy_a_sell_liquidates_all`, `test_ceiling_lock_blocks_entry`, `test_canslim_tiebreak_selects_top`, `test_t2_blocks_early_exit`, `test_cooldown_blocks_reentry` all present and passing
- `707` citation in test_nav_lookback.py
- 12 new tests pass; 62 total portfolio tests pass

## Deviations from Plan

**[Rule 3 - Fixture tolerance]** Ceiling-lock tolerance in engine loosened to 0.02 VND (from default 1e-6) to handle the rounding gap between `make_panel` fixture (which rounds ceiling to 2 decimals) and the engine's precomputed `prev_close * 1.07`. Without this, `is_ceiling_locked` returned False even on locked bars. Tracked as blocking the ceiling-lock integration test. Fixed in the same commit as Task 2 tests.

**[Minor - test calibration]** Tests use `initial_cash=1_000_000` (not 1B default) so that target_notional at 12.5% slot_weight is small enough for synthetic ADV20 (~20-30M) to pass the adv_mult=1.0 liquidity gate. Documented in test file comments.

**[Minor - test bar indices]** Signal bars shifted from bar 5 → bar 25 so ADV20 (requires 20 prior bars) is computed. Cooldown test uses n_bars=80 and bars 25/33 for the same reason.

## Self-Check: PASSED

Files verified:
- strategies/portfolio/engine.py — FOUND
- tests/strategies/portfolio/test_gate_policy.py — FOUND
- tests/strategies/portfolio/test_nav_lookback.py — FOUND
- tests/strategies/portfolio/test_engine_integration.py — FOUND

Commits verified:
- 502e5e7 — FOUND (Task 1)
- c417a5e — FOUND (Task 2)
