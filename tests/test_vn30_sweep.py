"""
Tests for VN30 parameter sweep scoring function abstraction, VN30 sweep script,
and backtest report functionality.

Tests cover:
- Scoring function abstraction (scoring_fn vs match_rate modes)
- VN30 Sharpe-optimized sweep integration
- Backtest report metrics (V2PerformanceAnalyzer output validation)
- Buy-and-hold comparison accuracy
- Text summary format
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analysis.hypothesis.parameter_sweep import run_sweep, print_sweep_summary
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from strategies.mdm_v2.performance import V2PerformanceAnalyzer
from analysis.backtest_vn30 import compute_buy_and_hold, generate_text_summary
from analysis.sweep_vn30 import sharpe_scoring_fn, VN30_PARAM_GRID
from strategies.mdm_v2.vn30_filters import apply_vn30_filters


def _make_synthetic_ohlcv(n_rows=50, start_date='2018-01-01'):
    """Create synthetic OHLCV DataFrame for testing."""
    dates = pd.bdate_range(start=start_date, periods=n_rows)
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n_rows) * 0.5)
    return pd.DataFrame({
        'date': dates,
        'open': close - np.random.rand(n_rows) * 0.3,
        'high': close + np.abs(np.random.randn(n_rows)) * 0.5,
        'low': close - np.abs(np.random.randn(n_rows)) * 0.5,
        'close': close,
        'volume': np.random.randint(1000000, 5000000, size=n_rows).astype(float),
    })


def _make_synthetic_vn30_data(n_rows=100, start_price=500.0, start_date='2014-01-02'):
    """Create synthetic VN30-like DataFrame for testing.

    Generates n_rows of daily OHLCV data with realistic VN30 prices
    around the start_price range and volume around 100M.
    """
    np.random.seed(42)
    dates = pd.bdate_range(start=start_date, periods=n_rows)
    daily_returns = np.random.normal(0.0005, 0.012, n_rows)
    close = start_price * np.cumprod(1 + daily_returns)

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


def _make_synthetic_vn30(n_rows=100, start_date='2017-01-01'):
    """Create a synthetic VN30-like DataFrame with enough rows for engine warm-up."""
    dates = pd.bdate_range(start=start_date, periods=n_rows)
    np.random.seed(123)
    close = 900 + np.cumsum(np.random.randn(n_rows) * 5.0)
    close = np.maximum(close, 100)
    return pd.DataFrame({
        'date': dates,
        'open': close - np.random.rand(n_rows) * 2,
        'high': close + np.abs(np.random.randn(n_rows)) * 4,
        'low': close - np.abs(np.random.randn(n_rows)) * 4,
        'close': close,
        'volume': np.random.randint(50_000_000, 200_000_000, size=n_rows).astype(float),
    })


# ============================================================
# Scoring function abstraction tests (Plan 06-02, Task 1)
# ============================================================

def test_scoring_fn_abstraction():
    """Test that run_sweep uses scoring_fn when provided instead of run_hypothesis."""
    df = _make_synthetic_ohlcv(20)

    call_count = [0]

    def mock_scoring_fn(config, df):
        call_count[0] += 1
        return {
            'score': 1.5 + np.random.random() * 0.5,
            'sharpe_ratio': 1.5,
            'total_return': 0.25,
            'max_drawdown': -0.05,
            'win_rate': 0.6,
        }

    mini_grid = {
        'correction_threshold': [-0.08, -0.10],
        'ftd_min_rally_day': [3],
    }

    results = run_sweep(
        df=df,
        param_grid=mini_grid,
        top_n=10,
        scoring_fn=mock_scoring_fn,
    )

    assert call_count[0] == 2, f"Expected 2 calls, got {call_count[0]}"
    assert 'score' in results.columns
    scores = results['score'].tolist()
    assert scores == sorted(scores, reverse=True), "Results not sorted by score descending"
    assert 'correction_threshold' in results.columns
    assert 'ftd_min_rally_day' in results.columns
    assert 'hypothesis' in results.columns


def test_backward_compatibility():
    """Test that run_sweep without scoring_fn still uses run_hypothesis and sorts by match_rate."""
    df = _make_synthetic_ohlcv(20)

    published_signals = pd.DataFrame({
        'date': pd.to_datetime(['2018-01-15', '2018-02-01']),
        'signal': ['Buy', 'Cash'],
    })

    import analysis.hypothesis.parameter_sweep as sweep_mod
    original_run_hypothesis = sweep_mod.run_hypothesis

    call_count = [0]

    def mock_run_hypothesis(name, config, df, published_signals):
        call_count[0] += 1
        return {
            'hypothesis': name,
            'match_rate': 50.0 + np.random.random() * 30,
            'total_published': 10,
            'total_matched': 5,
            'buy_rate': 60.0,
            'sell_rate': 40.0,
            'cash_rate': 50.0,
        }

    try:
        sweep_mod.run_hypothesis = mock_run_hypothesis

        mini_grid = {
            'correction_threshold': [-0.08, -0.10],
        }

        results = run_sweep(
            df=df,
            published_signals=published_signals,
            param_grid=mini_grid,
            top_n=10,
        )

        assert call_count[0] == 2, f"Expected 2 calls, got {call_count[0]}"
        assert 'match_rate' in results.columns
        rates = results['match_rate'].tolist()
        assert rates == sorted(rates, reverse=True), "Results not sorted by match_rate descending"

    finally:
        sweep_mod.run_hypothesis = original_run_hypothesis


def test_run_sweep_requires_scoring_or_signals():
    """Test that run_sweep raises ValueError when neither scoring_fn nor published_signals given."""
    df = _make_synthetic_ohlcv(10)
    mini_grid = {'correction_threshold': [-0.08]}

    with pytest.raises(ValueError, match="Either scoring_fn or published_signals"):
        run_sweep(df=df, param_grid=mini_grid)


def test_print_sweep_summary_score_mode():
    """Test that print_sweep_summary handles score-mode results correctly."""
    results_df = pd.DataFrame({
        'hypothesis': ['sweep_0000', 'sweep_0001'],
        'score': [1.8, 1.2],
        'sharpe_ratio': [1.8, 1.2],
        'total_return': [0.30, 0.15],
        'max_drawdown': [-0.05, -0.08],
        'win_rate': [0.65, 0.55],
        'correction_threshold': [-0.08, -0.10],
    })

    summary = print_sweep_summary(results_df, top_n=2)
    assert 'score: 1.8000' in summary
    assert 'Sharpe: 1.800' in summary
    assert 'Return:' in summary
    assert 'MaxDD:' in summary


# ============================================================
# VN30 Sharpe sweep integration tests (Plan 06-02, Task 2)
# ============================================================

def test_sharpe_sweep_runs():
    """Test that Sharpe-optimized sweep completes with a small grid and returns sorted results."""
    df = _make_synthetic_vn30(100)
    df = apply_vn30_filters(df)

    mini_grid = {
        'correction_threshold': [-0.08, -0.10],
        'ftd_min_rally_day': [3, 4],
    }

    results = run_sweep(
        df=df,
        param_grid=mini_grid,
        top_n=10,
        scoring_fn=sharpe_scoring_fn,
    )

    assert isinstance(results, pd.DataFrame)
    assert len(results) == 4
    assert 'score' in results.columns
    assert 'hypothesis' in results.columns

    scores = results['score'].tolist()
    assert scores == sorted(scores, reverse=True), "Results not sorted by score descending"


def test_sharpe_scoring_fn_returns_metrics():
    """Test that sharpe_scoring_fn returns all required metric keys."""
    df = _make_synthetic_vn30(100)
    df = apply_vn30_filters(df)

    config = MDMV2Config(name='test_sharpe')
    result = sharpe_scoring_fn(config, df)

    assert isinstance(result, dict)
    required_keys = {'score', 'sharpe_ratio', 'total_return', 'max_drawdown', 'win_rate',
                     'annualized_return', 'num_trades'}
    assert required_keys.issubset(result.keys()), (
        f"Missing keys: {required_keys - set(result.keys())}"
    )

    assert result['score'] == result['sharpe_ratio']
    assert isinstance(result['num_trades'], int)
    assert result['num_trades'] >= 0


def test_sharpe_scoring_fn_no_trades():
    """Test that sharpe_scoring_fn handles edge case of no CASH_EXIT trades gracefully."""
    dates = pd.bdate_range(start='2017-01-01', periods=10)
    df = pd.DataFrame({
        'date': dates,
        'open': [100.0] * 10,
        'high': [100.0] * 10,
        'low': [100.0] * 10,
        'close': [100.0] * 10,
        'volume': [1000000.0] * 10,
    })
    df = apply_vn30_filters(df)

    config = MDMV2Config(name='test_no_trades')
    result = sharpe_scoring_fn(config, df)

    assert result['score'] == 0.0
    assert result['num_trades'] == 0


# ============================================================
# Backtest report tests (Plan 06-03)
# ============================================================

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
            assert isinstance(val, (int, float, np.integer, np.floating)), (
                f"Value for {key} is not numeric: {type(val)}"
            )
            assert not np.isnan(val), f"Value for {key} is NaN"


class TestBuyAndHoldComparison:
    """Test buy-and-hold metrics computation."""

    def test_buy_and_hold_comparison(self):
        """compute_buy_and_hold returns correct total_return for known prices."""
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

        assert abs(result['total_return'] - 0.20) < 0.01, (
            f"Expected total_return ~0.20, got {result['total_return']}"
        )

        assert result['max_drawdown'] == 0.0, (
            f"Expected max_drawdown 0.0 for increasing prices, got {result['max_drawdown']}"
        )


class TestTextSummaryFormat:
    """Test text summary generation format."""

    def test_text_summary_format(self):
        """generate_text_summary returns string with expected sections."""
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
