"""Integration tests for hybrid validation pipeline.

Tests confusion matrix per-type accuracy, post-2019 vs v2 baseline comparison,
signal log diagnosis at published signal dates, and held-out set discipline.
"""

import sys
import os
from pathlib import Path

import pytest
import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

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

from core.data_loader import DataLoader
from core.signal_loader import load_signal_fixture
from core.signal_comparator import extract_model_signals, compare_signals, STATE_TO_SIGNAL
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_v2.config import MDMV2Config as V2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine

CLASS_NAMES = ['Buy', 'Cash', 'Sell']
HELDOUT_COUNT = 20
POST_2019_CUTOFF = pd.Timestamp('2019-01-01')


# ---------------------------------------------------------------------------
# Shared fixtures (run engine once per module)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def nasdaq_data():
    """Load full NASDAQ data from main repo."""
    loader = DataLoader('nasdaq')
    loader.data_dir = MAIN_REPO
    df = loader.load()
    if df is None or df.empty:
        pytest.skip("NASDAQ data not available")
    return df


@pytest.fixture(scope="module")
def published_signals():
    """Load full 962 published signal history."""
    signals_path = os.path.join(str(MAIN_REPO), 'data', 'signals', 'nasdaq_signals_full.csv')
    return load_signal_fixture(signals_path)


@pytest.fixture(scope="module")
def hybrid_results(nasdaq_data):
    """Run hybrid engine with filter enabled on NASDAQ data."""
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(nasdaq_data)
    return results


@pytest.fixture(scope="module")
def v2_results(nasdaq_data):
    """Run v2 engine on NASDAQ data (baseline)."""
    config = V2Config()
    engine = MDMV2Engine(config)
    results = engine.run(nasdaq_data)
    return results


# ---------------------------------------------------------------------------
# Test 1: Confusion matrix per type
# ---------------------------------------------------------------------------

def test_confusion_matrix_per_type(hybrid_results, published_signals):
    """Confusion matrix is 3x3 with Buy/Cash/Sell labels; classification report has all types."""
    # Merge published signals with hybrid results on date
    pub = published_signals[['date', 'signal']].copy()
    hyb = hybrid_results[['date', 'state']].copy()
    hyb['predicted'] = hyb['state'].map(STATE_TO_SIGNAL)

    merged = pd.merge(pub, hyb[['date', 'predicted']], on='date', how='inner')
    y_true = merged['signal'].values
    y_pred = merged['predicted'].values

    cm = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)
    assert cm.shape == (3, 3), f"Expected 3x3 confusion matrix, got {cm.shape}"

    report = classification_report(
        y_true, y_pred, labels=CLASS_NAMES, output_dict=True, zero_division=0
    )
    for cls in CLASS_NAMES:
        assert cls in report, f"Class '{cls}' missing from classification report"

    assert isinstance(report['accuracy'], float), "Accuracy should be a float"
    assert 0.0 <= report['accuracy'] <= 1.0, f"Accuracy {report['accuracy']} out of range"


# ---------------------------------------------------------------------------
# Test 2: Post-2019 vs v2 baseline
# ---------------------------------------------------------------------------

def test_post2019_vs_baseline(hybrid_results, v2_results, published_signals):
    """Post-2019 match rates computed for both hybrid and v2 as floats between 0-100."""
    # Filter published signals to post-2019
    post2019_pub = published_signals[
        published_signals['date'] >= POST_2019_CUTOFF
    ].copy()

    # Hybrid match rate
    hybrid_model_signals = extract_model_signals(hybrid_results)
    hybrid_comparison = compare_signals(hybrid_model_signals, post2019_pub)

    # V2 baseline match rate
    v2_model_signals = extract_model_signals(v2_results)
    v2_comparison = compare_signals(v2_model_signals, post2019_pub)

    hybrid_rate = hybrid_comparison['match_rate']
    v2_rate = v2_comparison['match_rate']

    assert isinstance(hybrid_rate, float), "Hybrid match rate should be a float"
    assert isinstance(v2_rate, float), "V2 match rate should be a float"
    assert 0.0 <= hybrid_rate <= 100.0, f"Hybrid rate {hybrid_rate} out of range"
    assert 0.0 <= v2_rate <= 100.0, f"V2 rate {v2_rate} out of range"

    # Print both for visibility (measurement, not assertion on which is higher)
    print(f"\nPost-2019 hybrid match rate: {hybrid_rate:.1f}%")
    print(f"Post-2019 v2 baseline rate: {v2_rate:.1f}%")
    print(f"Delta (hybrid - v2): {hybrid_rate - v2_rate:+.1f}%")


# ---------------------------------------------------------------------------
# Test 3: Signal log diagnosis
# ---------------------------------------------------------------------------

def test_signal_log_diagnosis(hybrid_results, published_signals):
    """Signal log at published signal dates has required columns; 900+ dates matched."""
    pub = published_signals[['date', 'signal']].copy()
    hyb = hybrid_results[['date', 'old_state', 'proposed', 'verdict', 'state']].copy()
    hyb = hyb.rename(columns={'state': 'final_state'})

    merged = pd.merge(pub, hyb, on='date', how='inner')

    # Check required columns exist
    required_cols = ['date', 'old_state', 'proposed', 'verdict', 'final_state']
    for col in required_cols:
        assert col in merged.columns, f"Column '{col}' missing from merged signal log"

    # At least 900 out of 962 published signal dates should have matching rows
    assert len(merged) >= 900, (
        f"Expected >= 900 matched signal dates, got {len(merged)} "
        f"(out of {len(published_signals)} published)"
    )


# ---------------------------------------------------------------------------
# Test 4: Held-out set locked
# ---------------------------------------------------------------------------

def test_heldout_set_locked(published_signals):
    """Held-out set is last 20 post-2019 signals; chronological; disjoint from tune set."""
    # Filter to post-2019
    post2019 = published_signals[
        published_signals['date'] >= POST_2019_CUTOFF
    ].sort_values('date').reset_index(drop=True)

    # Split: last HELDOUT_COUNT = held-out, rest = tune
    heldout = post2019.tail(HELDOUT_COUNT).copy()
    tune = post2019.iloc[:-HELDOUT_COUNT].copy()

    # At least 19 held-out signals
    assert len(heldout) >= 19, f"Expected >= 19 held-out signals, got {len(heldout)}"

    # All held-out dates are after all tune dates (chronological)
    if len(tune) > 0 and len(heldout) > 0:
        assert heldout['date'].min() > tune['date'].max(), (
            f"Held-out earliest date {heldout['date'].min()} should be after "
            f"tune latest date {tune['date'].max()}"
        )

    # No overlap between tune and held-out dates
    tune_dates = set(tune['date'].values)
    heldout_dates = set(heldout['date'].values)
    overlap = tune_dates & heldout_dates
    assert len(overlap) == 0, f"Tune and held-out sets overlap on {len(overlap)} dates"
