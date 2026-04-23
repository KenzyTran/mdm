---
phase: 45-walk-forward-grid-search
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - tests/test_walkforward_oos_guard.py
autonomous: true
requirements: [WF-01]

must_haves:
  truths:
    - "pytest -m regression tests/test_walkforward_oos_guard.py -v exits 0 and runs exactly 2 tests"
    - "test_assert_fires_on_2025_data injects a synthetic DataFrame with a 2025-06-15 row and asserts AssertionError message contains literal 'OOS leak'"
    - "test_selection_excludes_2025_when_present asserts the selection function never accepts a row whose eval slice contains 2025 data — synthetic rows flagged via rejection_reason mentioning OOS"
    - "Tests run in < 2 seconds total (no real engine invocation, no real data load)"
    - "Test file imports load_vn30_data + run_combo (or select_winner) from analysis.walkforward_grid — i.e., exercises the Plan 01 factoring"
  artifacts:
    - path: "tests/test_walkforward_oos_guard.py"
      provides: "Regression test for D-14 runtime OOS-guard assert + D-15 synthetic-data selection leak check"
      contains: "@pytest.mark.regression, test_assert_fires_on_2025_data, test_selection_excludes_2025_when_present"
      min_lines: 60
  key_links:
    - from: "tests/test_walkforward_oos_guard.py"
      to: "analysis/walkforward_grid.py::load_vn30_data"
      via: "from analysis.walkforward_grid import load_vn30_data"
      pattern: "from analysis.walkforward_grid import .*load_vn30_data"
    - from: "tests/test_walkforward_oos_guard.py"
      to: "analysis/walkforward_grid.py::OOS_FENCE"
      via: "Test verifies the assert message mentions OOS and the fence date"
      pattern: "OOS_FENCE|OOS leak"
---

<objective>
Build `tests/test_walkforward_oos_guard.py` — the regression pytest that closes ROADMAP SC-4 (walk-forward selection provably never considers 2025+ data) with 2 synthetic-data tests per CONTEXT D-15.

Purpose: Give the executor and future reviewers a fast (< 2s) automated check that OOS leakage cannot happen. Provides the second of two OOS defenses (first is the runtime assert inside the script itself, which this test activates on synthetic data).

Output: 2 pytest functions under @pytest.mark.regression marker, checked-in so CI/local runs catch accidental weakening of the OOS fence.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/45-walk-forward-grid-search/45-CONTEXT.md
@analysis/walkforward_grid.py
@tests/test_baseline_determinism.py
@tests/test_macro_filter_v6_parity.py

<interfaces>
<!-- Extracted from Plan 01 work product + existing test patterns -->

From analysis/walkforward_grid.py (Plan 01):
```python
OOS_FENCE = '2025-01-01'
EVAL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
DEGRADATION_THRESHOLD = 0.30

def load_vn30_data(df_override: pd.DataFrame | None = None) -> pd.DataFrame:
    """Inject df_override to bypass DataLoader; runtime-asserts date.max() < OOS_FENCE.
    AssertionError message contains literal 'OOS leak'."""

def run_combo(df: pd.DataFrame, overrides: dict, stage: str, combo_id: int) -> dict:
    """Returns row dict with accepted, rejection_reason, per-year metrics keyed on EVAL_YEARS."""

def select_winner(stage_rows: list[dict], stage: str) -> tuple[dict, list[dict]]:
    """Filters accepted==True only; 2025-labeled rows (if synthetically given accepted=True) should NOT pass through any mechanism in the script since no eval-year column for 2025 exists and median calc skips it."""
```

From tests/test_baseline_determinism.py (D-15 precedent):
  Module docstring format, `@pytest.mark.regression` marker applied at FUNCTION level (not class-scoped this time — 2 independent tests are fine), sys.path hygiene not needed (project has tests/ as top-level with proper pytest discovery).

From tests/test_macro_filter_v6_parity.py:
  `from strategies.mdm_hybrid.config import ...` pattern for engine-adjacent test imports.
  `@pytest.mark.regression` marker — same as Phase 42/44 precedent.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write tests/test_walkforward_oos_guard.py with 2 regression tests</name>
  <files>tests/test_walkforward_oos_guard.py</files>
  <read_first>
    - analysis/walkforward_grid.py (Plan 01 output — verify load_vn30_data signature, OOS_FENCE constant, DEGRADATION_THRESHOLD constant, EVAL_YEARS, run_combo / select_winner function signatures)
    - tests/test_baseline_determinism.py (lines 1-80 — module docstring + imports + marker placement style)
    - tests/test_macro_filter_v6_parity.py (lines 1-60 — `@pytest.mark.regression` module-level marker convention)
    - .planning/phases/45-walk-forward-grid-search/45-CONTEXT.md D-15 — verbatim the 2 test function definitions
  </read_first>
  <action>
    Create `tests/test_walkforward_oos_guard.py` with the following exact structure. Use `@pytest.mark.regression` marker on each test function (matches Phase 42 + Phase 44 precedent).

    ```python
    """Walk-Forward OOS Guard Regression Tests (WF-01 SC-4, Phase 45 D-15).

    Two defenses against 2025+ data leaking into the macro filter grid search:
      1. Runtime assert inside analysis/walkforward_grid.py::load_vn30_data —
         fires 'OOS leak: max date ... crossed 2025-01-01' on any date >= OOS_FENCE.
      2. Selection function — rows whose eval slice contains 2025 data can never
         become accepted combos; either they're flagged via rejection_reason
         mentioning OOS, or they never enter the accepted pool.

    These tests run in < 2 seconds with synthetic data only (no DataLoader,
    no HybridEngine). Run locally:

        uv run pytest -m regression tests/test_walkforward_oos_guard.py -v

    Acceptance bar: pytest passes on every HEAD commit. Failure means the OOS
    fence has been weakened; Phase 45 is invalid until fixed.
    """

    import pytest
    import pandas as pd

    from analysis.walkforward_grid import (
        load_vn30_data,
        select_winner,
        OOS_FENCE,
        EVAL_YEARS,
        DEGRADATION_THRESHOLD,
    )


    @pytest.mark.regression
    def test_assert_fires_on_2025_data():
        """D-15 test 1: load_vn30_data must reject any DataFrame whose max date >= OOS_FENCE.

        Synthetic injection path: pass df_override directly, skipping DataLoader
        so this test is deterministic and < 1 second.
        """
        # Build a minimal synthetic DataFrame with one 2024 row + one 2025 row
        df_leaky = pd.DataFrame({
            'date': [pd.Timestamp('2024-06-01'), pd.Timestamp('2025-06-15')],
            'close': [1000.0, 1100.0],
        })
        with pytest.raises(AssertionError) as exc_info:
            load_vn30_data(df_override=df_leaky)
        # Message MUST contain literal 'OOS leak' (Plan 01 Task 2 contract)
        assert 'OOS leak' in str(exc_info.value), (
            f"Expected 'OOS leak' in AssertionError message, got: {exc_info.value}"
        )
        # And the fence date should appear in the message for reviewer clarity
        assert OOS_FENCE in str(exc_info.value) or '2025' in str(exc_info.value), (
            f"Expected fence date in message, got: {exc_info.value}"
        )

        # Sanity check: a synthetic df strictly before the fence MUST pass
        df_ok = pd.DataFrame({
            'date': [pd.Timestamp('2024-06-01'), pd.Timestamp('2024-12-31')],
            'close': [1000.0, 1050.0],
        })
        result = load_vn30_data(df_override=df_ok)
        assert result is df_ok, "Pass-through path should return the override DataFrame unchanged"


    @pytest.mark.regression
    def test_selection_excludes_2025_when_present():
        """D-15 test 2: selection logic can never promote a row whose acceptance
        depended on a 2025-labeled eval slice.

        Strategy: Fabricate two row dicts matching the D-06 CSV schema. The first
        row has legitimate 2019-2024 metrics. The second row simulates a
        hypothetical leak by encoding a 2025 key that the schema does NOT support
        (no 'cagr_eval_2025_pct' column exists in EVAL_YEARS). Assert that:
          (a) select_winner only considers rows where row['accepted'] == True
          (b) a row flagged as accepted=False with a rejection_reason mentioning
              OOS is NOT promoted to winner
          (c) EVAL_YEARS does NOT contain 2025 (schema-level leak prevention)
        """
        # Schema-level leak prevention: if 2025 ever enters EVAL_YEARS, the entire
        # median calculation would silently include it. Assert the fence at config level.
        assert 2025 not in EVAL_YEARS, (
            f"OOS leak via EVAL_YEARS: {EVAL_YEARS} must not include 2025 "
            f"(fence is OOS_FENCE={OOS_FENCE})"
        )
        assert max(EVAL_YEARS) < 2025, (
            f"OOS leak: max(EVAL_YEARS)={max(EVAL_YEARS)} must be < 2025"
        )

        # Fabricate a legitimate accepted row
        legit_row = _make_fake_row(
            combo_id=0,
            stage='stage1_dxy',
            median_eval_cagr_pct=10.0,
            median_degradation=0.15,
            accepted=True,
            rejection_reason='',
        )
        # Fabricate a "poisoned" row that pretends to have been accepted via
        # 2025 data (our simulated leak). Use rejection_reason to flag it.
        poisoned_row = _make_fake_row(
            combo_id=1,
            stage='stage1_dxy',
            median_eval_cagr_pct=999.0,  # artificially high — would win if not filtered
            median_degradation=0.05,
            accepted=False,
            rejection_reason='OOS leak detected in eval slice 2025-XX',
        )

        winner, runners_up = select_winner([legit_row, poisoned_row], 'stage1_dxy')
        assert winner is not None, 'Expected legit_row to win'
        assert winner['combo_id'] == 0, (
            f"Poisoned row (combo_id=1) must NOT win despite higher CAGR. Got combo_id={winner['combo_id']}"
        )
        assert winner['accepted'] is True
        # Poisoned row must appear in NEITHER winner NOR runners-up
        runner_ids = [r['combo_id'] for r in runners_up]
        assert 1 not in runner_ids, (
            f"Poisoned row (combo_id=1) must be excluded from runners_up. Got: {runner_ids}"
        )


    # ── Helpers ────────────────────────────────────────────────────────
    def _make_fake_row(
        combo_id: int,
        stage: str,
        median_eval_cagr_pct: float,
        median_degradation: float,
        accepted: bool,
        rejection_reason: str,
    ) -> dict:
        """Construct a row matching the D-06 CSV schema for select_winner testing."""
        row = {
            'stage': stage,
            'combo_id': combo_id,
            'config_name': f'{stage}-c{combo_id}',
            # 10 config fields (D-11 tuple) — VN30_PRESET defaults
            'dxy_easing_z_threshold': -1.0,
            'dxy_tightening_z_threshold': 1.0,
            'dxy_tightening_dd_threshold': 3,
            'eem_easing_z_threshold': 1.0,
            'eem_tightening_z_threshold': -1.0,
            'sbv_tightening_stop_loss_max_multiplier': 1.5,
            'dxy_window_days': 20,
            'eem_window_days': 20,
            'sbv_decay_days': 90,
            'macro_filter_enabled': True,
            # Train metrics
            'cagr_train_pct': 11.0,
            'sharpe_rf3_train': 0.5,
            'max_dd_train_pct': -20.0,
            # Per-year eval metrics (18 cols)
            **{f'cagr_eval_{y}_pct': 10.0 for y in EVAL_YEARS},
            **{f'sharpe_rf3_eval_{y}': 0.5 for y in EVAL_YEARS},
            **{f'max_dd_eval_{y}_pct': -18.0 for y in EVAL_YEARS},
            # Per-year degradation (6 cols)
            **{f'degradation_{y}': 0.1 for y in EVAL_YEARS},
            # Aggregates
            'median_eval_cagr_pct': median_eval_cagr_pct,
            'median_degradation': median_degradation,
            'eval_years_count': 6,
            # Accept gate
            'accepted': accepted,
            'rejection_reason': rejection_reason,
            # Errors (empty)
            'error_train': '',
            **{f'error_year_{y}': '' for y in EVAL_YEARS},
        }
        return row
    ```

    Critical constraints (copy verbatim):
    - Use `@pytest.mark.regression` at the FUNCTION level (not class-scoped — only 2 tests, no shared setup justifies a class).
    - Import from `analysis.walkforward_grid` — this depends on Plan 01 being complete. If `load_vn30_data` signature drifts, this test fails loudly.
    - Assertion about EVAL_YEARS not containing 2025 is a schema-level leak check — catches a future maintainer who naively extends EVAL_YEARS.
    - No real engine invocation, no real DataLoader — tests must complete in < 2 seconds.
    - The `_make_fake_row` helper constructs rows matching the 45-01 Task 3 schema exactly; if that schema changes, this helper must be updated in lockstep.
  </action>
  <verify>
    <automated>uv run pytest -m regression tests/test_walkforward_oos_guard.py -v --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "@pytest.mark.regression" tests/test_walkforward_oos_guard.py` returns exactly 2 (one per test function)
    - `grep -c "def test_assert_fires_on_2025_data" tests/test_walkforward_oos_guard.py` returns 1
    - `grep -c "def test_selection_excludes_2025_when_present" tests/test_walkforward_oos_guard.py` returns 1
    - `grep -c "from analysis.walkforward_grid import" tests/test_walkforward_oos_guard.py` returns at least 1 (exercises Plan 01 factoring)
    - `grep -c "load_vn30_data" tests/test_walkforward_oos_guard.py` returns at least 2 (imported + called with df_override)
    - `grep -c "OOS leak" tests/test_walkforward_oos_guard.py` returns at least 1 (the message-content assertion)
    - `grep -c "2025 not in EVAL_YEARS" tests/test_walkforward_oos_guard.py` returns 1 (schema-level guard)
    - `uv run pytest -m regression tests/test_walkforward_oos_guard.py -v` exits 0 and reports "2 passed" in output
    - Test runtime < 2 seconds (inspect pytest timing summary — expected < 0.5s without engine)
  </acceptance_criteria>
  <done>
    Both regression tests pass. pytest `-m regression tests/test_walkforward_oos_guard.py -v` exits 0, reports 2 tests passed. AssertionError path returns literal 'OOS leak' in message (contracts Plan 01 Task 2). Schema-level assertion `2025 not in EVAL_YEARS` catches future maintainer errors. Selection logic proved incapable of promoting a row flagged with OOS rejection_reason even when it has artificially highest CAGR.
  </done>
</task>

</tasks>

<verification>
After the single task completes:

- `uv run pytest -m regression tests/test_walkforward_oos_guard.py -v` exits 0 and shows "2 passed" with runtime < 2s
- `uv run pytest -m regression tests/test_walkforward_oos_guard.py tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v` — all prior regression tests still pass (no accidental breakage)
- Test file imports resolve cleanly (no ImportError on analysis.walkforward_grid symbols)

**Out-of-scope self-check (MUST all be NO):**
- Did this plan modify `analysis/walkforward_grid.py`? → NO (the test imports from it, does not modify)
- Did this plan touch any strategies/ file? → NO
- Did this plan add new MDMV2Config fields? → NO
- Did this plan run the real engine? → NO (synthetic data only, < 2s runtime)
</verification>

<success_criteria>
- `tests/test_walkforward_oos_guard.py` committed with 2 @pytest.mark.regression tests
- Both tests green on HEAD
- Tests cover the 2 D-15 requirements: (a) runtime assert fires on 2025 data, (b) selection cannot promote a row flagged as OOS-poisoned
- Schema-level EVAL_YEARS assertion catches future maintainer drift
- Test file depends cleanly on Plan 01's `load_vn30_data` + `select_winner` + `OOS_FENCE` + `EVAL_YEARS` exports — demonstrates Plan 01 factored the data-load helper correctly
</success_criteria>

<output>
After completion, executor creates `.planning/phases/45-walk-forward-grid-search/45-02-SUMMARY.md` summarizing: test function names, assertions covered, runtime, and verification that the entire regression suite (baseline_determinism + macro_filter_v6_parity + walkforward_oos_guard) stays green.
</output>
