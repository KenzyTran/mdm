"""
Discovery Validation: Match Rate Scoring and Cross-Era Validation

Scores decision tree rules discovered in Phase 9 against all 962 published
signals with per-type breakdown, confusion matrices, high-confidence filtering,
and era-based cross-validation quantifying structural change degradation.

Usage:
    uv run python analysis/validate_discovery.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

from analysis.rule_discovery import (
    train_era_tree, split_by_era, BOOLEAN_FEATURES, CLASS_NAMES, ERA_SPLIT_DATE
)


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_predictions(snapshot, clf, feature_cols):
    """Score a trained classifier against a snapshot of signal-date predictions.

    Produces per-signal predictions, confusion matrix, classification report,
    and overall accuracy.

    Args:
        snapshot: Feature snapshot DataFrame with 'signal' and feature columns.
        clf: Trained sklearn classifier with predict() and predict_proba().
        feature_cols: List of feature column names used for prediction.

    Returns:
        Dict with keys: y_true, y_pred, y_proba, confusion_matrix,
        classification_report, accuracy.
    """
    X = snapshot[feature_cols].values
    y_true = snapshot['signal'].values

    y_pred = clf.predict(X)
    y_proba = clf.predict_proba(X)

    cm = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)
    report = classification_report(
        y_true, y_pred, labels=CLASS_NAMES, output_dict=True, zero_division=0
    )
    accuracy = float((y_true == y_pred).mean())

    return {
        'y_true': y_true,
        'y_pred': y_pred,
        'y_proba': y_proba,
        'confusion_matrix': cm,
        'classification_report': report,
        'accuracy': accuracy,
    }


def filter_high_confidence(results, threshold=0.70):
    """Filter predictions to high-confidence subset based on predict_proba.

    Args:
        results: Dict returned by score_predictions.
        threshold: Minimum max class probability to include (default 0.70).

    Returns:
        Dict with same shape as score_predictions output, plus 'n_total'
        and 'n_high_conf' keys. If no predictions meet threshold, returns
        dict with empty arrays and a 'note' key.
    """
    max_proba = results['y_proba'].max(axis=1)
    mask = max_proba >= threshold

    n_total = len(results['y_true'])
    n_high_conf = int(mask.sum())

    if n_high_conf == 0:
        return {
            'y_true': np.array([]),
            'y_pred': np.array([]),
            'y_proba': np.empty((0, results['y_proba'].shape[1])),
            'confusion_matrix': np.zeros((3, 3), dtype=int),
            'classification_report': {},
            'accuracy': 0.0,
            'n_total': n_total,
            'n_high_conf': 0,
            'note': f'No predictions met threshold {threshold:.0%}',
        }

    y_true_f = results['y_true'][mask]
    y_pred_f = results['y_pred'][mask]
    y_proba_f = results['y_proba'][mask]

    cm = confusion_matrix(y_true_f, y_pred_f, labels=CLASS_NAMES)
    report = classification_report(
        y_true_f, y_pred_f, labels=CLASS_NAMES, output_dict=True, zero_division=0
    )
    accuracy = float((y_true_f == y_pred_f).mean())

    return {
        'y_true': y_true_f,
        'y_pred': y_pred_f,
        'y_proba': y_proba_f,
        'confusion_matrix': cm,
        'classification_report': report,
        'accuracy': accuracy,
        'n_total': n_total,
        'n_high_conf': n_high_conf,
    }


def cross_era_validation(snapshot, feature_cols, max_depth=4):
    """Cross-era validation: train on one era, test on the other.

    Quantifies structural change degradation by comparing same-era accuracy
    with cross-era accuracy.

    Args:
        snapshot: Full feature snapshot DataFrame spanning both eras.
        feature_cols: List of feature column names.
        max_depth: Maximum decision tree depth.

    Returns:
        Dict with keys: pre_same_era, post_same_era, pre_on_post, post_on_pre,
        pre_degradation, post_degradation, pre_clf, post_clf.
    """
    pre, post = split_by_era(snapshot)

    # Train era-specific trees (retrain per D-09, no saved models)
    pre_clf, pre_cv, pre_feat = train_era_tree(pre, feature_cols, max_depth=max_depth)
    post_clf, post_cv, post_feat = train_era_tree(post, feature_cols, max_depth=max_depth)

    # Extract features and labels for each era
    X_pre = pre[feature_cols].values
    y_pre = pre['signal'].values
    X_post = post[feature_cols].values
    y_post = post['signal'].values

    # Same-era accuracy
    pre_same = float((pre_clf.predict(X_pre) == y_pre).mean())
    post_same = float((post_clf.predict(X_post) == y_post).mean())

    # Cross-era accuracy
    pre_on_post = float((pre_clf.predict(X_post) == y_post).mean())
    post_on_pre = float((post_clf.predict(X_pre) == y_pre).mean())

    # Degradation deltas (D-05)
    pre_degradation = pre_same - pre_on_post
    post_degradation = post_same - post_on_pre

    return {
        'pre_same_era': pre_same,
        'post_same_era': post_same,
        'pre_on_post': pre_on_post,
        'post_on_pre': post_on_pre,
        'pre_degradation': pre_degradation,
        'post_degradation': post_degradation,
        'pre_clf': pre_clf,
        'post_clf': post_clf,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _format_confusion_matrix(cm, class_names):
    """Format confusion matrix as markdown table."""
    lines = []
    header = "| Actual \\ Predicted | " + " | ".join(class_names) + " |"
    sep = "| --- | " + " | ".join(["---"] * len(class_names)) + " |"
    lines.append(header)
    lines.append(sep)
    for i, cls in enumerate(class_names):
        vals = " | ".join(str(cm[i, j]) for j in range(len(class_names)))
        lines.append(f"| {cls} | {vals} |")
    return "\n".join(lines)


def _format_classification_report(report, class_names):
    """Format classification report as markdown table."""
    lines = []
    lines.append("| Class | Precision | Recall | F1-Score | Support |")
    lines.append("| --- | --- | --- | --- | --- |")
    for cls in class_names:
        if cls in report:
            r = report[cls]
            lines.append(
                f"| {cls} | {r['precision']:.3f} | {r['recall']:.3f} | "
                f"{r['f1-score']:.3f} | {int(r['support'])} |"
            )
    return "\n".join(lines)


def generate_validation_report(snapshot, feature_cols, confidence_threshold=0.70):
    """Generate a full validation report with match rates and cross-era analysis.

    Trains era-specific trees, scores predictions on full data, filters
    high-confidence subset, and runs cross-era validation.

    Args:
        snapshot: Full feature snapshot DataFrame with 'date', 'signal', and features.
        feature_cols: List of feature column names.
        confidence_threshold: Threshold for high-confidence filtering (default 0.70).

    Returns:
        Tuple of (report_text, results_dict) where report_text is a markdown
        string and results_dict has all computed data.
    """
    pre, post = split_by_era(snapshot)

    # Train era-specific trees (D-09: retrain in script)
    pre_clf, pre_cv, pre_feat = train_era_tree(pre, feature_cols)
    post_clf, post_cv, post_feat = train_era_tree(post, feature_cols)

    # Score each tree on its own era data
    pre_on_pre = score_predictions(pre, pre_clf, feature_cols)
    post_on_post = score_predictions(post, post_clf, feature_cols)

    # Score each tree on full data
    pre_on_full = score_predictions(snapshot, pre_clf, feature_cols)
    post_on_full = score_predictions(snapshot, post_clf, feature_cols)

    # High-confidence filtering on full-data results
    pre_hc = filter_high_confidence(pre_on_full, threshold=confidence_threshold)
    post_hc = filter_high_confidence(post_on_full, threshold=confidence_threshold)

    # Cross-era validation
    cross_era = cross_era_validation(snapshot, feature_cols)

    # Build markdown report
    lines = []
    lines.append("# Discovery Validation Report")
    lines.append("")

    # --- Overall Match Rate ---
    lines.append("## Overall Match Rate")
    lines.append("")
    lines.append(f"**Pre-2019 tree on pre-2019 data:** {pre_on_pre['accuracy']:.1%} "
                 f"({len(pre)} signals)")
    lines.append(f"**Post-2019 tree on post-2019 data:** {post_on_post['accuracy']:.1%} "
                 f"({len(post)} signals)")
    lines.append(f"**Pre-2019 tree on all data:** {pre_on_full['accuracy']:.1%}")
    lines.append(f"**Post-2019 tree on all data:** {post_on_full['accuracy']:.1%}")
    lines.append("")

    # Per-type metrics for pre-era tree on pre data
    lines.append("### Pre-2019 Tree Per-Type Metrics")
    lines.append("")
    lines.append(_format_classification_report(pre_on_pre['classification_report'], CLASS_NAMES))
    lines.append("")

    # Per-type metrics for post-era tree on post data
    lines.append("### Post-2019 Tree Per-Type Metrics")
    lines.append("")
    lines.append(_format_classification_report(post_on_post['classification_report'], CLASS_NAMES))
    lines.append("")

    # --- Confusion Matrix ---
    lines.append("## Confusion Matrix")
    lines.append("")
    lines.append("### Pre-2019 Tree on Pre-2019 Data")
    lines.append("")
    lines.append(_format_confusion_matrix(pre_on_pre['confusion_matrix'], CLASS_NAMES))
    lines.append("")
    lines.append("### Post-2019 Tree on Post-2019 Data")
    lines.append("")
    lines.append(_format_confusion_matrix(post_on_post['confusion_matrix'], CLASS_NAMES))
    lines.append("")

    # --- High-Confidence Subset ---
    pct = int(confidence_threshold * 100)
    lines.append(f"## High-Confidence Subset (>= {pct}%)")
    lines.append("")
    lines.append(f"**Pre-2019 tree on all data:** {pre_hc.get('n_high_conf', 0)} / "
                 f"{pre_hc.get('n_total', 0)} predictions meet threshold")
    if pre_hc.get('n_high_conf', 0) > 0:
        lines.append(f"  Accuracy: {pre_hc['accuracy']:.1%}")
    lines.append(f"**Post-2019 tree on all data:** {post_hc.get('n_high_conf', 0)} / "
                 f"{post_hc.get('n_total', 0)} predictions meet threshold")
    if post_hc.get('n_high_conf', 0) > 0:
        lines.append(f"  Accuracy: {post_hc['accuracy']:.1%}")
    lines.append("")

    # --- Era-Based Cross-Validation ---
    lines.append("## Era-Based Cross-Validation")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Pre-2019 same-era accuracy | {cross_era['pre_same_era']:.1%} |")
    lines.append(f"| Post-2019 same-era accuracy | {cross_era['post_same_era']:.1%} |")
    lines.append(f"| Pre-2019 tree on post-2019 data | {cross_era['pre_on_post']:.1%} |")
    lines.append(f"| Post-2019 tree on pre-2019 data | {cross_era['post_on_pre']:.1%} |")
    lines.append(f"| Pre-2019 degradation delta | {cross_era['pre_degradation']:+.1%} |")
    lines.append(f"| Post-2019 degradation delta | {cross_era['post_degradation']:+.1%} |")
    lines.append("")

    # --- Structural Change Quantification ---
    lines.append("## Structural Change Quantification")
    lines.append("")
    if cross_era['pre_degradation'] > 0.10 or cross_era['post_degradation'] > 0.10:
        lines.append("**Significant structural change detected.** The degradation deltas "
                     "exceed 10 percentage points, confirming that the rules governing MDM "
                     "signals changed materially around February 2019. Era-specific models "
                     "are substantially better than cross-era models, indicating the "
                     "post-2019 MDM uses different indicator conditions for signal generation.")
    else:
        lines.append("Degradation deltas are modest (< 10pp), suggesting the underlying "
                     "signal logic has not changed dramatically between eras. A unified "
                     "model may be viable.")
    lines.append("")

    report_text = "\n".join(lines)

    results_dict = {
        'pre_on_pre': pre_on_pre,
        'post_on_post': post_on_post,
        'pre_on_full': pre_on_full,
        'post_on_full': post_on_full,
        'pre_high_confidence': pre_hc,
        'post_high_confidence': post_hc,
        'cross_era': cross_era,
        'pre_clf': pre_clf,
        'post_clf': post_clf,
    }

    return (report_text, results_dict)


# ---------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from core.data_loader import DataLoader
    from core.indicators import build_indicator_dataframe
    from core.signal_loader import load_signal_fixture
    from core.feature_snapshot import extract_feature_snapshot

    print("=" * 70)
    print("Discovery Validation: Match Rate Scoring & Cross-Era Analysis")
    print("=" * 70)
    print()

    # Step 1: Load NASDAQ OHLCV data
    print("Loading NASDAQ OHLCV data...")
    ohlcv = DataLoader('nasdaq').load()
    print(f"  Loaded {len(ohlcv)} trading days ({ohlcv['date'].min().date()} to {ohlcv['date'].max().date()})")

    # Step 2: Build indicators
    print("Building indicator dataframe...")
    indicators = build_indicator_dataframe(ohlcv)
    print(f"  Indicators computed: {len(indicators)} rows")

    # Step 3: Load signals
    signal_csv = 'data/signals/nasdaq_signals_full.csv'
    print(f"Loading signals from {signal_csv}...")
    signals = load_signal_fixture(signal_csv)
    print(f"  Loaded {len(signals)} published signals")

    # Step 4: Extract feature snapshot
    print("Extracting feature snapshot...")
    snapshot = extract_feature_snapshot(indicators, signals)
    print(f"  Snapshot: {len(snapshot)} signal-date rows")

    # Drop rows with NaN in any boolean feature column (warm-up period)
    before = len(snapshot)
    snapshot = snapshot.dropna(subset=BOOLEAN_FEATURES).copy()
    after = len(snapshot)
    if before != after:
        print(f"  Dropped {before - after} rows with NaN in boolean features ({after} remaining)")

    # Step 5: Generate validation report
    print("Generating validation report...")
    report_text, results_dict = generate_validation_report(snapshot, BOOLEAN_FEATURES)

    # Print report to stdout
    print()
    print(report_text)

    # Save outputs
    os.makedirs('output', exist_ok=True)

    # Save report
    report_path = 'output/discovery_validation_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"Report saved to {report_path}")

    # Save per-signal predictions CSV
    cross_era = results_dict['cross_era']
    pre_results = results_dict['pre_on_pre']
    post_results = results_dict['post_on_post']

    # Build per-signal CSV from era-specific predictions
    pre_snap, post_snap = split_by_era(snapshot)
    records = []
    for snap_df, res in [(pre_snap, pre_results), (post_snap, post_results)]:
        for i in range(len(res['y_true'])):
            max_conf = float(res['y_proba'][i].max())
            records.append({
                'date': snap_df.iloc[i]['date'],
                'actual': res['y_true'][i],
                'predicted': res['y_pred'][i],
                'confidence': max_conf,
                'correct': res['y_true'][i] == res['y_pred'][i],
            })
    match_df = pd.DataFrame(records)
    match_path = 'output/discovery_match_rates.csv'
    match_df.to_csv(match_path, index=False)
    print(f"Per-signal predictions saved to {match_path}")

    # Save confusion matrix
    cm_path = 'output/discovery_confusion_matrix.txt'
    with open(cm_path, 'w', encoding='utf-8') as f:
        f.write("Pre-2019 Confusion Matrix (Actual rows, Predicted columns)\n")
        f.write(f"Labels: {CLASS_NAMES}\n")
        f.write(str(pre_results['confusion_matrix']))
        f.write("\n\nPost-2019 Confusion Matrix (Actual rows, Predicted columns)\n")
        f.write(f"Labels: {CLASS_NAMES}\n")
        f.write(str(post_results['confusion_matrix']))
    print(f"Confusion matrices saved to {cm_path}")

    print("\nSaved to output/")
