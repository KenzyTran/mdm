---
phase: 44
plan: 04
type: execute
wave: 4
depends_on: ["44-03"]
files_modified:
  - tests/test_macro_filter_v6_parity.py
  - .planning/phases/44-macro-filter-module/44-VALIDATION.md
autonomous: true
requirements: [MACRO-04]
must_haves:
  truths:
    - "Parity regression test (tests/test_macro_filter_v6_parity.py) is the formal sign-off for MACRO-04 / VAL-04 alignment"
    - "Two fresh HybridEngine runs with macro_filter_enabled=False AND v60_strict_mode=True produce byte-exact equal results DataFrames on full VN30 2015-2026"
    - "No dxy_z / eem_z / sbv_regime columns leak into results when macro_filter_enabled=False (D-09 dual-layer gate verified)"
    - "Smoke test for macro_filter_enabled=True confirms the engine runs end-to-end on full VN30 2015-2026 without crashing AND produces the expected new columns"
    - "Test suite is run with @pytest.mark.regression marker so it can be invoked separately from the unit suite (matches Phase 42 D-17 precedent)"
    - "All Phase 44 deliverables are now committed and verified — parity invariant locked"
    - "VALIDATION.md frontmatter shows nyquist_compliant=true, wave_0_complete=true, status=approved (closes plan-checker WARNING 2)"
    - "VALIDATION.md per-task verification map has correct task IDs (44-02-* / 44-03-* / 44-04-*) — no stale 44-01-* placeholder IDs remain"
  artifacts:
    - path: "tests/test_macro_filter_v6_parity.py"
      provides: "Final parity regression test suite for MACRO-04 / VAL-04"
      contains: "test_signal_log_byte_exact_with_macro_off"
      min_lines: 100
    - path: ".planning/phases/44-macro-filter-module/44-VALIDATION.md"
      provides: "Phase 44 validation sign-off — frontmatter flipped to approved + task IDs renumbered to match actual plan structure"
      contains: "nyquist_compliant: true"
  key_links:
    - from: "tests/test_macro_filter_v6_parity.py::TestMacroFilterV6Parity"
      to: "Plan 03 engine integration (HybridEngine with macro_filter_enabled=False)"
      via: "Two fresh _run_once() calls + df.equals(df) byte-exact assertion"
      pattern: "results_1\\.equals\\(results_2\\)"
    - from: "tests/test_macro_filter_v6_parity.py::test_macro_columns_absent_when_disabled"
      to: "Plan 03 engine D-09 dual-layer gate"
      via: "Asserts dxy_z/eem_z/sbv_regime NOT in results.columns when feature off"
      pattern: "col not in results\\.columns"
---

<objective>
Final regression sign-off for Phase 44. Plan 02 Task 3 created the test stubs in `tests/test_macro_filter_v6_parity.py`; Plan 03 wired the engine integration that makes the parity invariant meaningful. This plan EXTENDS the existing test file with:

1. A smoke-test for the macro-on path so Plan 03's enabled-path coverage is committed (current parity test only exercises the disabled path)
2. A "non-trivial change when enabled" sanity assertion proving MacroFilter actually moves the needle on at least one signal when turned on (catches the scenario where a future refactor accidentally makes the engine ignore macro_verdict)
3. A 3-run determinism check for the enabled path (matches Phase 42 D-17 precedent for the disabled path)

Per CONTEXT.md MACRO-04 success criterion: "running the engine on VN30 2015-2026 with the flag False produces a signal log byte-exact to the reconciled v6.0 baseline from Phase 42 (regression test locks this invariant — VAL-04 alignment)". This plan is the lockdown.

Per RESEARCH §"State of the Art", the parity test does NOT need to read `output/v10_reconciled_baseline.json` — the parity invariant is "two macro-off runs are byte-exact" via df.equals, NOT "macro-off run matches a hardcoded number". The JSON consumption is for Phase 46 HARD gate.

Purpose: Lock down the byte-exact parity invariant + guarantee the macro-on path runs correctly + prove MacroFilter actually does something when enabled. After this plan, all 5 ROADMAP success criteria for Phase 44 are met:
- SC-1: DXY 20d z-score column verified (Plan 02 Task 3 unit tests)
- SC-2: EEM 20d z-score column verified (Plan 02 Task 3 unit tests)
- SC-3: SBV regime classifier verified (Plan 02 Task 3 unit tests)
- SC-4: MacroFilter integrated into HybridEngine + v6.0 parity verified (Plan 03 + this plan)
- SC-5: Filter policy implemented + 6 thresholds exposed (Plan 02 Task 1 + Plan 03 Task 1)

Output: 1 file extended (test_macro_filter_v6_parity.py — adds 2 new test methods to existing class).
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/44-macro-filter-module/44-CONTEXT.md
@.planning/phases/44-macro-filter-module/44-RESEARCH.md
@.planning/phases/44-macro-filter-module/44-VALIDATION.md

@tests/test_macro_filter_v6_parity.py
@tests/test_baseline_determinism.py
@strategies/mdm_hybrid/mdm_hybrid_engine.py
@strategies/mdm_hybrid/config.py
@strategies/mdm_hybrid/macro_filter.py

<interfaces>
<!-- Test contract verified end of Plan 03. -->

From tests/test_macro_filter_v6_parity.py (Plan 02 Task 3 stub, activated by Plan 03):
```python
@pytest.mark.regression
class TestMacroFilterV6Parity:
    @pytest.fixture(scope='class')
    def prepared_df(self) -> pd.DataFrame: ...

    def test_signal_log_byte_exact_with_macro_off(self, prepared_df):
        """Two fresh-engine macro-off runs → byte-exact equal results."""

    def test_macro_columns_absent_when_disabled(self, prepared_df):
        """D-09: no dxy_z / eem_z / sbv_regime columns when feature off."""
```

The class already has:
- _build_macro_off_cfg() → MDMV2Config with macro_filter_enabled=False, v60_strict_mode=True
- _run_once(df) → fresh HybridEngine, returns results

This plan ADDS:
- _build_macro_on_cfg() → mirrors _build_macro_off_cfg but with macro_filter_enabled=True
- _run_once_macro_on(df) → fresh HybridEngine with macro on
- test_signal_log_byte_exact_with_macro_on(prepared_df) — D-17 determinism for enabled path
- test_macro_on_produces_macro_columns(prepared_df) — proves columns ARE added when enabled
- test_macro_on_changes_at_least_one_signal(prepared_df) — proves MacroFilter has actual effect

DataLoader contract (verified via test_baseline_determinism.py:180):
- DataLoader('vn30').load('2015-01-05', '2026-03-31') returns DataFrame with date column
- build_indicator_dataframe(df) returns df enriched with indicators
- Test fixture is class-scoped to avoid 4× expensive reload across tests
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend tests/test_macro_filter_v6_parity.py with macro-on smoke + determinism + effect-proof tests</name>
  <files>tests/test_macro_filter_v6_parity.py</files>
  <read_first>
    - tests/test_macro_filter_v6_parity.py (Plan 02 Task 3 stub + Plan 03 activation — currently has 2 test methods inside TestMacroFilterV6Parity class, both for the macro-off path; this task ADDS 3 new test methods to the same class)
    - tests/test_baseline_determinism.py (full file — pattern source for `_run_once`, class fixture, df.equals assertion at line 229; D-17 byte-exact determinism pattern at line 184-223)
    - .planning/phases/44-macro-filter-module/44-CONTEXT.md §D-09 (parity invariant scope)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Code Examples §Common Operation 3" (verbatim parity test pattern, lines 693-763)
    - .planning/phases/44-macro-filter-module/44-RESEARCH.md §"Common Pitfalls §Pitfall 8" (v60_strict_mode requirement in parity-test fixture, lines 481-499)
    - strategies/mdm_hybrid/macro_filter.py (post-Plan 03 — to confirm the columns add_macro_columns produces: dxy_z, eem_z, sbv_regime, sbv_days_since_event)
  </read_first>
  <behavior>
    - Test 1 (test_signal_log_byte_exact_with_macro_on): With macro_filter_enabled=True + v60_strict_mode=True, two fresh engine runs on full VN30 2015-2026 produce df.equals(df)=True (D-17 determinism for enabled path — engine must be deterministic with macro on too)
    - Test 2 (test_macro_on_produces_macro_columns): With macro_filter_enabled=True, results DataFrame DOES contain dxy_z, eem_z, sbv_regime columns (proves precompute gate fires when enabled — opposite of test_macro_columns_absent_when_disabled)
    - Test 3 (test_macro_on_changes_at_least_one_signal): With macro_filter_enabled=True, the results DataFrame differs from the macro-off run on at least one row's state/action column (proves MacroFilter actually does SOMETHING — defends against the silent-no-op refactor scenario where MacroVerdict gets created but never read by the engine)
  </behavior>
  <action>
    Open the EXISTING `tests/test_macro_filter_v6_parity.py` (created in Plan 02 Task 3, activated in Plan 03). The current file ends with the `test_macro_columns_absent_when_disabled` method inside `TestMacroFilterV6Parity` class.

    APPEND a new helper function (module-level, AFTER `_run_once`) and 3 new test methods (inside the class, AFTER the existing 2):

    Add module-level helper AFTER existing `_run_once` function definition:
    ```python


    def _build_macro_on_cfg() -> MDMV2Config:
        """Reconciled v6.0 preset with macro filter EXPLICITLY enabled.

        Mirrors _build_macro_off_cfg with macro_filter_enabled=True and DEFAULT
        threshold values from D-15 (no override of dxy_easing_z_threshold etc.).
        v60_strict_mode=True per Phase 42-04 contract (RESEARCH.md Pitfall 8).
        """
        overrides = dict(
            atr_buffer_enabled=False,
            refined_dd_enabled=False,
            macro_filter_enabled=True,   # Phase 44 — flip the feature gate ON
        )
        if 'v60_strict_mode' in MDMV2Config.__dataclass_fields__:
            overrides['v60_strict_mode'] = True
        return replace(VN30_PRESET, **overrides)


    def _run_once_macro_on(df: pd.DataFrame) -> pd.DataFrame:
        """Fresh HybridEngine with macro_filter_enabled=True -> .run(df.copy())."""
        engine = HybridEngine(HybridConfig(
            v2_config=_build_macro_on_cfg(),
            two_phase_enabled=True,
            filter_enabled=False,
        ))
        return engine.run(df.copy())
    ```

    APPEND inside `TestMacroFilterV6Parity` class, AFTER `test_macro_columns_absent_when_disabled`:

    ```python

        def test_signal_log_byte_exact_with_macro_on(self, prepared_df):
            """D-17 determinism for the macro-on path.

            Two fresh-engine runs with macro_filter_enabled=True produce
            byte-exact equal results DataFrames. If this fails, MacroFilter has
            non-deterministic state (e.g., reading wall-clock time, depending on
            dict iteration order, mutating the input DataFrame). Determinism is
            a PRE-REQUISITE for Phase 45 walk-forward grid search and Phase 46
            OOS HARD gate reproducibility.

            Note: this is NOT a parity test (the disabled-path test above
            covers parity). This is a determinism test for the ENABLED path —
            different invariant, same `df.equals()` mechanism per Phase 42 D-17.
            """
            results_1 = _run_once_macro_on(prepared_df)
            results_2 = _run_once_macro_on(prepared_df)
            assert results_1.equals(results_2), (
                "Signal log DataFrames differ between two macro-on runs. "
                "Engine is non-deterministic with MacroFilter enabled — Phase 45 "
                "grid search and Phase 46 HARD gate reproducibility are blocked."
            )

        def test_macro_on_produces_macro_columns(self, prepared_df):
            """D-09 dual-layer gate fires correctly when enabled — opposite of
            test_macro_columns_absent_when_disabled.

            With macro_filter_enabled=True, the precompute gate in
            HybridEngine.run() (Plan 03 INSERTION 3) calls add_macro_columns
            and the resulting DataFrame contains the new columns.
            """
            results = _run_once_macro_on(prepared_df)
            for col in ('dxy_z', 'eem_z', 'sbv_regime'):
                assert col in results.columns, (
                    f"Column '{col}' MISSING when macro_filter_enabled=True. "
                    f"Plan 03 INSERTION 3 (precompute gate around add_macro_columns) "
                    f"either skipped or the helper was not invoked."
                )
            # Sanity: dxy_z / eem_z must have non-NaN values somewhere (not all warm-up)
            assert results['dxy_z'].notna().any(), 'dxy_z column is all NaN — z-score warm-up never completed'
            assert results['eem_z'].notna().any(), 'eem_z column is all NaN — z-score warm-up never completed'
            # Sanity: sbv_regime must include all 3 regime labels at some point in 2015-2026 history
            # (12 SBV events across 2017-2023 → easing AND tightening both occur AND some neutral periods)
            regimes = set(results['sbv_regime'].dropna().unique())
            assert 'neutral' in regimes, f'sbv_regime never neutral: {regimes}'
            # easing OR tightening must appear (12 events span both directions)
            assert ('easing' in regimes) or ('tightening' in regimes), (
                f'sbv_regime never had any directional regime (only {regimes}); '
                f'90-day decay may have collapsed everything to neutral'
            )

        def test_macro_on_changes_at_least_one_signal(self, prepared_df):
            """MacroFilter has actual effect when enabled — defends against
            silent-no-op refactor.

            The macro-on signal log MUST differ from the macro-off signal log
            on at least one row in (state, action) columns. If they're identical,
            either:
              (a) MacroFilter.apply always returns pass_through even when
                  macro_filter_enabled=True (e.g., short-circuit guard inverted)
              (b) The engine ignores macro_verdict (e.g., INSERTION 5 dropped
                  effective_dd_threshold from the kwargs)
              (c) DXY/EEM/SBV signals never trigger any policy on 2015-2026
                  data with default thresholds — would indicate the defaults
                  are too conservative; this test would catch and surface that

            Compares state + action columns only (other columns may differ for
            non-MacroFilter reasons in future refactors).
            """
            results_off = _run_once(prepared_df)
            results_on = _run_once_macro_on(prepared_df)

            # Both DataFrames have identical row count (same input)
            assert len(results_off) == len(results_on), (
                f'Row count mismatch: off={len(results_off)} on={len(results_on)}'
            )

            # Compare on the two columns MacroFilter is designed to influence:
            # 'state' (changes when veto_sell rolls back a SELL) and 'action'
            # (text changes when DD threshold lowered or stop-loss tightens).
            states_differ = not (results_off['state'] == results_on['state']).all()
            actions_differ = not (results_off['action'] == results_on['action']).all()

            assert states_differ or actions_differ, (
                "MacroFilter has NO observable effect on signal log when enabled. "
                "Either the filter never fires (default thresholds too conservative — "
                "investigate evidence in docs/research/liquidity_proxy_correlation.md), "
                "or engine wiring is broken (INSERTION 4-6 of Plan 03 — verify "
                "macro_verdict.* fields actually flow to consumers). "
                f"Compared {len(results_off)} rows of state + action columns; all identical."
            )
    ```

    DO NOT modify the existing 2 test methods (`test_signal_log_byte_exact_with_macro_off`, `test_macro_columns_absent_when_disabled`) — they're the PRIMARY parity assertions and locked.
    DO NOT change `_build_macro_off_cfg` or `_run_once` — Plan 02 Task 3 created them, Plan 03 verified them.
    DO NOT add `output/v10_reconciled_baseline.json` consumption — RESEARCH §State of the Art explicitly says the parity test does NOT need it (the JSON is for Phase 46 HARD gate). Adding it here would couple Phase 44 unnecessarily to Phase 42's JSON shape.
    DO NOT import `analysis.validate_v9` — Pitfall 7 forbids module-top import. The test uses `df.equals()`, not `compute_metrics`.

    **VALIDATION.md UPDATE STEP (Phase 44 sign-off bookkeeping — closes WARNING 2 from plan-checker):**

    After all 5 parity tests PASS, update `.planning/phases/44-macro-filter-module/44-VALIDATION.md` to lock in the validated state. The current draft has stale frontmatter (`nyquist_compliant: false`, `wave_0_complete: false`, `status: draft`) AND placeholder task IDs (`44-01-01..04` for MACRO-01/02/03 unit tests that are actually created in Plan 02 Wave 2, NOT Plan 01).

    Make EXACTLY these edits to `.planning/phases/44-macro-filter-module/44-VALIDATION.md`:

    1. **Frontmatter flips** — replace the three lines:
       ```yaml
       status: draft
       nyquist_compliant: false
       wave_0_complete: false
       ```
       with:
       ```yaml
       status: approved
       nyquist_compliant: true
       wave_0_complete: true
       ```

    2. **Per-Task Verification Map renumbering** — the placeholder note at the bottom of the table already says "Wave numbers/plan IDs above are PLACEHOLDERS — gsd-planner refines them when generating PLAN.md files." This task IS that refinement. Renumber the Task ID column as follows (Plan/Wave columns must move in lockstep):

       | Old Task ID | New Task ID | Plan | Wave | Notes |
       |-------------|-------------|------|------|-------|
       | 44-01-01 | 44-02-01 | 02 | 2 | MACRO-01 dxy_zscore_known_date — created in Plan 02 Task 3 |
       | 44-01-02 | 44-02-02 | 02 | 2 | MACRO-02 eem_zscore_known_date — created in Plan 02 Task 3 |
       | 44-01-03 | 44-02-03 | 02 | 2 | MACRO-03 sbv_regime_transitions — created in Plan 02 Task 3 |
       | 44-01-04 | 44-02-04 | 02 | 2 | MACRO-03 sbv_decay_to_neutral — created in Plan 02 Task 3 |
       | 44-02-01 | 44-03-01 | 03 | 3 | MACRO-04 macro_verdict_pass_through — covered by Plan 03 unit suite |
       | 44-02-02 | 44-03-02 | 03 | 3 | MACRO-04 short_circuit_when_disabled — Plan 03 Task 1 |
       | 44-02-03 | 44-03-03 | 03 | 3 | MACRO-05 dxy_easing_vetoes_sell — Plan 03 Task 1 |
       | 44-02-04 | 44-03-04 | 03 | 3 | MACRO-05 dxy_tightening_lowers_dd — Plan 03 Task 1 |
       | 44-02-05 | 44-03-05 | 03 | 3 | MACRO-05 sbv_tightening_shrinks_stop_loss — Plan 03 Task 1 |
       | 44-02-06 | 44-03-06 | 03 | 3 | MACRO-05 most_restrictive_combiner — Plan 03 Task 1 |
       | 44-03-01 | 44-04-01 | 04 | 4 | MACRO-04 v6 parity full suite — this plan |
       | 44-03-02 | 44-04-02 | 04 | 4 | MACRO-04 byte-exact signal log — this plan |

       Update both the `Task ID` column AND the `Plan` column AND the `Wave` column in the table for each row. Status column flips from `⬜ pending` to `✅ green` for ALL rows since at this point all tests are PASSING (this task runs LAST in the phase).

    3. **Approval line** — replace the bottom line `**Approval:** pending` with `**Approval:** approved 2026-04-23`.

    Do NOT modify any other section of VALIDATION.md (Test Infrastructure, Sampling Rate, Wave 0 Requirements, Manual-Only Verifications stay verbatim — those sections are still accurate post-execution).

    DO NOT touch the `*Wave numbers/plan IDs above are PLACEHOLDERS...*` italic note — leave it as-is for historical context (it documents that the original VALIDATION.md was a draft).
  </action>
  <verify>
    <automated>uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression -v</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/test_macro_filter_v6_parity.py` exists with at least 5 test methods total in the TestMacroFilterV6Parity class: `grep -c "    def test_" tests/test_macro_filter_v6_parity.py` returns at least 5 (2 from Plan 02 Task 3 + 3 added by this task)
    - `grep -c "_build_macro_on_cfg" tests/test_macro_filter_v6_parity.py` returns at least 2 (helper definition + at least one usage)
    - `grep -c "_run_once_macro_on" tests/test_macro_filter_v6_parity.py` returns at least 4 (helper definition + 3 usages in 3 new tests)
    - `grep -c "macro_filter_enabled=True" tests/test_macro_filter_v6_parity.py` returns at least 1 (in _build_macro_on_cfg)
    - `grep -c "macro_filter_enabled=False" tests/test_macro_filter_v6_parity.py` returns at least 1 (in _build_macro_off_cfg, intact from Plan 02)
    - `grep -c "v60_strict_mode" tests/test_macro_filter_v6_parity.py` returns at least 2 (both helpers — Pitfall 8 enforced)
    - `grep -c "results_1.equals(results_2)" tests/test_macro_filter_v6_parity.py` returns at least 2 (one for off, one for on)
    - `grep -c "from analysis.validate_v9" tests/test_macro_filter_v6_parity.py` returns 0 (Pitfall 7)
    - All 5 tests PASS: `uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression -v 2>&1 | grep -c "PASSED"` returns at least 5
    - Zero skipped: `uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression -v 2>&1 | grep -c "SKIPPED"` returns 0
    - Zero failed: `uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression -v 2>&1 | grep -c "FAILED"` returns 0
    - Existing baseline determinism still passes: `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0
    - Existing hybrid engine tests still pass: `uv run pytest tests/test_hybrid_engine.py -x` exits 0
    - Full Phase 44 unit test suite still passes: `uv run pytest tests/test_macro_filter.py -x` exits 0
    - **VALIDATION.md frontmatter flipped to approved state (closes plan-checker WARNING 2):** `grep -c "nyquist_compliant: true" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns 1
    - `grep -c "wave_0_complete: true" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns 1
    - `grep -c "status: approved" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns 1
    - **Stale placeholder task IDs purged (closes WARNING 2 renumbering):** `grep -c "44-01-01" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns 0 (all `44-01-*` IDs renumbered to `44-02-*` per the renumbering table in the action body)
    - `grep -c "44-01-02" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns 0
    - `grep -c "44-01-03" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns 0
    - `grep -c "44-01-04" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns 0
    - `grep -c "44-04-01" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns at least 1 (this plan's parity test row)
    - `grep -c "Approval:.*approved" .planning/phases/44-macro-filter-module/44-VALIDATION.md` returns at least 1
  </acceptance_criteria>
  <done>5 tests in test_macro_filter_v6_parity.py all PASS under @pytest.mark.regression; macro-off byte-exact parity locked; macro-on determinism locked; macro-on column presence locked; MacroFilter actually-has-an-effect proven; existing test suites still green.</done>
</task>

</tasks>

<verification>
After Task 1:

1. `uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression -v` shows 5 PASSED, 0 SKIPPED, 0 FAILED
2. `uv run pytest tests/test_macro_filter.py -x` shows all PASSED, 0 SKIPPED
3. `uv run pytest tests/test_baseline_determinism.py -x -m regression` exits 0 (no Phase 42 regression)
4. `uv run pytest tests/test_hybrid_engine.py -x` exits 0 (no NASDAQ-path regression)
5. `uv run pytest -m regression` exits 0 (full regression marker subset)
6. Phase 44 success criteria 1-5 (from ROADMAP.md after Plan 01 rewrite) all met:
   - SC-1 (DXY 20d z-score): test_dxy_zscore_known_date PASS
   - SC-2 (EEM 20d z-score): test_eem_zscore_known_date PASS
   - SC-3 (SBV regime): test_sbv_regime_transitions + test_sbv_decay_to_neutral + test_sbv_publication_lag_shift PASS
   - SC-4 (HybridEngine integration + v6.0 parity): test_signal_log_byte_exact_with_macro_off + test_macro_columns_absent_when_disabled PASS
   - SC-5 (Filter policy): test_dxy_easing_vetoes_sell + test_dxy_tightening_lowers_dd + test_sbv_tightening_shrinks_stop_loss + test_most_restrictive_combiner + test_d04_cautionary_wins + test_eem_easing_vetoes_sell + test_config_field_presence + test_config_validation_gated_on_flag PASS
</verification>

<success_criteria>
- 5 tests in test_macro_filter_v6_parity.py all PASS (2 from Plan 02 stubs + 3 new from this task)
- Macro-off path: byte-exact parity with two fresh runs (locks MACRO-04 / VAL-04 invariant)
- Macro-on path: byte-exact determinism with two fresh runs (locks Phase 45/46 reproducibility prerequisite)
- D-09 dual-layer gate verified in BOTH directions (no columns when off, columns present when on)
- MacroFilter actually-has-an-effect proven (state OR action differs between off and on runs)
- All existing test suites still green
- All 5 Phase 44 ROADMAP success criteria objectively met
</success_criteria>

<output>
After completion, create `.planning/phases/44-macro-filter-module/44-04-SUMMARY.md` documenting:
- Final pytest output for `tests/test_macro_filter_v6_parity.py -v -m regression` (paste the 5 PASS lines + summary)
- Final pytest output for `tests/test_macro_filter.py -v` (paste the PASS line counts)
- Final pytest output for `tests/test_baseline_determinism.py -v -m regression` (confirms no Phase 42 regression)
- Final pytest output for `tests/test_hybrid_engine.py -v` (confirms no NASDAQ-path regression)
- Confirmation that all 5 Phase 44 ROADMAP success criteria met (with mapping table: SC → tests that prove it)
- Confirmation: docs/rules_mdm_hybrid.md NOT touched (Phase 47 DOC-01 scope per CONTEXT.md memory anchors)
- Confirmation: docs/liquidity_proxy_spec.md NOT touched (RESEARCH §Open Q5 — implementation is verbatim to spec)
- Note for Phase 45: MacroFilter is now production-ready; default thresholds are evidence-based starting points; grid search can sweep all 6 thresholds + 3 windows + dxy_tightening_dd_threshold + sbv_tightening_stop_loss_max_multiplier (10-dim search space)
- Phase 44 milestone complete — all 5 MACRO-XX requirements addressed; ready for /gsd:verify-work
</output>
