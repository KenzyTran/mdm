---
phase: 39-refined-distribution-day-module
plan: 03
subsystem: regression-fixture-and-docs
tags: [mdm-hybrid, distribution-day, regression, pytest, parquet-fixture, code-docs-sync]

# Dependency graph
requires:
  - phase: 39-01
    provides: MDMV2Config.refined_dd_* fields with refined_dd_enabled=False default
  - phase: 39-02
    provides: DistributionDayCounter dual-threshold branch + HybridEngine wiring (disabled path = byte-identical v6.0)
  - phase: 38-atr-buffer-zone-module
    provides: regression fixture/test pattern (parquet baseline + pytest), generate_phase38_fixture.py template
provides:
  - tests/fixtures/phase39_v6_baseline_dd_sequence.parquet (2808 rows, 110 DDs from VN30 2015-2026)
  - tests/test_phase39_backward_compat.py (locks DD-04 invariant: refined_dd_enabled=False -> byte-identical DD columns)
  - scripts/generate_phase39_fixture.py (one-shot reproducible fixture generator)
  - docs/rules_mdm_hybrid.md Section XVII (Refined Distribution Day rule, parameters, expiry suppression, sweep preview)
affects: [phase-40-grid-search, phase-42-documentation]

# Tech tracking
tech-stack:
  added: []  # No new libraries -- pure pandas/pytest/parquet
  patterns:
    - "Phase 39 backward-compat regression mirrors Phase 38: parquet baseline + pytest test that fails (not skips) on missing repo asset (D-10/D-11)"
    - "Code-docs sync rule applied across phase: code shipped in 39-01/39-02 documented atomically in 39-03 (CLAUDE.md mandate)"
    - "Engine column naming clarified: plan/decisions reference dd_count_20d conceptually but engine output column is dd_count -- fixture COLS use the actual engine column names"

key-files:
  created:
    - scripts/generate_phase39_fixture.py
    - tests/fixtures/phase39_v6_baseline_dd_sequence.parquet
    - tests/test_phase39_backward_compat.py
  modified:
    - docs/rules_mdm_hybrid.md

key-decisions:
  - "Fixture COLS use dd_count (engine output) instead of dd_count_20d (decision-language). Engine has always exposed the column without the _20d suffix; renaming would have meant a chained refactor that is out of scope for Plan 03."
  - "Regression test asserts row-count invariant first, then per-column boolean/integer equality with explicit row indices in failure messages -- makes diagnosing a regression in CI cheap (top 10 mismatched rows reported)."
  - "Doc Section XVII follows the Phase 38 ATR buffer template (XVI) for symmetry: same subsection ordering (Goal -> Feature gate -> Rule -> Type 2 invariance -> Counting -> Params table -> Indicators -> Expiry -> Backward-compat -> Sweep). Future readers can cross-reference both v9.0 features with identical mental model."

patterns-established:
  - "Per-phase regression fixture pattern: tests/fixtures/phase{NN}_v6_baseline_*.parquet + scripts/generate_phase{NN}_fixture.py + tests/test_phase{NN}_backward_compat.py"
  - "Code-docs sync deferred to terminal plan in phase: when a multi-plan phase touches the same code surface, defer the docs/rules_*.md update to the last plan rather than touching docs in every plan -- avoids merge conflicts and keeps doc updates atomic with completed feature surface"

requirements-completed: [DD-04]

# Metrics
duration: ~14 min
completed: 2026-04-16
---

# Phase 39 Plan 03: Backward-Compat Fixture + Rule Documentation Summary

**Captured the v6.0 DD baseline as a parquet fixture (2808 rows, 110 DDs), shipped a 2-test pytest regression that locks DD-04 byte-identical invariant when `refined_dd_enabled=False`, and added Section XVII to docs/rules_mdm_hybrid.md documenting the full refined DD rule per CLAUDE.md Code-Docs Sync Rule.**

## Performance

- **Duration:** ~14 min (start 2026-04-16T04:20:25Z, end 2026-04-16T04:34:37Z)
- **Tasks:** 2
- **Files created:** 3 (script, parquet fixture, regression test)
- **Files modified:** 1 (docs)
- **Tests added:** 2 (`test_refined_dd_disabled_matches_baseline`, `test_phase39_fixture_schema`)
- **Total Phase 39 test count after Plan 03:** 29 tests (2 backward-compat + 11 DD logic + 14 indicators + 2 Phase 38 carryover)

## Accomplishments

- **DD-04 invariant locked.** `tests/test_phase39_backward_compat.py::test_refined_dd_disabled_matches_baseline` runs `HybridEngine(refined_dd_enabled=False)` on VN30 2015-2026 and asserts every row of `is_dd`, `dd_type`, `dd_count` equals the captured baseline fixture. Boolean and integer columns use exact equality (no float tolerance) so any DD-detection regression fails loudly.
- **Fixture is reproducible and committed.** `scripts/generate_phase39_fixture.py` is the canonical generator. Running it on current code produces the exact 2808-row parquet (110 DD days: 109 Type 1 + 1 Type 2) checked in at `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet`.
- **Test fails (not skips) on missing assets.** Per D-10/D-11, missing VN30 CSV triggers `pytest.fail` with a clear message — a SKIP is not a pass of DD-04. The fixture file existence is also asserted before any other check so a missing parquet produces an immediate `AssertionError`.
- **Docs synced atomically (CLAUDE.md mandate).** `docs/rules_mdm_hybrid.md` Section XVII covers: feature gate semantics, dual-threshold rule, Type 2 invariance, DD counting unchanged, parameters table (6 fields with defaults), indicator columns + their gating, dual-layer expiry suppression, backward-compat invariant, and Phase 40 sweep preview. Section follows the Phase 38 ATR buffer template (XVI) for symmetry.
- **No regressions.** All prior tests still green: 14 Phase 39 indicators, 11 Phase 39 DD logic, 2 Phase 38 backward-compat. Total 29 passed in 13.78s.

## Task Commits

Each task committed atomically:

1. **Task 1: v6.0 DD baseline fixture + backward-compat regression** — `e713624` (test)
2. **Task 2: Section XVII refined DD rule docs** — `ba1ac02` (docs)

_No TDD RED→GREEN split for Task 1: the regression test by definition required the fixture to exist first, so the fixture was generated and the test written + verified in a single commit. Task 2 is pure docs._

## Files Created/Modified

- `scripts/generate_phase39_fixture.py` — one-shot generator: loads VN30 2015-2026, runs `HybridEngine(MDMV2Config(refined_dd_enabled=False))`, captures `[date, is_dd, dd_type, dd_count]` to parquet. Reproducible and idempotent.
- `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet` — 2808-row × 4-col baseline fixture. Type breakdown: 0=2698 (no DD), 1=109 (Type 1 heavy selling), 2=1 (Type 2 stalling).
- `tests/test_phase39_backward_compat.py` — 2 tests: full backward-compat against baseline + fixture schema validation.
- `docs/rules_mdm_hybrid.md` — appended Section XVII (98 lines) covering refined DD rule end-to-end.

## Decisions Made

- **Use `dd_count` not `dd_count_20d` in fixture COLS.** Plan/decision language used `dd_count_20d` conceptually, but the actual engine output column is `dd_count` (no suffix). Renaming the engine column would have been a chained refactor across `position_manager`, signal log code, and any consumer notebooks — out of Plan 03 scope. The fixture and test use the actual column name; the doc Section XVII clarifies this naming explicitly.
- **Boolean/integer exact equality (no float tolerance).** `is_dd` (bool), `dd_type` (int), `dd_count` (int) are all discrete. Float tolerance would silently permit a regression that flips `dd_type` from 1→2 or `dd_count` from 4→5 (which is the difference between "stay BUY" and "trigger SELL" for the 5DD threshold). Test asserts byte-exact equality with row-index reporting in failure messages.
- **Docs Section XVII mirrors Phase 38 Section XVI structure.** Same subsection ordering (Goal → Feature gate → Rule → Type 2 invariance → Counting → Params → Indicators → Expiry → Backward-compat → Sweep). Future maintainers reading both v9.0 features get identical mental models, and the doc reads as a coherent v9.0 ruleset rather than two ad-hoc additions.
- **Single commit for Task 1 (no TDD split).** Task 1 is intrinsically "fixture-first" — the regression test cannot be written until the fixture exists. Splitting RED commit (failing test, no fixture) → GREEN commit (fixture, test passes) would have added noise without value because there is no implementation behavior being driven by the test. Both files plus the generator script land together in `e713624`.

## Deviations from Plan

None of substance. The plan's `<action>` block already noted that the engine's actual column name is `dd_count` (not `dd_count_20d`) and instructed to use whatever the engine produces — implementation matched verbatim. No Rule 1/2/3 auto-fixes triggered. No architectural questions surfaced.

## Issues Encountered

None. Fixture generation completed in ~5s, regression test passes in <5s, full test suite (29 tests) passes in 13.78s.

## User Setup Required

None — pure code/docs change, no external service configuration.

## Next Phase Readiness

- **Phase 40 (Grid Search) ready.** All infrastructure for the DD sweep is in place:
  - 6 parameter dimensions exposed on `MDMV2Config` with validated bounds
  - Engine wiring tested in both enabled/disabled modes
  - Backward-compat regression locks the disabled baseline
  - Documentation describes the sweep grid (54 combos: 6 × 3 × 3) for Phase 40 to consume
- **Phase 42 (Documentation) ready.** `docs/rules_mdm_hybrid.md` is now current through v9.0 — Section XVI (ATR buffer) + Section XVII (refined DD) cover both whipsaw-reduction features. Phase 42 will only need to add post-sweep results (locked params + A/B + walk-forward) rather than describe the rules from scratch.
- **No blockers.** All Plan 03 acceptance criteria met:
  - Fixture exists, 2808 rows >> 100 ✓
  - Generator script runnable ✓
  - Regression test contains `test_refined_dd_disabled_matches_baseline` ✓
  - Regression test contains `test_phase39_fixture_schema` ✓
  - Regression test contains `refined_dd_enabled=False` ✓
  - Regression test contains `pytest.fail` for missing data (not pytest.skip) ✓
  - `uv run pytest tests/test_phase39_backward_compat.py -x` exits 0 ✓
  - All 8 docs content checks pass ✓
  - Phase 38 regression still green (no side effects) ✓

## Self-Check: PASSED

- File `scripts/generate_phase39_fixture.py`: FOUND
- File `tests/fixtures/phase39_v6_baseline_dd_sequence.parquet`: FOUND
- File `tests/test_phase39_backward_compat.py`: FOUND
- File `docs/rules_mdm_hybrid.md` (Section XVII added): FOUND
- Commit `e713624` (Task 1: fixture + regression test): FOUND
- Commit `ba1ac02` (Task 2: docs Section XVII): FOUND
- `uv run pytest tests/test_phase39_backward_compat.py -x -v`: 2 passed
- `uv run pytest tests/test_phase39_dd_logic.py tests/test_phase39_indicators.py -x`: 25 passed (no regression)
- `uv run pytest tests/test_phase38_backward_compat.py -x`: 2 passed (no regression)
- All 8 documentation content checks (Refined DD title, refined_dd_enabled, refined_dd_large_drop, refined_dd_small_drop, refined_dd_small_vol_percentile, dual-threshold, vol_ma20, vol_top_pct): PASSED

---
*Phase: 39-refined-distribution-day-module*
*Completed: 2026-04-16*
