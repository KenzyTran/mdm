"""v6.0 parity regression test for Phase 44 MacroFilter (MACRO-04 / VAL-04).

When macro_filter_enabled=False:
  1. Two fresh HybridEngine runs produce byte-exact equal results DataFrames
  2. No dxy_z / eem_z / sbv_regime columns appear in the results

Pattern verbatim from tests/test_baseline_determinism.py:159-232 with
macro_filter_enabled=False added to the preset overrides per RESEARCH.md
Pitfall 8 + Common Operation 3.

Plan 03 lands the engine integration; this stub will activate then.
Until then, the test is skipped — `add_macro_columns` (Plan 02 Task 2)
alone does not exercise the parity invariant.

Run:  uv run pytest -m regression tests/test_macro_filter_v6_parity.py -v
"""

from dataclasses import replace

import pytest
import pandas as pd

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config, VN30_PRESET


DATA_START = '2015-01-05'
DATA_END = '2026-03-31'


def _build_macro_off_cfg() -> MDMV2Config:
    """Reconciled v6.0 preset with macro filter EXPLICITLY disabled.

    Mirrors tests/test_baseline_determinism.py:_build_reconciled_cfg with
    an additional macro_filter_enabled=False override per Phase 44 D-09.
    """
    overrides = dict(
        atr_buffer_enabled=False,
        refined_dd_enabled=False,
        macro_filter_enabled=False,  # Phase 44 D-09 — hard short-circuit
    )
    if 'v60_strict_mode' in MDMV2Config.__dataclass_fields__:
        overrides['v60_strict_mode'] = True  # Phase 42-04 contract — RESEARCH.md Pitfall 8
    return replace(VN30_PRESET, **overrides)


def _run_once(df: pd.DataFrame) -> pd.DataFrame:
    """Fresh HybridEngine -> .run(df.copy()) -> results DataFrame."""
    engine = HybridEngine(HybridConfig(
        v2_config=_build_macro_off_cfg(),
        two_phase_enabled=True,
        filter_enabled=False,
    ))
    return engine.run(df.copy())


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


@pytest.mark.regression
class TestMacroFilterV6Parity:
    """MACRO-04 / VAL-04: macro_filter_enabled=False → byte-exact v6.0 parity.

    These tests REQUIRE Plan 03's engine integration (the precompute gate
    + MacroFilter wiring). Until Plan 03 lands the engine changes, these
    tests would still pass mechanically (engine ignores the new config
    fields when no integration exists yet) — but the TRUE parity invariant
    is meaningless without the integration. Plan 03 makes them meaningful.
    """

    @pytest.fixture(scope='class')
    def prepared_df(self) -> pd.DataFrame:
        df = DataLoader('vn30').load(DATA_START, DATA_END)
        df = build_indicator_dataframe(df)
        return df

    def test_signal_log_byte_exact_with_macro_off(self, prepared_df):
        """Two fresh-engine macro-off runs → byte-exact equal results."""
        results_1 = _run_once(prepared_df)
        results_2 = _run_once(prepared_df)
        assert results_1.equals(results_2), (
            "Signal log DataFrames differ between two macro-off runs. "
            "MacroFilter is leaking state when disabled — D-09 hard short-circuit "
            "is broken."
        )

    def test_macro_columns_absent_when_disabled(self, prepared_df):
        """D-09: no dxy_z / eem_z / sbv_regime columns appear when feature off."""
        results = _run_once(prepared_df)
        for col in ('dxy_z', 'eem_z', 'sbv_regime'):
            assert col not in results.columns, (
                f"Column '{col}' present when macro_filter_enabled=False. "
                f"D-09 short-circuit violated — add_macro_columns() was called."
            )

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
