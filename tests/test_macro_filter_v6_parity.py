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
