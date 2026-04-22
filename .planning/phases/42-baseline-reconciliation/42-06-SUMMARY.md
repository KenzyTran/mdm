---
phase: 42-baseline-reconciliation
plan: 06
subsystem: tests
tags: [determinism, regression-test, byte-exact, pytest, hybrid-engine, base-03, downstream-contract, json-schema, co-wave-tolerant]

# Dependency graph
requires:
  - phase: 42-baseline-reconciliation (plan 42-04)
    provides: reconciled-HEAD commit (v60_strict_mode=True preset path) on which determinism must hold; canonical tuple CAGR 11.4700 / SELL 124 / MaxDD -28.1700 as the values byte-exactly repeatable across 3 fresh engines
  - phase: 42-baseline-reconciliation (plan 42-05)
    provides: output/v10_reconciled_baseline.json (schema_version=1, 18 D-12 fields) — guarded by test_reconciled_baseline_json_loadable; co-wave-4 tolerance preserved via pytest.skip when JSON is absent
provides:
  - tests/test_baseline_determinism.py — pytest @pytest.mark.regression class TestBaselineDeterminism with 3 tests totaling 274 lines (byte-exact numeric variance + byte-exact signal log + downstream-JSON regression guard)
  - Byte-exact determinism gate (M5 tightening): CAGR/MaxDD/Sharpe/SELL/transitions len(set(...))==1 across 3 fresh HybridEngine runs
  - pandas-native byte-exact DataFrame equality gate via results_1.equals(results_2) across 2 fresh runs
  - D-14 downstream-JSON regression guard (m4): schema_version==1 + all 18 D-12 field names + Python-type conformance (float/int/str) + reconciliation_outcome in VALID_OUTCOMES tuple — SKIPS gracefully when the JSON is absent (preserves wave-4 parallel-execution legality)
  - Stdout-safe lazy-import pattern for analysis.validate_v9.compute_metrics (orphan-wrapper parking in module-level list prevents pytest capture-teardown ValueError: I/O operation on closed file)
affects: [44 MACRO-04 (v6.0 parity regression precondition — non-determinism in HybridEngine would silently poison the byte-exact signal-log compare), 45 WF-02 (walk-forward median degradation <30% reproducibility — degradation numbers meaningless if engine reruns give different outputs), 46 VAL-02 (HARD gate reproducibility — CAGR ≥ reconciled baseline must hold on every fresh run, not just the one that published the JSON), 46 VAL-04 (byte-exact signal log regression — same determinism precondition as MACRO-04), 43-47 all (D-14 downstream-JSON consumption — any silent shape drift in output/v10_reconciled_baseline.json now surfaces in this pytest suite before consumer phases break)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Byte-exact determinism assertion via len(set(...)) == 1 on floats AND ints — strongest primary gate; D-17's 0.1pp/0.005 threshold numbers retained only as informative fallback text in failure messages so reviewers see observed-spread vs post-mortem-band context"
    - "pandas.DataFrame.equals() as the byte-exact signal-log equality primitive — catches index, column, dtype, and value differences in one assertion (stronger than per-column allclose); mirrors the canonical 'signal log is the source of truth' contract from v6.0 ship"
    - "Class-scoped pytest fixture prepared_df with DataLoader('vn30').load() + build_indicator_dataframe() precomputed once per test class; each test takes .copy() before passing to the engine so fixture state is not mutated across runs"
    - "Co-wave-4 tolerance via pytest.skip when output/v10_reconciled_baseline.json is missing — allows plan 42-06 to commit before OR after plan 42-05 in wave-4 parallel execution; once both are at HEAD, the test runs fully and catches downstream schema drift"
    - "Stdout-preserving lazy import pattern for modules that rewrite sys.stdout at import time: snapshot sys.stdout, perform import, restore snapshot, park the orphan TextIOWrapper in a module-level list to prevent GC-induced close of the shared buffer (fixes pytest's 'ValueError: I/O operation on closed file' during teardown)"
    - "Defensive dataclass-field probe 'v60_strict_mode' in MDMV2Config.__dataclass_fields__ before the replace() call — gates the strict-mode activation only when the field exists, keeping the test resilient to D-07 step-1/step-2/step-3 path variance (if Phase 42-04 had taken the revert path instead of preset-flag, the field wouldn't exist and the test would still run correctly on the reverted-HEAD reconciled preset)"

key-files:
  created:
    - "tests/test_baseline_determinism.py (274 lines; pytest @pytest.mark.regression class TestBaselineDeterminism with 3 tests + 2 module-level helpers + EXPECTED_JSON_TYPES dict + stdout-safe lazy import shim for analysis.validate_v9.compute_metrics; module docstring names the reconciled preset path including v60_strict_mode=True conditional and references output/v10_reconciled_baseline.json reconciliation_outcome field per M2 specificity)"
  modified: []

key-decisions:
  - "M5 byte-exact primary assertions over D-17 threshold assertions. Plan-level decision: spread of 0.0 is the correct determinism gate; any spread > 0 is a bug regardless of whether it's inside a post-mortem threshold. D-17's 0.1pp/0.005 thresholds were the ORIGINAL D-17 contract from 42-CONTEXT.md but were tightened by the planner at plan-write time (M5) to byte-exact. Retained the threshold constants (CAGR_SPREAD_POSTMORTEM, MAXDD_SPREAD_POSTMORTEM, SHARPE_SPREAD_POSTMORTEM) as module-level constants and cite them in assertion failure messages so a reviewer reading a future failure sees both observed-spread AND post-mortem-threshold context in one trace. The threshold constants never gate pass/fail — len(set(...)) == 1 is the sole gate."
  - "Co-wave-4 tolerance for the downstream-JSON guard (m4). Plan 42-05 and plan 42-06 both live in wave 4 of phase 42 per depends_on graphs; they can legally commit in either order under parallel execution. If test_reconciled_baseline_json_loadable hard-required the JSON, 42-06 would be non-executable when run before 42-05 in the same wave. Fixed via pytest.skip with a clear 'plan 42-05 has not committed its artifacts yet' message — the test is self-healing; the next invocation after both plans have committed runs the full downstream-schema regression check. At commit time, plan 42-05 had already completed and the JSON existed, so the test PASSED rather than SKIPPED on first run."
  - "Stdout-safe lazy import of analysis.validate_v9.compute_metrics. The obvious top-of-module `from analysis.validate_v9 import compute_metrics` caused pytest collection to crash with 'ValueError: I/O operation on closed file' because validate_v9.py line 41 does `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` at import time. This rewrites sys.stdout with an orphan wrapper; when the wrapper is eventually GC'd during pytest teardown, its destructor closes the shared underlying buffer that pytest's capture machinery is still holding. Three fixes considered: (1) inline-copy compute_metrics [rejected: violates the canonical-refs 'reuse, don't reinvent' principle], (2) subprocess isolation [rejected: breaks fixture-scoped DataFrame sharing, adds process-spawn cost], (3) stdout-preserving lazy import with wrapper parking [CHOSEN: snapshot sys.stdout, import inside a function body, restore the snapshot, pin the orphan wrapper in a module-level list so it survives GC for the process lifetime]. The fix is documented inline with a multi-paragraph explanation so future maintainers don't naively move the import to module top."
  - "Use MDMV2Config.__dataclass_fields__ probe instead of hasattr. Defensive: the 42-04 fix took the preset-flag path (D-07 step 2) adding a v60_strict_mode field, but future phases might refactor MDMV2Config. Using `'v60_strict_mode' in MDMV2Config.__dataclass_fields__` as the gate is more specific than hasattr (the latter would false-positive on methods/descriptors) and makes the 'strict mode only if available as a dataclass field' semantic intent explicit. Mirrors the defensive getattr(..., 'atr_buffer_enabled', False) pattern already in V2PositionManager."

patterns-established:
  - "Test file references to CANONICAL DOCS by grep-stable phrases: 'reconciliation outcome' grep-matches the M2 acceptance criterion and future-proofs the test against doc-path renames; the module docstring uses 'v60_strict_mode=True iff' as another grep anchor; D-17 post-mortem threshold text appears 4x so grep finds all three metric sites (CAGR/MaxDD/Sharpe fallback) and the module docstring reference with one call. This grep-stability is a test-file maintenance pattern worth reusing for future BASE-class regression tests."
  - "SKIP-tolerant downstream-contract tests for co-wave-parallel plans. When a test in plan X validates an artifact produced by plan Y and X/Y both live in the same wave, the test MUST skip cleanly when the artifact is absent rather than fail. The skip message must be actionable (names the producing plan number) so a reviewer running pytest in mid-wave state can immediately distinguish 'waiting for co-wave plan' from 'genuine regression'. Opposite patterns (hard-require with a depends_on bump) would serialize the wave unnecessarily."
  - "Stdout-safe lazy import for modules with import-time sys.stdout rewrites. General pattern: snapshot sys.stdout → import → restore sys.stdout → park orphan wrapper in a module-level list. Applicable to any test file needing to import analysis/*.py scripts that predate the sys.stdout.reconfigure() pattern introduced in plan 42-01. Documented inline in test_baseline_determinism.py so future maintainers can cross-reference."
  - "Dataclass-field probe via __dataclass_fields__ dict membership is the canonical 'is this a configured dataclass field' check — stricter than hasattr, faster than dataclasses.fields() iteration, and grep-visible (the acceptance-criterion grep literally looks for the exact string 'v60_strict_mode' in MDMV2Config.__dataclass_fields__)."

requirements-completed: [BASE-03]

# Metrics
duration: 20min
completed: 2026-04-22
---

# Phase 42 Plan 06: Engine Determinism Regression Test Summary

**BASE-03 closed with a 274-line pytest regression class containing 3 tests: byte-exact CAGR/MaxDD/Sharpe/SELL/transitions across 3 fresh engines, byte-exact results DataFrame equality across 2 fresh engines, and a co-wave-tolerant downstream-JSON schema+type regression guard for output/v10_reconciled_baseline.json.**

## Performance

- **Duration:** ~20 min (including one stdout-capture debugging iteration — see Deviations)
- **Started:** 2026-04-22T06:41:00Z (approximate, based on wave-4 parallel dispatch)
- **Completed:** 2026-04-22T07:00:29Z
- **Tasks:** 1 / 1
- **Files created:** 1 (tests/test_baseline_determinism.py)
- **Test runtime at reconciled-HEAD:** ~38.67s (under the D-18 60s budget)
- **Tests collected:** 3 (`collected 3 items`)
- **Tests PASSED:** 3 / 3 (test_numeric_variance_across_3_runs, test_signal_log_byte_exact, test_reconciled_baseline_json_loadable — the last one ran fully rather than skipping because plan 42-05's JSON landed at HEAD before this test ran)

## Accomplishments

- **Created `tests/test_baseline_determinism.py` at 274 lines** with a single @pytest.mark.regression class `TestBaselineDeterminism` containing 3 test methods, 2 module-level helpers (`_build_reconciled_cfg`, `_run_once`), 1 stdout-safe lazy-import shim (`_get_compute_metrics` with wrapper-parking), 1 class-scoped fixture (`prepared_df`), and module constants (DATA_START/DATA_END/postmortem-thresholds/RECONCILED_JSON path/EXPECTED_JSON_TYPES dict of 19 fields with expected Python types/VALID_OUTCOMES tuple).

- **M5 byte-exact primary assertions wired and passing.** `test_numeric_variance_across_3_runs` asserts `len(set(cagrs)) == 1`, `len(set(maxdds)) == 1`, `len(set(sharpes)) == 1`, `len(set(sells)) == 1`, `len(set(trans)) == 1` — five byte-exact gates covering float CAGR/MaxDD/Sharpe and integer SELL/transitions across 3 fresh HybridEngine runs. All five passed at reconciled-HEAD on the first run, confirming the engine is deterministic by construction with the current reconciled preset (v60_strict_mode=True, atr_buffer_enabled=False, refined_dd_enabled=False).

- **D-17 thresholds retained as informative fallback messages.** CAGR_SPREAD_POSTMORTEM=0.1pp, MAXDD_SPREAD_POSTMORTEM=0.1pp, SHARPE_SPREAD_POSTMORTEM=0.005 are module constants; each byte-exact assertion failure message includes the observed spread AND the post-mortem threshold value so a future failure trace gives the reviewer both the hard gate context AND the original D-17 sanity-band context in a single line. The phrase "D-17 post-mortem threshold" appears 4× in the file (3 assertion sites + 1 module-docstring reference), satisfying the M5 acceptance grep (`>= 3 matches`).

- **M2 module docstring specificity satisfied.** The module docstring explicitly names the reconciled preset path including the conditional ("Preset used: VN30_PRESET with atr_buffer_enabled=False, refined_dd_enabled=False, and v60_strict_mode=True iff that field exists on MDMV2Config at test time"), references `output/v10_reconciled_baseline.json` and its `reconciliation_outcome` field, and uses the grep-stable phrase "reconciliation outcome" for future doc-grep audits. All three M2 acceptance greps (`reconciliation outcome`, `v60_strict_mode=True iff`) pass with one match each in the docstring region.

- **m4 downstream-JSON regression guard wired and PASSING on first run.** `test_reconciled_baseline_json_loadable` opens `output/v10_reconciled_baseline.json`, asserts `schema_version == 1`, asserts all 18 D-12 field names present, asserts each field's Python type matches the `EXPECTED_JSON_TYPES` dict (7 floats + 4 ints + 7 strings = 18 typed fields, with schema_version as the 19th typed field for a total of 19 dict entries), and asserts `reconciliation_outcome in ('fixed_by_revert', 'fixed_by_preset', 'accepted_drift')`. The co-wave-4 tolerance path via `pytest.skip` was wired in but not exercised at test time — plan 42-05 had already committed its JSON artifact (`fixed_by_preset` outcome, CAGR 11.47, MaxDD -28.17, SELL 124) before this test ran, so the test ran the full shape+type validation and passed.

- **Stdout-safe lazy-import pattern established for future validate_v9.py consumers.** The obvious `from analysis.validate_v9 import compute_metrics` at module top caused pytest collection to crash with "ValueError: I/O operation on closed file" because `analysis/validate_v9.py` line 41 does `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` — the orphan wrapper gets GC'd during pytest teardown and closes the shared underlying buffer that pytest's capture machinery is still holding. Resolved via a stdout-preserving lazy-import helper `_get_compute_metrics()` that: (1) snapshots current sys.stdout, (2) imports inside a function body, (3) restores the snapshot, (4) pins the orphan wrapper in a module-level list (`_ORPHAN_STDOUT_WRAPPER_HOLDER`) to prevent GC-induced buffer close for the rest of the process lifetime. Caches the import result so the side-effect fires at most once per test process. This pattern is documented inline with a multi-paragraph explanation so future maintainers understand why the import is lazy and what breaks if it's moved to module top.

- **All 26 acceptance-criteria greps pass.** Verified inline via `grep -c -F` loop: `@pytest.mark.regression` (1), `class TestBaselineDeterminism` (1), `def test_numeric_variance_across_3_runs` (1), `def test_signal_log_byte_exact` (1), `def test_reconciled_baseline_json_loadable` (1), `reconciliation outcome` (1), `v60_strict_mode=True iff` (1), byte-exact asserts for cagrs/maxdds/sharpes/sells/trans (1 each = 5), `D-17 post-mortem threshold` (4, >= 3 required), postmortem constants (1 each = 3), DATA_START/DATA_END (1 each = 2), `results_1.equals(results_2)` (1), `from analysis.validate_v9 import compute_metrics` (2, the commented hint + the lazy import inside the helper function; plan required >= 1), `build_indicator_dataframe` (2), `two_phase_enabled=True` (1), `filter_enabled=False` (1), `import json` (1, >= 1), `EXPECTED_JSON_TYPES` (3, >= 2), `schema_version` (5, >= 2), `pytest.skip` (1, >= 1), `'v60_strict_mode' in MDMV2Config.__dataclass_fields__` (1).

- **pytest runtime ~38s, well under D-18 budget.** The test class runs the full VN30 2015-2026 engine 5 times (3 in the numeric-variance test + 2 in the signal-log-byte-exact test) plus the JSON-load test which is O(ms). DataLoader + build_indicator_dataframe runs once per class (class-scoped fixture). Total ~38s on the dev machine — comfortably under the D-18 60s budget and 90s acceptance-criteria limit.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/test_baseline_determinism.py with byte-exact regression tests + co-wave-tolerant downstream-JSON guard** — `8c6722b` (test)

_Note: Single-task plan with one atomic commit containing the full 274-line test file. No implementation code outside the test file was needed — the helpers are all test-local, the compute_metrics reuse is via a lazy import that does not mutate analysis/validate_v9.py, and the JSON regression guard reads output/v10_reconciled_baseline.json without modifying it. `--no-verify` was used per the wave-4 parallel-execution instructions to avoid pre-commit hook contention with plan 42-05._

## Files Created/Modified

- `tests/test_baseline_determinism.py` (created, 274 lines) — @pytest.mark.regression class TestBaselineDeterminism containing 3 tests, module docstring with M2 reconciled-preset specificity, module constants (DATA_START='2015-01-05', DATA_END='2026-03-31', CAGR/MAXDD_SPREAD_POSTMORTEM=0.1, SHARPE_SPREAD_POSTMORTEM=0.005, RECONCILED_JSON path, EXPECTED_JSON_TYPES dict with 19 typed fields, VALID_OUTCOMES tuple with 3 canonical labels), 2 helper functions (_build_reconciled_cfg with the v60_strict_mode __dataclass_fields__ probe, _run_once with two_phase_enabled=True/filter_enabled=False), 1 stdout-safe lazy-import shim (_get_compute_metrics with orphan-wrapper parking in _ORPHAN_STDOUT_WRAPPER_HOLDER list), 1 class-scoped prepared_df fixture. Committed in `8c6722b` atomically.

## Decisions Made

- **M5 byte-exact primary assertions retained as hard gate; D-17 thresholds demoted to fallback-message constants.** See Key Decisions section above. Rationale: spread of 0.0 is the correct determinism gate; any non-zero spread indicates non-deterministic engine behavior which is a bug per D-21 regardless of whether it falls inside a post-mortem sanity threshold. The threshold constants are retained in the module namespace and referenced in failure-message f-strings so a reviewer reading a future failure trace sees observed-spread AND post-mortem-threshold context together.

- **Co-wave-4 tolerance via pytest.skip for the downstream-JSON guard.** Implemented the m4 test with an `if not os.path.isfile(RECONCILED_JSON): pytest.skip(...)` guard at the top, with a skip message that explicitly names plan 42-05 as the producing plan. At commit time, plan 42-05's JSON artifact was already at HEAD (the wave-4 parallel scheduler happened to resolve 42-05 before 42-06's commit), so the test ran the full shape+type validation and passed. The skip-tolerant design is preserved so future re-runs in mid-wave state (e.g., a future BASE-class phase that rewrites wave-4 ordering) still work without requiring depends_on bumps.

- **Stdout-safe lazy import of compute_metrics via wrapper parking.** See Key Decisions section above and the inline multi-paragraph explanation in the test file for the full rationale. The alternative paths (inline copy, subprocess isolation) were each rejected in the test file's inline comment; the chosen path (snapshot + import + restore + park-orphan-in-list) is documented with enough detail that future maintainers can reproduce the reasoning.

- **Defensive `'v60_strict_mode' in MDMV2Config.__dataclass_fields__` probe over hasattr.** The probe is grep-visible (literal string match on the acceptance-criterion grep), semantically precise (only matches dataclass fields, not methods/descriptors), and runs in O(1) on the __dataclass_fields__ dict lookup. Resilient against future MDMV2Config refactors that might re-organize the field layout or move the flag elsewhere.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pytest stdout-capture crash during collection when analysis.validate_v9 imported at module top**

- **Found during:** Task 1 (first pytest run after initial file creation)
- **Issue:** `uv run pytest -m regression tests/test_baseline_determinism.py -v` failed at collection time with `ValueError: I/O operation on closed file` in `_pytest/capture.py::snap` during session teardown (`stop_global_capturing`). Zero tests collected. Root cause: `analysis/validate_v9.py` line 41 does `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` at module import time, installing a FRESH TextIOWrapper over the same underlying buffer that pytest's capture machinery is holding. When the orphan wrapper is later GC'd during teardown, its `__del__` closes the buffer, causing pytest's capture-tempfile snap to fail.
- **Fix:** Converted the top-level `from analysis.validate_v9 import compute_metrics` into a stdout-safe lazy import helper `_get_compute_metrics()` that: (1) snapshots current `sys.stdout`, (2) performs the import inside a function body (so the rewrite fires during test execution where pytest can handle it), (3) restores the snapshot immediately after import, (4) parks the orphan wrapper in a module-level list `_ORPHAN_STDOUT_WRAPPER_HOLDER` to prevent GC-induced close of the underlying buffer for the rest of the process lifetime. Caches the import result in a module-level `_VALIDATE_V9_COMPUTE_METRICS` so the side-effect fires at most once per test process.
- **Files modified:** tests/test_baseline_determinism.py (same file — no separate commit; fix was rolled into the Task 1 atomic commit `8c6722b`).
- **Verification:** Re-ran `uv run pytest -m regression tests/test_baseline_determinism.py -v` → `collected 3 items` → all 3 PASSED in 38.67s with exit code 0. Acceptance-criteria grep `from analysis.validate_v9 import compute_metrics` returns 2 matches (the commented-out module-top reference that serves as a documentation hint, plus the actual lazy import inside the helper function body) — satisfies the plan's `>= 1` requirement.
- **Committed in:** `8c6722b` (part of the Task 1 atomic commit — no separate commit, since the deviation was rolled into the same file).

---

**Total deviations:** 1 auto-fixed (1 blocking via stdout-capture compatibility)
**Impact on plan:** The plan anticipated the reuse of `analysis.validate_v9.compute_metrics` (read_first line and the acceptance-criterion grep) but did not anticipate the sys.stdout import-time-rewrite side effect that breaks pytest's capture machinery. The fix is contained within the test file and does not require changes to `analysis/validate_v9.py` (which is referenced as a canonical asset by multiple other phases and should not be mutated for a single consumer). The wave-4 parallel-execution instruction `--no-verify` was followed consistently.

## Issues Encountered

- **validate_v9.py predates the plan-42-01 sys.stdout.reconfigure() pattern.** Plan 42-01 introduced `sys.stdout.reconfigure(encoding='utf-8')` in `analysis/bisect_v10_baseline.py` as the Windows-safe alternative to `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)` — the latter is what validate_v9.py still does and what breaks pytest capture. A future hygiene task could port validate_v9.py to use reconfigure() instead, which would eliminate the need for the lazy-import workaround in this test file. Not done in this plan (out of scope for BASE-03 — the fix is a pure test-file concern that doesn't touch analysis/validate_v9.py). Future BASE-class phases or a follow-up quick task could address this.

- **Plan 42-05 wave-4 parallel outcome: landed BEFORE 42-06 at HEAD.** The wave-4 scheduler happened to resolve plan 42-05 first (its commit `a424818` landed before plan 42-06's test commit `8c6722b`), so when test_reconciled_baseline_json_loadable ran it found the JSON and ran the full shape+type validation rather than skipping. The co-wave-tolerant skip path is preserved for future mid-wave test runs and remains unit-testable via deletion of output/v10_reconciled_baseline.json.

## User Setup Required

None — pure test-file addition + reuse of existing canonical assets (analysis.validate_v9.compute_metrics, DataLoader('vn30'), build_indicator_dataframe, HybridEngine, VN30_PRESET). `uv run pytest -m regression tests/test_baseline_determinism.py -v` is the verification command (no user setup to run it).

## Next Phase Readiness

**Phase 42 CLOSED with BASE-01, BASE-02, BASE-03 all satisfied:**

- **BASE-01 (forensic audit):** Closed by plan 42-03 (`docs/audits/v10_baseline_drift.md` with bisect log + offending-commit f80394f + root-cause narrative).
- **BASE-02 (fix-forward reconciliation):** Closed by plan 42-04 (`v60_strict_mode` preset flag in MDMV2Config + branch-guard in V2PositionManager.process_day() restoring v6.0 flat-elif-chain semantics; parity verified CAGR 11.4700 / SELL 124 / MaxDD -28.1700).
- **BASE-03 (determinism regression test):** Closed by this plan (42-06) — `tests/test_baseline_determinism.py` committed at `8c6722b` with all 3 tests passing on reconciled-HEAD.
- **BASE-02 publication (downstream-JSON contract):** Closed by plan 42-05 (`output/v10_reconciled_baseline.json` at commit `a424818` with `schema_version=1` and 18 D-12 fields, `reconciliation_outcome="fixed_by_preset"`, CAGR 11.47, MaxDD -28.17, SELL 124).

**Ready for Phase 43 (Canonical Liquidity Data Pipeline):**

- Phase 43 has no dependency on the reconciled baseline or the determinism test — it's a data-pipeline regeneration task for vn_liquidity_proxy.csv + sbv_policy_events.csv with publication-lag tracking. Phase 43 planner can start from its CONTEXT immediately without waiting for Phase 42 artifacts (Phase 43's only v10.0 dependency is on REQUIREMENTS.md LIQ-01/02/03 + the existing quick-task 260421-lb4 data files).

**Ready for Phase 44 (Macro Filter Module):**

- Phase 44 MACRO-04 will byte-exact-compare `macro_filter_enabled=False` signal logs to reconciled-HEAD signal logs. The determinism gate from this plan is a precondition: without it, MACRO-04's regression gate is meaningless (a non-deterministic engine would produce different signal logs on re-runs). Phase 44 planner should cite `tests/test_baseline_determinism.py::test_signal_log_byte_exact` as the prerequisite regression that makes MACRO-04's byte-exact compare sound.
- Phase 44 also inherits the v60_strict_mode=True preset convention (D-22) — when MACRO-04 compares pre/post-filter-disable signal logs, both must run with v60_strict_mode=True. The test file's `_build_reconciled_cfg` helper is a reusable reference for how to build the canonical preset without hardcoding field values.

**Ready for Phase 45 (Walk-Forward Grid Search):**

- Phase 45's median-degradation <30% gate (WF-02) assumes engine determinism. The determinism test closes the precondition. Phase 45 walk-forward windows can re-run the engine on rolling train/test slices with confidence that numeric metric spreads reflect true walk-forward degradation, not engine-internal non-determinism.

**Ready for Phase 46 (A/B + OOS Validation — HARD Gate):**

- Phase 46 VAL-02 HARD gate reads `output/v10_reconciled_baseline.json` at run time (D-14) and asserts OOS CAGR ≥ reconciled_baseline.cagr_pct AND MaxDD < -20%. The downstream-JSON regression guard in this plan (`test_reconciled_baseline_json_loadable`) is the safety net: if any Phase 43-46 work accidentally mutates the JSON shape, this test fails BEFORE VAL-02 breaks silently. Phase 46 VAL-04 (byte-exact signal log regression) is the production consumer of `test_signal_log_byte_exact` — Phase 46 planner should cite this test in VAL-04's implementation as the regression that proves engine determinism under production HARD-gate conditions.

**Concerns passed forward:**

- **analysis/validate_v9.py Windows-stdout hygiene:** The `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)` rewrite at validate_v9.py line 41 is the root cause of the stdout-capture workaround in this test file. Porting validate_v9.py to use `sys.stdout.reconfigure(encoding='utf-8')` (matching the plan-42-01 bisect-script pattern) would eliminate the need for the lazy-import shim. This is a follow-up hygiene task, NOT a Phase 42 fix — scope creep if done here. Candidates to pick this up: a future BASE-class cleanup phase, or a quick task under milestone v10.0 polish.
- **STATE.md progress counter:** At the time of writing, STATE.md shows `completed_phases: 4` with `completed_plans: 9` — these are placeholder/stale values from a prior state snapshot (6 plans in phase 42 alone, all 6 now complete plus 42-03 was shown separately). The state-advance-plan tool will reset these on the final commit of this plan. No data integrity concern — just cosmetic until the counter recomputes.
- **plan 42-05's output/v10_reconciled_baseline.json was force-added past .gitignore.** Plan 42-05 summary notes "Force-added past output/ gitignore so Phases 43-47 load without re-running publisher (D-14)". The downstream-JSON regression guard in this plan depends on that force-add — if a future hygiene pass re-gitignores the JSON, test_reconciled_baseline_json_loadable will start SKIPPING in fresh clones (even on reconciled-HEAD), which would silently break the D-14 invariant. Mitigation: Phase 42 as a whole (plans 42-05 + 42-06) documents this force-add decision; future phases should not re-gitignore the file without bumping the test's skip-path to a fail-path.

## Self-Check: PASSED

Artifact and commit existence verified:
- FOUND: `tests/test_baseline_determinism.py` (274 lines, matches plan's min_lines=80 with substantial margin)
- FOUND: commit `8c6722b` in `git log --oneline -3 -- tests/test_baseline_determinism.py` (test(42-06): add BASE-03 engine determinism regression suite)
- FOUND: pytest run `uv run pytest -m regression tests/test_baseline_determinism.py -v` returns exit 0 with `3 passed in 38.67s`

Acceptance-criteria block from plan (all 26 checks):
- CK1 `@pytest.mark.regression` >= 1: PASS (1 match)
- CK2 `class TestBaselineDeterminism` == 1: PASS (1 match)
- CK3 `def test_numeric_variance_across_3_runs` == 1: PASS (1 match)
- CK4 `def test_signal_log_byte_exact` == 1: PASS (1 match)
- CK5 `def test_reconciled_baseline_json_loadable` == 1: PASS (1 match)
- CK6 (M2 preset-path) `reconciliation outcome` >= 1: PASS (1 match)
- CK7 (M2 conditional) `v60_strict_mode=True iff` >= 1: PASS (1 match)
- CK8 (M5 byte-exact CAGR) `len(set(cagrs)) == 1` == 1: PASS (1 match)
- CK9 (M5 byte-exact MaxDD) `len(set(maxdds)) == 1` == 1: PASS (1 match)
- CK10 (M5 byte-exact Sharpe) `len(set(sharpes)) == 1` == 1: PASS (1 match)
- CK11 (M5 D-17 fallback cites) `D-17 post-mortem threshold` >= 3: PASS (4 matches)
- CK12 `CAGR_SPREAD_POSTMORTEM = 0.1` == 1: PASS (1 match)
- CK13 `MAXDD_SPREAD_POSTMORTEM = 0.1` == 1: PASS (1 match)
- CK14 `SHARPE_SPREAD_POSTMORTEM = 0.005` == 1: PASS (1 match)
- CK15 `DATA_START = '2015-01-05'` == 1: PASS (1 match)
- CK16 `DATA_END = '2026-03-31'` == 1: PASS (1 match)
- CK17 `len(set(sells)) == 1` == 1: PASS (1 match)
- CK18 `len(set(trans)) == 1` == 1: PASS (1 match)
- CK19 `results_1.equals(results_2)` == 1: PASS (1 match)
- CK20 `from analysis.validate_v9 import compute_metrics` >= 1: PASS (2 matches — commented hint + lazy import body)
- CK21 `build_indicator_dataframe` >= 1: PASS (2 matches)
- CK22 `two_phase_enabled=True` == 1: PASS (1 match)
- CK23 `filter_enabled=False` == 1: PASS (1 match)
- CK24 (m4 imports+schema_version) `import json` >= 1 AND `EXPECTED_JSON_TYPES` >= 2 AND `schema_version` >= 2: PASS (1 / 3 / 5 matches respectively)
- CK25 (m4 co-wave) `pytest.skip` >= 1: PASS (1 match)
- CK26 (v60_strict_mode probe) `'v60_strict_mode' in MDMV2Config.__dataclass_fields__` == 1: PASS (1 match)

Pytest run at committed HEAD `8c6722b`:
- `collected 3 items` in 0.08s
- `TestBaselineDeterminism::test_numeric_variance_across_3_runs PASSED`
- `TestBaselineDeterminism::test_signal_log_byte_exact PASSED`
- `TestBaselineDeterminism::test_reconciled_baseline_json_loadable PASSED` (ran fully — JSON present at HEAD)
- Total: `3 passed in 38.67s`, exit code 0

---
*Phase: 42-baseline-reconciliation*
*Completed: 2026-04-22*
