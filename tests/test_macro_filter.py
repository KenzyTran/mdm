"""Unit tests for strategies/mdm_hybrid/macro_filter.py (Phase 44, MACRO-01..05).

Tests cover:
  - MACRO-01: DXY 20d z-score on a known date (test_dxy_zscore_known_date,
              test_dxy_z_uses_vn_calendar)
  - MACRO-02: EEM 20d z-score on a known date (test_eem_zscore_known_date,
              test_eem_sign_flipped)
  - MACRO-03: SBV regime classifier transitions + decay + +1-day shift
              (test_sbv_regime_transitions, test_sbv_decay_to_neutral,
              test_sbv_publication_lag_shift)
  - MACRO-04: MacroVerdict.pass_through, hard short-circuit when disabled
              (test_macro_verdict_pass_through, test_short_circuit_when_disabled)
              [test_short_circuit_when_disabled requires Plan 03 MacroFilter class]
  - MACRO-05: Policy verbs + most-restrictive combiner + EEM symmetry +
              config validation gating (test_dxy_easing_vetoes_sell,
              test_dxy_tightening_lowers_dd, test_sbv_tightening_shrinks_stop_loss,
              test_most_restrictive_combiner, test_d04_cautionary_wins,
              test_eem_easing_vetoes_sell, test_config_field_presence,
              test_config_validation_gated_on_flag)
              [policy/combiner tests require Plan 03 MacroFilter class]

Synthetic mini-fixtures inline per Phase 42 D-18 precedent — see
tests/test_baseline_determinism.py for the established pattern.
"""

from dataclasses import replace
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

from strategies.mdm_hybrid.config import MDMV2Config, VN30_PRESET, NASDAQ_PRESET
from strategies.mdm_hybrid.macro_filter import (
    MacroVerdict,
    add_macro_columns,
    LIQUIDITY_PROXY_PATH,
    SBV_EVENTS_PATH,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _write_synthetic_proxy(tmp_path: Path, dates, dxy_values, eem_values) -> Path:
    """Write a synthetic 6-column liquidity proxy CSV matching Phase 43 schema."""
    df = pd.DataFrame({
        'date': pd.to_datetime(dates),
        'usdvnd_close': [25000.0] * len(dates),  # placeholder — not consumed
        'dxy_close': dxy_values,
        'tnx_close': [4.0] * len(dates),         # placeholder — not consumed
        'vnm_close': [15.0] * len(dates),        # placeholder — not consumed
        'eem_close': eem_values,
    })
    path = tmp_path / 'proxy.csv'
    df.to_csv(path, index=False)
    return path


def _write_synthetic_sbv(tmp_path: Path, events) -> Path:
    """Write a synthetic SBV events CSV.

    events: list of (date_str, direction) tuples.
    """
    df = pd.DataFrame({
        'date': pd.to_datetime([e[0] for e in events]) if events else pd.to_datetime([]),
        'rate_change_pct': [-0.5 if e[1] == 'easing' else +0.5 for e in events],
        'new_refinance_rate_pct': [4.0] * len(events),
        'direction': [e[1] for e in events],
        'source': ['synthetic'] * len(events),
    })
    path = tmp_path / 'sbv.csv'
    df.to_csv(path, index=False)
    return path


# ── MACRO-01 / MACRO-02 / MACRO-03 (add_macro_columns) ──────────────────

def test_dxy_zscore_known_date(tmp_path):
    """MACRO-01: DXY 20d z-score on a known date matches manual computation.

    Synthetic case: 30 VN30 dates, dxy_close = [100, 101, ..., 129]. On day
    30 (idx 29), z = (129 - mean(110..129)) / std(110..129).
    """
    dates = pd.date_range('2020-01-01', periods=30, freq='B')
    dxy_values = [100.0 + i for i in range(30)]
    eem_values = [50.0] * 30  # constant — std=0, z will be NaN — separate test
    proxy_path = _write_synthetic_proxy(tmp_path, dates, dxy_values, eem_values)
    sbv_path = _write_synthetic_sbv(tmp_path, [])  # empty SBV — all 'neutral'

    df = pd.DataFrame({'date': dates})
    result = add_macro_columns(df, proxy_path, sbv_path, dxy_window_days=20)

    # Expected dxy_z[29] uses values at indices 10..29 (20-day window ending at 29)
    window = dxy_values[10:30]
    expected_z = (dxy_values[29] - np.mean(window)) / np.std(window, ddof=1)
    assert abs(result['dxy_z'].iloc[29] - expected_z) < 1e-9, (
        f"DXY z-score mismatch: got {result['dxy_z'].iloc[29]}, expected {expected_z}"
    )


def test_dxy_z_uses_vn_calendar(tmp_path):
    """MACRO-01: rolling z-score window respects VN30 trading days, not US calendar.

    Spec §5.3 + §6 trap #4: z-score MUST be computed AFTER merge so the
    20-day window counts VN30 dates.
    """
    # VN30 has fewer days in the window than US (different calendars).
    # If z is computed pre-merge: uses proxy-indexed rolling window.
    # If z is computed post-merge: uses VN30-indexed rolling window (backward-fill
    #   on days VN30 doesn't have a fresh proxy print).
    # Test verifies post-merge behavior: the VN30-indexed rolling computation.
    vn_dates = pd.date_range('2020-01-01', periods=30, freq='2B')  # every other business day
    proxy_dates = pd.date_range('2020-01-01', periods=60, freq='B')
    proxy_dxy = list(range(100, 160))
    proxy_eem = [50.0] * 60
    proxy_path = _write_synthetic_proxy(tmp_path, proxy_dates, proxy_dxy, proxy_eem)
    sbv_path = _write_synthetic_sbv(tmp_path, [])

    df = pd.DataFrame({'date': vn_dates})
    result = add_macro_columns(df, proxy_path, sbv_path, dxy_window_days=20)

    # Post-merge z uses VN-indexed values: result['dxy_z'].iloc[29] uses
    # the dxy_close values backward-merged onto vn_dates[10:30].
    # Reconstruct expected from proxy lookup using merge_asof semantics.
    expected_window = []
    proxy_dates_ts = pd.to_datetime(proxy_dates)
    for d in vn_dates[10:30]:
        mask = proxy_dates_ts <= d
        expected_window.append(proxy_dxy[mask.sum() - 1])
    expected_z = (expected_window[-1] - np.mean(expected_window)) / np.std(expected_window, ddof=1)
    assert abs(result['dxy_z'].iloc[29] - expected_z) < 1e-9, (
        f"DXY z computed on US calendar (pre-merge) instead of VN calendar (post-merge). "
        f"Spec §6 trap #4 violated. Got {result['dxy_z'].iloc[29]}, expected {expected_z}"
    )


def test_eem_zscore_known_date(tmp_path):
    """MACRO-02: EEM 20d z-score matches manual computation, same pipeline as DXY."""
    dates = pd.date_range('2020-01-01', periods=30, freq='B')
    dxy_values = [100.0] * 30
    eem_values = [40.0 + i * 0.5 for i in range(30)]
    proxy_path = _write_synthetic_proxy(tmp_path, dates, dxy_values, eem_values)
    sbv_path = _write_synthetic_sbv(tmp_path, [])

    df = pd.DataFrame({'date': dates})
    result = add_macro_columns(df, proxy_path, sbv_path, eem_window_days=20)

    window = eem_values[10:30]
    expected_z = (eem_values[29] - np.mean(window)) / np.std(window, ddof=1)
    assert abs(result['eem_z'].iloc[29] - expected_z) < 1e-9


def test_eem_sign_flipped(tmp_path):
    """MACRO-02 / D-12: EEM column is produced with natural z-score sign;
    sign-flip semantics live in MacroFilter.apply (Plan 03), not in helper.

    This test ensures add_macro_columns does NOT prematurely apply the EEM
    sign convention — it produces a standard z-score, and the consumer
    applies the (z > +threshold = easing) convention per D-12.
    """
    dates = pd.date_range('2020-01-01', periods=30, freq='B')
    dxy_values = [100.0] * 30
    eem_values = [40.0 - i * 0.5 for i in range(30)]  # DECREASING
    proxy_path = _write_synthetic_proxy(tmp_path, dates, dxy_values, eem_values)
    sbv_path = _write_synthetic_sbv(tmp_path, [])

    df = pd.DataFrame({'date': dates})
    result = add_macro_columns(df, proxy_path, sbv_path, eem_window_days=20)

    # Decreasing series → final z is NEGATIVE (standard z-score)
    # Sign convention flip happens in MacroFilter, not here
    assert result['eem_z'].iloc[29] < 0, (
        f"EEM z-score for decreasing series should be negative (raw z), "
        f"sign convention flip is consumer-side per D-12. Got {result['eem_z'].iloc[29]}"
    )


def test_sbv_regime_transitions(tmp_path):
    """MACRO-03: SBV regime classifier transitions across known event sequence.

    Synthetic: easing event on 2020-03-17 + tightening on 2020-06-17.
    BusinessDay(1) shift: regime visible from 2020-03-18 (Wed) onward.
    """
    # Use existing SBV CSV format dates; pick weekday to avoid weekend complications
    dates = pd.date_range('2020-03-13', '2020-06-25', freq='B')
    proxy_path = _write_synthetic_proxy(
        tmp_path, dates, [100.0] * len(dates), [50.0] * len(dates)
    )
    sbv_path = _write_synthetic_sbv(tmp_path, [
        ('2020-03-17', 'easing'),
        ('2020-06-17', 'tightening'),
    ])

    df = pd.DataFrame({'date': dates})
    result = add_macro_columns(df, proxy_path, sbv_path, sbv_decay_days=90)

    # 2020-03-17 (Tue) — same-day, regime should be 'neutral' (no prior event,
    # current event not effective until +1 BusinessDay)
    row_0317 = result[result['date'] == pd.Timestamp('2020-03-17')].iloc[0]
    assert row_0317['sbv_regime'] == 'neutral', (
        f"Same-day SBV regime should be 'neutral' (no prior event); got {row_0317['sbv_regime']}"
    )
    # 2020-03-18 (Wed) — effective_date of the easing event, regime = 'easing'
    row_0318 = result[result['date'] == pd.Timestamp('2020-03-18')].iloc[0]
    assert row_0318['sbv_regime'] == 'easing', (
        f"+1-BusinessDay regime should be 'easing'; got {row_0318['sbv_regime']}"
    )
    # 2020-06-18 (Thu) — effective_date of tightening event, regime = 'tightening'
    row_0618 = result[result['date'] == pd.Timestamp('2020-06-18')].iloc[0]
    assert row_0618['sbv_regime'] == 'tightening', (
        f"After tightening event, regime should be 'tightening'; got {row_0618['sbv_regime']}"
    )


def test_sbv_decay_to_neutral(tmp_path):
    """MACRO-03: SBV regime decays to 'neutral' after sbv_decay_days."""
    dates = pd.date_range('2020-03-13', '2020-08-01', freq='B')
    proxy_path = _write_synthetic_proxy(
        tmp_path, dates, [100.0] * len(dates), [50.0] * len(dates)
    )
    sbv_path = _write_synthetic_sbv(tmp_path, [('2020-03-17', 'easing')])

    df = pd.DataFrame({'date': dates})
    result = add_macro_columns(df, proxy_path, sbv_path, sbv_decay_days=90)

    # effective_date = 2020-03-18; +89 days = 2020-06-15 (within decay)
    # +90 days = 2020-06-16 (exactly at threshold, INCLUSIVE per spec §5.2)
    # +91 days = 2020-06-17 (outside, decayed to neutral)
    row_within = result[result['date'] == pd.Timestamp('2020-06-15')].iloc[0]
    assert row_within['sbv_regime'] == 'easing', (
        f"Within decay window (89 days), regime should still be 'easing'; "
        f"got {row_within['sbv_regime']}"
    )
    row_at_threshold = result[result['date'] == pd.Timestamp('2020-06-16')].iloc[0]
    assert row_at_threshold['sbv_regime'] == 'easing', (
        f"At decay threshold (90 days, INCLUSIVE), regime should still be 'easing'; "
        f"got {row_at_threshold['sbv_regime']}"
    )
    row_decayed = result[result['date'] == pd.Timestamp('2020-06-17')].iloc[0]
    assert row_decayed['sbv_regime'] == 'neutral', (
        f"After decay window (91 days), regime should decay to 'neutral'; "
        f"got {row_decayed['sbv_regime']}"
    )


def test_sbv_publication_lag_shift(tmp_path):
    """MACRO-03: +1 BusinessDay shift — same-day event NOT visible (spec §6 trap #2)."""
    dates = pd.date_range('2020-03-13', '2020-03-25', freq='B')
    proxy_path = _write_synthetic_proxy(
        tmp_path, dates, [100.0] * len(dates), [50.0] * len(dates)
    )
    sbv_path = _write_synthetic_sbv(tmp_path, [('2020-03-17', 'tightening')])

    df = pd.DataFrame({'date': dates})
    result = add_macro_columns(df, proxy_path, sbv_path, sbv_decay_days=90)

    row_0317 = result[result['date'] == pd.Timestamp('2020-03-17')].iloc[0]
    assert row_0317['sbv_regime'] != 'tightening', (
        f"Same-day SBV regime MUST NOT be 'tightening' — spec §6 trap #2. "
        f"Got '{row_0317['sbv_regime']}' on 2020-03-17 with event on same day."
    )


# ── MACRO-04 (MacroVerdict + short-circuit) ─────────────────────────────

def test_macro_verdict_pass_through():
    """MACRO-04: MacroVerdict.pass_through() returns a verdict with is_pass()=True."""
    v = MacroVerdict.pass_through()
    assert v.is_pass(), "pass_through verdict must satisfy is_pass()"
    assert v.veto_sell is False
    assert v.effective_dd_threshold is None
    assert v.effective_stop_loss_max_multiplier is None


def test_macro_verdict_stacking():
    """MACRO-04 / D-04: MacroVerdict supports stacking — multiple non-None fields."""
    v = MacroVerdict(
        veto_sell=False,
        effective_dd_threshold=3,
        effective_stop_loss_max_multiplier=1.5,
    )
    assert not v.is_pass()
    assert v.effective_dd_threshold == 3
    assert v.effective_stop_loss_max_multiplier == 1.5


@pytest.mark.skipif(
    not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
    reason='MacroFilter class lands in Plan 03; this test is a stub for that plan'
)
def test_short_circuit_when_disabled():
    """MACRO-04 / D-09: macro_filter_enabled=False → first-line return pass_through.

    Plan 03 implements MacroFilter.apply(); this stub passes when the class
    lands and exercises the disabled-path short-circuit.
    """
    from strategies.mdm_hybrid.macro_filter import MacroFilter
    from strategies.mdm_hybrid.config import HybridConfig
    cfg = HybridConfig(v2_config=replace(VN30_PRESET, macro_filter_enabled=False))
    mf = MacroFilter(cfg)
    # Empty row — should not even read columns due to short-circuit
    verdict = mf.apply(pd.Series(dtype=object), current_state=None)
    assert verdict.is_pass(), 'Short-circuit broken — pass_through expected'


# ── MACRO-05 policy verbs (require MacroFilter class — Plan 03) ─────────

@pytest.mark.skipif(
    not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
    reason='MacroFilter class lands in Plan 03'
)
def test_dxy_easing_vetoes_sell():
    """MACRO-05 / D-01: DXY z < dxy_easing_z_threshold → veto_sell=True."""
    from strategies.mdm_hybrid.macro_filter import MacroFilter
    from strategies.mdm_hybrid.config import HybridConfig
    from strategies.mdm_hybrid.position_manager import V2MarketState
    cfg = HybridConfig(v2_config=replace(VN30_PRESET,
        macro_filter_enabled=True, dxy_easing_z_threshold=-1.0))
    mf = MacroFilter(cfg)
    row = pd.Series({'dxy_z': -1.5, 'eem_z': 0.0, 'sbv_regime': 'neutral'})
    verdict = mf.apply(row, current_state=V2MarketState.BUY)
    assert verdict.veto_sell is True


@pytest.mark.skipif(
    not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
    reason='MacroFilter class lands in Plan 03'
)
def test_dxy_tightening_lowers_dd():
    """MACRO-05 / D-02: DXY z > dxy_tightening_z_threshold → effective_dd_threshold set."""
    from strategies.mdm_hybrid.macro_filter import MacroFilter
    from strategies.mdm_hybrid.config import HybridConfig
    from strategies.mdm_hybrid.position_manager import V2MarketState
    cfg = HybridConfig(v2_config=replace(VN30_PRESET,
        macro_filter_enabled=True, dxy_tightening_z_threshold=+1.0,
        dxy_tightening_dd_threshold=3))
    mf = MacroFilter(cfg)
    row = pd.Series({'dxy_z': +1.5, 'eem_z': 0.0, 'sbv_regime': 'neutral'})
    verdict = mf.apply(row, current_state=V2MarketState.BUY)
    assert verdict.effective_dd_threshold == 3


@pytest.mark.skipif(
    not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
    reason='MacroFilter class lands in Plan 03'
)
def test_sbv_tightening_shrinks_stop_loss():
    """MACRO-05 / D-03: SBV regime=tightening → effective_stop_loss_max_multiplier set."""
    from strategies.mdm_hybrid.macro_filter import MacroFilter
    from strategies.mdm_hybrid.config import HybridConfig
    from strategies.mdm_hybrid.position_manager import V2MarketState
    cfg = HybridConfig(v2_config=replace(VN30_PRESET,
        macro_filter_enabled=True, sbv_tightening_stop_loss_max_multiplier=1.5))
    mf = MacroFilter(cfg)
    row = pd.Series({'dxy_z': 0.0, 'eem_z': 0.0, 'sbv_regime': 'tightening'})
    verdict = mf.apply(row, current_state=V2MarketState.BUY)
    assert verdict.effective_stop_loss_max_multiplier == 1.5


@pytest.mark.skipif(
    not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
    reason='MacroFilter class lands in Plan 03'
)
def test_most_restrictive_combiner():
    """MACRO-05 / D-04: DXY tightening + SBV tightening → BOTH overrides set (stacking)."""
    from strategies.mdm_hybrid.macro_filter import MacroFilter
    from strategies.mdm_hybrid.config import HybridConfig
    from strategies.mdm_hybrid.position_manager import V2MarketState
    cfg = HybridConfig(v2_config=replace(VN30_PRESET, macro_filter_enabled=True))
    mf = MacroFilter(cfg)
    row = pd.Series({'dxy_z': +1.5, 'eem_z': 0.0, 'sbv_regime': 'tightening'})
    verdict = mf.apply(row, current_state=V2MarketState.BUY)
    # BOTH overrides must be set per D-04 stacking
    assert verdict.effective_dd_threshold is not None, 'D-04 stacking broken: dd_threshold not set'
    assert verdict.effective_stop_loss_max_multiplier is not None, 'D-04 stacking broken: stop_loss not set'
    # AND no veto_sell (cautionary tightening blocks bullish veto)
    assert verdict.veto_sell is False, 'D-04 cautionary-wins broken: veto_sell set despite tightening'


@pytest.mark.skipif(
    not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
    reason='MacroFilter class lands in Plan 03'
)
def test_d04_cautionary_wins():
    """MACRO-05 / D-04: DXY easing + SBV tightening → no veto_sell (cautionary blocks bullish)."""
    from strategies.mdm_hybrid.macro_filter import MacroFilter
    from strategies.mdm_hybrid.config import HybridConfig
    from strategies.mdm_hybrid.position_manager import V2MarketState
    cfg = HybridConfig(v2_config=replace(VN30_PRESET, macro_filter_enabled=True))
    mf = MacroFilter(cfg)
    row = pd.Series({'dxy_z': -1.5, 'eem_z': 0.0, 'sbv_regime': 'tightening'})
    verdict = mf.apply(row, current_state=V2MarketState.BUY)
    assert verdict.veto_sell is False, 'D-04 cautionary-wins broken'
    assert verdict.effective_stop_loss_max_multiplier is not None, 'SBV tightening should still tighten stop-loss'


@pytest.mark.skipif(
    not hasattr(__import__('strategies.mdm_hybrid.macro_filter', fromlist=['']), 'MacroFilter'),
    reason='MacroFilter class lands in Plan 03'
)
def test_eem_easing_vetoes_sell():
    """MACRO-05 / D-13: EEM easing alone (z > +threshold) → veto_sell=True (symmetric to DXY)."""
    from strategies.mdm_hybrid.macro_filter import MacroFilter
    from strategies.mdm_hybrid.config import HybridConfig
    from strategies.mdm_hybrid.position_manager import V2MarketState
    cfg = HybridConfig(v2_config=replace(VN30_PRESET,
        macro_filter_enabled=True, eem_easing_z_threshold=+1.0))
    mf = MacroFilter(cfg)
    # Note D-12 sign flip: EEM easing = z > +threshold (positive)
    row = pd.Series({'dxy_z': 0.0, 'eem_z': +1.5, 'sbv_regime': 'neutral'})
    verdict = mf.apply(row, current_state=V2MarketState.BUY)
    assert verdict.veto_sell is True, 'D-13 EEM symmetry broken: EEM easing did not veto SELL'


# ── Config presence + validation gating (lands with Task 1, runs now) ──

def test_config_field_presence():
    """MACRO-05 / D-15: All 10 fields present in MDMV2Config + both presets."""
    expected_fields = [
        'macro_filter_enabled',
        'dxy_easing_z_threshold', 'dxy_tightening_z_threshold',
        'eem_easing_z_threshold', 'eem_tightening_z_threshold',
        'dxy_window_days', 'eem_window_days', 'sbv_decay_days',
        'dxy_tightening_dd_threshold', 'sbv_tightening_stop_loss_max_multiplier',
    ]
    for f in expected_fields:
        assert f in MDMV2Config.__dataclass_fields__, f'MDMV2Config missing field: {f}'
        assert hasattr(VN30_PRESET, f), f'VN30_PRESET missing field: {f}'
        assert hasattr(NASDAQ_PRESET, f), f'NASDAQ_PRESET missing field: {f}'
    # Defaults
    assert VN30_PRESET.macro_filter_enabled is False, 'VN30_PRESET must default macro filter OFF (D-09 parity)'
    assert NASDAQ_PRESET.macro_filter_enabled is False, 'NASDAQ_PRESET must default macro filter OFF'
    assert VN30_PRESET.dxy_easing_z_threshold == -1.0
    assert VN30_PRESET.dxy_tightening_z_threshold == +1.0
    assert VN30_PRESET.eem_easing_z_threshold == +1.0
    assert VN30_PRESET.eem_tightening_z_threshold == -1.0
    assert VN30_PRESET.dxy_window_days == 20
    assert VN30_PRESET.eem_window_days == 20
    assert VN30_PRESET.sbv_decay_days == 90
    assert VN30_PRESET.dxy_tightening_dd_threshold == 3
    assert VN30_PRESET.sbv_tightening_stop_loss_max_multiplier == 1.5


def test_config_validation_gated_on_flag():
    """MACRO-05 / D-09: Validation only fires when macro_filter_enabled=True (Phase 39 D-06 precedent)."""
    # OFF + invalid value → no error (validation gated)
    MDMV2Config(macro_filter_enabled=False, dxy_easing_z_threshold=+1.0)  # Should not raise
    # ON + invalid value → AssertionError
    with pytest.raises(AssertionError, match='should be negative'):
        MDMV2Config(macro_filter_enabled=True, dxy_easing_z_threshold=+1.0)
    with pytest.raises(AssertionError, match='should be positive'):
        MDMV2Config(macro_filter_enabled=True, dxy_tightening_z_threshold=-1.0)
    with pytest.raises(AssertionError, match='must be in'):
        MDMV2Config(macro_filter_enabled=True,
                   sbv_tightening_stop_loss_max_multiplier=3.0,
                   stop_loss_max_multiplier=2.5)
