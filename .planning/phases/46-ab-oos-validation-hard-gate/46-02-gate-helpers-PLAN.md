---
phase: 46-ab-oos-validation-hard-gate
plan: 02
type: execute
wave: 2
depends_on: ["46-01-scenario-scaffold-PLAN"]
files_modified:
  - analysis/validate_v10.py
autonomous: true
requirements: [VAL-02, VAL-03, VAL-04]

must_haves:
  truths:
    - "load_hard_gate_thresholds() reads output/v10_reconciled_baseline.json and returns (cagr_floor, max_dd_ceiling) — NOT hardcoded 11.47"
    - "evaluate_hard_gate(metrics, thresholds) returns a 3-field verdict tuple (passed: bool, cagr_verdict: str, max_dd_verdict: str) for any scenario's metrics"
    - "lookup_walkforward_degradation() reads output/v10_grid_results.csv and returns (median_degradation, accepted) for the stage3_all_three-c1 row without re-running the sweep"
    - "run_parity_gate() invokes pytest on tests/test_macro_filter_v6_parity.py via subprocess and returns (returncode, captured_stdout_tail) — does NOT duplicate parity test logic"
    - "All four helpers are pure functions (no global state mutation) — callable independently by Plan 03 main() OR by a future ad-hoc debug session"
  artifacts:
    - path: "analysis/validate_v10.py"
      provides: "HARD gate + walk-forward + parity helper functions"
      contains: "def evaluate_hard_gate"
      min_lines: 250
  key_links:
    - from: "analysis/validate_v10.py::load_hard_gate_thresholds"
      to: "output/v10_reconciled_baseline.json"
      via: "json.load + reconciled_cagr_pct field read (D-05)"
      pattern: "reconciled_baseline\\[.?cagr_pct.?\\]"
    - from: "analysis/validate_v10.py::lookup_walkforward_degradation"
      to: "output/v10_grid_results.csv"
      via: "pd.read_csv + config_name filter = stage3_all_three-c1 (D-07)"
      pattern: "stage3_all_three-c1"
    - from: "analysis/validate_v10.py::run_parity_gate"
      to: "tests/test_macro_filter_v6_parity.py"
      via: "subprocess.run(['uv', 'run', 'python', '-m', 'pytest', ...]) (D-08)"
      pattern: "test_macro_filter_v6_parity"
---

<objective>
Add the four gate-evaluation helpers to `analysis/validate_v10.py` so Plan 03's main() can call each gate as a one-liner. Each helper is a pure function that reads external state (JSON, CSV, pytest subprocess) and returns a structured verdict — no side effects, no stdout, no module state mutation.

Purpose: Isolate gate logic from orchestration so the helpers can be unit-tested (this plan provides smoke tests via `python -c`) and so Plan 03's main() reads like a sequence of gate invocations rather than intermingled I/O + decision code.

Output: `analysis/validate_v10.py` extended with `load_hard_gate_thresholds()`, `evaluate_hard_gate()`, `lookup_walkforward_degradation()`, `run_parity_gate()`.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-01-scenario-scaffold-SUMMARY.md

@analysis/validate_v10.py
@analysis/validate_v9.py
@output/v10_reconciled_baseline.json
@tests/test_macro_filter_v6_parity.py

<interfaces>
<!-- External schemas the helpers consume. -->

From output/v10_reconciled_baseline.json (Phase 42 BASE-02 canonical tuple):
```json
{
  "schema_version": 1,
  "cagr_pct": 11.47,
  "max_dd_pct": -28.17,
  "sharpe_rf3": 0.502414,
  "sell_count": 124,
  "total_return_pct": 238.78,
  ...
  "reconciliation_outcome": "fixed_by_preset"
}
```
The `cagr_pct` field is the HARD gate CAGR floor (D-05). `max_dd_pct`
is baseline reference only — the HARD gate max_dd ceiling is a FIXED
-20.0 (D-05), not the baseline max_dd.

From output/v10_grid_results.csv (Phase 45 Plan 03 — 39 rows, gitignored-but-force-added):
```
Columns of interest:
  stage, combo_id, config_name   (identifier triple)
  dxy_easing_z_threshold, dxy_tightening_z_threshold, dxy_tightening_dd_threshold,
  eem_easing_z_threshold, eem_tightening_z_threshold,
  sbv_tightening_stop_loss_max_multiplier,
  (window/decay days — same as VN30_PRESET defaults)
  macro_filter_enabled   (True for all 39 rows)
  cagr_train_pct, sharpe_rf3_train, max_dd_train_pct
  cagr_eval_{2019,2020,2021,2022,2023,2024}_pct
  sharpe_rf3_eval_{2019..2024}
  max_dd_eval_{2019..2024}_pct
  degradation_{2019..2024}
  median_degradation         ← VAL-03 read key
  median_eval_cagr_pct
  eval_years_count
  accepted                   (False for all 39 rows under retain-v6.0 branch)
  rejection_reason           ('median_degradation 0.537 >= 0.30' for stage3_all_three-c1)
  error_train, error_year_{2019..2024}   (all blank — clean runs)
```
Lookup target (D-07): `config_name == 'stage3_all_three-c1'`.
This row has `median_degradation ≈ 0.5374873353596757`, `accepted == False`.

From tests/test_macro_filter_v6_parity.py (Phase 44 Plan 04):
5 tests under @pytest.mark.regression TestMacroFilterV6Parity class:
  - test_signal_log_byte_exact_with_macro_off
  - test_macro_columns_absent_when_disabled
  - test_signal_log_byte_exact_with_macro_on
  - test_macro_on_produces_macro_columns
  - test_macro_on_changes_at_least_one_signal

Pytest invocation (D-08):
  uv run python -m pytest tests/test_macro_filter_v6_parity.py -v
Exit code 0 = all pass; non-zero = VAL-04 gate fails.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add load_hard_gate_thresholds() + evaluate_hard_gate() helpers (VAL-02)</name>

  <read_first>
    - analysis/validate_v10.py (current state — scaffold + scenarios from Plan 01; pick an insertion point AFTER verify_extremes_never_trigger, BEFORE the EOF placeholder comment)
    - output/v10_reconciled_baseline.json (the JSON schema this helper reads)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-05 HARD gate spec)
    - .planning/phases/42-baseline-reconciliation/42-05*SUMMARY.md (context on why reconciled_cagr_pct=11.47 — Plan 42 audit pattern this plan extends)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `load_hard_gate_thresholds()` returns dict `{'cagr_floor': 11.47, 'max_dd_ceiling': -20.0, 'baseline_source': 'output/v10_reconciled_baseline.json'}` — the 11.47 comes from JSON, the -20.0 from the HARD_GATE_MAX_DD_CEILING module constant
    - `load_hard_gate_thresholds()` raises FileNotFoundError with remediation message when the JSON is missing
    - `load_hard_gate_thresholds()` raises KeyError with the missing field name when the JSON lacks `cagr_pct`
    - `evaluate_hard_gate(metrics, thresholds)` returns a dict: `{'passed': bool, 'cagr_pass': bool, 'max_dd_pass': bool, 'cagr_observed': float, 'max_dd_observed': float, 'cagr_required': float, 'max_dd_required': float, 'detail': str}`
    - `evaluate_hard_gate` pass rule: `cagr_observed >= cagr_required AND max_dd_observed > max_dd_required` (max_dd is negative; observed must be LESS NEGATIVE than the ceiling) — matches D-05 exactly
  </behavior>

  <action>
    Append to `analysis/validate_v10.py` (insert before the EOF Plan 02/03 placeholder comment):

    ```python
    # ═══════════════════════════════════════════════════════════════════════
    # Gate helpers (Plan 02) — pure functions consumed by Plan 03 main()
    # ═══════════════════════════════════════════════════════════════════════

    def load_hard_gate_thresholds() -> dict:
        """Load VAL-02 HARD gate thresholds per D-05.

        CAGR floor comes from output/v10_reconciled_baseline.json (Phase 42
        BASE-02 canonical tuple) so we never hardcode 11.47 in this script —
        any future reconciliation re-run updates the gate automatically.
        MaxDD ceiling is the module constant HARD_GATE_MAX_DD_CEILING = -20.0
        (milestone decision, not subject to baseline drift).

        Returns:
            Dict with:
              cagr_floor: float (from reconciled baseline cagr_pct field)
              max_dd_ceiling: float (HARD_GATE_MAX_DD_CEILING, always -20.0)
              baseline_source: str (the JSON path, for report provenance)
              schema_version: int (from JSON, for compatibility tracking)

        Raises:
            FileNotFoundError: if RECONCILED_BASELINE_JSON missing (message
                points to Phase 42 Plan 42-05 as the owner).
            KeyError: if JSON lacks 'cagr_pct' key (schema drift — fail loud).
        """
        if not os.path.exists(RECONCILED_BASELINE_JSON):
            raise FileNotFoundError(
                f"{RECONCILED_BASELINE_JSON} not found. "
                "Phase 42 Plan 42-05 owns this artifact; verify "
                "output/v10_reconciled_baseline.json exists (force-added past "
                "output/ gitignore) before running Phase 46 validation."
            )
        with open(RECONCILED_BASELINE_JSON, 'r', encoding='utf-8') as f:
            baseline = json.load(f)
        if 'cagr_pct' not in baseline:
            raise KeyError(
                f"'cagr_pct' missing from {RECONCILED_BASELINE_JSON}. "
                f"Found keys: {sorted(baseline.keys())}. Schema drift — "
                "check Phase 42 BASE-02 contract."
            )
        return {
            'cagr_floor': float(baseline['cagr_pct']),
            'max_dd_ceiling': HARD_GATE_MAX_DD_CEILING,
            'baseline_source': RECONCILED_BASELINE_JSON,
            'schema_version': baseline.get('schema_version', None),
        }


    def evaluate_hard_gate(metrics: dict, thresholds: dict) -> dict:
        """Evaluate VAL-02 HARD gate against a single scenario's metrics.

        D-05 rule: pass iff
          (cagr_pct >= cagr_floor) AND (max_dd_pct > max_dd_ceiling)
        where max_dd_pct and max_dd_ceiling are both negative; "strictly
        less negative" means "observed drawdown shallower than the -20% cap".

        Args:
            metrics: Dict from compute_metrics() — must have 'cagr_pct' and
                'max_dd_pct' keys (float percent values; e.g. 11.47 and -28.17).
            thresholds: Dict from load_hard_gate_thresholds() — must have
                'cagr_floor' and 'max_dd_ceiling'.

        Returns:
            Dict with:
              passed: bool — True iff both sub-gates pass
              cagr_pass: bool
              max_dd_pass: bool
              cagr_observed: float
              max_dd_observed: float
              cagr_required: float (>=)
              max_dd_required: float (strictly > i.e. shallower-than)
              detail: str — one-line human summary for the report
        """
        cagr_obs = float(metrics['cagr_pct'])
        max_dd_obs = float(metrics['max_dd_pct'])
        cagr_req = float(thresholds['cagr_floor'])
        max_dd_req = float(thresholds['max_dd_ceiling'])

        cagr_pass = cagr_obs >= cagr_req
        # max_dd_obs and max_dd_req both negative. 'shallower' = less negative = greater.
        max_dd_pass = max_dd_obs > max_dd_req
        passed = cagr_pass and max_dd_pass

        cagr_glyph = '✓' if cagr_pass else '✗'
        maxdd_glyph = '✓' if max_dd_pass else '✗'
        detail = (
            f"CAGR {cagr_glyph} {cagr_obs:.2f}% vs floor {cagr_req:.2f}% | "
            f"MaxDD {maxdd_glyph} {max_dd_obs:.2f}% vs ceiling {max_dd_req:.2f}%"
        )

        return {
            'passed': passed,
            'cagr_pass': cagr_pass,
            'max_dd_pass': max_dd_pass,
            'cagr_observed': cagr_obs,
            'max_dd_observed': max_dd_obs,
            'cagr_required': cagr_req,
            'max_dd_required': max_dd_req,
            'detail': detail,
        }
    ```
  </action>

  <verify>
    <automated>uv run python -c "
from analysis.validate_v10 import load_hard_gate_thresholds, evaluate_hard_gate

# Real load from disk
th = load_hard_gate_thresholds()
assert th['cagr_floor'] == 11.47, f'expected 11.47 from JSON, got {th[\"cagr_floor\"]}'
assert th['max_dd_ceiling'] == -20.0, f'expected -20.0 constant, got {th[\"max_dd_ceiling\"]}'
assert 'v10_reconciled_baseline.json' in th['baseline_source']

# Gate: scenario passes (e.g. CAGR 12.0%, MaxDD -18%)
r1 = evaluate_hard_gate({'cagr_pct': 12.0, 'max_dd_pct': -18.0}, th)
assert r1['passed'] is True
assert r1['cagr_pass'] is True
assert r1['max_dd_pass'] is True

# Gate: CAGR fails (11.0 < 11.47)
r2 = evaluate_hard_gate({'cagr_pct': 11.0, 'max_dd_pct': -18.0}, th)
assert r2['passed'] is False
assert r2['cagr_pass'] is False
assert r2['max_dd_pass'] is True

# Gate: MaxDD fails (-22 < -20 ceiling, i.e. deeper than cap)
r3 = evaluate_hard_gate({'cagr_pct': 12.0, 'max_dd_pct': -22.0}, th)
assert r3['passed'] is False
assert r3['cagr_pass'] is True
assert r3['max_dd_pass'] is False

# Gate: boundary exact cagr (11.47 == 11.47 must pass since rule is >=)
r4 = evaluate_hard_gate({'cagr_pct': 11.47, 'max_dd_pct': -19.99}, th)
assert r4['passed'] is True

# Gate: boundary MaxDD (-20.0 exactly must FAIL since rule is > not >=)
r5 = evaluate_hard_gate({'cagr_pct': 12.0, 'max_dd_pct': -20.0}, th)
assert r5['max_dd_pass'] is False, 'MaxDD=-20.0 exactly must FAIL per D-05 strict inequality'

# Expected Phase 46 baseline scenario (CAGR 11.47%, MaxDD -28.17% from reconciled baseline) — MUST FAIL on max_dd
r6 = evaluate_hard_gate({'cagr_pct': 11.47, 'max_dd_pct': -28.17}, th)
assert r6['passed'] is False
assert r6['cagr_pass'] is True
assert r6['max_dd_pass'] is False
print('HARD GATE helper: 6/6 cases PASS')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def load_hard_gate_thresholds" analysis/validate_v10.py` returns 1 hit
    - `grep -n "def evaluate_hard_gate" analysis/validate_v10.py` returns 1 hit
    - `grep -n "baseline\\['cagr_pct'\\]\\|baseline.get.'cagr_pct'." analysis/validate_v10.py` returns at least 1 hit (reads the JSON field, NOT hardcoded 11.47)
    - `grep -cn "11.47" analysis/validate_v10.py` returns 0 (no hardcoded 11.47 ANYWHERE in the file — all CAGR floor values come from JSON at runtime)
    - Verify command prints `HARD GATE helper: 6/6 cases PASS` with exit code 0
    - Boundary case CAGR=11.47 exactly PASSES (>= inequality)
    - Boundary case MaxDD=-20.0 exactly FAILS (> strict inequality)
    - File load raises FileNotFoundError (not generic IOError) when JSON is missing — confirmed by inspection that the raise statement uses `FileNotFoundError`
  </acceptance_criteria>

  <done>HARD gate helpers land; CAGR floor drawn from reconciled baseline JSON (no 11.47 literal in script); 6 boundary cases validated including the expected Phase 46 retain-v6.0 outcome (CAGR pass, MaxDD fail).</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Add lookup_walkforward_degradation() helper (VAL-03)</name>

  <read_first>
    - analysis/validate_v10.py (current state — HARD gate helpers from Task 1)
    - output/v10_grid_results.csv (peek row 39 config_name=stage3_all_three-c1; header row has 52 columns — only need config_name, median_degradation, accepted, rejection_reason)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-07 locks the lookup target row)
    - .planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md (lines 97-103 confirm 0/39 accepted, median_degradation 0.5374... for stage3_all_three)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `lookup_walkforward_degradation()` returns dict `{'combo': 'stage3_all_three-c1', 'median_degradation': 0.5374873353596757, 'accepted': False, 'rejection_reason': 'median_degradation 0.537 >= 0.30', 'passed_gate': False, 'threshold': 0.30, 'source_csv': 'output/v10_grid_results.csv', 'total_combos': 39, 'total_accepted': 0}`
    - `passed_gate` is `median_degradation < 0.30` — implements D-07 gate rule directly (not relying on the CSV's own `accepted` column, which uses the composite D-09 rule from Phase 45)
    - Raises FileNotFoundError when CSV is missing, with Phase 45 Plan 03 pointer
    - Raises ValueError when the stage3_all_three-c1 row is not present (schema drift)
  </behavior>

  <action>
    Append to `analysis/validate_v10.py` (after evaluate_hard_gate):

    ```python
    def lookup_walkforward_degradation(combo_name: str = None) -> dict:
        """Read walk-forward median_degradation for the +all defaults combo (VAL-03 per D-07).

        Does NOT re-run the 39-combo sweep. Reads the row of
        output/v10_grid_results.csv whose config_name matches
        WALKFORWARD_VN30_PRESET_COMBO (default 'stage3_all_three-c1' —
        matches VN30_PRESET defaults: dxy_easing=-1.0, dxy_tightening=+1.0,
        dxy_tightening_dd=3, eem_easing=+1.0, eem_tightening=-1.0,
        sbv_mult=1.5).

        VAL-03 gate rule (D-07): pass iff median_degradation < 0.30. The CSV's
        own 'accepted' column uses the Phase 45 D-09 composite gate
        (median_degradation < 0.30 AND median_eval_cagr > 0.0); for VAL-03 we
        apply only the degradation half so the gate is interpretable in
        isolation as "walk-forward stability".

        Args:
            combo_name: Override for the target row's config_name. Default
                None → uses WALKFORWARD_VN30_PRESET_COMBO.

        Returns:
            Dict with:
              combo: str                (resolved config_name)
              median_degradation: float (from CSV)
              accepted: bool            (from CSV's own composite D-09 column)
              rejection_reason: str     (from CSV; empty string if accepted)
              passed_gate: bool         (VAL-03 rule: median_degradation < 0.30)
              threshold: float          (WALKFORWARD_DEGRADATION_THRESHOLD = 0.30)
              source_csv: str           (provenance)
              total_combos: int         (row count in CSV)
              total_accepted: int       (sum of CSV's accepted column)

        Raises:
            FileNotFoundError: if WALKFORWARD_GRID_CSV missing (points to
                Phase 45 Plan 03 as owner).
            ValueError: if combo_name not found in the CSV (schema drift).
        """
        target = combo_name if combo_name is not None else WALKFORWARD_VN30_PRESET_COMBO

        if not os.path.exists(WALKFORWARD_GRID_CSV):
            raise FileNotFoundError(
                f"{WALKFORWARD_GRID_CSV} not found. "
                "Phase 45 Plan 03 owns this artifact; re-run "
                "`uv run python analysis/walkforward_grid.py` to regenerate "
                "(or git log for commit 4dd00a0 which force-added it)."
            )

        df = pd.read_csv(WALKFORWARD_GRID_CSV)
        matches = df[df['config_name'] == target]
        if len(matches) == 0:
            available = sorted(df['config_name'].unique().tolist())[:10]
            raise ValueError(
                f"config_name='{target}' not found in {WALKFORWARD_GRID_CSV}. "
                f"First 10 available: {available}. "
                "Check Phase 45 D-07 combo-naming scheme."
            )
        if len(matches) > 1:
            raise ValueError(
                f"config_name='{target}' matches {len(matches)} rows; "
                "expected exactly 1. CSV has non-unique config_name (schema drift)."
            )

        row = matches.iloc[0]
        median_deg = float(row['median_degradation'])
        # CSV's 'accepted' is a boolean column; pandas loads it as str or bool
        # depending on dtype inference. Normalise.
        raw_accepted = row['accepted']
        if isinstance(raw_accepted, str):
            accepted = raw_accepted.strip().lower() == 'true'
        else:
            accepted = bool(raw_accepted)
        rejection_reason = (
            str(row['rejection_reason']) if pd.notna(row['rejection_reason']) else ''
        )

        # Aggregate CSV counts for report context
        if df['accepted'].dtype == object:
            total_accepted = int((df['accepted'].astype(str).str.lower() == 'true').sum())
        else:
            total_accepted = int(df['accepted'].sum())

        return {
            'combo': target,
            'median_degradation': median_deg,
            'accepted': accepted,
            'rejection_reason': rejection_reason,
            'passed_gate': median_deg < WALKFORWARD_DEGRADATION_THRESHOLD,
            'threshold': WALKFORWARD_DEGRADATION_THRESHOLD,
            'source_csv': WALKFORWARD_GRID_CSV,
            'total_combos': int(len(df)),
            'total_accepted': total_accepted,
        }
    ```
  </action>

  <verify>
    <automated>uv run python -c "
from analysis.validate_v10 import lookup_walkforward_degradation

# Read the real CSV and verify retain-v6.0 expected outcome
r = lookup_walkforward_degradation()
assert r['combo'] == 'stage3_all_three-c1', f'expected stage3_all_three-c1, got {r[\"combo\"]}'
assert 0.53 < r['median_degradation'] < 0.54, f'expected ~0.537, got {r[\"median_degradation\"]}'
assert r['accepted'] is False, 'retain-v6.0 branch requires accepted=False'
assert r['passed_gate'] is False, 'VAL-03 gate must fail — median_deg ~0.537 > 0.30'
assert r['threshold'] == 0.30
assert r['total_combos'] == 39, f'expected 39 combos, got {r[\"total_combos\"]}'
assert r['total_accepted'] == 0, f'expected 0 accepted combos, got {r[\"total_accepted\"]}'
assert 'median_degradation' in r['rejection_reason'].lower() or r['rejection_reason'] != ''
print(f'VAL-03 lookup: median_deg={r[\"median_degradation\"]:.4f}, accepted={r[\"accepted\"]}, passed_gate={r[\"passed_gate\"]}')

# Override: nonexistent combo raises ValueError
try:
    lookup_walkforward_degradation('nonexistent-combo-xyz')
    raise SystemExit('expected ValueError for missing combo')
except ValueError as e:
    assert 'nonexistent-combo-xyz' in str(e)
    assert 'First 10 available' in str(e)

print('VAL-03 helper: 2/2 cases PASS')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def lookup_walkforward_degradation" analysis/validate_v10.py` returns 1 hit
    - `grep -n "WALKFORWARD_VN30_PRESET_COMBO" analysis/validate_v10.py` returns at least 2 hits (one in module constants from Plan 01, one in this helper as default arg or constant reference)
    - `grep -n "median_degradation < WALKFORWARD_DEGRADATION_THRESHOLD" analysis/validate_v10.py` returns 1 hit (explicit D-07 rule, not delegating to CSV's accepted column)
    - Verify command prints BOTH `VAL-03 lookup: median_deg=0.5375, accepted=False, passed_gate=False` AND `VAL-03 helper: 2/2 cases PASS` with exit code 0 (allow floating-point precision in printed value)
    - CSV loads 39 rows with 0 accepted — confirms retain-v6.0 evidence surface is intact
    - Missing-combo path raises ValueError, NOT KeyError or pandas IndexError
  </acceptance_criteria>

  <done>VAL-03 reads Phase 45 CSV, applies the < 0.30 degradation gate, and returns structured verdict including the rejection_reason text for the Plan 03 report. Confirmed on the retain-v6.0 evidence row.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Add run_parity_gate() subprocess helper (VAL-04)</name>

  <read_first>
    - analysis/validate_v10.py (current state — helpers from Tasks 1, 2)
    - tests/test_macro_filter_v6_parity.py (the test file to invoke — 5 tests under @pytest.mark.regression)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-08 — no new parity test, reuse existing Phase 44 Plan 04 test)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `run_parity_gate()` invokes `uv run python -m pytest tests/test_macro_filter_v6_parity.py -v` via subprocess.run
    - Returns dict `{'passed': bool, 'returncode': int, 'stdout_tail': str, 'stderr_tail': str, 'tests_passed': int, 'tests_failed': int, 'test_file': 'tests/test_macro_filter_v6_parity.py', 'duration_sec': float}`
    - `passed` is `returncode == 0`
    - `stdout_tail` contains last ~50 lines of pytest output (for the Plan 03 report to inline)
    - Does NOT duplicate parity logic — just shells out to the existing test (D-08)
    - Timeout: 300 seconds (test historically runs in ~90s; give 3× margin)
  </behavior>

  <action>
    Append to `analysis/validate_v10.py` (after lookup_walkforward_degradation):

    ```python
    def run_parity_gate(timeout_sec: int = 300) -> dict:
        """Invoke the Phase 44 parity pytest as the VAL-04 gate (D-08).

        Does NOT duplicate parity logic. Shells out to:
            uv run python -m pytest tests/test_macro_filter_v6_parity.py -v

        Exit code 0 = all 5 tests pass = VAL-04 gate PASS.
        Any non-zero = any test failure = VAL-04 gate FAIL (blocks acceptance
        per the v10.0 HARD gate contract regardless of VAL-01..03 outcome).

        Args:
            timeout_sec: Max seconds to wait. Historical runtime ~90s;
                default 300 gives 3× margin for slow CI.

        Returns:
            Dict with:
              passed: bool          (returncode == 0)
              returncode: int
              stdout_tail: str      (last ~50 lines of stdout)
              stderr_tail: str      (last ~50 lines of stderr)
              tests_passed: int     (parsed from pytest summary; -1 if unparseable)
              tests_failed: int     (parsed from pytest summary; -1 if unparseable)
              test_file: str        (PARITY_TEST_PATH)
              duration_sec: float   (wall-clock subprocess time)

        Does NOT raise — subprocess failures (pytest not installed, test file
        missing, timeout) are captured in the return dict for report inclusion.
        """
        import time
        import re as _re

        cmd = [
            'uv', 'run', 'python', '-m', 'pytest',
            PARITY_TEST_PATH, '-v', '--tb=short',
        ]
        start = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
            )
            rc = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired as exc:
            rc = -1
            stdout = (exc.stdout or '') + f"\n[TIMEOUT after {timeout_sec}s]"
            stderr = (exc.stderr or '') + f"\n[TIMEOUT after {timeout_sec}s]"
        except FileNotFoundError as exc:
            # 'uv' not in PATH or similar — capture and fail the gate
            rc = -2
            stdout = ''
            stderr = f"[subprocess FileNotFoundError: {exc}]"

        duration = time.time() - start

        # Tail helpers (last N lines)
        def _tail(text: str, n: int = 50) -> str:
            if not text:
                return ''
            lines = text.splitlines()
            return '\n'.join(lines[-n:])

        # Parse pytest summary line: "5 passed in 90.2s" or "4 passed, 1 failed in ..."
        tests_passed = -1
        tests_failed = -1
        if stdout:
            # Look for the final summary line
            passed_match = _re.search(r'(\d+) passed', stdout)
            failed_match = _re.search(r'(\d+) failed', stdout)
            if passed_match:
                tests_passed = int(passed_match.group(1))
            if failed_match:
                tests_failed = int(failed_match.group(1))
            # If no 'failed' token found AND 'passed' found AND rc==0, set failed=0
            if tests_passed >= 0 and tests_failed == -1 and rc == 0:
                tests_failed = 0

        return {
            'passed': rc == 0,
            'returncode': rc,
            'stdout_tail': _tail(stdout, 50),
            'stderr_tail': _tail(stderr, 50),
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'test_file': PARITY_TEST_PATH,
            'duration_sec': duration,
        }
    ```

    NOTE: The subprocess `cwd` is set to the repo root so `uv` and pytest find `pyproject.toml`. The test file path is relative to that cwd.
  </action>

  <verify>
    <automated>uv run python -c "
from analysis.validate_v10 import run_parity_gate

# Run the real pytest subprocess — historically ~90s, may be longer on first cache build
result = run_parity_gate(timeout_sec=300)
print(f'returncode={result[\"returncode\"]}  tests_passed={result[\"tests_passed\"]}  tests_failed={result[\"tests_failed\"]}  duration={result[\"duration_sec\"]:.1f}s')
print('stdout tail (last 5 lines):')
print('\n'.join(result['stdout_tail'].splitlines()[-5:]))

assert result['test_file'] == 'tests/test_macro_filter_v6_parity.py'
assert result['returncode'] == 0, f'VAL-04 parity gate FAILED: rc={result[\"returncode\"]}\\nstderr:\\n{result[\"stderr_tail\"]}'
assert result['passed'] is True
assert result['tests_passed'] >= 5, f'expected >=5 tests passed, got {result[\"tests_passed\"]}'
assert result['tests_failed'] == 0
print('VAL-04 helper: subprocess gate PASS')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def run_parity_gate" analysis/validate_v10.py` returns 1 hit
    - `grep -n "subprocess.run" analysis/validate_v10.py` returns at least 1 hit (D-08 subprocess invocation)
    - `grep -n "tests/test_macro_filter_v6_parity.py" analysis/validate_v10.py` returns at least 1 hit (via PARITY_TEST_PATH constant)
    - `grep -n "capture_output=True" analysis/validate_v10.py` returns 1 hit
    - Verify command completes successfully with `VAL-04 helper: subprocess gate PASS` on exit code 0
    - Printed `returncode=0` AND `tests_passed>=5` AND `tests_failed=0` (proves the 5 parity tests from Phase 44 Plan 04 still pass)
    - Duration < 300 seconds (within the configured timeout)
    - NO duplication of parity assertion logic inside validate_v10.py: `grep -n "def test_signal_log_byte_exact\\|df.equals\\|test_macro_columns_absent" analysis/validate_v10.py` returns 0 hits (except for trivial string references in comments/docstrings)
  </acceptance_criteria>

  <done>VAL-04 gate invokes existing Phase 44 parity pytest via subprocess, captures returncode + summary counts + stdout tail for the validation report. No parity logic duplicated.</done>
</task>

</tasks>

<verification>
After all 3 tasks:

1. All four gate helpers importable and callable:
   ```
   uv run python -c "
   from analysis.validate_v10 import (
       load_hard_gate_thresholds, evaluate_hard_gate,
       lookup_walkforward_degradation, run_parity_gate,
   )
   th = load_hard_gate_thresholds()
   wf = lookup_walkforward_degradation()
   parity = run_parity_gate()
   print(f'HARD gate floor: {th[\"cagr_floor\"]}% CAGR, {th[\"max_dd_ceiling\"]}% MaxDD')
   print(f'VAL-03 walk-forward: median_deg={wf[\"median_degradation\"]:.4f}, passed_gate={wf[\"passed_gate\"]}')
   print(f'VAL-04 parity: passed={parity[\"passed\"]} ({parity[\"tests_passed\"]}/{parity[\"tests_passed\"]+parity[\"tests_failed\"]} tests)')
   "
   ```
   Must exit 0 and print three lines with real values.

2. No hardcoded 11.47 in file: `grep -cn "11\\.47" analysis/validate_v10.py` returns 0.

3. Regression tests still green (no side effects from helper additions):
   `uv run pytest -m regression tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v` — all 8 tests PASS.
</verification>

<success_criteria>
- [ ] `load_hard_gate_thresholds()` reads CAGR floor from JSON (not hardcoded 11.47)
- [ ] `evaluate_hard_gate()` implements D-05 rule (CAGR >= floor AND MaxDD > ceiling) with correct boundary semantics
- [ ] `lookup_walkforward_degradation()` reads Phase 45 CSV and returns structured verdict; does NOT re-run the sweep
- [ ] `run_parity_gate()` invokes existing pytest via subprocess; does NOT duplicate parity logic
- [ ] All four helpers are pure functions (no mutation of global state)
- [ ] Smoke tests in each task's verify block prove helpers behave correctly against real disk state
- [ ] Pre-existing regression tests remain green
</success_criteria>

<output>
After completion, create `.planning/phases/46-ab-oos-validation-hard-gate/46-02-gate-helpers-SUMMARY.md`
</output>
