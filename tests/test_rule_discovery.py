"""Tests for Phase 9 Rule Discovery (DISC-01 through DISC-04)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np


def _make_mock_snapshot(n=100):
    """Create a mock feature snapshot DataFrame for testing."""
    rng = np.random.RandomState(42)
    dates = pd.date_range('2010-01-01', periods=n, freq='7D')
    signals = rng.choice(['Buy', 'Cash', 'Sell'], size=n)
    return pd.DataFrame({
        'date': dates,
        'signal': signals,
        'close': rng.uniform(1000, 5000, n),
        'ema9': rng.uniform(1000, 5000, n),
        'ema21': rng.uniform(1000, 5000, n),
        'ema55': rng.uniform(1000, 5000, n),
        'ma200': rng.uniform(1000, 5000, n),
        'macd': rng.uniform(-50, 50, n),
        'macd_signal': rng.uniform(-50, 50, n),
        'macd_histogram': rng.uniform(-30, 30, n),
        'ema9_above_ema21': rng.choice([True, False], n),
        'ema21_above_ema55': rng.choice([True, False], n),
        'close_above_ma200': rng.choice([True, False], n),
        'close_above_ema9': rng.choice([True, False], n),
        'close_above_ema21': rng.choice([True, False], n),
        'close_above_ema55': rng.choice([True, False], n),
        'macd_histogram_positive': rng.choice([True, False], n),
        'macd_above_signal': rng.choice([True, False], n),
    })


def test_boolean_frequency_profile():
    """DISC-01: Boolean feature frequency table has all 8 features and 3 signal types."""
    from analysis.rule_discovery import profile_boolean_features, BOOLEAN_FEATURES
    snap = _make_mock_snapshot()
    result = profile_boolean_features(snap, BOOLEAN_FEATURES)
    # Result is a DataFrame with features as rows, signal types as columns
    assert isinstance(result, pd.DataFrame)
    assert set(result.index) == set(BOOLEAN_FEATURES)
    for sig in ['Buy', 'Cash', 'Sell']:
        assert sig in result.columns, f"Missing signal type column: {sig}"
    # Values should be between 0 and 1 (proportions)
    assert (result >= 0).all().all()
    assert (result <= 1).all().all()


def test_continuous_stats_profile():
    """DISC-01: Continuous feature stats produce per-signal-type descriptive statistics."""
    from analysis.rule_discovery import profile_continuous_features, CONTINUOUS_FEATURES
    snap = _make_mock_snapshot()
    result = profile_continuous_features(snap, CONTINUOUS_FEATURES)
    # Result is a multi-index DataFrame from groupby.describe()
    assert isinstance(result, pd.DataFrame)
    # Should contain stats for all signal types
    assert set(result.index.get_level_values(0)) == {'Buy', 'Cash', 'Sell'}


def test_era_split_produces_separate_results():
    """DISC-04: Era split at 2019-02-09 separates pre/post-2019 data."""
    from analysis.rule_discovery import split_by_era, ERA_SPLIT_DATE
    snap = _make_mock_snapshot(200)
    # Override dates to span the era boundary
    snap['date'] = pd.date_range('2018-01-01', periods=200, freq='7D')
    pre, post = split_by_era(snap)
    assert len(pre) > 0
    assert len(post) > 0
    assert len(pre) + len(post) == len(snap)
    assert pre['date'].max() < pd.Timestamp(ERA_SPLIT_DATE)
    assert post['date'].min() >= pd.Timestamp(ERA_SPLIT_DATE)


def test_decision_tree_above_chance():
    """DISC-02: Decision tree achieves above-chance accuracy (>34% for 3-class)."""
    from analysis.rule_discovery import train_era_tree, BOOLEAN_FEATURES
    # Use real-ish data with some signal in features
    snap = _make_mock_snapshot(300)
    # Inject signal: when ema9_above_ema21=True, bias toward Buy
    mask = snap['ema9_above_ema21'] == True
    snap.loc[mask, 'signal'] = np.where(
        np.random.RandomState(1).random(mask.sum()) < 0.6, 'Buy', snap.loc[mask, 'signal']
    )
    clf, cv_accuracy, feature_names = train_era_tree(snap, BOOLEAN_FEATURES, max_depth=4)
    assert cv_accuracy > 0.34, f"CV accuracy {cv_accuracy:.2%} not above chance (34%)"
    assert clf is not None
    assert hasattr(clf, 'predict')


def test_rule_extraction_format():
    """DISC-03: Extracted rules match expected format with confidence scores."""
    from analysis.rule_discovery import train_era_tree, extract_rules, BOOLEAN_FEATURES
    snap = _make_mock_snapshot(300)
    clf, _, feature_names = train_era_tree(snap, BOOLEAN_FEATURES, max_depth=3)
    class_names = ['Buy', 'Cash', 'Sell']
    rules = extract_rules(clf, feature_names, class_names)
    assert len(rules) > 0, "No rules extracted"
    for rule in rules:
        # Each rule should contain a signal type, 'when', and 'confidence'
        assert any(cls in rule for cls in class_names), f"No class name in rule: {rule}"
        assert 'when' in rule, f"Missing 'when' keyword in rule: {rule}"
        assert 'confidence' in rule, f"Missing 'confidence' in rule: {rule}"
        assert '(' in rule and 'N=' in rule, f"Missing sample count in rule: {rule}"
