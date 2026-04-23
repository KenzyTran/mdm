"""Walk-Forward OOS Guard Regression Tests (WF-01 SC-4, Phase 45 D-15).

Two defenses against 2025+ data leaking into the macro filter grid search:
  1. Runtime assert inside analysis/walkforward_grid.py::load_vn30_data --
     fires 'OOS leak: max date ... crossed 2025-01-01' on any date >= OOS_FENCE.
  2. Selection function -- rows whose eval slice contains 2025 data can never
     become accepted combos; either they're flagged via rejection_reason
     mentioning OOS, or they never enter the accepted pool.

These tests run in < 2 seconds with synthetic data only (no DataLoader,
no HybridEngine). Run locally:

    uv run python -m pytest -m regression tests/test_walkforward_oos_guard.py -v

Acceptance bar: pytest passes on every HEAD commit. Failure means the OOS
fence has been weakened; Phase 45 is invalid until fixed.

NOTE (stdout-safe lazy import): `analysis.walkforward_grid` imports
`analysis.validate_v9.compute_metrics` at module level, and validate_v9
rewrites `sys.stdout = io.TextIOWrapper(sys.stdout.buffer)` at import time.
Importing walkforward_grid at the test-module top breaks pytest's capture
machinery with "ValueError: I/O operation on closed file". We mirror the
`tests/test_baseline_determinism.py:_get_compute_metrics` stdout-preserving
lazy-import pattern: snapshot sys.stdout, perform the import, restore
sys.stdout, and park the orphan wrapper so GC doesn't close the buffer.
"""

import sys

import pytest
import pandas as pd


# -- stdout-safe lazy import of analysis.walkforward_grid ----------------
# See module docstring for rationale; pattern copied verbatim from
# tests/test_baseline_determinism.py:98-143.
_WALKFORWARD_GRID = None
_ORPHAN_STDOUT_WRAPPER_HOLDER = []  # keeps the rewritten wrapper alive; prevents GC-induced buffer close


def _get_walkforward_grid():
    """Lazy, stdout-safe import of analysis.walkforward_grid module.

    Transitively triggers analysis.validate_v9 import which rewrites sys.stdout.
    Result cached in a module global so the import side-effect fires at most
    once per test process.
    """
    global _WALKFORWARD_GRID
    if _WALKFORWARD_GRID is not None:
        return _WALKFORWARD_GRID
    saved_stdout = sys.stdout
    try:
        import analysis.walkforward_grid as wfg  # noqa: E402
        orphan_wrapper = sys.stdout  # the freshly-installed TextIOWrapper
    finally:
        sys.stdout = saved_stdout
    _ORPHAN_STDOUT_WRAPPER_HOLDER.append(orphan_wrapper)  # pin for process lifetime
    _WALKFORWARD_GRID = wfg
    return wfg


@pytest.mark.regression
def test_assert_fires_on_2025_data():
    """D-15 test 1: load_vn30_data must reject any DataFrame whose max date >= OOS_FENCE.

    Synthetic injection path: pass df_override directly, skipping DataLoader
    so this test is deterministic and < 1 second.
    """
    wfg = _get_walkforward_grid()
    load_vn30_data = wfg.load_vn30_data
    OOS_FENCE = wfg.OOS_FENCE

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
    hypothetical leak by being flagged as accepted=False with an OOS-leak
    rejection_reason. Assert that:
      (a) select_winner only considers rows where row['accepted'] == True
      (b) a row flagged as accepted=False with a rejection_reason mentioning
          OOS is NOT promoted to winner
      (c) EVAL_YEARS does NOT contain 2025 (schema-level leak prevention)
    """
    wfg = _get_walkforward_grid()
    select_winner = wfg.select_winner
    EVAL_YEARS = wfg.EVAL_YEARS
    OOS_FENCE = wfg.OOS_FENCE

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
        eval_years=EVAL_YEARS,
    )
    # Fabricate a "poisoned" row that pretends to have been accepted via
    # 2025 data (our simulated leak). Use rejection_reason to flag it.
    poisoned_row = _make_fake_row(
        combo_id=1,
        stage='stage1_dxy',
        median_eval_cagr_pct=999.0,  # artificially high -- would win if not filtered
        median_degradation=0.05,
        accepted=False,
        rejection_reason='OOS leak detected in eval slice 2025-XX',
        eval_years=EVAL_YEARS,
    )

    winner, runners_up = select_winner([legit_row, poisoned_row], 'stage1_dxy')
    assert winner is not None, 'Expected legit_row to win'
    assert winner['combo_id'] == 0, (
        f"Poisoned row (combo_id=1) must NOT win despite higher CAGR. "
        f"Got combo_id={winner['combo_id']}"
    )
    assert winner['accepted'] is True
    # Poisoned row must appear in NEITHER winner NOR runners-up
    runner_ids = [r['combo_id'] for r in runners_up]
    assert 1 not in runner_ids, (
        f"Poisoned row (combo_id=1) must be excluded from runners_up. Got: {runner_ids}"
    )


# -- Helpers -------------------------------------------------------------
def _make_fake_row(
    combo_id: int,
    stage: str,
    median_eval_cagr_pct: float,
    median_degradation: float,
    accepted: bool,
    rejection_reason: str,
    eval_years: list,
) -> dict:
    """Construct a row matching the D-06 CSV schema for select_winner testing."""
    row = {
        'stage': stage,
        'combo_id': combo_id,
        'config_name': f'{stage}-c{combo_id}',
        # 10 config fields (D-11 tuple) -- VN30_PRESET defaults
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
        **{f'cagr_eval_{y}_pct': 10.0 for y in eval_years},
        **{f'sharpe_rf3_eval_{y}': 0.5 for y in eval_years},
        **{f'max_dd_eval_{y}_pct': -18.0 for y in eval_years},
        # Per-year degradation (6 cols)
        **{f'degradation_{y}': 0.1 for y in eval_years},
        # Aggregates
        'median_eval_cagr_pct': median_eval_cagr_pct,
        'median_degradation': median_degradation,
        'eval_years_count': 6,
        # Accept gate
        'accepted': accepted,
        'rejection_reason': rejection_reason,
        # Errors (empty)
        'error_train': '',
        **{f'error_year_{y}': '' for y in eval_years},
    }
    return row
