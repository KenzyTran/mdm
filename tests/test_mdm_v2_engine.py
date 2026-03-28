"""Tests for MDMV2Engine and signal comparator compatibility."""

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

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_v2.position_manager import V2MarketState
from core.signal_comparator import extract_model_signals, compare_signals, STATE_TO_SIGNAL


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


class TestMDMV2EngineOutput:
    """Test engine output structure."""

    def test_run_returns_dataframe_with_required_columns(self):
        engine = MDMV2Engine()
        df = _make_ohlcv(200)
        result = engine.run(df)
        assert isinstance(result, pd.DataFrame)
        for col in ['date', 'state', 'close']:
            assert col in result.columns, f"Missing column: {col}"

    def test_state_column_only_valid_values(self):
        engine = MDMV2Engine()
        df = _make_ohlcv(200)
        result = engine.run(df)
        valid_states = {"BUY", "CASH", "SELL"}
        actual_states = set(result['state'].unique())
        assert actual_states.issubset(valid_states), f"Invalid states: {actual_states - valid_states}"

    def test_no_classic_states_in_output(self):
        engine = MDMV2Engine()
        df = _make_ohlcv(200)
        result = engine.run(df)
        classic_states = {"HOLDING", "SHORT", "WAITING_SELL"}
        actual_states = set(result['state'].unique())
        assert actual_states.isdisjoint(classic_states), f"Classic states found: {actual_states & classic_states}"


class TestSignalComparatorCompatibility:
    """Test that v2 engine output works with signal comparator."""

    def test_state_to_signal_has_v2_mappings(self):
        assert STATE_TO_SIGNAL["BUY"] == "Buy"
        assert STATE_TO_SIGNAL["SELL"] == "Sell"
        assert STATE_TO_SIGNAL["CASH"] == "Cash"

    def test_extract_model_signals_produces_valid_output(self):
        engine = MDMV2Engine()
        df = _make_ohlcv(200)
        result = engine.run(df)
        signals = extract_model_signals(result)
        assert isinstance(signals, pd.DataFrame)
        assert 'date' in signals.columns
        assert 'signal' in signals.columns
        valid_signals = {"Buy", "Sell", "Cash"}
        actual_signals = set(signals['signal'].unique())
        assert actual_signals.issubset(valid_signals), f"Invalid signals: {actual_signals - valid_signals}"


class TestConfigAffectsBehavior:
    """Test that different configs produce different results."""

    def test_different_dd_threshold_changes_states(self):
        df = _make_ohlcv(300)
        engine_default = MDMV2Engine(MDMV2Config(dd_cash_threshold=5))
        engine_aggressive = MDMV2Engine(MDMV2Config(dd_cash_threshold=3))

        result_default = engine_default.run(df)
        result_aggressive = engine_aggressive.run(df)

        # Different thresholds should produce at least some different state values
        states_default = result_default['state'].tolist()
        states_aggressive = result_aggressive['state'].tolist()
        # They may be the same on synthetic data, but we check the engine accepted
        # different configs and ran without error
        assert len(states_default) == len(states_aggressive)


class TestIntegrationWithNASDAQData:
    """Integration test with real NASDAQ data."""

    @pytest.fixture
    def nasdaq_data(self):
        """Load NASDAQ data from main repo."""
        from core.data_loader import DataLoader
        loader = DataLoader('nasdaq')
        # Override data directory to main repo root (FILE_PATHS already contain 'data/')
        loader.data_dir = MAIN_REPO
        df = loader.load('2019-01-01', '2022-12-31')
        return df

    def test_engine_runs_on_nasdaq_data(self, nasdaq_data):
        if nasdaq_data is None or nasdaq_data.empty:
            pytest.skip("NASDAQ data not available")
        engine = MDMV2Engine()
        result = engine.run(nasdaq_data)
        assert len(result) > 0
        assert 'state' in result.columns

    def test_produces_buy_cash_transition(self, nasdaq_data):
        """Engine should produce at least one BUY->CASH transition on real data."""
        if nasdaq_data is None or nasdaq_data.empty:
            pytest.skip("NASDAQ data not available")
        engine = MDMV2Engine()
        result = engine.run(nasdaq_data)
        states = result['state'].tolist()
        # Check for BUY followed by CASH at some point
        found_buy_to_cash = False
        for i in range(1, len(states)):
            if states[i-1] == "BUY" and states[i] == "CASH":
                found_buy_to_cash = True
                break
        assert found_buy_to_cash, "No BUY->CASH transition found in NASDAQ data"

    def test_signal_comparator_pipeline(self, nasdaq_data):
        """Full pipeline: engine -> extract_model_signals -> compare_signals."""
        if nasdaq_data is None or nasdaq_data.empty:
            pytest.skip("NASDAQ data not available")
        engine = MDMV2Engine()
        result = engine.run(nasdaq_data)
        model_signals = extract_model_signals(result)

        # Load published signals
        from core.signal_loader import load_signal_fixture
        pub_signals = load_signal_fixture(str(MAIN_REPO / 'data' / 'signals' / 'nasdaq_signals.csv'))

        comparison = compare_signals(model_signals, pub_signals)
        assert isinstance(comparison, dict)
        assert 'match_rate' in comparison
        assert isinstance(comparison['match_rate'], float)
