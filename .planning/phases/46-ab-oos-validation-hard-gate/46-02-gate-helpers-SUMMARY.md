---
phase: 46-ab-oos-validation-hard-gate
plan: 02
subsystem: validation
tags: [validation, macro-filter, hard-gate, walk-forward, parity, subprocess, v10, ab-test, oos]

# Dependency graph
requires:
  - phase: 42-baseline-reconciliation
    provides: "output/v10_reconciled_baseline.json cagr_pct field (HARD gate CAGR floor, D-05)"
  - phase: 44-macro-filter-module
    provides: "tests/test_macro_filter_v6_parity.py (5 regression tests invoked by VAL-04)"
  - phase: 45-walk-forward-grid-search
    provides: "output/v10_grid_results.csv stage3_all_three-c1 row (VAL-03 lookup target, D-07)"
  - phase: 46-ab-oos-validation-hard-gate/46-01-scenario-scaffold
    provides: "analysis/validate_v10.py scaffold with SCENARIO_ORDER + module constants used by helpers (RECONCILED_BASELINE_JSON, WALKFORWARD_GRID_CSV, WALKFORWARD_DEGRADATION_THRESHOLD, WALKFORWARD_VN30_PRESET_COMBO, HARD_GATE_MAX_DD_CEILING, PARITY_TEST_PATH)"
provides:
  - "analysis/validate_v10.py extended with 4 pure gate helpers (VAL-02 / VAL-03 / VAL-04 gates isolated from orchestration)"
  - "load_hard_gate_thresholds() -> dict — reads CAGR floor from reconciled baseline JSON (NO hardcoded 11.47 literal), pairs with -20.0 ceiling constant, raises FileNotFoundError/KeyError with remediation messages"
  - "evaluate_hard_gate(metrics, thresholds) -> dict — D-05 rule exact: cagr_obs >= cagr_req AND max_dd_obs > max_dd_req (strict > so -20.0 boundary FAILS); returns 8-field verdict dict (passed/cagr_pass/max_dd_pass/observed/required/detail)"
  - "lookup_walkforward_degradation(combo_name=None) -> dict — reads Phase 45 CSV row, applies D-07 gate (passed_gate = median_degradation < 0.30) independently of CSV's composite 'accepted' column; surfaces 9-field dict with total_combos / total_accepted for 0-of-39 context"
  - "run_parity_gate(timeout_sec=300) -> dict — shells out to `uv run python -m pytest tests/test_macro_filter_v6_parity.py -v --tb=short`, captures returncode/stdout_tail/stderr_tail + regex-parsed (tests_passed, tests_failed); does NOT duplicate parity logic (D-08); does NOT raise on subprocess failure (returns rc=-1/-2 diagnostic)"
affects: [46-03-pipeline-wiring, 46-04-execute-and-commit, 47-docs-and-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gate helpers as pure functions — separate read-from-disk gate logic from orchestration so Plan 03 main() reads as a sequence of one-liner gate invocations"
    - "D-05 strict-inequality on negative MaxDD — max_dd_obs > max_dd_req (not >=) implemented uniformly so the -20.0 boundary FAILS per spec; rule reused if v11 ever wants a -15 ceiling"
    - "Subprocess gate as D-08 no-duplication enforcement — shell out to existing pytest rather than rewriting parity assertion logic inside validate_v10.py"
    - "Non-raising subprocess helper — pytest invocation failures (timeout, FileNotFoundError) captured as (rc=-1, rc=-2) diagnostic in return dict so the whole validation pipeline doesn't abort on a single gate's environment failure"
    - "Cross-phase baseline coupling via JSON load at runtime — load_hard_gate_thresholds never hardcodes 11.47; any Phase 42 reconciliation re-run updates the gate automatically (drift-resistant)"

key-files:
  created: []
  modified:
    - "analysis/validate_v10.py (263 -> 552 lines, +289 LOC across 3 atomic commits)"

key-decisions:
  - "Task 1 docstring '11.47 and -28.17' example replaced with 'reconciled baseline cagr and its max drawdown' prose — Plan 02 acceptance criterion is absolute 0 instances of 11.47 in the file (not just 0 at runtime); prose describes the contract without embedding the number"
  - "VAL-03 gate applies strict D-07 rule (median_degradation < 0.30) in-function rather than delegating to the CSV's 'accepted' column — CSV 'accepted' is composite D-09 (degradation < 0.30 AND median_eval_cagr > 0.0) while VAL-03 text locks only the stability half; in-function rule makes the gate interpretable in isolation and portable if Phase 47 wants to report the two gate bands separately"
  - "run_parity_gate NEVER raises — subprocess shape guards FileNotFoundError (uv not in PATH) and TimeoutExpired so a single gate's environment failure cannot abort the whole Plan 03 pipeline; non-zero rc + diagnostic stderr capture is the failure surface, not Python exceptions"
  - "Subprocess cwd set to os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) — the repo root — so `uv` resolves pyproject.toml and pytest finds tests/ regardless of where main() is invoked from (e.g. a future notebook runner or CI working dir)"

patterns-established:
  - "Pattern: 'pure gate helper returning structured verdict dict' — load_from_disk + apply_rule + return (passed, detail, observed, required, source_path) dict. Plan 03 main() can compose these as one-liners and the report writer inlines 'detail' verbatim. Reusable for future v11 gate work."
  - "Pattern: 'no-hardcode contract with grep-acceptance' — grep \"11.47\" must return 0 hits in the file (not just in code); docstring prose describes the contract without embedding the numeric value. Reusable discipline for any drift-sensitive threshold."
  - "Pattern: 'subprocess gate with rc-coded environment errors' — rc=-1 for TimeoutExpired, rc=-2 for FileNotFoundError, rc=proc.returncode otherwise; stdout_tail/stderr_tail capture last 50 lines for the report. Reusable for any future 'invoke external test as a gate' helper."

requirements-completed: [VAL-02, VAL-03, VAL-04]

# Metrics
duration: 5min
completed: 2026-04-24
---

# Phase 46 Plan 02: Gate Helpers Summary

**Four pure-function gate helpers land in analysis/validate_v10.py (load_hard_gate_thresholds / evaluate_hard_gate / lookup_walkforward_degradation / run_parity_gate) — each reads external state (JSON, CSV, pytest subprocess) and returns a structured verdict dict, isolating VAL-02/03/04 gate logic from the Plan 03 orchestrator.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-24T09:05:13Z
- **Completed:** 2026-04-24T09:09:52Z
- **Tasks:** 3
- **Files modified:** 1 (`analysis/validate_v10.py`, 263 → 552 lines, +289 LOC)

## Accomplishments

- **VAL-02 HARD gate (Task 1):** `load_hard_gate_thresholds()` reads reconciled baseline JSON (Phase 42 BASE-02 canonical tuple) to extract `cagr_floor = 11.47` at runtime — **no hardcoded 11.47 literal anywhere in the file** (grep `11\.47` returns 0 hits); `max_dd_ceiling = -20.0` from module constant `HARD_GATE_MAX_DD_CEILING`. `evaluate_hard_gate(metrics, thresholds)` returns an 8-field verdict dict applying the D-05 rule byte-exact: `(cagr_obs >= cagr_req) AND (max_dd_obs > max_dd_req)` — the strict `>` on MaxDD makes the -20.0 boundary FAIL per milestone spec (both values negative, strictly-less-negative means shallower).
- **VAL-03 walk-forward re-check (Task 2):** `lookup_walkforward_degradation()` reads Phase 45 `output/v10_grid_results.csv` row where `config_name == 'stage3_all_three-c1'` (VN30_PRESET defaults combo) and applies D-07 gate: `passed_gate = median_degradation < 0.30`. Real artifact returns `{median_degradation: 0.5375, accepted: False, passed_gate: False, total_combos: 39, total_accepted: 0}` — retain-v6.0 evidence surface intact. Does NOT re-run the 39-combo sweep (D-07) and does NOT delegate to the CSV's composite 'accepted' column so VAL-03 is interpretable in isolation as "walk-forward stability".
- **VAL-04 parity regression gate (Task 3):** `run_parity_gate()` shells out to `uv run python -m pytest tests/test_macro_filter_v6_parity.py -v --tb=short` with 300s timeout, captures 8-field dict (passed/returncode/stdout_tail/stderr_tail/tests_passed/tests_failed/test_file/duration_sec). Does NOT duplicate parity logic (D-08 — no `df.equals(` / `test_signal_log_byte_exact` / `test_macro_columns_absent` substrings in validate_v10.py). Subprocess failures (timeout, FileNotFoundError) captured as rc=-1/-2 diagnostics rather than raising, so Plan 03's pipeline can surface the environment error and continue.
- **All four helpers are pure functions** — no `global` statement usage, no module state mutation; each takes its own inputs and returns its own verdict dict. Plan 03 main() can compose them as one-liners.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add load_hard_gate_thresholds() + evaluate_hard_gate() (VAL-02)** — `2d79e76` (feat)
2. **Task 2: Add lookup_walkforward_degradation() (VAL-03)** — `5a3bca8` (feat)
3. **Task 3: Add run_parity_gate() subprocess helper (VAL-04)** — `804cb54` (feat)

_Metadata commit for SUMMARY + STATE + ROADMAP + REQUIREMENTS follows this SUMMARY._

## Files Created/Modified

- `analysis/validate_v10.py` (modified, 263 → 552 lines, +289 LOC) — appended the four gate helpers after `verify_extremes_never_trigger` and before the EOF Plan 03 placeholder comment; preserved Plan 01 scaffold byte-identical above the insertion point. Per-helper breakdown:
  - `load_hard_gate_thresholds()` — 41 LOC (docstring + body + raises)
  - `evaluate_hard_gate()` — 52 LOC (docstring + rule + detail-string + return)
  - `lookup_walkforward_degradation()` — 85 LOC (docstring + path-guard + pd.read_csv + single-match validation + dtype-normalised accepted + aggregate counts)
  - `run_parity_gate()` — 89 LOC (docstring + subprocess call + timeout/FNF guards + stdout tail helper + regex summary parser + 8-field return)

## Decisions Made

- **Task 1 docstring '11.47 and -28.17' example replaced with 'reconciled baseline cagr and its max drawdown' prose.** The acceptance criterion reads `grep -cn "11\.47" analysis/validate_v10.py` must return 0 — absolute, not just "no runtime hardcoded". The example in the docstring would have counted as a hit. Prose describes the contract without embedding the number; discipline is drift-resistant because any future Phase 42 reconciliation update doesn't require editing the docstring.
- **VAL-03 gate applies the strict D-07 rule in-function rather than delegating to the CSV's 'accepted' column.** The CSV's `accepted` is composite D-09 (median_degradation < 0.30 AND median_eval_cagr > 0.0), while VAL-03 text in REQUIREMENTS specifies only the degradation-stability half. Applying the rule in `lookup_walkforward_degradation` keeps VAL-03 interpretable in isolation — Plan 03 report can surface "the degradation gate failed" separately from any composite acceptance question, and Phase 47's audit narrative can cite VAL-03 without having to re-read Phase 45's D-09 definition.
- **run_parity_gate NEVER raises.** Subprocess pitfalls — `uv` not in PATH (FileNotFoundError) or pytest hanging (TimeoutExpired) — are captured as rc=-2 / rc=-1 with diagnostic stderr strings, not propagated. Rationale: the D-05 HARD gate combines VAL-01..04 in sequence; if VAL-04 raises, Plan 03's pipeline aborts before writing the report. Non-raising gate means the verdict writer always has a verdict dict, even if VAL-04 failed for an infrastructure reason the user needs to see.
- **Subprocess cwd locked to repo root via `os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))`** so pytest can discover `pyproject.toml` regardless of where the Plan 03 main() is invoked from (ad-hoc notebook, CI, IDE run-current-file). Slightly more robust than relying on the caller's cwd.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `11.47` example in `evaluate_hard_gate` docstring violated acceptance criterion**
- **Found during:** Task 1 verification
- **Issue:** The `evaluate_hard_gate` docstring originally contained the example `'max_dd_pct' keys (float percent values; e.g. 11.47 and -28.17)` which caused `grep -cn "11\.47"` to return 1 (violating the plan's explicit "0 hits anywhere in the file" criterion). Plan text itself contained this same example in the `<action>` block (plan line 207), so the literal was copy-pasted from the plan into the file. The plan's docstring example is inconsistent with its own acceptance criterion.
- **Fix:** Rewrote the docstring example to non-numeric prose: `'max_dd_pct' keys (float percent values; e.g. reconciled baseline cagr and its max drawdown)`. Preserves the intent (describe the scale/format of the input) without embedding the reconciled-baseline number that would need editing on every reconciliation run.
- **Files modified:** `analysis/validate_v10.py:319-320` (1 line changed — docstring comment only, no code change)
- **Verification:** `grep -cn "11.47"` returns 0 after the edit.
- **Committed in:** `2d79e76` (Task 1 commit — edit made before commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — plan-internal inconsistency between docstring example and acceptance criterion; fixed to honor the acceptance criterion, which is the contractually locked constraint)
**Impact on plan:** No scope creep. No code-behavior change. Single docstring line rewritten to remove a specific numeric literal whose presence would have failed the file's own acceptance grep. Plan 03 is not affected.

## Issues Encountered

- **Windows Application Control policy blocks `_ctypes.pyd` for uv's cpython-3.10.20** (same as Wave 1 Plan 01 deviation). `uv run python -c "..."` cannot import pandas / numpy / ctypes / pytest, so the planned `uv run python -c "from analysis.validate_v10 import ..."` verify commands could not execute in this session. Also blocks `uv run pytest` directly (caught as "Failed to spawn: pytest" at runtime).

  **Substitution:** AST-level structural verification via system Python 3.13 (at `C:\Users\trant\AppData\Local\Programs\Python\Python313\python.exe`, which loads ctypes cleanly but lacks pandas) plus logic-level replays using stdlib `json`, `csv`, `re`, `subprocess`. Verified:
  - Task 1: All 6 boundary cases for `evaluate_hard_gate` (cagr pass / fail, max_dd pass / fail, boundary CAGR=11.47 exact, boundary MaxDD=-20.0 exact, expected Phase 46 outcome 11.47/-28.17) — pure Python replica of the D-05 rule PASSES 6/6. `load_hard_gate_thresholds` JSON read verified against `output/v10_reconciled_baseline.json` — returns `cagr_floor=11.47, max_dd_ceiling=-20.0` as expected.
  - Task 2: Real CSV lookup via stdlib `csv.DictReader` found `stage3_all_three-c1` row with `median_degradation=0.5375` (matches Plan 45 SUMMARY line 97-103 canonical 0.5374873353596757), `accepted=False`, `passed_gate=False`. Total combos=39, total_accepted=0. Missing-combo ValueError path verified via list comprehension emptiness.
  - Task 3: Subprocess shape exercised end-to-end in the session (`uv run pytest` via run_parity_gate's exact code path) — rc=1 captured, stderr captures Windows Application Control block ("An Application Control policy has blocked this file"), duration=2.2s under 30s timeout. Parser logic verified against two mock pytest outputs: (5 passed, rc=0) → tests_passed=5/tests_failed=0, (4 passed + 1 failed, rc=1) → tests_passed=4/tests_failed=1. Both PASS.

  **What was NOT empirically exercised in this session** (deferred to Plan 03 or CI run on an unblocked environment):
  - `load_hard_gate_thresholds()` raise-path when `RECONCILED_BASELINE_JSON` is missing — sign-preservation math in source is trivial; raise uses `FileNotFoundError` (not generic IOError) — verified via AST.
  - `lookup_walkforward_degradation()` dtype-normalisation branch for numpy bool `raw_accepted` — pandas `read_csv` in the real helper may load `accepted` as numpy.bool_ or str depending on CSV format; the stdlib csv replay used string `'False'`, which exercises the `isinstance(raw_accepted, str)` branch. The numpy.bool_ branch is inferred-correct from AST read but not empirically fired.
  - `run_parity_gate()` happy path (rc=0, tests_passed=5, tests_failed=0, duration ~90s) — this is the scenario Plan 03 will exercise on an unblocked machine; in this session all the subprocess shape is verified except the actual 5-parity-test result.

- **Plan text used "\\[" grep patterns in acceptance criteria** (e.g. `grep -n "baseline\\['cagr_pct'\\]"`). On bash the `\\[` is literal, on Grep tool regex it matches `[`. Confirmed both literal and regex greps match the code via AST `ast.unparse()` substring check. Substantively identical; no code change required.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All four VAL-02 / VAL-03 / VAL-04 gate helpers are importable from `analysis.validate_v10` — Plan 03 `main()` can start with:
  ```python
  from analysis.validate_v10 import (
      SCENARIO_ORDER, OOS_SCENARIO_SUBSET,
      build_scenarios, run_engine, verify_extremes_never_trigger,
      load_hard_gate_thresholds, evaluate_hard_gate,
      lookup_walkforward_degradation, run_parity_gate,
      VERDICT_PASS, VERDICT_FAIL,
      REPORT_TXT, AB_COMPARISON_TXT, SCENARIOS_CSV,
  )
  ```
- Gate composition for Plan 03 main() (one-liner per gate):
  ```python
  th = load_hard_gate_thresholds()                              # VAL-02 pre
  hard = evaluate_hard_gate(plus_all_metrics, th)               # VAL-02 gate
  wf = lookup_walkforward_degradation()                         # VAL-03 gate
  parity = run_parity_gate()                                    # VAL-04 gate
  all_pass = hard['passed'] and wf['passed_gate'] and parity['passed']
  verdict = VERDICT_PASS if all_pass else VERDICT_FAIL
  ```
- **Retain-v6.0 expected outcome** (Phase 45 evidence): `hard['passed']=False` (CAGR pass, MaxDD fail at -28.17 vs -20 ceiling), `wf['passed_gate']=False` (median_degradation 0.5375 > 0.30), `parity['passed']=True` (5/5 tests still pass on unblocked env). Plan 03 report writer will surface all three gate verdicts and the rejection narrative per D-10.
- **Blocker for Plan 03:** None known. Plan 03 needs `uv run python analysis/validate_v10.py` to execute the HybridEngine runs end-to-end, which means Plan 03 must run on a machine with unblocked `_ctypes.pyd` (this session's environment cannot exercise the engine runs). The gate helpers themselves are syntax-valid and structurally complete regardless.

## Self-Check: PASSED

**Modified files (verified via filesystem):**
- FOUND: `analysis/validate_v10.py` (552 lines, git-tracked, commits 2d79e76 / 5a3bca8 / 804cb54)

**Commits (verified via `git log --oneline -5`):**
- FOUND: `2d79e76` feat(46-02): add load_hard_gate_thresholds + evaluate_hard_gate (VAL-02)
- FOUND: `5a3bca8` feat(46-02): add lookup_walkforward_degradation (VAL-03)
- FOUND: `804cb54` feat(46-02): add run_parity_gate subprocess helper (VAL-04)

**AST-level acceptance verification (via system Python 3.13 `ast.parse`):**
- FOUND: `def load_hard_gate_thresholds` (single match; 41 LOC; raises FileNotFoundError + KeyError; reads `baseline['cagr_pct']`)
- FOUND: `def evaluate_hard_gate` (single match; 52 LOC; implements `cagr_obs >= cagr_req AND max_dd_obs > max_dd_req`; returns 8-field dict)
- FOUND: `def lookup_walkforward_degradation` (single match; 85 LOC; raises FileNotFoundError + ValueError; applies `median_deg < WALKFORWARD_DEGRADATION_THRESHOLD` explicitly)
- FOUND: `def run_parity_gate` (single match; 89 LOC; uses `subprocess.run` + `capture_output=True`; references `PARITY_TEST_PATH`; handles TimeoutExpired + FileNotFoundError; returns 8-field dict)
- FOUND: 4+ references to `WALKFORWARD_VN30_PRESET_COMBO` (plan required ≥2)
- FOUND: 1 reference to `subprocess.run` (plan required ≥1)
- FOUND: `capture_output=True` (plan required exactly 1)
- FOUND: `tests/test_macro_filter_v6_parity.py` reference via `PARITY_TEST_PATH` constant
- ABSENT: `11.47` anywhere in file (plan required 0 hits)
- ABSENT: `df.equals(`, `def test_signal_log_byte_exact`, `test_macro_columns_absent` (plan required 0 hits each — no parity logic duplication)
- ABSENT: `def main(` (correct — Plan 03 adds)
- ABSENT: `global ` statements in any of the 4 helpers (purity invariant)
- Line count: 552 (was 263 in Plan 01; ≥ 250 min_lines required)

**Runtime behavior verification (replay via stdlib Python 3.13):**
- PASSED: 6/6 HARD gate boundary cases against reconciled baseline JSON
- PASSED: Real CSV lookup for `stage3_all_three-c1` returns `median_degradation=0.5375, accepted=False, passed_gate=False`
- PASSED: 2/2 parity-gate parser mock cases (5 passed rc=0 → 5/0; 4 passed + 1 failed rc=1 → 4/1)
- PASSED: run_parity_gate subprocess end-to-end shape (rc=1 from Windows App Control block captured as expected non-raising diagnostic)

**Runtime verification deferred to Plan 03 / CI** (Wave 1 environmental DLL block persists): pandas-mediated behaviors in `lookup_walkforward_degradation` (numpy.bool_ dtype branch) and `run_parity_gate` happy path (actual 5 parity tests passing) will be first exercised when Plan 03 runs on an unblocked environment. AST + replay coverage is provably complete for the structural contract.

---
*Phase: 46-ab-oos-validation-hard-gate*
*Completed: 2026-04-24*
