"""
Three-Way Model Comparison Dashboard

Compares pure state machine (v2), pure decision tree, and hybrid MDM
model accuracy against 962 published signals, with per-type breakdown
and side-by-side confusion matrices.

Usage:
    uv run python analysis/compare_models.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.tree import DecisionTreeClassifier

from core.data_loader import DataLoader
from core.signal_loader import load_signal_fixture
from core.signal_comparator import extract_model_signals, compare_signals
from core.indicators import build_indicator_dataframe
from core.feature_snapshot import extract_feature_snapshot
from strategies.mdm_hybrid.config import HybridConfig
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLASS_NAMES = ['Buy', 'Cash', 'Sell']
STATE_TO_SIGNAL = {"BUY": "Buy", "SELL": "Sell", "CASH": "Cash"}


# ---------------------------------------------------------------------------
# Model runners
# ---------------------------------------------------------------------------

def resolve_project_root():
    """Resolve project root, handling git worktree paths."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if '.claude' in project_root and 'worktrees' in project_root:
        from pathlib import Path
        parts = Path(project_root).parts
        for i, part in enumerate(parts):
            if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
                project_root = str(Path(*parts[:i]))
                break
    return project_root


def run_v2_model(df, published_signals):
    """Run pure state machine (v2) and return y_true, y_pred arrays.

    Args:
        df: NASDAQ OHLCV DataFrame.
        published_signals: DataFrame with date, signal columns.

    Returns:
        Tuple of (y_true, y_pred, report_dict, accuracy) aligned to published signal dates.
    """
    engine = MDMV2Engine(MDMV2Config())
    results = engine.run(df)

    # Map state to signal
    hyb = results[['date', 'state']].copy()
    hyb['predicted'] = hyb['state'].map(STATE_TO_SIGNAL)

    pub = published_signals[['date', 'signal']].copy()
    merged = pd.merge(pub, hyb[['date', 'predicted']], on='date', how='inner')

    y_true = merged['signal'].values
    y_pred = merged['predicted'].values

    report = classification_report(y_true, y_pred, labels=CLASS_NAMES,
                                   output_dict=True, zero_division=0)
    accuracy = report.get('accuracy', 0.0)

    return y_true, y_pred, report, accuracy


def run_dt_model(df, published_signals):
    """Run pure decision tree model and return y_true, y_pred arrays.

    Trains DecisionTreeClassifier on feature snapshots at signal dates,
    then predicts signal types from indicator features.

    Args:
        df: NASDAQ OHLCV DataFrame.
        published_signals: DataFrame with date, signal columns.

    Returns:
        Tuple of (y_true, y_pred, report_dict, accuracy) aligned to published signal dates.
    """
    # Build indicators and extract feature snapshots
    indicator_df = build_indicator_dataframe(df)
    snapshot = extract_feature_snapshot(indicator_df, published_signals)

    # Feature columns (boolean features used for DT)
    feature_cols = [
        'ema9_above_ema21',
        'ema21_above_ema55',
        'close_above_ma200',
        'close_above_ema9',
        'close_above_ema21',
        'close_above_ema55',
        'macd_histogram_positive',
        'macd_above_signal',
    ]

    # Drop rows with NaN in feature columns (warm-up period)
    valid_mask = snapshot[feature_cols].notna().all(axis=1)
    snapshot_clean = snapshot[valid_mask].copy()

    X = snapshot_clean[feature_cols].values.astype(float)
    y_true = snapshot_clean['signal'].values

    # Train on full dataset and predict (same data — shows DT's best-case)
    clf = DecisionTreeClassifier(
        max_depth=5,
        min_samples_leaf=10,
        random_state=42,
        class_weight='balanced',
    )
    clf.fit(X, y_true)
    y_pred = clf.predict(X)

    report = classification_report(y_true, y_pred, labels=CLASS_NAMES,
                                   output_dict=True, zero_division=0)
    accuracy = report.get('accuracy', 0.0)

    return y_true, y_pred, report, accuracy


def run_hybrid_model(df, published_signals):
    """Run hybrid model and return y_true, y_pred arrays.

    Args:
        df: NASDAQ OHLCV DataFrame.
        published_signals: DataFrame with date, signal columns.

    Returns:
        Tuple of (y_true, y_pred, report_dict, accuracy) aligned to published signal dates.
    """
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)
    results = engine.run(df)

    # Map state to signal
    hyb = results[['date', 'state']].copy()
    hyb['predicted'] = hyb['state'].map(STATE_TO_SIGNAL)

    pub = published_signals[['date', 'signal']].copy()
    merged = pd.merge(pub, hyb[['date', 'predicted']], on='date', how='inner')

    y_true = merged['signal'].values
    y_pred = merged['predicted'].values

    report = classification_report(y_true, y_pred, labels=CLASS_NAMES,
                                   output_dict=True, zero_division=0)
    accuracy = report.get('accuracy', 0.0)

    return y_true, y_pred, report, accuracy


# ---------------------------------------------------------------------------
# Dashboard plotting
# ---------------------------------------------------------------------------

def plot_accuracy_comparison(models, output_path):
    """Create 4-subplot dashboard comparing three models.

    Args:
        models: Dict with keys 'v2', 'dt', 'hybrid', each containing
                (y_true, y_pred, report, accuracy).
        output_path: Path to save the figure.
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Three-Way Model Comparison Dashboard', fontsize=16, fontweight='bold')

    model_names = ['Pure State Machine (v2)', 'Pure Decision Tree', 'Hybrid']
    model_keys = ['v2', 'dt', 'hybrid']
    colors = ['#4472C4', '#ED7D31', '#70AD47']

    # --- Top-left: Per-type accuracy bar chart ---
    ax1 = axes[0, 0]
    x = np.arange(len(CLASS_NAMES))
    width = 0.25

    for i, (key, name, color) in enumerate(zip(model_keys, model_names, colors)):
        report = models[key][2]
        recalls = [report.get(cls, {}).get('recall', 0.0) for cls in CLASS_NAMES]
        ax1.bar(x + i * width, recalls, width, label=name, color=color)

    ax1.set_xlabel('Signal Type')
    ax1.set_ylabel('Recall (Accuracy per Type)')
    ax1.set_title('Per-Type Recall')
    ax1.set_xticks(x + width)
    ax1.set_xticklabels(CLASS_NAMES)
    ax1.set_ylim(0, 1.05)
    ax1.legend(fontsize=8)
    ax1.grid(axis='y', alpha=0.3)

    # --- Top-right: Overall accuracy comparison ---
    ax2 = axes[0, 1]
    accuracies = [models[key][3] for key in model_keys]
    bars = ax2.bar(model_names, accuracies, color=colors)
    ax2.set_ylabel('Overall Accuracy')
    ax2.set_title('Overall Accuracy Comparison')
    ax2.set_ylim(0, 1.05)
    ax2.grid(axis='y', alpha=0.3)

    # Add text labels on bars
    for bar, acc in zip(bars, accuracies):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f'{acc:.1%}', ha='center', va='bottom', fontweight='bold', fontsize=10)

    # Hide unused top-right subplot
    axes[0, 2].axis('off')

    # --- Bottom row: Three confusion matrix heatmaps ---
    for i, (key, name, color) in enumerate(zip(model_keys, model_names, colors)):
        ax = axes[1, i]
        y_true = models[key][0]
        y_pred = models[key][1]
        cm = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)

        im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
        ax.set_title(name, fontsize=11)

        # Annotate cells with counts
        for row in range(len(CLASS_NAMES)):
            for col in range(len(CLASS_NAMES)):
                val = cm[row, col]
                text_color = 'white' if val > cm.max() / 2 else 'black'
                ax.text(col, row, str(val), ha='center', va='center',
                        color=text_color, fontsize=11, fontweight='bold')

        ax.set_xticks(range(len(CLASS_NAMES)))
        ax.set_yticks(range(len(CLASS_NAMES)))
        ax.set_xticklabels(CLASS_NAMES)
        ax.set_yticklabels(CLASS_NAMES)
        ax.set_xlabel('Predicted')
        ax.set_ylabel('Actual')

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def print_accuracy_table(models):
    """Print overall accuracy table to stdout.

    Args:
        models: Dict with model results.
    """
    model_names = ['Pure State Machine (v2)', 'Pure Decision Tree', 'Hybrid']
    model_keys = ['v2', 'dt', 'hybrid']

    print("\n" + "=" * 70)
    print("OVERALL ACCURACY COMPARISON")
    print("=" * 70)
    print(f"{'Model':<30} {'Accuracy':>10} {'Signals':>10}")
    print("-" * 50)
    for key, name in zip(model_keys, model_names):
        acc = models[key][3]
        n = len(models[key][0])
        print(f"{name:<30} {acc:>9.1%} {n:>10}")

    print("\n" + "=" * 70)
    print("PER-TYPE BREAKDOWN (Precision / Recall / F1)")
    print("=" * 70)

    for key, name in zip(model_keys, model_names):
        report = models[key][2]
        print(f"\n--- {name} ---")
        print(f"  {'Type':<8} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
        print(f"  {'-'*48}")
        for cls in CLASS_NAMES:
            if cls in report:
                r = report[cls]
                print(f"  {cls:<8} {r['precision']:>10.3f} {r['recall']:>10.3f} "
                      f"{r['f1-score']:>10.3f} {int(r['support']):>10}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Run three-way model comparison and generate dashboard."""
    project_root = resolve_project_root()

    print("=" * 70)
    print("THREE-WAY MODEL COMPARISON DASHBOARD")
    print("=" * 70)

    # Step 1: Load data
    print("\n[1/5] Loading NASDAQ data and published signals...")
    loader = DataLoader('nasdaq', data_dir=project_root)
    df = loader.load()
    print(f"  NASDAQ data: {len(df)} rows")

    signals_path = os.path.join(project_root, 'data', 'signals', 'nasdaq_signals_full.csv')
    published = load_signal_fixture(signals_path)
    print(f"  Published signals: {len(published)} signals")

    # Step 2: Run pure state machine (v2)
    print("\n[2/5] Running pure state machine (v2)...")
    v2_true, v2_pred, v2_report, v2_acc = run_v2_model(df, published)
    print(f"  V2 accuracy: {v2_acc:.1%} ({len(v2_true)} signals matched)")

    # Step 3: Run pure decision tree
    print("\n[3/5] Running pure decision tree...")
    dt_true, dt_pred, dt_report, dt_acc = run_dt_model(df, published)
    print(f"  DT accuracy: {dt_acc:.1%} ({len(dt_true)} signals)")

    # Step 4: Run hybrid model
    print("\n[4/5] Running hybrid model...")
    hyb_true, hyb_pred, hyb_report, hyb_acc = run_hybrid_model(df, published)
    print(f"  Hybrid accuracy: {hyb_acc:.1%} ({len(hyb_true)} signals matched)")

    # Step 5: Generate dashboard
    print("\n[5/5] Generating dashboard...")
    models = {
        'v2': (v2_true, v2_pred, v2_report, v2_acc),
        'dt': (dt_true, dt_pred, dt_report, dt_acc),
        'hybrid': (hyb_true, hyb_pred, hyb_report, hyb_acc),
    }

    output_path = os.path.join(project_root, 'output', 'model_comparison.png')
    plot_accuracy_comparison(models, output_path)
    print(f"  Dashboard saved to {output_path}")

    # Print text report
    print_accuracy_table(models)

    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
