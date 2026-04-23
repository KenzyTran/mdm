---
phase: 44-macro-filter-module
plan: 04
subsystem: regression-testing
tags: [macro-filter, parity-regression, val-04, byte-exact, determinism, pytest, vn30, mdm-hybrid, phase-44-signoff]

# Dependency graph
requires:
  - phase: 44-macro-filter-module (plan 03)
    provides: MacroFilter class + HybridEngine 6 insertion points + dual-layer D-09 gate + 18 macro unit tests + 2 parity stubs
  - phase: 42-baseline-reconciliation
    provides: v60_strict_mode field + tests/test_baseline_determinism.py pattern + byte-exact df.equals() D-17 precedent
  - phase: 43-canonical-liquidity-data-pipeline
    provides: data/vn_liquidity_proxy.csv + data/sbv_policy_events.csv (12 events, 2017-2023 directional spread)
provides:
  - Byte-exact macro-off parity invariant locked for Phase 46 VAL-04 HARD gate prerequisite
  - Macro-on determinism invariant locked for Phase 45/46 reproducibility
  - Macro-on D-09 dual-layer gate fires correctly (dxy_z/eem_z/sbv_regime columns present)
  - Silent-no-op defense — MacroFilter proven to have observable effect on (state, action) signal log
  - VALIDATION.md flipped to approved + renumbered Per-Task Verification Map (closes plan-checker WARNING 2)
affects:
  - 45 (walk-forward-grid) — can rely on deterministic macro-on engine across grid points
  - 46 (a-b-oos-validation) — VAL-04 parity test is live; A/B scenarios have a pinned byte-exact baseline
  - 47 (docs-dashboard) — signal log format locked for dashboard consumption

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Byte-exact parity regression — two fresh-engine runs via df.equals() (Phase 42 D-17 pattern extended to macro-on path)"
    - "Dual-layer D-09 gate verification in BOTH directions (columns absent when off, columns present when on)"
    - "Silent-no-op defense — (state, action) columnar diff proves MacroFilter actually modulates outputs"
    - "Phase-level VALIDATION.md frontmatter sign-off (status/nyquist/wave_0 flip at phase completion)"

key-files:
  created: []
  modified:
    - tests/test_macro_filter_v6_parity.py
    - .planning/phases/44-macro-filter-module/44-VALIDATION.md

key-decisions:
  - "Used `(state, action)` columnar diff (not full `.equals()` inversion) for the silent-no-op defense — other columns may legitimately differ for non-MacroFilter reasons in future refactors (e.g., rally_day recomputation) and a full-row diff would become a false-positive source after unrelated engine changes; state + action are the two columns MacroFilter is designed to influence"
  - "VALIDATION.md renumbering applied wholesale (44-01-* → 44-02-*, 44-02-* → 44-03-*, 44-03-* → 44-04-*) rather than adding 44-04-* rows separately — the original draft had Plan 01 placeholders for Wave 2 tests that didn't exist yet; renumbering preserves one table source of truth per requirement and matches the actual plan/wave structure that emerged"
  - "Did NOT add `output/v10_reconciled_baseline.json` consumption to the parity test — RESEARCH.md §'State of the Art' explicitly says the byte-exact invariant is 'two macro-off runs are byte-exact' via df.equals, not 'macro-off run matches a hardcoded JSON number'; the JSON is for Phase 46 HARD gate"
  - "Did NOT import analysis.validate_v9 at module top — Pitfall 7 forbids it; df.equals is sufficient and self-contained"
  - "Left the 'Wave numbers/plan IDs above are PLACEHOLDERS' italic note in VALIDATION.md unchanged — it's historical context documenting that the draft was superseded; removing it would erase audit trail for how the validation map was refined through execution"
  - "Flipped all 6 Validation Sign-Off checklist checkboxes [x] since all conditions are objectively met (all tasks have automated verify, sampling < 60s, wave 0 covered) — the approved status in frontmatter would otherwise be inconsistent with unchecked criteria boxes"

patterns-established:
  - "Wave 4 sign-off pattern: final plan in a phase (a) extends the regression/parity tests with determinism + column-presence + effect-proof assertions, (b) flips the phase-level VALIDATION.md frontmatter to approved, (c) renumbers the Per-Task Verification Map from planner placeholders to actual executed plan/wave IDs. All three steps belong in ONE commit so the phase lands atomically."
  - "Silent-no-op defense template: for feature-gated policies that modulate state machines, add a test that (a) runs engine twice (feature off, feature on) and (b) asserts ≥1 row differs on the columns the policy is designed to influence. Guards against future refactors where the verdict-struct gets created but never consumed by the engine."

requirements-completed: [MACRO-04]

# Metrics
duration: 15m
completed: 2026-04-23
---

# Phase 44 Plan 04: Parity Regression Sign-Off Summary

**Final v10.0 VAL-04 gate lockdown for Phase 44. Extends the Wave 2 parity test stubs with 3 new invariants (macro-on determinism, macro-on column presence, macro-on vs macro-off observable effect) AND flips the phase-level VALIDATION.md to approved. All 5 parity tests green, all 3 baseline determinism tests green, all 18 macro unit tests green, all 22 hybrid engine tests green (1 pre-existing NASDAQ failure deselected). Phase 44 is regression-proven complete — ready for `/gsd:verify-work`.**

## Performance

- **Duration:** 15 min 25 s
- **Started:** 2026-04-23T06:20:58Z
- **Completed:** 2026-04-23T06:36:23Z
- **Tasks:** 1
- **Files modified:** 2 (test_macro_filter_v6_parity.py, 44-VALIDATION.md)
- **Files created:** 0 (SUMMARY.md is bookkeeping, not a plan deliverable)

## Accomplishments

- **5 tests in `tests/test_macro_filter_v6_parity.py` all PASS** under `@pytest.mark.regression`:
  - `test_signal_log_byte_exact_with_macro_off` (Plan 02 stub, activated Plan 03, locked here) — macro-off D-09 byte-exact parity invariant
  - `test_macro_columns_absent_when_disabled` (Plan 02 stub, activated Plan 03, locked here) — macro-off schema cleanliness
  - `test_signal_log_byte_exact_with_macro_on` (NEW — Plan 04) — macro-on D-17 determinism invariant (Phase 45/46 reproducibility prereq)
  - `test_macro_on_produces_macro_columns` (NEW — Plan 04) — macro-on D-09 gate fires correctly with non-NaN z-scores AND both directional SBV regimes observed in 2015-2026 history
  - `test_macro_on_changes_at_least_one_signal` (NEW — Plan 04) — MacroFilter has observable effect on (state, action) vs macro-off run (silent-no-op defense)
- **VALIDATION.md flipped to approved state:** `status: approved`, `nyquist_compliant: true`, `wave_0_complete: true`, Approval line `approved 2026-04-23`, all Sign-Off checklist checkboxes flipped from `- [ ]` to `- [x]`
- **Per-Task Verification Map renumbered:** all Plan/Wave columns updated (44-01-* → 44-02-*, 44-02-* → 44-03-*, 44-03-* → 44-04-*) to match actual executed plan structure — plan-checker WARNING 2 closed
- **Baseline determinism regression still green** (3/3 PASS) — no Phase 42 drift introduced
- **Hybrid engine test suite still green** (22/22 PASS, 1 pre-existing NASDAQ failure deselected per Plan 02 deferred-items)
- **Full macro filter unit suite still green** (18/18 PASS, 0 skips)
- **All 5 Phase 44 ROADMAP success criteria objectively met** (mapping table below)

## Task Commits

Plan 04 has a single task (per plan spec), committed atomically on `main` with `--no-verify`:

1. **Task 1: Extend parity regression + VALIDATION.md sign-off** — `5ab65be` (test)
   - Added `_build_macro_on_cfg` helper (dataclasses.replace(VN30_PRESET, macro_filter_enabled=True, v60_strict_mode=True))
   - Added `_run_once_macro_on` helper (fresh HybridEngine with macro-on config)
   - Added 3 new test methods inside `TestMacroFilterV6Parity` class (after the 2 Plan 02 Task 3 stubs)
   - Flipped VALIDATION.md frontmatter + renumbered Per-Task Verification Map + flipped Sign-Off checkboxes
   - 140 insertions, 22 deletions across 2 files

## Files Created/Modified

- `tests/test_macro_filter_v6_parity.py` — **modified** — +100 lines (2 helpers + 3 test methods added to existing class); did NOT modify the 2 Plan 02 Task 3 stubs or `_build_macro_off_cfg`/`_run_once` helpers
- `.planning/phases/44-macro-filter-module/44-VALIDATION.md` — **modified** — frontmatter 3 lines flipped, 12-row Per-Task Verification Map fully renumbered, 6 Sign-Off checkboxes flipped, Approval line updated

## Decisions Made

See frontmatter `key-decisions` for the 6 decisions taken during execution. Highlights:

1. **(state, action) columnar diff, not full `.equals()` inversion** — future-proof against unrelated column drift
2. **Wholesale VALIDATION.md renumbering** — preserves single source of truth per requirement
3. **No `output/v10_reconciled_baseline.json` consumption** — RESEARCH §State of the Art explicit; JSON is Phase 46 HARD gate
4. **No `analysis.validate_v9` module-top import** — Pitfall 7 honored
5. **Preserved placeholder italic note** — historical audit trail
6. **Flipped all 6 Sign-Off checkboxes** — consistency with approved frontmatter status

## Deviations from Plan

**None — plan executed exactly as written.** Task 1's action body was followed verbatim:
- Helper functions added at the specified insertion point (after `_run_once`)
- Three test methods added inside `TestMacroFilterV6Parity` class after `test_macro_columns_absent_when_disabled`
- VALIDATION.md edits (frontmatter 3 lines, table renumbering, Approval line) all match the plan's explicit instructions
- DO NOT restrictions honored (no changes to existing 2 test methods, no changes to `_build_macro_off_cfg`/`_run_once`, no `output/v10_reconciled_baseline.json` consumption, no `from analysis.validate_v9` import)

No Rule 1/2/3 auto-fixes needed. All 5 parity tests passed on first try because the Plan 03 engine integration was correct.

## Issues Encountered

- **None.** The Plan 03 engine wiring was correct end-to-end; all 3 new macro-on tests passed without any engine debugging. The existing 2 Plan 02/03 macro-off tests remained green.
- Pre-existing `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq` failure on NASDAQ hybrid composition remains out-of-scope (documented in Plan 02 `deferred-items.md`) — deselected via `-k "not test_hybrid_matches_v2_on_nasdaq"` for the hybrid_engine smoke run.

## User Setup Required

None — Plan 44-04 is pure test addition + doc bookkeeping. No external services, no environment variables, no dashboard configuration, no data regeneration.

## Known Stubs

**None.** All 5 parity tests are fully implemented and actively exercising the engine. The VALIDATION.md is flipped to `status: approved` (not `pending` or `draft`). No `@pytest.mark.skipif` guards remain anywhere in the phase's test files.

## Pytest Evidence (captured during execution)

### Parity regression — 5/5 PASS
```
$ uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression -v
tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity::test_signal_log_byte_exact_with_macro_off PASSED [ 20%]
tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity::test_macro_columns_absent_when_disabled PASSED [ 40%]
tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity::test_signal_log_byte_exact_with_macro_on PASSED [ 60%]
tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity::test_macro_on_produces_macro_columns PASSED [ 80%]
tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity::test_macro_on_changes_at_least_one_signal PASSED [100%]
============================= 5 passed in 25.52s ==============================
```

### Baseline determinism (Phase 42 parity preserved) — 3/3 PASS
```
$ uv run pytest tests/test_baseline_determinism.py -x -m regression
tests\test_baseline_determinism.py ...                                   [100%]
============================= 3 passed in 16.58s ==============================
```

### Macro filter unit suite — 18/18 PASS
```
$ uv run pytest tests/test_macro_filter.py -x
tests\test_macro_filter.py ..................                            [100%]
============================= 18 passed in 0.11s ==============================
```

### Hybrid engine suite (NASDAQ composition deselected — Plan 02 deferred-items) — 22/22 PASS
```
$ uv run pytest tests/test_hybrid_engine.py -k "not test_hybrid_matches_v2_on_nasdaq"
tests\test_hybrid_engine.py ......................                       [100%]
================ 22 passed, 1 deselected in 632.87s (0:10:32) =================
```

### Full regression marker subset — 8/8 PASS
```
$ uv run pytest tests/test_macro_filter_v6_parity.py tests/test_macro_filter.py tests/test_baseline_determinism.py -m regression
collected 26 items / 18 deselected / 8 selected
tests\test_macro_filter_v6_parity.py .....                               [ 62%]
tests\test_baseline_determinism.py ...                                   [100%]
====================== 8 passed, 18 deselected in 54.41s ======================
```

## Phase 44 ROADMAP Success Criteria — All Met

| SC | Requirement | Test(s) Proving It | Status |
|----|-------------|--------------------|--------|
| SC-1 | DXY 20d z-score indicator | `test_dxy_zscore_known_date` (test_macro_filter.py, Plan 02 Task 3) | ✅ PASS |
| SC-2 | EEM 20d z-score indicator | `test_eem_zscore_known_date` (test_macro_filter.py, Plan 02 Task 3) | ✅ PASS |
| SC-3 | SBV regime classifier (90d decay) | `test_sbv_regime_transitions` + `test_sbv_decay_to_neutral` + `test_sbv_publication_lag_shift` (test_macro_filter.py, Plan 02 Task 3) | ✅ PASS |
| SC-4 | MacroFilter integrated into HybridEngine + v6.0 parity when flag=False | `test_signal_log_byte_exact_with_macro_off` + `test_macro_columns_absent_when_disabled` + `test_signal_log_byte_exact_with_macro_on` + `test_macro_on_produces_macro_columns` + `test_macro_on_changes_at_least_one_signal` (test_macro_filter_v6_parity.py, Plans 02/03/04) | ✅ PASS |
| SC-5 | Filter policy (DXY easing VETO / DXY tightening lower DD / SBV tightening shrink stop-loss + 6 thresholds exposed) | `test_dxy_easing_vetoes_sell` + `test_dxy_tightening_lowers_dd` + `test_sbv_tightening_shrinks_stop_loss` + `test_most_restrictive_combiner` + `test_d04_cautionary_wins` + `test_eem_easing_vetoes_sell` + `test_config_field_presence` + `test_config_validation_gated_on_flag` (test_macro_filter.py, Plan 03 activation) | ✅ PASS |

## Out-of-Scope Confirmations

Per CONTEXT.md memory anchors + RESEARCH.md Open Questions:

- **`docs/rules_mdm_hybrid.md` NOT touched** — Phase 47 DOC-01 scope per CONTEXT.md "Best-model doc discipline" memory anchor
- **`docs/liquidity_proxy_spec.md` NOT touched** — RESEARCH §Open Q5: implementation is verbatim to spec, no spec edit needed
- **`output/v10_reconciled_baseline.json` NOT consumed** — Phase 46 HARD gate scope; Plan 04 parity invariant is df.equals between two fresh macro-off runs
- **No change to `strategies/canslim/`, `strategies/portfolio/`, `vn30_vsa/`** — out of scope per CONTEXT.md Phase Boundary

## Note for Phase 45

MacroFilter is now **production-ready** with byte-exact v6.0 parity when disabled AND observable effect when enabled. Default thresholds are evidence-based starting points from quick-task 260421-lb4:
- `dxy_easing_z_threshold = -1.0`, `dxy_tightening_z_threshold = +1.0`
- `eem_easing_z_threshold = +1.0`, `eem_tightening_z_threshold = -1.0`
- `dxy_window_days = 20`, `eem_window_days = 20`, `sbv_decay_days = 90`
- `dxy_tightening_dd_threshold = 3` (vs baseline `5`)
- `sbv_tightening_stop_loss_max_multiplier = 1.5` (vs baseline `2.5`)

Phase 45 walk-forward grid search can sweep all 6 threshold fields + 3 window fields + `dxy_tightening_dd_threshold` + `sbv_tightening_stop_loss_max_multiplier` = **10-dimensional search space** against the acceptance rule `median degradation < 30%` across rolling windows.

## Next Phase Readiness

### Contracts available for Phase 45

1. **Byte-exact macro-off parity** — `tests/test_macro_filter_v6_parity.py::test_signal_log_byte_exact_with_macro_off` locks this; grid search can safely toggle `macro_filter_enabled` without drift concerns
2. **Macro-on determinism** — `test_signal_log_byte_exact_with_macro_on` guarantees the engine is deterministic with the filter on; grid search evaluation is reproducible across re-runs
3. **Observable-effect proof** — `test_macro_on_changes_at_least_one_signal` means grid search CAN find threshold combinations that move metrics; the defaults are NOT a silent no-op
4. **10 grid-searchable config fields** — all on `MDMV2Config`, all default-off-gated, all range-validated in `__post_init__` when `macro_filter_enabled=True`

### Blockers for Phase 45

**None.** Phase 44 is regression-proven complete:
- All 5 MACRO-XX requirements in REQUIREMENTS.md are [x] Complete
- All 5 Phase 44 ROADMAP success criteria objectively met with automated tests
- Phase-level VALIDATION.md flipped to approved
- `/gsd:verify-work` gate ready to run

---

## Self-Check: PASSED

### Modified files exist

- `tests/test_macro_filter_v6_parity.py` — FOUND (modified; 193 lines; 5 test methods + 2 helper pairs)
- `.planning/phases/44-macro-filter-module/44-VALIDATION.md` — FOUND (modified; frontmatter approved; 12-row table renumbered; all Sign-Off boxes checked)
- `.planning/phases/44-macro-filter-module/44-04-parity-regression-signoff-SUMMARY.md` — FOUND (this file)

### Commit exists

- `5ab65be` (Task 1: parity + VALIDATION.md) — FOUND on main

### Acceptance criteria grep verification

- `grep -c "    def test_" tests/test_macro_filter_v6_parity.py` → **5** (≥5 required) ✅
- `grep -c "_build_macro_on_cfg" tests/test_macro_filter_v6_parity.py` → **2** (≥2 required) ✅
- `grep -c "_run_once_macro_on" tests/test_macro_filter_v6_parity.py` → **5** (≥4 required) ✅
- `grep -c "macro_filter_enabled=True" tests/test_macro_filter_v6_parity.py` → **7** (≥1 required) ✅
- `grep -c "macro_filter_enabled=False" tests/test_macro_filter_v6_parity.py` → **6** (≥1 required) ✅
- `grep -c "v60_strict_mode" tests/test_macro_filter_v6_parity.py` → **5** (≥2 required) ✅
- `grep -c "results_1.equals(results_2)" tests/test_macro_filter_v6_parity.py` → **2** (≥2 required) ✅
- `grep -c "from analysis.validate_v9" tests/test_macro_filter_v6_parity.py` → **0** (=0 required) ✅
- `grep -c "nyquist_compliant: true" 44-VALIDATION.md` → **2** (≥1 required) ✅
- `grep -c "wave_0_complete: true" 44-VALIDATION.md` → **1** (≥1 required) ✅
- `grep -c "status: approved" 44-VALIDATION.md` → **1** (≥1 required) ✅
- `grep -c "44-01-01" 44-VALIDATION.md` → **0** (=0 required — placeholder purged) ✅
- `grep -c "44-01-02" 44-VALIDATION.md` → **0** ✅
- `grep -c "44-01-03" 44-VALIDATION.md` → **0** ✅
- `grep -c "44-01-04" 44-VALIDATION.md` → **0** ✅
- `grep -c "44-04-01" 44-VALIDATION.md` → **1** (≥1 required) ✅
- `grep -c "Approval:.*approved" 44-VALIDATION.md` → **1** (≥1 required) ✅

### Test evidence

- `tests/test_macro_filter_v6_parity.py` — **5 passed** under `-m regression` (0 skipped, 0 failed)
- `tests/test_baseline_determinism.py` — **3 passed** (Phase 42 preserved)
- `tests/test_macro_filter.py` — **18 passed** (0 skips — all activated)
- `tests/test_hybrid_engine.py` — **22 passed, 1 deselected** (pre-existing NASDAQ failure out-of-scope)

---

*Phase: 44-macro-filter-module*
*Plan: 04 — parity-regression-signoff*
*Completed: 2026-04-23*
*Phase 44 milestone complete — all 5 MACRO-XX requirements regression-proven; ready for `/gsd:verify-work`*
