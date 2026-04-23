---
phase: 44-macro-filter-module
plan: 02
subsystem: testing
tags: [macro-filter, dxy, eem, sbv, merge-asof, dataclass, pytest, vn30, mdm-hybrid]

# Dependency graph
requires:
  - phase: 43-canonical-liquidity-data-pipeline
    provides: data/vn_liquidity_proxy.csv (6-col) + data/sbv_policy_events.csv (5-col) + docs/liquidity_proxy_spec.md
  - phase: 42-baseline-reconciliation
    provides: v60_strict_mode field + tests/test_baseline_determinism.py pattern + output/v10_reconciled_baseline.json
  - phase: 44-macro-filter-module (plan 01)
    provides: rewritten MACRO-05 with 6 canonical threshold field names + ROADMAP SC-5
provides:
  - 10 D-15 macro filter config fields on MDMV2Config (default-off, feature-gated validation)
  - VN30_PRESET + NASDAQ_PRESET extended with all 10 fields explicitly
  - strategies/mdm_hybrid/macro_filter.py with MacroVerdict frozen dataclass + add_macro_columns helper + path constants
  - 12+ unit test stubs + 2 parity regression stubs covering all MACRO-01..05 contracts
  - Robust empty-SBV-CSV handling in add_macro_columns (defensive fix)
affects:
  - 44-03 (engine-integration) — consumes MacroVerdict + add_macro_columns, lands MacroFilter class + engine/position_manager/stop_loss wiring
  - 44-04 (parity-regression-signoff) — extends tests/test_macro_filter_v6_parity.py with byte-exact signal-log assertions
  - 45 (walk-forward-grid) — grid-searches the 10 D-15 config fields
  - 46 (a-b-oos-validation) — uses test_macro_filter_v6_parity.py as the VAL-04 parity gate

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen dataclass with orthogonal fields for policy stacking (MacroVerdict pattern — D-04)"
    - "merge_asof(direction='backward') + z-score-after-merge for no-look-ahead enrichment"
    - "Feature-gated __post_init__ validation (Phase 39 D-06 precedent extended to 10 fields)"
    - "Test stubs with pytest.mark.skipif guarding class-dependent tests (Wave 2 → Wave 3 handoff)"

key-files:
  created:
    - strategies/mdm_hybrid/macro_filter.py
    - tests/test_macro_filter.py
    - tests/test_macro_filter_v6_parity.py
    - .planning/phases/44-macro-filter-module/deferred-items.md
  modified:
    - strategies/mdm_hybrid/config.py

key-decisions:
  - "MacroVerdict is a frozen dataclass (not enum) because D-04 stacking requires multiple independent tightening policies simultaneously — orthogonal fields veto_sell / effective_dd_threshold / effective_stop_loss_max_multiplier carry that orthogonality; a single-value enum cannot"
  - "add_macro_columns pipeline order is load-bearing per docs/liquidity_proxy_spec.md §5: (1) merge_asof(backward) proxy → VN30 dates, (2) rolling z-score AFTER merge on VN30-indexed DataFrame (trap #4 guard), (3) SBV merge with +1 BusinessDay effective_date shift (trap #2 guard) then N-day decay to neutral"
  - "Both VN30_PRESET and NASDAQ_PRESET carry all 10 D-15 fields explicitly — no inheritance, no defaults-fall-through — so Pitfall 6 (forgetting one preset) is mechanically unreachable and parity is obvious from the constructor literal"
  - "MacroFilter class DELIBERATELY deferred to Plan 03 alongside engine/position_manager/stop_loss wiring — landing the class here would be dead code per PLAN Task 2 action note; Plan 03 adds .apply() with the D-04 combiner and the integration hooks"
  - "Empty-SBV-CSV defensive short-circuit added to add_macro_columns (Rule 2 auto-fix) — pd.read_csv on empty file returns object dtypes, and BusinessDay(1) on empty datetime Series collapses to float64 which breaks merge_asof dtype alignment; short-circuit to all-neutral regime when len(sbv) == 0 keeps the helper robust for test fixtures and future edge cases without touching the production 12-row path"
  - "Feature-gated validation in MDMV2Config.__post_init__ fires 10 assertions only when macro_filter_enabled=True (Phase 39 D-06 precedent extended): sign conventions on all 4 z-thresholds, positivity on 3 window/decay fields + dxy_tightening_dd_threshold, and sbv_tightening_stop_loss_max_multiplier ≤ stop_loss_max_multiplier — ensures Phase 45 grid search cannot produce physically meaningless combinations when feature ON"

patterns-established:
  - "Wave 2 foundation pattern: land dataclass + helper + test stubs BEFORE landing the integration class (Plan 03). Test stubs use pytest.mark.skipif against hasattr(module, 'MacroFilter') so the suite never breaks on module-level imports even before Plan 03 lands."
  - "Multi-preset D-15 field block: when a feature adds N config fields, both VN30_PRESET and NASDAQ_PRESET receive the block as an explicit comment-delimited section appended at the end of the constructor before the `name` kwarg — keeps diff readable and future presets obvious"
  - "Spec-driven helper comment style: each step in add_macro_columns cites the load-bearing spec section (§5.3, §6 trap #N) so future maintainers understand WHY the merge direction / timing / shift is critical (not just what it does)"

requirements-completed: [MACRO-01, MACRO-02, MACRO-03]

# Metrics
duration: 12m
completed: 2026-04-23
---

# Phase 44 Plan 02: Foundation Config Helper Stubs Summary

**10-field D-15 macro filter config block + MacroVerdict frozen dataclass + add_macro_columns no-look-ahead helper + 12+ test stubs landing the Plan 03 foundation without touching the engine**

## Performance

- **Duration:** 12 min 11 s
- **Started:** 2026-04-23T04:25:40Z
- **Completed:** 2026-04-23T04:37:51Z
- **Tasks:** 3
- **Files modified:** 1 (config.py)
- **Files created:** 4 (macro_filter.py, test_macro_filter.py, test_macro_filter_v6_parity.py, deferred-items.md)

## Accomplishments

- All 10 D-15 macro filter config fields present on `MDMV2Config` + both presets (VN30, NASDAQ) with documented defaults and feature-gated validation
- `strategies/mdm_hybrid/macro_filter.py` created with `MacroVerdict` frozen dataclass, `add_macro_columns` helper (verbatim from RESEARCH §Common Operation 1), and path constants — honors docs/liquidity_proxy_spec.md §5 merge contract + §6 look-ahead traps
- Test scaffolding lands with 11 tests passing immediately (Task 1+2 coverage) and 7 tests skipping cleanly until Plan 03 lands the MacroFilter class
- Baseline determinism regression (`tests/test_baseline_determinism.py`) remains green — config additions are default-off and inert, no drift introduced

## Task Commits

Each task was committed atomically on `main` (single-repo, no branch per config.json `branching_strategy: none`):

1. **Task 1: Append D-15 field block to MDMV2Config + extend BOTH presets** — `3d532c2` (feat)
   - Adds `macro_filter_enabled` + 4 z-thresholds + 3 window/decay fields + 2 policy overrides = 10 fields
   - Gates 10 validation assertions in `__post_init__` on `macro_filter_enabled=True`
   - Extends both presets with the block explicitly (Pitfall 6 guard)

2. **Task 2: Create strategies/mdm_hybrid/macro_filter.py with MacroVerdict + add_macro_columns + path constants** — `15115f9` (feat)
   - 208-line module; 1 class (`MacroVerdict`), 1 function (`add_macro_columns`), 2 path constants
   - `direction='backward'` appears 2x (proxy merge + SBV merge); `BusinessDay(1)` 1x; `rolling(dxy_window_days` 2x (mean + std)
   - `class MacroFilter` absent — deliberately deferred to Plan 03

3. **Task 3: Create tests/test_macro_filter.py + tests/test_macro_filter_v6_parity.py** — `4358ccb` (test)
   - 456-line test module (18 tests: 11 immediate pass, 7 skip-until-Plan-03)
   - 93-line parity module (2 tests: class-level `@pytest.mark.regression`, ready for Plan 03 activation)
   - Bundled a Rule 2 auto-fix in `strategies/mdm_hybrid/macro_filter.py` for empty-SBV-CSV robustness

## Files Created/Modified

- `strategies/mdm_hybrid/config.py` — **modified** — appended 10-field D-15 macro filter block + gated `__post_init__` validation + extended both VN30_PRESET and NASDAQ_PRESET explicitly (+70 lines)
- `strategies/mdm_hybrid/macro_filter.py` — **created** — 208 lines — `MacroVerdict` frozen dataclass + `add_macro_columns` no-look-ahead helper + `LIQUIDITY_PROXY_PATH` / `SBV_EVENTS_PATH` path constants
- `tests/test_macro_filter.py` — **created** — 456 lines — 18 unit-test stubs covering MACRO-01..05 contracts with synthetic mini-fixtures inline (Phase 42 D-18 precedent)
- `tests/test_macro_filter_v6_parity.py` — **created** — 93 lines — 2 parity regression stubs with class-level `@pytest.mark.regression`, `v60_strict_mode=True` override (Pitfall 8 guard), ready to activate when Plan 03 wires the engine
- `.planning/phases/44-macro-filter-module/deferred-items.md` — **created** — tracks the pre-existing `test_hybrid_matches_v2_on_nasdaq` failure verified via `git stash` as not introduced by this plan

## Decisions Made

See frontmatter `key-decisions` for the 6 decisions taken during execution. Highlights:

1. **MacroVerdict as frozen dataclass** (not enum) — D-04 stacking requires orthogonal fields
2. **Pipeline order in add_macro_columns is load-bearing** — merge → z-score (post-merge per §5.3) → SBV shift-then-merge; any reordering breaks the no-look-ahead contract
3. **Both presets explicit** — Pitfall 6 unreachable
4. **MacroFilter class deferred to Plan 03** — avoids dead code in HEAD between waves
5. **Empty-SBV-CSV defensive guard** (Rule 2) — edge case revealed by synthetic test fixtures
6. **Feature-gated validation** — Phase 39 D-06 precedent extended to 10 fields

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Empty SBV CSV dtype mismatch in add_macro_columns**
- **Found during:** Task 3 (running test_macro_filter.py the first time)
- **Issue:** Synthetic test fixtures with zero SBV events write an empty CSV. `pd.read_csv` on an empty file produces object dtypes across all columns; the `pd.tseries.offsets.BusinessDay(1)` shift on the empty datetime Series returns float64 (NaN); `pd.merge_asof` then raises `MergeError: incompatible merge keys [0] dtype('<M8[ns]') and dtype('float64')` when attempting to align the left (VN30 date, datetime64) and right (empty effective_date, float64) keys.
- **Root cause:** The helper implicitly assumed the SBV CSV always has ≥1 row, which holds for the production 12-row file but not for test fixtures or the theoretical future-empty-state case.
- **Fix:** Added a `if len(sbv) == 0: return merged with all-neutral regime` short-circuit in `add_macro_columns` BEFORE the BusinessDay shift. Writes `sbv_regime='neutral'` across the whole VN30 DataFrame and returns `sbv_days_since_event` as an `Int64` NA column. Does not change behavior for the production CSV (len > 0 → falls through to the normal pipeline).
- **Files modified:** `strategies/mdm_hybrid/macro_filter.py` (+11 lines — the short-circuit block)
- **Verification:** All 11 immediately-runnable tests pass on first try after the fix, including `test_dxy_zscore_known_date` and `test_eem_zscore_known_date` which use empty SBV fixtures. Production path (loads the real 12-row `data/sbv_policy_events.csv`) unchanged — verified indirectly because baseline determinism regression remains green.
- **Committed in:** `4358ccb` (bundled with Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 2 missing critical functionality)
**Impact on plan:** Zero scope creep. The fix is defensive robustness for an edge case (empty events file) that any real-world macro filter helper must handle; deferring it would have forced every future test to use a placeholder fake event. No change to the production semantics.

## Issues Encountered

- **Pre-existing `tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq` failure** — discovered while running the full hybrid_engine test suite as a smoke check after Task 1. Verified pre-existing via `git stash` (same failure at `e95fc07`), documented in `.planning/phases/44-macro-filter-module/deferred-items.md` as out-of-scope (Scope Boundary rule — only auto-fix issues DIRECTLY caused by current task's changes). Not a regression from the 10 config-field additions because `macro_filter_enabled=False` is the new default and all validation is gated behind it.

- **Line ending warnings from git** — the Windows CRLF/LF autoconverter warns on the new `.py` files during `git add`, but the files are committed and persistent. No action required.

## User Setup Required

None — Plan 44-02 is a pure code/config/test foundation. No external services, no environment variables, no dashboard configuration.

## Known Stubs

Five stubs were introduced deliberately with `@pytest.mark.skipif` guards, all documented in the test file:

- `test_short_circuit_when_disabled` (MACRO-04 / D-09) — needs `MacroFilter` class from Plan 03
- `test_dxy_easing_vetoes_sell` (MACRO-05 / D-01) — needs Plan 03
- `test_dxy_tightening_lowers_dd` (MACRO-05 / D-02) — needs Plan 03
- `test_sbv_tightening_shrinks_stop_loss` (MACRO-05 / D-03) — needs Plan 03
- `test_most_restrictive_combiner` (MACRO-05 / D-04) — needs Plan 03
- `test_d04_cautionary_wins` (MACRO-05 / D-04) — needs Plan 03
- `test_eem_easing_vetoes_sell` (MACRO-05 / D-13) — needs Plan 03

Plus `tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity` (both tests) — need Plan 03 engine integration to make the parity invariant meaningful.

**Resolution:** Plan 44-03 lands `MacroFilter` class + engine/position_manager/stop_loss wiring, which activates all 7 class-dependent tests AND the 2 parity tests. Plan 44-04 extends the parity tests with byte-exact signal-log equality assertions. This is the **documented Wave 2 → Wave 3 handoff** — not accidental stubs.

## Next Phase Readiness

### Contracts available for Plan 44-03

1. **10 config fields** on `MDMV2Config` (import from `strategies.mdm_hybrid.config`):
   - `macro_filter_enabled`, `dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `eem_easing_z_threshold`, `eem_tightening_z_threshold`, `dxy_window_days`, `eem_window_days`, `sbv_decay_days`, `dxy_tightening_dd_threshold`, `sbv_tightening_stop_loss_max_multiplier`

2. **`MacroVerdict` frozen dataclass** (import from `strategies.mdm_hybrid.macro_filter`):
   - 3 fields (`veto_sell`, `effective_dd_threshold`, `effective_stop_loss_max_multiplier`)
   - Classmethod `pass_through()` (D-09 short-circuit sentinel)
   - Instance method `is_pass()` (invariant check)

3. **`add_macro_columns(df, ...)` helper** (import from `strategies.mdm_hybrid.macro_filter`):
   - Returns DataFrame with `dxy_z`, `eem_z`, `sbv_regime`, `sbv_days_since_event` columns appended
   - Robust to empty SBV CSV edge case (returns all-neutral regime)
   - No-look-ahead enforced per spec §5 + §6

4. **Path constants**: `LIQUIDITY_PROXY_PATH`, `SBV_EVENTS_PATH` (use as test-fixture overrides or defaults)

### Plan 03 scope

Plan 44-03 implements:
- `MacroFilter` class with `.apply(row, current_state) → MacroVerdict` — the D-04 most-restrictive combiner logic
- `HybridEngine.run()` hook — calls `add_macro_columns(df)` when `macro_filter_enabled=True`, iterates the filter in-loop after IndicatorFilter (D-08 ordering)
- `V2PositionManager.process_day()` — consumes `effective_dd_threshold` override from the verdict
- `StopLossChecker` — consumes `effective_stop_loss_max_multiplier` override from the verdict

### Blockers for Plan 44-03

None. All Plan 44-02 contracts are available, baseline determinism is green, and the 7+2 stub tests are ready to activate on Plan 03 landing.

---

## Self-Check: PASSED

### Created files exist

- `strategies/mdm_hybrid/macro_filter.py` — FOUND (208 lines)
- `tests/test_macro_filter.py` — FOUND (456 lines)
- `tests/test_macro_filter_v6_parity.py` — FOUND (93 lines)
- `.planning/phases/44-macro-filter-module/deferred-items.md` — FOUND
- `.planning/phases/44-macro-filter-module/44-02-foundation-config-helper-stubs-SUMMARY.md` — FOUND (this file)

### Commits exist

- `3d532c2` (Task 1: config) — FOUND on main
- `15115f9` (Task 2: macro_filter.py) — FOUND on main
- `4358ccb` (Task 3: tests + empty-SBV fix) — FOUND on main

### Verification

- `uv run pytest tests/test_macro_filter.py -v` → 11 passed, 7 skipped (expected skips until Plan 03)
- `uv run pytest tests/test_baseline_determinism.py -x -m regression` → 3 passed (no regression from Plan 02 additions)
- `uv run python -c "from strategies.mdm_hybrid.config import MDMV2Config; m = MDMV2Config(); print(m.macro_filter_enabled, m.dxy_easing_z_threshold, m.sbv_decay_days)"` → `False -1.0 90` (D-15 defaults correct)
- `uv run python -c "import pandas as pd; from strategies.mdm_hybrid.macro_filter import add_macro_columns; print(list(add_macro_columns(pd.DataFrame({'date': pd.date_range('2020-01-01', periods=30, freq='B')})).columns))"` → `['date', 'dxy_z', 'eem_z', 'sbv_days_since_event', 'sbv_regime']` (helper runs end-to-end on real production CSVs)

---
*Phase: 44-macro-filter-module*
*Plan: 02 — foundation-config-helper-stubs*
*Completed: 2026-04-23*
