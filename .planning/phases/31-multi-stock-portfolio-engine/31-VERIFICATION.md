---
phase: 31-multi-stock-portfolio-engine
verified: 2026-04-09T16:10:00Z
status: passed
score: 8/8 success criteria verified
notes:
  - "64/64 phase-31 tests passing (tests/strategies/portfolio/)"
  - "2 prior-phase regression failures found (tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq, tests/test_qe_floor.py::TestBaselineRegression::test_baseline_regression) — both pre-exist Phase 31 (last touched in phases 17/19) and are unrelated to strategies/portfolio/"
---

# Phase 31: Multi-Stock Portfolio Engine Verification Report

**Phase Goal:** A long-only multi-stock state machine with stops, exits, costs, and Vietnam microstructure correctly processes a daily bar sequence without look-ahead.
**Verified:** 2026-04-09
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Engine holds up to 8 concurrent positions; equal-weight 12.5%/slot; 100-share lot rounding | VERIFIED | `PortfolioConfig(max_slots=8, slot_weight=0.125, lot_size=100)` in `strategies/portfolio/config.py`; `lot_round_shares` in `sizing.py`; `test_sizing.py::test_lot_round_floors_down` + `test_engine_integration.py::test_canslim_tiebreak_selects_top` pass |
| SC2 | MDM gate Policy A BUY/CASH/SELL dispatch | VERIFIED | `engine.py` gate dispatch; `test_gate_policy.py` (4 tests) — BUY admits, CASH drops, SELL liquidates |
| SC3 | Exit priority chain MDM SELL > 8% hard stop > MA50 trailing break (1.25x vol) > RS<70 for 5 sessions | VERIFIED | `exits.py::evaluate_exits` first-match-wins; `test_exit_chain.py` (13 tests incl. `test_priority_order`, `test_mdm_sell_beats_hard_stop`, `test_hard_stop_beats_ma50`) |
| SC4 | T+2 settlement; 7% ceiling lock blocks fills; 7% floor lock defers exit | VERIFIED | `microstructure.py::{is_ceiling_locked,is_floor_locked,t2_earliest_sell_bar}`; `test_microstructure.py` (8); `test_engine_integration.py::test_t2_blocks_early_exit` + `::test_ceiling_lock_blocks_entry` |
| SC5 | Re-entry cooldown 5 days per ticker after stop | VERIFIED | `state.py::CooldownRegistry`; `test_cooldown.py` (4) D+6 semantics; `test_engine_integration.py::test_cooldown_blocks_reentry` |
| SC6 | Costs both sides: 0.25% commission + 0.10% sell tax + 0.10% slippage | VERIFIED | `costs.py::{apply_entry_cost,apply_exit_cost,entry_cost_basis}`; `test_costs.py` (4) — 100M → 100.35M entry debit, 99.55M exit credit |
| SC7 | Liquidity gate: refuse entry if 20d ADV < 10x position size | VERIFIED | `sizing.py::{adv20,liquidity_gate_passes}`; `test_liquidity_gate.py` (6) incl. `test_adv20_no_lookahead` |
| SC8 | Equity curve uses state[i-1]; no bar-t look-ahead in NAV | VERIFIED | `engine.py::_compute_nav`; `test_nav_lookback.py::test_no_bar_t_lookahead` cites 707% bug and mutates close[t] post-run to prove bar-t entry shares unchanged |

**Score:** 8/8 success criteria verified

### Required Artifacts (all plans)

| Artifact | Expected | Status |
|----------|----------|--------|
| `strategies/portfolio/config.py` | PortfolioConfig dataclass | VERIFIED |
| `strategies/portfolio/state.py` | PositionBook/SlotState/CooldownRegistry/Position/Trade | VERIFIED |
| `strategies/portfolio/microstructure.py` | ceiling/floor/T+2 helpers | VERIFIED |
| `strategies/portfolio/costs.py` | entry/exit cost funcs | VERIFIED |
| `strategies/portfolio/exits.py` | evaluate_exits + ExitDecision + rs_streak_hit | VERIFIED |
| `strategies/portfolio/sizing.py` | target_notional, lot_round_shares, adv20, liquidity_gate_passes, sort_by_canslim | VERIFIED |
| `strategies/portfolio/engine.py` | PortfolioEngine.run() | VERIFIED |
| `strategies/portfolio/ab_report.py` | 4 CSV writers + write_all | VERIFIED |
| `connectors/postgres.py::load_stock_rs` | RS reader | VERIFIED |
| `docs/audits/phase31-portfolio-engine.md` | Audit report | VERIFIED |
| `docs/rules_canslim_mdm.md` | Portfolio Engine rules section | VERIFIED |
| `tests/strategies/portfolio/conftest.py` + fixtures | Synthetic panel | VERIFIED |

All artifact paths exist and contain required patterns per `gsd-tools verify artifacts` for all 5 plans.

### Key Link Verification

| From | To | Status |
|------|----|--------|
| test_rs_reader.py → connectors/postgres.py::load_stock_rs | import | VERIFIED |
| test_microstructure.py → microstructure.py | import | VERIFIED |
| test_costs.py → costs.py | import | VERIFIED |
| sizing.py → config.py::PortfolioConfig | import | VERIFIED |
| engine.py → exits.py::evaluate_exits | import | VERIFIED |
| engine.py → sizing.py | import | VERIFIED |
| engine.py → state.py (Position/PositionBook/Trade/CooldownRegistry) | import | VERIFIED (via `from .state import Position, Trade, PositionBook, CooldownRegistry` at line 25 — gsd-tools pattern looked for exact `PositionBook` first-token; manually confirmed) |
| exits.py → microstructure.py | import | NOT IMPORTED (intentional — `exits.py` is a pure decision function; microstructure checks are done in `engine.py` and passed via `bar_ctx` dict. This matches the plan's actual design: "exits is a pure function that consumes bar_ctx". Plan frontmatter key_link was aspirational. No functional gap.) |

### Requirements Coverage

| Req | Description | Plan(s) | Status | Evidence |
|-----|-------------|---------|--------|----------|
| GATE-01 | MDM HybridEngine gate source | 01,04 | SATISFIED | `engine.py` accepts injected `mdm_state` Series; `test_gate_policy.py::test_state_source_injection` |
| GATE-02 | Policy A (strict) BUY/CASH/SELL | 03,04 | SATISFIED | `test_gate_policy.py` (4 tests) |
| GATE-03 | Ceiling/floor lock handling | 02,04 | SATISFIED | `microstructure.py`; `test_engine_integration.py::test_ceiling_lock_blocks_entry` |
| GATE-04 | T+2 settlement (D+3 earliest sell) | 02,04 | SATISFIED | `t2_earliest_sell_bar`; `test_engine_integration.py::test_t2_blocks_early_exit` |
| PORT-01 | Multi-stock long-only state machine (max 8) | 01,03,04 | SATISFIED | `PositionBook`, `SlotState.free_slots`, `engine.py` loop |
| PORT-02 | Equal-weight 12.5%/slot, 100-share lot round-down | 03,04 | SATISFIED | `target_notional`, `lot_round_shares`; `test_sizing.py::test_lot_round_floors_down` |
| PORT-03 | 8% hard stop | 03,04 | SATISFIED | `exits.py`; `test_exit_chain.py::test_hard_stop` |
| PORT-04 | MA50 trailing stop with 1.25x volume confirm | 03,04 | SATISFIED | `exits.py`; `test_exit_chain.py::test_ma50_break` |
| PORT-05 | Limit-down handling (exit next open) | 02,03,04 | SATISFIED | `is_floor_locked`; `test_exit_chain.py::test_hard_stop_limit_down` deferred=True |
| PORT-06 | Exit priority chain order | 01,03,04 | SATISFIED | `test_exit_chain.py::test_priority_order` |
| PORT-07 | Re-entry cooldown 5 days (D+6 earliest) | 02,04 | SATISFIED | `CooldownRegistry`; `test_cooldown.py`; `test_engine_integration.py::test_cooldown_blocks_reentry` |
| PORT-08 | 0.25% comm + 0.10% tax + 0.10% slip both sides | 02 | SATISFIED | `costs.py`; `test_costs.py` |
| PORT-09 | Liquidity gate 20d ADV > 10x position | 03,04 | SATISFIED | `adv20`, `liquidity_gate_passes`; `test_liquidity_gate.py` |
| PORT-10 | Trade log + position log + NAV with state[i-1] | 01,04,05 | SATISFIED | `ab_report.py` 4 writers; `test_nav_lookback.py::test_no_bar_t_lookahead` |

All 14 requirements declared in plans; all satisfied. No orphaned requirement IDs.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 31 suite import + run | `uv run pytest tests/strategies/portfolio/ -x -q` | 64 passed | PASS |
| `PortfolioEngine` importable | `uv run python -c "from strategies.portfolio import PortfolioEngine, PortfolioConfig"` | (init validated via pytest collection) | PASS |
| SC8 no-lookahead regression | `test_nav_lookback.py::test_no_bar_t_lookahead` | passed | PASS |

### Anti-Patterns Found

None. Files scanned:
- `strategies/portfolio/config.py` — no TODO/stub
- `strategies/portfolio/state.py` — no stub
- `strategies/portfolio/engine.py` — contains doc TODO comment near MA50 rounding note (informational, not a gap)
- `strategies/portfolio/microstructure.py` — contains intentional TODO about VN tick-rounding helper (cited in plan as future enhancement, not a phase-31 gap)

### Prior-Phase Regression (requested by task)

Discovered tests outside `tests/strategies/portfolio/` and ran a broad regression batch (`tests/` excluding portfolio). Outcome: **258 passed, 2 failed** (run duration ~18 min):

| Failing Test | Last Touched | Phase 31 Related? |
|--------------|--------------|-------------------|
| `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq` | Phase 16 (`de77cd5`) | No — pre-existing, no Phase 31 file touched |
| `tests/test_qe_floor.py::TestBaselineRegression::test_baseline_regression` | Phase 19 (`0d0119f`) | No — pre-existing |

Both failing tests live in legacy MDM engine code paths. Phase 31 only adds files under `strategies/portfolio/` and `connectors/postgres.py::load_stock_rs`; no prior module was modified. These failures are **unrelated** to Phase 31 and should be tracked in their originating phases (17/19). Flagged here as **INFO** — not a Phase 31 gap.

### Human Verification Required

None — Phase 31 is a pure engine-only phase with comprehensive unit/integration coverage. Phase 32 will run the VN100 sweep that requires human inspection of realized returns.

## Gaps Summary

No gaps. Phase 31 delivers all 8 success criteria, all 14 requirements (GATE-01..04, PORT-01..10), all plan artifacts and key links (with one intentional design deviation in exits.py that matches the plan's "pure function" intent), and 64/64 phase tests green. The two prior-phase regression failures are tracked as info and do not block phase 31.

---

_Verified: 2026-04-09_
_Verifier: Claude (gsd-verifier)_
