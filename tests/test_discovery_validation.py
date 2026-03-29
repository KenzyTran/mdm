"""Tests for Phase 10 Discovery Validation (VAL-01, VAL-02, VAL-03)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from analysis.rule_discovery import train_era_tree, BOOLEAN_FEATURES, CLASS_NAMES
from analysis.validate_discovery import score_predictions, filter_high_confidence, cross_era_validation, generate_dashboard


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


def test_match_rate_scoring():
    """VAL-01: score_predictions returns confusion matrix, per-type metrics, and accuracy."""
    snapshot = _make_mock_snapshot(200)
    clf, _, feature_names = train_era_tree(snapshot, BOOLEAN_FEATURES)
    results = score_predictions(snapshot, clf, BOOLEAN_FEATURES)

    # Check return dict has required keys
    assert isinstance(results, dict)
    for key in ['y_true', 'y_pred', 'y_proba', 'confusion_matrix', 'classification_report', 'accuracy']:
        assert key in results, f"Missing key: {key}"

    # Confusion matrix shape is (3, 3)
    assert results['confusion_matrix'].shape == (3, 3)

    # Accuracy is a float between 0 and 1
    assert isinstance(results['accuracy'], float)
    assert 0.0 <= results['accuracy'] <= 1.0

    # Classification report has per-class keys
    report = results['classification_report']
    assert isinstance(report, dict)
    for cls in ['Buy', 'Cash', 'Sell']:
        assert cls in report, f"Missing class '{cls}' in classification_report"


def test_high_confidence_filtering():
    """VAL-01, D-02: filter_high_confidence filters by predict_proba >= threshold."""
    snapshot = _make_mock_snapshot(200)
    clf, _, feature_names = train_era_tree(snapshot, BOOLEAN_FEATURES)
    results = score_predictions(snapshot, clf, BOOLEAN_FEATURES)
    filtered = filter_high_confidence(results, threshold=0.70)

    # Return has same keys as score_predictions output
    assert isinstance(filtered, dict)
    for key in ['y_true', 'y_pred', 'y_proba', 'confusion_matrix', 'classification_report', 'accuracy']:
        assert key in filtered, f"Missing key in filtered: {key}"

    # Subset should be <= original size
    assert len(filtered['y_true']) <= 200

    # If any high-confidence predictions exist, classification_report has per-class keys
    if len(filtered['y_true']) > 0:
        report = filtered['classification_report']
        # At least one class should be present
        assert any(cls in report for cls in ['Buy', 'Cash', 'Sell'])


def test_cross_era_validation():
    """VAL-02, D-04: cross_era_validation returns same-era, cross-era, and degradation metrics."""
    snapshot = _make_mock_snapshot(200)
    # Override dates to span pre/post 2019 boundary (ERA_SPLIT_DATE = 2019-02-09)
    snapshot['date'] = pd.date_range('2016-01-01', periods=200, freq='14D')
    results = cross_era_validation(snapshot, BOOLEAN_FEATURES)

    # Check return dict has required keys
    assert isinstance(results, dict)
    for key in ['pre_same_era', 'post_same_era', 'pre_on_post', 'post_on_pre',
                'pre_degradation', 'post_degradation']:
        assert key in results, f"Missing key: {key}"
        assert isinstance(results[key], float), f"Key '{key}' is not float: {type(results[key])}"


def test_degradation_quantification():
    """VAL-02, D-05: degradation delta equals same-era minus cross-era accuracy."""
    snapshot = _make_mock_snapshot(200)
    # Override dates to span pre/post 2019 boundary
    snapshot['date'] = pd.date_range('2016-01-01', periods=200, freq='14D')
    results = cross_era_validation(snapshot, BOOLEAN_FEATURES)

    # pre_degradation = pre_same_era - pre_on_post
    expected_pre = results['pre_same_era'] - results['pre_on_post']
    assert abs(results['pre_degradation'] - expected_pre) < 1e-6, \
        f"pre_degradation {results['pre_degradation']} != {expected_pre}"

    # post_degradation = post_same_era - post_on_pre
    expected_post = results['post_same_era'] - results['post_on_pre']
    assert abs(results['post_degradation'] - expected_post) < 1e-6, \
        f"post_degradation {results['post_degradation']} != {expected_post}"


def test_dashboard_generates_png(tmp_path):
    """VAL-03: Dashboard generates PNG with two era panels."""
    snap = _make_mock_snapshot(200)
    # Ensure dates span both eras (pre and post 2019)
    dates_pre = pd.date_range('2015-01-01', periods=100, freq='14D')
    dates_post = pd.date_range('2020-01-01', periods=100, freq='14D')
    snap['date'] = list(dates_pre) + list(dates_post)
    output_path = str(tmp_path / 'test_dashboard.png')
    result = generate_dashboard(snap, BOOLEAN_FEATURES, output_path=output_path)
    assert os.path.exists(output_path), f"Dashboard PNG not created at {output_path}"
    assert os.path.getsize(output_path) > 1000, "Dashboard PNG too small (likely empty)"
    assert result == output_path
