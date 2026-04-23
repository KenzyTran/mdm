---
phase: 44-macro-filter-module
plan: 03
subsystem: engine-integration
tags: [macro-filter, hybrid-engine, dxy, eem, sbv, macro-verdict, vn30, mdm-hybrid, d-04-stacking, d-08-hook-order, d-09-dual-layer-gate]

# Dependency graph
requires:
  - phase: 44-macro-filter-module (plan 02)
    provides: MacroVerdict frozen dataclass + add_macro_columns helper + 10 D-15 config fields + 7 skipped MacroFilter unit tests + 2 parity stubs
  - phase: 42-baseline-reconciliation
    provides: v60_strict_mode flag + tests/test_baseline_determinism.py pattern + reconciled baseline tuple
  - phase: 43-canonical-liquidity-data-pipeline
    provides: data/vn_liquidity_proxy.csv + data/sbv_policy_events.csv + docs/liquidity_proxy_spec.md
provides:
  - MacroFilter class with D-04 most-restrictive combiner apply() method
  - V2PositionManager.process_day with effective_dd_threshold override param
  - StopLossChecker.check + _get_effective_stop_pct with effective_max_multiplier override
  - HybridEngine wired via 6 insertion points (import, __init__, precompute gate, per-row hook, process_day kwarg, VETO_SELL handling)
  - Activated 7 previously-skipped MacroFilter tests + 2 parity regression stubs
affects:
  - 44-04 (parity-regression-signoff) — parity tests now meaningfully exercise the engine path; Plan 04 extends with byte-exact signal-log assertions
  - 45 (walk-forward-grid) — grid-search can now exercise the 10 D-15 config fields against the real engine
  - 46 (a-b-oos-validation) — A/B scenarios via preset mutation work because MacroFilter is live

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-04 most-restrictive combiner — stacking via orthogonal MacroVerdict fields (veto_sell + effective_dd_threshold + effective_stop_loss_max_multiplier)"
    - "D-08 hook order — MacroFilter applies AFTER IndicatorFilter so macro regime can overrule local indicator consensus (restore-from-snapshot on VETO_SELL mirrors IndicatorFilter VETO branch)"
    - "D-09 DUAL-LAYER short-circuit — engine gate around add_macro_columns + MacroFilter.apply first-line guard; both gates required to protect byte-exact v6.0 parity (Pitfall 1 avoidance: no NaN-filled columns when disabled)"
    - "Effective-Override parameters down the call stack (None = use config default; override shrinks DD threshold / stop-loss multiplier at the use-site, never mutates config)"

key-files:
  created: []
  modified:
    - strategies/mdm_hybrid/macro_filter.py
    - strategies/mdm_hybrid/position_manager.py
    - strategies/mdm_hybrid/stop_loss.py
    - strategies/mdm_hybrid/mdm_hybrid_engine.py

key-decisions:
  - "MacroFilter.apply() uses a lazy V2MarketState import at function scope (not module top) to guard against future circular-dep refactors — position_manager.py does not import macro_filter today, but the defensive scoping keeps the contract robust"
  - "BUY-branch DD elif restructured as nested if/elif inside an else — logically identical control flow (stop_loss > DD > MA10) but now resolves dd_threshold once via an override-or-default pattern so the comparison is byte-identical to pre-Phase-44 when effective_dd_threshold is None"
  - "VETO_SELL handler placed AFTER IndicatorFilter block (D-08 ordering) not before — macro regime is the OUTER policy layer; even if IndicatorFilter CONFIRMs a SELL, MacroFilter can rollback. Restore-from-snapshot mirrors the existing IndicatorFilter VETO branch (lines 454-457)"
  - "INSERTION 6 includes a snapshot is not None guard that silently no-ops VETO_SELL when two_phase_enabled=False — this is the documented fallback for an unsupported configuration (macro on + two_phase off). Crash-proof acceptance test verifies the engine does not raise NameError in this edge case"
  - "Top-level import of add_macro_columns + MacroFilter + MacroVerdict in mdm_hybrid_engine.py (not lazy) — macro_filter module has zero side effects at import time (Plan 02 Task 2 verified). Mirrors the existing IndicatorFilter import pattern at line 26. The precompute gate at line 191 remains textually explicit regardless"
  - "Override parameters default to None so byte-exact parity is automatic when MacroFilter is disabled — the new branch's 'else' arm reads the EXACT same field the pre-change code read (self.config.dd_cash_threshold, self.config.stop_loss_max_multiplier). This is the Pattern 5 parity invariant from RESEARCH.md"

patterns-established:
  - "Wave 3 integration pattern: a MacroFilter class + override params + engine hooks land TOGETHER in one plan because they are tightly coupled — splitting risks one half landing without the other. This is the lesson from the planner's decision to bundle Tasks 1-3 into Plan 03 rather than 3 separate plans"
  - "Dual-layer D-09 short-circuit is the template for future feature gates that add precomputed columns — engine gate around the helper call + class-internal first-line guard. Both gates required to keep df.equals semantics byte-exact when feature disabled"

requirements-completed: [MACRO-04, MACRO-05]

# Metrics
duration: 94m
completed: 2026-04-23
---

# Phase 44 Plan 03: Engine Integration Summary

**MacroFilter class lands + HybridEngine wired via 6 insertion points + override parameters threaded through position_manager and stop_loss — the D-09 dual-layer parity gate is now live, and the 7 previously-skipped MacroFilter unit tests + 2 parity regression stubs all pass.**

## Performance

- **Duration:** 94 min
- **Started:** 2026-04-23T04:42:32Z
- **Completed:** 2026-04-23T06:16:49Z
- **Tasks:** 3
- **Files modified:** 4 (macro_filter.py, position_manager.py, stop_loss.py, mdm_hybrid_engine.py)
- **Files created:** 0 (all work is extension/modification)

## Accomplishments

- `MacroFilter` class lands in `strategies/mdm_hybrid/macro_filter.py` with D-04 most-restrictive combiner apply() method — first-line D-09 short-circuit when `macro_filter_enabled=False` protects v6.0 parity
- `V2PositionManager.process_day` + `StopLossChecker.check` + `_get_effective_stop_pct` accept None-defaulting override parameters (Pattern 5 effective-override-down-the-stack) — override threshold/multiplier shrinks at use-site when macro signal active; None-default is byte-identical to pre-Phase-44
- `HybridEngine` wired with all 6 insertion points (import, __init__ conditional instantiation, precompute gate, per-row macro_verdict computation, process_day kwarg, VETO_SELL handling after IndicatorFilter)
- All 18 tests in `tests/test_macro_filter.py` now PASS with zero skips (7 previously-skipped MacroFilter class tests now activate)
- Both parity tests in `tests/test_macro_filter_v6_parity.py` PASS — byte-exact DataFrame equality across two fresh macro-off engine runs + no `dxy_z` / `eem_z` / `sbv_regime` columns leak when feature disabled
- Smoke tests: macro-on + two_phase-on runs end-to-end on VN30 2020 H1 without crashing, `dxy_z` column present in output; macro-on + two_phase-off does NOT raise NameError (snapshot safeguard line 252 preserved + INSERTION 6 guard correctly no-ops)

## Task Commits

Each task was committed atomically on `main` (single-repo, `--no-verify` per parallel_execution directive; all 3 commits under the 44-03 scope):

1. **Task 1: Append MacroFilter class to macro_filter.py** — `1fa8345` (feat)
   - Adds 109 lines to strategies/mdm_hybrid/macro_filter.py (single file, append only)
   - MacroFilter class with first-line D-09 short-circuit, D-04 combiner, D-12 EEM sign flip, D-13 EEM symmetry
   - All 7 previously-skipped tests in test_macro_filter.py now PASS; 0 skipped; 18/18 total
   - Baseline determinism regression still green (3/3 PASS)

2. **Task 2: Override params on position_manager + stop_loss** — `222a77f` (feat)
   - 43 insertions, 12 deletions across 2 files
   - `effective_dd_threshold: int = None` added to `V2PositionManager.process_day`
   - `effective_max_multiplier: float = None` added to `StopLossChecker.check` + `_get_effective_stop_pct`
   - BUY-branch DD elif restructured to nest inside an else; control flow logically identical, dd_threshold now resolved once via override-or-default pattern
   - Parity invariant verified: None-default preserves byte-identical behavior; override path shrinks max_pct from 0.0375 to 0.0225 when max_multiplier=1.5 vs 2.5
   - 3/3 baseline_determinism PASS, 22/22 hybrid_engine PASS (1 deselected pre-existing), 3/3 mdm_regression PASS

3. **Task 3: Wire MacroFilter into HybridEngine (6 insertions)** — `15bee6b` (feat)
   - 53 insertions across 1 file (mdm_hybrid_engine.py)
   - INSERTION 1: module import of MacroFilter + MacroVerdict + add_macro_columns
   - INSERTION 2: __init__ conditional instantiation (self.macro_filter = MacroFilter(cfg) if enabled else None)
   - INSERTION 3: run() precompute gate around add_macro_columns (D-09 engine half of dual-layer)
   - INSERTION 3.5: snapshot = None safeguard at line 252 preserved (load-bearing for INSERTION 6's guard)
   - INSERTION 4: per-row macro_verdict = self.macro_filter.apply(row, current_state) + effective_max_multiplier passed to stop_loss check
   - INSERTION 5: effective_dd_threshold=macro_verdict.effective_dd_threshold passed to position_manager.process_day
   - INSERTION 6: VETO_SELL handling AFTER IndicatorFilter block — restore-from-snapshot + verdict column = 'MACRO_VETO_SELL'
   - 3/3 baseline_determinism PASS, 2/2 macro_filter_v6_parity PASS, 18/18 macro_filter PASS, 22/22 hybrid_engine PASS (1 deselected pre-existing), 3/3 mdm_regression PASS
   - Smoke test on VN30 2020 H1 + crash-proof test on macro-on+two_phase-off both PASS

## Files Created/Modified

- `strategies/mdm_hybrid/macro_filter.py` — **modified** (appended) — +109 lines — now contains `MacroVerdict` (Plan 02), `add_macro_columns` (Plan 02), `LIQUIDITY_PROXY_PATH` / `SBV_EVENTS_PATH` (Plan 02), PLUS the new `MacroFilter` class with `apply()` method (Plan 03)
- `strategies/mdm_hybrid/position_manager.py` — **modified** — +16 lines, -4 lines — `effective_dd_threshold` param added; BUY-branch DD elif restructured
- `strategies/mdm_hybrid/stop_loss.py` — **modified** — +18 lines, -8 lines — `effective_max_multiplier` param added to `check` + `_get_effective_stop_pct`; override-or-default pattern
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — **modified** — +53 lines — all 6 insertion points landed; dual-layer D-09 gate live

### Final symbol list of macro_filter.py (Task 1 verification)

```
47:class MacroVerdict:
75:    def pass_through(cls) -> "MacroVerdict":
83:    def is_pass(self) -> bool:
92:def add_macro_columns(
213:class MacroFilter:
239:    def __init__(self, config):
248:    def apply(self, row, current_state) -> MacroVerdict:
```

## Decisions Made

See frontmatter `key-decisions` for the 6 decisions taken during execution. Highlights:

1. **Lazy V2MarketState import inside MacroFilter.apply** — defensive guard against future circular-dep refactors
2. **BUY-branch restructure as nested if/elif inside else** — logically identical control flow; dd_threshold resolved once via override-or-default pattern so comparison stays byte-identical when override is None
3. **VETO_SELL placed AFTER IndicatorFilter block (D-08 order)** — macro regime is OUTER policy layer; even IndicatorFilter CONFIRM can be rolled back
4. **snapshot is not None guard in INSERTION 6** — crash-proof fallback for macro-on+two_phase-off (unsupported configuration; silent no-op documented)
5. **Top-level import of macro_filter symbols** — macro_filter module has zero side effects at import; mirrors IndicatorFilter import pattern; precompute gate remains textually explicit
6. **Override params default to None** — byte-exact parity is automatic; else-arm reads same config field pre-Phase-44 read (Pattern 5 parity invariant)

## Deviations from Plan

**None — plan executed exactly as written.** All 3 tasks landed as specified in the PLAN action blocks. The 6 insertion points map one-to-one to the PLAN's INSERTION 1..6 specifications. No auto-fixes needed.

Baseline determinism, macro_filter unit tests, macro_filter_v6_parity regression, hybrid_engine tests, and mdm_regression tests all PASS — no behavioral drift introduced. The single pre-existing `test_hybrid_matches_v2_on_nasdaq` failure (documented in Plan 02's `deferred-items.md`) remains out-of-scope — deselected from the hybrid_engine test run; verified unchanged by this plan via the Plan 02 pre-existing confirmation.

## Issues Encountered

- **None.** The plan's explicit line numbers in the `<interfaces>` section exactly matched the live file state at execution start (verified 2026-04-23). All 6 insertion points landed cleanly without line-number drift.
- Pre-existing `test_hybrid_matches_v2_on_nasdaq` failure on NASDAQ hybrid composition remains documented as out-of-scope in `.planning/phases/44-macro-filter-module/deferred-items.md` — deselected from the Plan 03 test run to isolate the regression signal.

## User Setup Required

None — Plan 44-03 is pure code integration work. No external services, no environment variables, no dashboard configuration, no data regeneration. The canonical CSVs (`data/vn_liquidity_proxy.csv`, `data/sbv_policy_events.csv`) are already frozen from Phase 43.

## Known Stubs

**None.** All 7 previously-skipped tests in `tests/test_macro_filter.py` now PASS (no `@pytest.mark.skipif` fires). The 2 parity tests in `tests/test_macro_filter_v6_parity.py` now meaningfully exercise the engine path (previously they would have mechanically passed even without engine integration). Plan 44-04 extends the parity tests with byte-exact signal-log equality assertions against the reconciled Phase 42 baseline JSON — but THIS plan closes MACRO-04 and MACRO-05 as integration-complete.

No stubbed implementations, no TODO markers, no placeholder data flows. The engine end-to-end path with `macro_filter_enabled=True` is LIVE and verified via smoke tests.

## Pytest evidence (captured during execution)

- `tests/test_macro_filter.py`: **18 passed in 0.21s** (all 7 previously-skipped tests now PASS)
- `tests/test_macro_filter_v6_parity.py`: **2 passed in 21.26s** (regression mark, macro-off byte-exact parity)
- `tests/test_baseline_determinism.py`: **3 passed in 36.27s** (regression mark, Phase 42 parity target)
- `tests/test_hybrid_engine.py`: **22 passed, 1 deselected in 1297.38s** (pre-existing NASDAQ hybrid failure deselected; documented in Plan 02 deferred-items)
- `tests/test_mdm_regression.py`: **3 passed in 0.87s**

### Smoke tests (manual verification)

- **Macro-on path (macro_filter_enabled=True, two_phase_enabled=True, VN30 2020 H1):**
  - 121 rows processed, `dxy_z` column present in output — PASS
- **Crash-proof test (macro_filter_enabled=True, two_phase_enabled=False, VN30 2024 Q1):**
  - Engine runs without raising NameError — INSERTION 6's `snapshot is not None` guard correctly no-ops; line 252's `snapshot = None` safeguard preserved — PASS
- **Override path verification (stop_loss):**
  - `pct_default=0.0375` (max_mult=2.5) vs `pct_override=0.0225` (max_mult=1.5) — override correctly shrinks the cap — PASS

## Resolution of RESEARCH.md Open Questions

The plan's `<output>` section requested confirmation of 3 open questions. All 3 are resolved:

- **Q1 (VETO_SELL safe when two_phase=False?):** Handled via `snapshot is not None` guard at INSERTION 6 — silent no-op for unsupported config (macro-on + two_phase-off). Crash-proof acceptance test verifies no NameError is raised.
- **Q2 (SBV decay calendar vs business days?):** Calendar days (spec §4.4 verbatim; already implemented in Plan 02 Task 2 helper via `(row_date - effective_date).dt.days <= sbv_decay_days`).
- **Q3 (sbv_days_since_event column?):** YES, included in helper output (Plan 02 Task 2 produced the column; this plan does not consume it but leaves it for Phase 45 grid-search diagnostics).

## Note for Plan 44-04

The parity test in `tests/test_macro_filter_v6_parity.py` now MEANINGFULLY exercises the engine path — two fresh macro-off engine runs produce byte-exact equal results, and `add_macro_columns` is actually skipped (no schema pollution). Plan 44-04 extends the parity coverage with:

- Byte-exact signal-log equality vs `output/v10_reconciled_baseline.json` (the Phase 42 tuple)
- Extended smoke-test coverage for the enabled path on full 2015-2026 VN30 window
- Formal MACRO-04 regression sign-off

Plan 44-03 closes MACRO-04 and MACRO-05 as INTEGRATION-COMPLETE. Plan 44-04 closes them as REGRESSION-PROVEN (the full v10.0 VAL-04 parity gate).

## Next Phase Readiness

### Contracts available for Plan 44-04

1. **MacroFilter class** is live (import from `strategies.mdm_hybrid.macro_filter`):
   - `MacroFilter(config).apply(row, current_state) -> MacroVerdict`
2. **HybridEngine** wired end-to-end — `macro_filter_enabled=True` toggles the full pipeline without crashes
3. **Parity invariant** holds: `macro_filter_enabled=False` + `v60_strict_mode=True` yields byte-identical DataFrames to pre-Phase-44

### Blockers for Plan 44-04

None. All Plan 44-03 contracts are available. The parity test is meaningful; the smoke test for enabled path passes; the deferred `test_hybrid_matches_v2_on_nasdaq` failure is out-of-scope (NASDAQ hybrid composition, unrelated to macro filter).

---

## Self-Check: PASSED

### Created/modified files exist

- `strategies/mdm_hybrid/macro_filter.py` — FOUND (322 lines; MacroFilter class at line 213; apply at line 248)
- `strategies/mdm_hybrid/position_manager.py` — FOUND (effective_dd_threshold at line 245)
- `strategies/mdm_hybrid/stop_loss.py` — FOUND (effective_max_multiplier at lines 40, 89)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — FOUND (6 insertion points all verified via grep)
- `.planning/phases/44-macro-filter-module/44-03-engine-integration-SUMMARY.md` — FOUND (this file)

### Commits exist

- `1fa8345` (Task 1: MacroFilter class) — FOUND on main
- `222a77f` (Task 2: override params) — FOUND on main
- `15bee6b` (Task 3: engine wiring) — FOUND on main

### Test evidence

- `tests/test_macro_filter.py` — **18 passed** (no skips)
- `tests/test_macro_filter_v6_parity.py` — **2 passed** (byte-exact parity when disabled)
- `tests/test_baseline_determinism.py` — **3 passed** (Phase 42 parity target preserved)
- `tests/test_hybrid_engine.py` — **22 passed, 1 deselected** (pre-existing out-of-scope failure)
- `tests/test_mdm_regression.py` — **3 passed** (MDM classic regression preserved)
- Smoke test on VN30 2020 H1 macro-on — **PASS** (121 rows, dxy_z column present)
- Crash-proof test macro-on+two_phase-off — **PASS** (no NameError)

---
*Phase: 44-macro-filter-module*
*Plan: 03 — engine-integration*
*Completed: 2026-04-23*
