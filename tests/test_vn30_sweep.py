"""
Tests for VN30 parameter sweep scoring function abstraction and VN30 sweep script.
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analysis.hypothesis.parameter_sweep import run_sweep, print_sweep_summary


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

    # Verify scoring_fn was called (not run_hypothesis)
    assert call_count[0] == 2, f"Expected 2 calls, got {call_count[0]}"

    # Verify results sorted by 'score' descending
    assert 'score' in results.columns
    scores = results['score'].tolist()
    assert scores == sorted(scores, reverse=True), "Results not sorted by score descending"

    # Verify parameter columns present
    assert 'correction_threshold' in results.columns
    assert 'ftd_min_rally_day' in results.columns

    # Verify hypothesis names present
    assert 'hypothesis' in results.columns


def test_backward_compatibility():
    """Test that run_sweep without scoring_fn still uses run_hypothesis and sorts by match_rate."""
    df = _make_synthetic_ohlcv(20)

    # Create fake published_signals DataFrame
    published_signals = pd.DataFrame({
        'date': pd.to_datetime(['2018-01-15', '2018-02-01']),
        'signal': ['Buy', 'Cash'],
    })

    # Patch run_hypothesis to return mock results without needing real engine
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

        # Verify run_hypothesis was called
        assert call_count[0] == 2, f"Expected 2 calls, got {call_count[0]}"

        # Verify sorted by match_rate
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


# --- Task 2 integration tests ---

from analysis.sweep_vn30 import sharpe_scoring_fn, VN30_PARAM_GRID
from strategies.mdm_v2.vn30_filters import apply_vn30_filters
from strategies.mdm_v2.config import MDMV2Config


def _make_synthetic_vn30(n_rows=100, start_date='2017-01-01'):
    """Create a synthetic VN30-like DataFrame with enough rows for engine warm-up."""
    dates = pd.bdate_range(start=start_date, periods=n_rows)
    np.random.seed(123)
    # Start at VN30-like price level
    close = 900 + np.cumsum(np.random.randn(n_rows) * 5.0)
    # Ensure positive
    close = np.maximum(close, 100)
    return pd.DataFrame({
        'date': dates,
        'open': close - np.random.rand(n_rows) * 2,
        'high': close + np.abs(np.random.randn(n_rows)) * 4,
        'low': close - np.abs(np.random.randn(n_rows)) * 4,
        'close': close,
        'volume': np.random.randint(50_000_000, 200_000_000, size=n_rows).astype(float),
    })


def test_sharpe_sweep_runs():
    """Test that Sharpe-optimized sweep completes with a small grid and returns sorted results."""
    df = _make_synthetic_vn30(100)
    df = apply_vn30_filters(df)

    # 2x2 = 4 combos (small grid for speed)
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

    # Verify result structure
    assert isinstance(results, pd.DataFrame)
    assert len(results) == 4
    assert 'score' in results.columns
    assert 'hypothesis' in results.columns

    # Verify sorted by score descending
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

    # score should equal sharpe_ratio
    assert result['score'] == result['sharpe_ratio']

    # num_trades should be non-negative integer
    assert isinstance(result['num_trades'], int)
    assert result['num_trades'] >= 0


def test_sharpe_scoring_fn_no_trades():
    """Test that sharpe_scoring_fn handles edge case of no CASH_EXIT trades gracefully."""
    # Create a flat dataset with no price movement -- no signals should fire
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

    # With flat prices and tiny data, should have 0 trades and score 0
    assert result['score'] == 0.0
    assert result['num_trades'] == 0
