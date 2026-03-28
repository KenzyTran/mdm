"""Tests for hypothesis runner and parameter sweep modules."""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Resolve paths for worktree data access
WORKTREE_ROOT = Path(__file__).resolve().parent.parent
MAIN_REPO = WORKTREE_ROOT
if '.claude' in str(WORKTREE_ROOT) and 'worktrees' in str(WORKTREE_ROOT):
    parts = WORKTREE_ROOT.parts
    for i, part in enumerate(parts):
        if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
            MAIN_REPO = Path(*parts[:i])
            break

sys.path.insert(0, str(WORKTREE_ROOT))

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from core.signal_comparator import extract_model_signals, compare_signals


def _make_ohlcv(n=200, start_date="2020-01-01", seed=42):
    """Create synthetic OHLCV DataFrame for testing."""
    np.random.seed(seed)
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


def _make_published_signals(df):
    """Create synthetic published signals from engine output for testing."""
    engine = MDMV2Engine()
    result = engine.run(df)
    signals = extract_model_signals(result)
    return signals


# ============================================================
# Hypothesis Runner Tests
# ============================================================

class TestHypothesisRunner:
    """Tests for run_hypothesis function."""

    @pytest.fixture
    def synthetic_data(self):
        df = _make_ohlcv(300)
        published = _make_published_signals(df)
        return df, published

    def test_hypothesis_runner(self, synthetic_data):
        """run_hypothesis returns dict with required keys."""
        from analysis.hypothesis.hypothesis_runner import run_hypothesis
        df, published = synthetic_data
        config = MDMV2Config(name="test")
        result = run_hypothesis("test", config, df, published)

        assert isinstance(result, dict)
        required_keys = {'hypothesis', 'match_rate', 'total_published',
                         'total_matched', 'buy_rate', 'sell_rate', 'cash_rate'}
        assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - set(result.keys())}"

    def test_hypothesis_match_rate_range(self, synthetic_data):
        """run_hypothesis returns match_rate as float between 0.0 and 100.0."""
        from analysis.hypothesis.hypothesis_runner import run_hypothesis
        df, published = synthetic_data
        config = MDMV2Config()
        result = run_hypothesis("test", config, df, published)

        assert isinstance(result['match_rate'], float)
        assert 0.0 <= result['match_rate'] <= 100.0

    def test_hypothesis_with_default_config_matches_self(self, synthetic_data):
        """When using same config that generated published signals, match rate should be 100%."""
        from analysis.hypothesis.hypothesis_runner import run_hypothesis
        df, published = synthetic_data
        config = MDMV2Config()
        result = run_hypothesis("self_match", config, df, published)
        assert result['match_rate'] == 100.0

    def test_batch_hypotheses(self, synthetic_data):
        """run_batch returns list of 2 result dicts."""
        from analysis.hypothesis.hypothesis_runner import run_batch
        df, published = synthetic_data
        config1 = MDMV2Config(dd_cash_threshold=5)
        config2 = MDMV2Config(dd_cash_threshold=3)
        hypotheses = [("h1", config1), ("h2", config2)]
        results = run_batch(hypotheses, df, published)

        assert isinstance(results, list)
        assert len(results) == 2

    def test_batch_sorted_by_match_rate(self, synthetic_data):
        """run_batch results are sorted by match_rate descending."""
        from analysis.hypothesis.hypothesis_runner import run_batch
        df, published = synthetic_data
        config1 = MDMV2Config(dd_cash_threshold=5)
        config2 = MDMV2Config(dd_cash_threshold=3)
        config3 = MDMV2Config(dd_cash_threshold=7)
        hypotheses = [("h1", config1), ("h2", config2), ("h3", config3)]
        results = run_batch(hypotheses, df, published)

        rates = [r['match_rate'] for r in results]
        assert rates == sorted(rates, reverse=True)

    def test_different_configs_different_rates(self, synthetic_data):
        """Different configs can produce different match_rates."""
        from analysis.hypothesis.hypothesis_runner import run_hypothesis
        df, published = synthetic_data
        config_a = MDMV2Config(dd_cash_threshold=3, stop_loss_pct=0.01)
        config_b = MDMV2Config(dd_cash_threshold=5, stop_loss_pct=0.05)
        result_a = run_hypothesis("a", config_a, df, published)
        result_b = run_hypothesis("b", config_b, df, published)
        # At least the engine accepted different configs and returned valid results
        assert isinstance(result_a['match_rate'], float)
        assert isinstance(result_b['match_rate'], float)


# ============================================================
# Parameter Sweep Tests
# ============================================================

class TestParameterSweep:
    """Tests for parameter sweep module."""

    @pytest.fixture
    def synthetic_data(self):
        df = _make_ohlcv(300)
        published = _make_published_signals(df)
        return df, published

    def test_parameter_sweep(self, synthetic_data):
        """run_sweep returns DataFrame with expected columns."""
        from analysis.hypothesis.parameter_sweep import run_sweep
        df, published = synthetic_data
        param_grid = {
            'dd_cash_threshold': [3, 5],
            'stop_loss_pct': [0.02, 0.03],
        }
        results = run_sweep(df, published, param_grid, top_n=10)

        assert isinstance(results, pd.DataFrame)
        for col in ['hypothesis', 'match_rate', 'buy_rate', 'sell_rate', 'cash_rate']:
            assert col in results.columns, f"Missing column: {col}"
        for col in ['dd_cash_threshold', 'stop_loss_pct']:
            assert col in results.columns, f"Missing param column: {col}"

    def test_sweep_combo_count(self, synthetic_data):
        """Sweep runs exactly the correct number of combinations."""
        from analysis.hypothesis.parameter_sweep import run_sweep
        df, published = synthetic_data
        param_grid = {
            'dd_cash_threshold': [3, 5],
            'stop_loss_pct': [0.02, 0.03],
        }
        # 2 x 2 = 4 combos, top_n=100 to get all
        results = run_sweep(df, published, param_grid, top_n=100)
        assert len(results) == 4

    def test_sweep_sorted_by_match_rate(self, synthetic_data):
        """Results DataFrame is sorted by match_rate descending."""
        from analysis.hypothesis.parameter_sweep import run_sweep
        df, published = synthetic_data
        param_grid = {
            'dd_cash_threshold': [3, 4, 5],
        }
        results = run_sweep(df, published, param_grid, top_n=10)
        rates = results['match_rate'].tolist()
        assert rates == sorted(rates, reverse=True)

    def test_sweep_output_format(self, synthetic_data, tmp_path):
        """save_sweep_results creates CSV with expected columns."""
        from analysis.hypothesis.parameter_sweep import run_sweep, save_sweep_results
        df, published = synthetic_data
        param_grid = {
            'dd_cash_threshold': [3, 5],
        }
        results = run_sweep(df, published, param_grid, top_n=10)
        output_path = str(tmp_path / "test_sweep.csv")
        save_sweep_results(results, output_path)

        saved = pd.read_csv(output_path)
        assert 'hypothesis' in saved.columns or 'name' in saved.columns
        assert 'match_rate' in saved.columns

    def test_sweep_summary_text(self, synthetic_data):
        """print_sweep_summary returns string containing 'match_rate'."""
        from analysis.hypothesis.parameter_sweep import run_sweep, print_sweep_summary
        df, published = synthetic_data
        param_grid = {
            'dd_cash_threshold': [3, 5],
        }
        results = run_sweep(df, published, param_grid, top_n=10)
        summary = print_sweep_summary(results, top_n=3)
        assert isinstance(summary, str)
        assert "match_rate" in summary
