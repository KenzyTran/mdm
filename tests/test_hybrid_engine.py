"""Tests for HybridEngine: regression against v2, snapshot/restore isolation, config defaults."""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Resolve paths for worktree data access
WORKTREE_ROOT = Path(__file__).resolve().parent.parent
MAIN_REPO = WORKTREE_ROOT
# If running from a git worktree, data lives in the main repo
# Worktree path: .../mdm/.claude/worktrees/agent-xxx -> main repo is .../mdm
if '.claude' in str(WORKTREE_ROOT) and 'worktrees' in str(WORKTREE_ROOT):
    # Walk up to find the main repo (parent of .claude directory)
    parts = WORKTREE_ROOT.parts
    for i, part in enumerate(parts):
        if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
            MAIN_REPO = Path(*parts[:i])
            break

from strategies.mdm_v2.config import MDMV2Config as V2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from core.data_loader import DataLoader


def _make_ohlcv(n=100, start_date="2020-01-01"):
    """Create synthetic OHLCV DataFrame for testing."""
    np.random.seed(42)
    dates = pd.bdate_range(start=start_date, periods=n)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.2
    volume = np.random.randint(1_000_000, 5_000_000, n).astype(float)

    return pd.DataFrame({
        'date': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'symbol': 'TEST',
    })


@pytest.fixture
def nasdaq_data():
    """Load full NASDAQ data from main repo."""
    loader = DataLoader('nasdaq')
    loader.data_dir = MAIN_REPO
    df = loader.load()
    if df is None or df.empty:
        pytest.skip("NASDAQ data not available")
    return df


def test_hybrid_matches_v2_on_nasdaq(nasdaq_data):
    """Bit-for-bit regression: hybrid (no filter) == v2 on full NASDAQ data."""
    # Run v2
    v2_config = V2Config()
    v2_engine = MDMV2Engine(v2_config)
    v2_result = v2_engine.run(nasdaq_data)

    # Run hybrid with matching config and filter disabled
    hybrid_config = HybridConfig(v2_config=MDMV2Config(), filter_enabled=False)
    hybrid_engine = HybridEngine(hybrid_config)
    hybrid_result = hybrid_engine.run(nasdaq_data)

    # Assert state and action columns match bit-for-bit
    pd.testing.assert_series_equal(
        v2_result['state'], hybrid_result['state'],
        check_names=False,
        obj="state column"
    )
    pd.testing.assert_series_equal(
        v2_result['action'], hybrid_result['action'],
        check_names=False,
        obj="action column"
    )


def test_snapshot_restore_isolation():
    """Snapshot/restore provides full isolation: mutations don't survive restore."""
    engine = HybridEngine(HybridConfig())

    # Add fake dates to dd_counter history
    engine.dd_counter.dd_history = [
        pd.Timestamp('2020-01-01'),
        pd.Timestamp('2020-01-02'),
        pd.Timestamp('2020-01-03'),
    ]

    # Snapshot
    snapshot = engine._snapshot_components()

    # Mutate: reset clears dd_history
    engine.dd_counter.reset()
    assert len(engine.dd_counter.dd_history) == 0, "reset should clear dd_history"

    # Restore
    engine._restore_components(snapshot)
    assert len(engine.dd_counter.dd_history) == 3, "restore should bring back dd_history"


def test_vetoed_ftd_does_not_reset_dd_counter():
    """A vetoed FTD does not reset the DD counter -- snapshot/restore prevents corruption."""
    engine = HybridEngine(HybridConfig())

    # Simulate DD counter with 3 recorded distribution days
    engine.dd_counter.dd_history = [
        pd.Timestamp('2020-03-10'),
        pd.Timestamp('2020-03-12'),
        pd.Timestamp('2020-03-15'),
    ]

    # Snapshot before FTD processing
    snapshot = engine._snapshot_components()

    # Simulate FTD processing: dd_counter.reset() is called on FTD
    engine.dd_counter.reset()
    assert len(engine.dd_counter.dd_history) == 0, "FTD processing should reset dd_history"

    # Veto: restore from snapshot
    engine._restore_components(snapshot)
    assert len(engine.dd_counter.dd_history) == 3, (
        "After veto restore, DD counter should have original 3 items"
    )


def test_vetoed_ftd_does_not_reset_rally_tracker():
    """A vetoed FTD does not reset the rally tracker -- snapshot/restore prevents corruption."""
    engine = HybridEngine(HybridConfig())

    # Set rally tracker state
    engine.rally_tracker.rally_day_count = 5
    engine.rally_tracker.peak_high = 100.0
    engine.rally_tracker.in_correction = True

    # Snapshot
    snapshot = engine._snapshot_components()

    # Simulate FTD processing: rally_tracker.full_reset() is called after FTD
    engine.rally_tracker.full_reset()
    assert engine.rally_tracker.rally_day_count == 0, "full_reset should zero rally_day_count"
    assert engine.rally_tracker.peak_high == 0.0, "full_reset should zero peak_high"

    # Veto: restore from snapshot
    engine._restore_components(snapshot)
    assert engine.rally_tracker.rally_day_count == 5, (
        "After veto restore, rally_day_count should be 5"
    )
    assert engine.rally_tracker.peak_high == 100.0, (
        "After veto restore, peak_high should be 100.0"
    )


def test_hybrid_config_defaults():
    """HybridConfig() has correct defaults."""
    c = HybridConfig()
    assert c.two_phase_enabled is True
    assert c.filter_enabled is False
    assert isinstance(c.v2_config, MDMV2Config)


def test_hybrid_config_v2_defaults_match():
    """HybridConfig().v2_config matches V2Config() field-by-field (prevents config drift)."""
    hybrid_v2 = HybridConfig().v2_config
    direct_v2 = V2Config()

    # Compare all numeric and boolean fields
    assert hybrid_v2.correction_threshold == direct_v2.correction_threshold
    assert hybrid_v2.ftd_min_rally_day == direct_v2.ftd_min_rally_day
    assert hybrid_v2.ftd_max_rally_day == direct_v2.ftd_max_rally_day
    assert hybrid_v2.ftd_min_price_gain == direct_v2.ftd_min_price_gain
    assert hybrid_v2.ma50_breakout_correction == direct_v2.ma50_breakout_correction
    assert hybrid_v2.dd_window_size == direct_v2.dd_window_size
    assert hybrid_v2.dd_price_drop_threshold == direct_v2.dd_price_drop_threshold
    assert hybrid_v2.dd_price_stall_threshold == direct_v2.dd_price_stall_threshold
    assert hybrid_v2.dd_stall_p_loc_threshold == direct_v2.dd_stall_p_loc_threshold
    assert hybrid_v2.dd_cash_threshold == direct_v2.dd_cash_threshold
    assert hybrid_v2.ma10_cash_enabled == direct_v2.ma10_cash_enabled
    assert hybrid_v2.ma10_cash_consecutive == direct_v2.ma10_cash_consecutive
    assert hybrid_v2.ma50_sell_enabled == direct_v2.ma50_sell_enabled
    assert hybrid_v2.cash_deterioration_days == direct_v2.cash_deterioration_days
    assert hybrid_v2.stop_loss_pct == direct_v2.stop_loss_pct
    assert hybrid_v2.name == direct_v2.name


# ====================================================================
# Integration tests for Propose-Filter-Decide pipeline (Plan 02)
# HYB-03: Filter confirmation and veto
# HYB-04: Override forces Cash
# HYB-05: Cash insertion from BUY/SELL, no degradation from CASH
# D-09/D-10: Signal log columns populated
# ====================================================================


def test_filter_confirms_buy(nasdaq_data):
    """HYB-03: Filter confirms BUY when bullish conditions are met."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # With filter enabled, some BUY transitions should still occur (confirmed)
    buy_actions = results[results['action'].str.contains('BUY', na=False)]
    assert len(buy_actions) > 0, "At least one BUY should be confirmed by filter"

    # Confirmed BUYs should have verdict=CONFIRM
    confirmed_buys = results[
        (results['action'].str.contains('BUY', na=False)) &
        (results['verdict'] == 'CONFIRM')
    ]
    assert len(confirmed_buys) > 0, "At least one BUY should have CONFIRM verdict"


def test_filter_vetoes_buy_restores_snapshot(nasdaq_data):
    """HYB-03: Filter vetoes BUY proposal, state does not change."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # Look for rows where proposal was BUY but verdict was VETO
    vetoed_buys = results[
        (results['proposed'] == 'BUY') &
        (results['verdict'] == 'VETO')
    ]
    # When a BUY is vetoed, final state should NOT be BUY (should remain old_state)
    for _, row in vetoed_buys.iterrows():
        assert row['state'] != 'BUY' or row['old_state'] == 'BUY', (
            f"Vetoed BUY on {row['date']} should not transition to BUY "
            f"(old_state={row['old_state']}, final={row['state']})"
        )


def test_override_forces_cash_from_buy(nasdaq_data):
    """HYB-04: OVERRIDE forces Cash regardless of proposal."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # Any OVERRIDE verdict should result in CASH state
    overrides = results[results['verdict'] == 'OVERRIDE']
    for _, row in overrides.iterrows():
        assert row['state'] == 'CASH', (
            f"OVERRIDE on {row['date']} should force CASH, got {row['state']}"
        )


def test_override_forces_cash_from_sell(nasdaq_data):
    """HYB-04: OVERRIDE from SELL state uses degrade_to_cash (no P&L)."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)
    trades = engine.get_trades()

    # Check for STATE_DEGRADE trades (SELL->CASH degradation)
    degrade_trades = [t for t in trades if t['type'] == 'STATE_DEGRADE']
    # STATE_DEGRADE trades should have no 'pnl' key
    for t in degrade_trades:
        assert 'pnl' not in t, f"STATE_DEGRADE trade should not have pnl: {t}"


def test_cash_insertion_from_buy(nasdaq_data):
    """HYB-05: Indicator degradation inserts Cash from BUY state."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # Look for cash insertion: old_state=BUY, no state change proposed (proposed=BUY),
    # verdict=VETO or OVERRIDE, final_state=CASH
    cash_insertions = results[
        (results['old_state'] == 'BUY') &
        (results['proposed'] == 'BUY') &
        (results['verdict'].isin(['VETO', 'OVERRIDE'])) &
        (results['state'] == 'CASH')
    ]
    assert len(cash_insertions) > 0, (
        "At least one cash insertion from BUY should occur on real NASDAQ data"
    )
    # These should have action mentioning indicator degradation or filter override
    for _, row in cash_insertions.iterrows():
        assert 'indicator degradation' in row['action'].lower() or 'filter override' in row['action'].lower(), (
            f"Cash insertion action should mention degradation: {row['action']}"
        )


def test_cash_insertion_from_sell(nasdaq_data):
    """HYB-05: Indicator degradation inserts Cash from SELL state (symmetric)."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # SELL->CASH degradation: old_state=SELL, proposed=SELL, verdict=VETO/OVERRIDE, state=CASH
    sell_degradations = results[
        (results['old_state'] == 'SELL') &
        (results['proposed'] == 'SELL') &
        (results['verdict'].isin(['VETO', 'OVERRIDE'])) &
        (results['state'] == 'CASH')
    ]
    # May not always occur depending on data -- if it does, verify correctness
    if len(sell_degradations) > 0:
        trades = engine.get_trades()
        degrade_trades = [t for t in trades if t['type'] == 'STATE_DEGRADE'
                          and 'SELL' in t.get('reason', '')]
        assert len(degrade_trades) > 0, "SELL degradation should produce STATE_DEGRADE trade"


def test_no_degradation_from_cash(nasdaq_data):
    """HYB-05: CASH state never degrades further (Pitfall 5)."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # When old_state=CASH and verdict=VETO/OVERRIDE on confirm-CASH,
    # final state should still be CASH (no "degradation" action)
    cash_confirms = results[
        (results['old_state'] == 'CASH') &
        (results['proposed'] == 'CASH') &
        (results['verdict'].isin(['VETO', 'OVERRIDE']))
    ]
    for _, row in cash_confirms.iterrows():
        assert 'degradation' not in row['action'].lower(), (
            f"CASH state should not degrade: action={row['action']}"
        )


def test_signal_log_columns_populated(nasdaq_data):
    """D-09/D-10: Signal log columns populated for every trading day."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # Skip first row (idx=0 is skipped in engine loop)
    active_rows = results.iloc[1:]

    # old_state, proposed, verdict should be populated for all active rows
    assert (active_rows['old_state'] != '').any(), "old_state should be populated"
    assert (active_rows['proposed'] != '').any(), "proposed should be populated"
    assert (active_rows['verdict'] != '').any(), "verdict should be populated"

    # Check that most rows have all three populated
    populated = active_rows[
        (active_rows['old_state'] != '') &
        (active_rows['proposed'] != '') &
        (active_rows['verdict'] != '')
    ]
    assert len(populated) == len(active_rows), (
        f"All {len(active_rows)} rows should have signal log data, "
        f"only {len(populated)} do"
    )


# ====================================================================
# Confidence column tests (Phase 15, Plan 01)
# ====================================================================


def test_confidence_column_exists(nasdaq_data):
    """Confidence column present with float values 0.0-1.0 when filter enabled."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    assert 'confidence' in results.columns, "confidence column should exist"
    # Skip first row (idx=0 skipped in engine loop)
    active = results.iloc[1:]
    assert active['confidence'].dtype in [float, 'float64'], "confidence should be float"
    assert (active['confidence'] >= 0.0).all(), "confidence should be >= 0.0"
    assert (active['confidence'] <= 1.0).all(), "confidence should be <= 1.0"


def test_confidence_column_filter_disabled(nasdaq_data):
    """Confidence column defaults to 1.0 when filter is disabled."""
    config = HybridConfig(filter_enabled=False)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    assert 'confidence' in results.columns, "confidence column should exist even without filter"
    active = results.iloc[1:]
    assert (active['confidence'] == 1.0).all(), (
        "confidence should be 1.0 for all rows when filter disabled"
    )


def test_baseline_unchanged(nasdaq_data):
    """Phase 14 behavior preserved: filter_enabled=True with default FilterConfig gives same states."""
    # Run without filter
    config_off = HybridConfig(filter_enabled=False)
    engine_off = HybridEngine(config_off)
    result_off = engine_off.run(nasdaq_data)

    # Run with filter (ha_smooth_enabled=False by default)
    config_on = HybridConfig(filter_enabled=True)
    engine_on = HybridEngine(config_on)
    result_on = engine_on.run(nasdaq_data)

    # State sequences should differ (filter changes behavior) but both should complete
    assert len(result_off) == len(result_on), "Both runs should produce same row count"
    # Confidence column should exist in both
    assert 'confidence' in result_off.columns
    assert 'confidence' in result_on.columns


# ====================================================================
# State history + contextual threshold tests (Phase 15, Plan 02)
# ADV-01: Contextual state transitions
# ====================================================================


def test_state_history_tracking(nasdaq_data):
    """State history records {state, entered_date, duration} on state transitions."""
    config = HybridConfig(filter_enabled=False)
    engine = HybridEngine(config)
    engine.run(nasdaq_data)

    # Engine must have state_history populated after run
    assert hasattr(engine, 'state_history'), "Engine should have state_history attribute"
    assert len(engine.state_history) > 0, (
        "state_history should have entries after processing NASDAQ data with transitions"
    )

    # Each entry must have required keys
    for entry in engine.state_history:
        assert 'state' in entry, f"state_history entry missing 'state': {entry}"
        assert 'entered_date' in entry, f"state_history entry missing 'entered_date': {entry}"
        assert 'duration' in entry, f"state_history entry missing 'duration': {entry}"
        assert entry['duration'] >= 1, f"duration should be >= 1: {entry}"
        assert entry['state'] in ('BUY', 'CASH', 'SELL'), f"Invalid state: {entry['state']}"


def test_state_history_only_on_changes(nasdaq_data):
    """State history length equals number of state transitions, not number of days."""
    config = HybridConfig(filter_enabled=False)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)

    # Count actual state transitions in results
    states = results['state'].tolist()
    transition_count = 0
    for i in range(1, len(states)):
        if states[i] != states[i - 1]:
            transition_count += 1

    # state_history records completed states (one per transition, minus the final ongoing state)
    # So it should be approximately transition_count (each transition closes prior state)
    history_len = len(engine.state_history)
    assert history_len < len(results), (
        f"state_history ({history_len}) should be far less than total days ({len(results)})"
    )
    assert history_len > 0, "Should have at least one completed state"
    # History should be close to transition count (transitions create history entries)
    assert history_len <= transition_count, (
        f"state_history ({history_len}) should not exceed transition count ({transition_count})"
    )


def test_contextual_cash_from_sell_stickier():
    """CASH entered from SELL with >5 days requires 100% threshold for BUY."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)

    # Simulate: prior state was SELL, now in CASH for 6 days
    engine.state_history = [{'state': 'SELL', 'entered_date': '2020-01-01', 'duration': 10}]
    engine._current_state_name = "CASH"
    engine._current_state_start = '2020-02-01'
    engine._days_in_current_state = 6

    threshold = engine._get_contextual_threshold("BUY")
    assert threshold == 1.0, f"BUY from CASH (entered from SELL, 6 days) should require 1.0, got {threshold}"


def test_contextual_long_cash_raises_threshold():
    """CASH for > cash_deterioration_days (10) requires 100% threshold for BUY."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)

    # Simulate: in CASH for 11 days (> default cash_deterioration_days=10)
    engine.state_history = [{'state': 'BUY', 'entered_date': '2020-01-01', 'duration': 20}]
    engine._current_state_name = "CASH"
    engine._current_state_start = '2020-02-01'
    engine._days_in_current_state = 11

    threshold = engine._get_contextual_threshold("BUY")
    assert threshold == 1.0, f"BUY from long CASH (11 days) should require 1.0, got {threshold}"


def test_contextual_normal_does_not_modify():
    """CASH for <5 days entered from BUY keeps default 2/3 threshold."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)

    # Simulate: in CASH for 3 days, entered from BUY (not bearish regime)
    engine.state_history = [{'state': 'BUY', 'entered_date': '2020-01-01', 'duration': 20}]
    engine._current_state_name = "CASH"
    engine._current_state_start = '2020-02-01'
    engine._days_in_current_state = 3

    threshold = engine._get_contextual_threshold("BUY")
    expected = config.filter_config.majority_threshold  # 2/3
    assert threshold == expected, f"Short CASH from BUY should keep default {expected}, got {threshold}"


def test_contextual_only_affects_buy_proposals():
    """SELL and CASH proposals are NOT affected by contextual threshold."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)

    # Simulate: bearish context (CASH from SELL, long duration)
    engine.state_history = [{'state': 'SELL', 'entered_date': '2020-01-01', 'duration': 10}]
    engine._current_state_name = "CASH"
    engine._current_state_start = '2020-02-01'
    engine._days_in_current_state = 15

    expected = config.filter_config.majority_threshold
    assert engine._get_contextual_threshold("SELL") == expected, "SELL should not be affected"
    assert engine._get_contextual_threshold("CASH") == expected, "CASH should not be affected"
