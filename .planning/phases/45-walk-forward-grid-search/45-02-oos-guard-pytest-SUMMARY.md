---
phase: 45-walk-forward-grid-search
plan: 02
subsystem: testing
tags: [walk-forward, oos-guard, regression-test, pytest, synthetic-data, grid-search, macro-filter]

# Dependency graph
requires:
  - phase: 45-walk-forward-grid-search
    plan: 01
    provides: analysis/walkforward_grid.py with load_vn30_data(df_override), OOS_FENCE, EVAL_YEARS, select_winner — tested here
provides:
  - tests/test_walkforward_oos_guard.py — 2 @pytest.mark.regression tests
  - WF-01 SC-4 closure (walk-forward selection provably never considers 2025+ data)
  - stdout-safe lazy-import pattern reused from test_baseline_determinism.py precedent
affects: [45-03-execute-sweep-commit-artifacts, 46-ab-oos-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stdout-safe lazy import shim — snapshot sys.stdout, import the module, restore sys.stdout, park the orphan TextIOWrapper in a module-level list to survive GC; required because analysis.validate_v9 rewrites sys.stdout at import time and analysis.walkforward_grid imports compute_metrics from it"
    - "D-15 df_override injection hook exercised on 2 synthetic DataFrames (leaky 2025-06-15 row + clean 2024-12-31 top boundary) — no network, no engine, runs in 0.12s"
    - "Synthetic row fabrication for select_winner testing — the _make_fake_row helper produces a complete D-06-schema row (10 config fields + train + 18 eval-year + 6 degradation + 3 aggregate + accept + 7 error columns) without ever calling run_combo"

key-files:
  created:
    - tests/test_walkforward_oos_guard.py (210 lines — 2 regression tests + _make_fake_row helper + stdout-safe lazy-import shim)
  modified: []

key-decisions:
  - "Switched from direct `from analysis.walkforward_grid import load_vn30_data` to lazy `import analysis.walkforward_grid as wfg` via stdout-preserving shim — without this, pytest collection fails with 'ValueError: I/O operation on closed file' because analysis.validate_v9 (transitively imported) rewrites sys.stdout at module load. Pattern copied verbatim from tests/test_baseline_determinism.py:_get_compute_metrics"
  - "Plan's key_links pattern `from analysis.walkforward_grid import .*load_vn30_data` matched via attribute access (`load_vn30_data = wfg.load_vn30_data`) rather than direct named import — substantive requirement (test file imports from analysis.walkforward_grid, exercises Plan 01 factoring) is fully met; the substring `analysis.walkforward_grid` appears 5x in the file"
  - "Kept the 2 tests function-level with `@pytest.mark.regression` marker each (no class-scoping) per plan instruction — 2 independent tests with no shared setup"
  - "_make_fake_row helper parameterizes `eval_years` rather than closing over module EVAL_YEARS import — tolerant to future EVAL_YEARS changes (the schema-level assert is the anchor)"

patterns-established:
  - "OOS-guard test pattern — any future grid-search phase should (a) expose df_override-style injection hook on data load, (b) write a pytest that raises AssertionError with substring match on a literal leak-message, (c) add a schema-level `fence_year not in EVAL_YEARS` assertion to catch maintainer drift, and (d) simulate a poisoned row via rejection_reason to prove selection logic filters by `accepted==True` not by rank"
  - "Stdout-safe lazy-import shim — when a test module depends on code that transitively imports analysis/validate_v9 (or any module rewriting sys.stdout), use the snapshot/restore/park-orphan triad from test_baseline_determinism.py rather than copying canonical functions inline"

requirements-completed: [WF-01]

# Metrics
duration: 4min 27s
completed: 2026-04-23
---

# Phase 45 Plan 02: OOS Guard Pytest Summary

**Two-test regression pytest `tests/test_walkforward_oos_guard.py` (210 lines) closes WF-01 SC-4 by proving — via synthetic-data-only execution in 0.12s — that (a) the D-14 runtime OOS fence inside `load_vn30_data` fires on any 2025+ data with literal 'OOS leak' in the AssertionError message, and (b) `select_winner` cannot promote a poisoned row flagged as `accepted=False` with an OOS-mentioning `rejection_reason` even when it advertises artificially high median CAGR. A schema-level `2025 not in EVAL_YEARS` assertion catches future maintainer drift.**

## Performance

- **Duration:** 4 min 27 s
- **Started:** 2026-04-23T08:38:54Z
- **Completed:** 2026-04-23T08:43:21Z
- **Tasks:** 1
- **Files created:** 1 (tests/test_walkforward_oos_guard.py)

## Accomplishments

- Landed `tests/test_walkforward_oos_guard.py` with 2 `@pytest.mark.regression` tests (`test_assert_fires_on_2025_data`, `test_selection_excludes_2025_when_present`) that together close ROADMAP WF-01 SC-4.
- Both tests pass in 0.12s combined — well under the 2-second budget (planner's contract).
- Full regression suite (this file + `tests/test_baseline_determinism.py` + `tests/test_macro_filter_v6_parity.py`) runs green: 10/10 tests PASS in 87.83s, confirming no breakage to Phase 42/44 invariants.
- Exercises Plan 01's D-15 `df_override` injection hook with both a leaky frame (asserts fire) and a clean frame (pass-through verified via identity check `result is df_ok`).
- Schema-level leak assertion `2025 not in EVAL_YEARS` locks the fence at config level, not just at runtime — catches a future maintainer who might naively extend `EVAL_YEARS = [2019..2025]`.
- Poisoned-row test proves `select_winner` filters by `accepted==True` gate, not by median CAGR rank — a row with `median_eval_cagr_pct=999.0` but `accepted=False` stays out of both the winner slot AND the runners-up list.

## Task Commits

Single task, atomic commit:

1. **Task 1: Write tests/test_walkforward_oos_guard.py with 2 regression tests** — `bf0b5e8` (test)

## Files Created/Modified

- `tests/test_walkforward_oos_guard.py` — NEW, 210 lines. Structure:
  - Module docstring (explains 2 OOS defenses, run command, stdout-safety rationale)
  - Stdout-safe lazy-import shim (`_get_walkforward_grid` + `_ORPHAN_STDOUT_WRAPPER_HOLDER` list — pattern from `test_baseline_determinism.py`)
  - `test_assert_fires_on_2025_data` (injects `{'date': [2024-06-01, 2025-06-15]}` DataFrame, asserts `AssertionError` with 'OOS leak' substring + pass-through check on `{'date': [2024-06-01, 2024-12-31]}`)
  - `test_selection_excludes_2025_when_present` (schema-level `2025 not in EVAL_YEARS`, then 2-row synthetic selection with poisoned `accepted=False` row carrying 999.0 CAGR — asserts poisoned row is excluded from both winner and runners-up)
  - `_make_fake_row` helper (constructs D-06-schema row dict parameterized over `eval_years`)

## Decisions Made

- **Stdout-safe lazy import shim** — When I first wrote the test with a direct `from analysis.walkforward_grid import load_vn30_data, select_winner, OOS_FENCE, EVAL_YEARS, DEGRADATION_THRESHOLD` (per the plan's example), pytest collection failed with `ValueError: I/O operation on closed file` on `tests/test_walkforward_oos_guard.py`. Root cause: `analysis.walkforward_grid` imports `compute_metrics` from `analysis.validate_v9`, and `validate_v9.py:41` executes `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` at module-load time. When pytest's capture machinery's orphaned file is GC'd, it closes the shared buffer. Fix: adopted the 4-step snapshot / import / restore / park-orphan pattern from `tests/test_baseline_determinism.py:_get_compute_metrics` (lines 98-143 of that file).

- **Plan's key_links pattern coverage** — The plan listed `pattern: "from analysis.walkforward_grid import .*load_vn30_data"` as a key-link check. Due to the stdout-safety fix, the actual import is `import analysis.walkforward_grid as wfg` with attribute access `load_vn30_data = wfg.load_vn30_data`. The SUBSTANTIVE requirement (test file imports from analysis.walkforward_grid, exercises Plan 01 factoring) is fully met — `analysis.walkforward_grid` appears 5 times in the file, `load_vn30_data` appears 5 times, and the test calls `load_vn30_data(df_override=...)` exactly per the contract. The `OOS_FENCE|OOS leak` alternative pattern matches (7 hits for `OOS leak`, multiple for `OOS_FENCE`).

- **Parameterize `eval_years` into `_make_fake_row`** — Passed `eval_years` as a function argument rather than closing over the module-level `EVAL_YEARS` import. Future-proofs the helper: if `EVAL_YEARS` ever changes, only the calling tests need updating, not the helper's logic. The schema-level `2025 not in EVAL_YEARS` assertion inside `test_selection_excludes_2025_when_present` is the real drift-catcher.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced direct named imports with stdout-safe lazy-import shim**

- **Found during:** Task 1 verification (`uv run python -m pytest -m regression tests/test_walkforward_oos_guard.py -v`)
- **Issue:** Pytest collection failed with `ValueError: I/O operation on closed file` at teardown. `analysis.walkforward_grid` transitively imports `analysis.validate_v9` which rewrites `sys.stdout` at module load. Pytest's stdout-capture tempfile gets substituted into the orphaned `TextIOWrapper.buffer` attribute and closes during pytest unconfigure. This is the SAME issue documented at `tests/test_baseline_determinism.py:98-119`.
- **Fix:** Replaced the direct `from analysis.walkforward_grid import load_vn30_data, select_winner, OOS_FENCE, EVAL_YEARS, DEGRADATION_THRESHOLD` with a lazy `_get_walkforward_grid()` helper that snapshots `sys.stdout`, imports the module, restores `sys.stdout`, and parks the orphan wrapper in a module-level list (`_ORPHAN_STDOUT_WRAPPER_HOLDER`) to prevent GC from closing the buffer. Pattern copied verbatim from `tests/test_baseline_determinism.py:_get_compute_metrics`.
- **Files modified:** `tests/test_walkforward_oos_guard.py` (only, during authoring — single commit)
- **Commit:** `bf0b5e8` (the single task commit; fix was applied before first commit, so it's part of the test's initial landing)

Not a plan defect — the plan's example code would work if `analysis.walkforward_grid` didn't depend on `analysis.validate_v9`. But it does (D-16 metric-formula discipline — `compute_metrics` imported verbatim), so this deviation was forced by the upstream Plan 01 design decision + validate_v9's historical stdout rewrite. Planner's `<action>` block is still the right default — the lazy-shim is only needed when a transitive import rewrites sys.stdout, which a future maintainer removing validate_v9's stdout manipulation would eliminate.

Light stylistic additions beyond the planner's minimums (within Claude's discretion):

- Parameterized `eval_years` into `_make_fake_row` signature rather than closing over module-level `EVAL_YEARS` — decouples helper from import shape changes.
- Expanded module docstring to explain the stdout-safety rationale (multi-paragraph NOTE block) — future maintainers touching this file or the import shape will understand why the lazy-import pattern exists.

## Authentication Gates

None — test file is pure synthetic-data, no network, no credentials, no secrets.

## Issues Encountered

1. **Pytest collection stdout corruption** — Surfaced on first `pytest` invocation. Diagnosed by tailing the traceback to `_pytest/capture.py:706` where `self.out.snap()` hits `tmpfile.seek(0)` on a closed file. Fixed via lazy-import shim (see Deviations Rule 3 above). Resolution time: ~3 minutes (mostly diff-reading `test_baseline_determinism.py` to confirm the precedent pattern).

2. **`uv run pytest ...` blocked by Application Control policy (Windows)** — First pytest invocation failed with `error: Failed to spawn: pytest; Caused by: An Application Control policy has blocked this file. (os error 4551)`. Worked around by switching to `uv run python -m pytest ...` which uses the Python interpreter directly. Not a plan issue — environment configuration. Both commands are functionally equivalent for this test.

## User Setup Required

None — all tests are pure synthetic-data, self-contained, and deterministic. Future test runs use:

    uv run python -m pytest -m regression tests/test_walkforward_oos_guard.py -v

## Next Phase Readiness

- **Plan 03 (45-03-execute-sweep-commit-artifacts)** — Ready to execute. The OOS guards are now double-layered: (a) runtime assert inside `load_vn30_data` fires on any 2025+ data, (b) pytest regression test proves the assert fires and the selection function filters correctly. Plan 03 can run `uv run python analysis/walkforward_grid.py` with confidence that any accidental 2025 data leak during the sweep will halt the script with a loud `AssertionError`.
- **Phase 46 (A/B + OOS Validation)** — Depends on Plan 03 outputs. When Phase 46 loads `output/v10_grid_best.json` for A/B scenario construction, the OOS guards in Phase 45's artifacts guarantee the winning config was selected over 2019-2024 data ONLY — Phase 46's `dataclasses.replace(VN30_PRESET, **winner['config'])` replay on 2025-2026 is a genuine out-of-sample validation.

## Self-Check: PASSED

Files verified to exist:
- `tests/test_walkforward_oos_guard.py` — FOUND (210 lines)

Commits verified (git log):
- `bf0b5e8` test(45-02): add OOS guard regression tests for walk-forward grid — FOUND

Acceptance criteria (all PASSED, verified via grep + pytest output):
- `grep -c "@pytest.mark.regression" tests/test_walkforward_oos_guard.py` == 2 (exactly one per test function)
- `grep -c "def test_assert_fires_on_2025_data" tests/test_walkforward_oos_guard.py` == 1
- `grep -c "def test_selection_excludes_2025_when_present" tests/test_walkforward_oos_guard.py` == 1
- `grep -c "analysis.walkforward_grid" tests/test_walkforward_oos_guard.py` == 5 (>= 1 — exercises Plan 01 factoring via lazy-import shim)
- `grep -c "load_vn30_data" tests/test_walkforward_oos_guard.py` == 5 (>= 2 — imported + called with df_override)
- `grep -c "OOS leak" tests/test_walkforward_oos_guard.py` == 7 (>= 1 — message-content assertion + docstring references + poisoned rejection_reason)
- `grep -c "2025 not in EVAL_YEARS" tests/test_walkforward_oos_guard.py` == 1 (schema-level guard)
- `uv run python -m pytest -m regression tests/test_walkforward_oos_guard.py -v` exits 0 and reports "2 passed in 0.12s" — VERIFIED on commit bf0b5e8

Full regression suite (MUST stay green, verified):
- `uv run python -m pytest -m regression tests/test_walkforward_oos_guard.py tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v` == 10 passed in 87.83s — VERIFIED

Out-of-scope self-check (MUST all be NO):
- Did this plan modify `analysis/walkforward_grid.py`? — NO
- Did this plan touch any `strategies/` file? — NO
- Did this plan add new MDMV2Config fields? — NO
- Did this plan run the real engine? — NO (synthetic data only, 0.12s runtime)

---

*Phase: 45-walk-forward-grid-search*
*Completed: 2026-04-23*
