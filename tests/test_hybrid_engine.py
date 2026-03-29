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
