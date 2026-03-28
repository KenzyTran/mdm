"""
Tests for VN30 sweep and backtest report functionality.

Tests cover:
- Backtest report metrics (V2PerformanceAnalyzer output validation)
- Buy-and-hold comparison accuracy
- Text summary format
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_v2.performance import V2PerformanceAnalyzer
from analysis.backtest_vn30 import compute_buy_and_hold, generate_text_summary


def _make_synthetic_vn30_data(n_rows=100, start_price=500.0, start_date='2014-01-02'):
    """Create synthetic VN30-like DataFrame for testing.

    Generates n_rows of daily OHLCV data with realistic VN30 prices
    around the start_price range and volume around 100M.
    """
    np.random.seed(42)
    dates = pd.bdate_range(start=start_date, periods=n_rows)
    # Random walk for close prices
    daily_returns = np.random.normal(0.0005, 0.012, n_rows)
    close = start_price * np.cumprod(1 + daily_returns)

    # Build OHLCV
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n_rows)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n_rows)))
    open_price = close * (1 + np.random.normal(0, 0.003, n_rows))
    volume = np.random.uniform(80e6, 120e6, n_rows)

    df = pd.DataFrame({
        'date': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })
    return df


class TestBacktestReportMetrics:
    """Test that backtest report produces all required metrics."""

    def test_backtest_report_metrics(self):
        """V2PerformanceAnalyzer.summary() returns all required keys with numeric values."""
        df = _make_synthetic_vn30_data(100, start_price=500.0)

        engine = MDMV2Engine(MDMV2Config())
        results = engine.run(df)
        trades = engine.get_trades()

        analyzer = V2PerformanceAnalyzer(results, trades)
        summary = analyzer.summary()

        required_keys = ['total_return', 'annualized_return', 'max_drawdown',
                         'sharpe_ratio', 'win_rate']
        for key in required_keys:
            assert key in summary, f"Missing key: {key}"
            val = summary[key]
            # win_rate can be 0.0 if no trades, but must be numeric
            assert isinstance(val, (int, float, np.integer, np.floating)), (
                f"Value for {key} is not numeric: {type(val)}"
            )
            assert not np.isnan(val), f"Value for {key} is NaN"


class TestBuyAndHoldComparison:
    """Test buy-and-hold metrics computation."""

    def test_buy_and_hold_comparison(self):
        """compute_buy_and_hold returns correct total_return for known prices."""
        # Linear increase from 500 to 600 over 50 days
        dates = pd.bdate_range(start='2014-01-02', periods=50)
        close = np.linspace(500, 600, 50)
        df = pd.DataFrame({
            'date': dates,
            'close': close,
        })

        result = compute_buy_and_hold(df)

        assert 'total_return' in result
        assert 'annualized_return' in result
        assert 'max_drawdown' in result
        assert 'sharpe_ratio' in result

        # total_return should be 0.20 (600/500 - 1)
        assert abs(result['total_return'] - 0.20) < 0.01, (
            f"Expected total_return ~0.20, got {result['total_return']}"
        )

        # Max drawdown should be 0.0 for monotonically increasing prices
        assert result['max_drawdown'] == 0.0, (
            f"Expected max_drawdown 0.0 for increasing prices, got {result['max_drawdown']}"
        )


class TestTextSummaryFormat:
    """Test text summary generation format."""

    def test_text_summary_format(self):
        """generate_text_summary returns string with expected sections."""
        # Create mock analyzer
        df = _make_synthetic_vn30_data(100, start_price=500.0)
        engine = MDMV2Engine(MDMV2Config())
        results = engine.run(df)
        trades = engine.get_trades()
        analyzer = V2PerformanceAnalyzer(results, trades)

        bh_metrics = {
            'total_return': 0.15,
            'annualized_return': 0.10,
            'max_drawdown': -0.20,
            'sharpe_ratio': 0.80,
        }

        config = MDMV2Config(name='test_config')

        text = generate_text_summary(analyzer, bh_metrics, config)

        assert "VN30 MDM v2 Backtest Summary" in text
        assert "Buy-and-Hold" in text
        assert "Sharpe" in text
        assert "test_config" in text

    def test_text_summary_with_train_test(self):
        """generate_text_summary includes train/test gap when analyzers provided."""
        df = _make_synthetic_vn30_data(200, start_price=500.0)
        engine = MDMV2Engine(MDMV2Config())
        results = engine.run(df)
        trades = engine.get_trades()

        full_analyzer = V2PerformanceAnalyzer(results, trades)
        # Split at midpoint for train/test
        mid = len(results) // 2
        train_analyzer = V2PerformanceAnalyzer(results.iloc[:mid].reset_index(drop=True))
        test_analyzer = V2PerformanceAnalyzer(results.iloc[mid:].reset_index(drop=True))

        bh_metrics = {'total_return': 0.10, 'annualized_return': 0.05,
                      'max_drawdown': -0.15, 'sharpe_ratio': 0.60}
        config = MDMV2Config()

        text = generate_text_summary(full_analyzer, bh_metrics, config,
                                     train_analyzer, test_analyzer)

        assert "Train Period" in text
        assert "Test Period" in text
        assert "Train/Test Gap" in text
