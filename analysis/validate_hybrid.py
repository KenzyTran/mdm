"""
Hybrid MDM Validation Pipeline

Validates the hybrid MDM engine (state machine + indicator filter) against
all 962 published signals, producing confusion matrices with per-type accuracy,
v2 baseline comparison, held-out set discipline, and diagnostic signal log.

Usage:
    uv run python analysis/validate_hybrid.py
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

from core.data_loader import DataLoader
from core.signal_loader import load_signal_fixture
from core.signal_comparator import extract_model_signals, compare_signals
from strategies.mdm_hybrid.config import HybridConfig
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLASS_NAMES = ['Buy', 'Cash', 'Sell']
STATE_TO_SIGNAL = {"BUY": "Buy", "SELL": "Sell", "CASH": "Cash"}
HELDOUT_COUNT = 20  # Last 20 post-2019 signals held out chronologically
POST_2019_CUTOFF = '2019-01-01'


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def build_confusion_matrices(hybrid_results, published_signals):
    """Build confusion matrices for full, pre-2019, and post-2019 signal subsets.

    Args:
        hybrid_results: DataFrame from HybridEngine.run() with date, state columns.
        published_signals: DataFrame with date, signal columns (962 signals).

    Returns:
        Dict with keys: full_cm, full_report, pre2019_cm, pre2019_report,
        post2019_cm, post2019_report, full_accuracy, pre2019_accuracy,
        post2019_accuracy, n_matched.
    """
    # Merge published signals with hybrid results on date
    pub = published_signals[['date', 'signal']].copy()
    hyb = hybrid_results[['date', 'state']].copy()
    hyb['predicted'] = hyb['state'].map(STATE_TO_SIGNAL)

    merged = pd.merge(pub, hyb[['date', 'predicted']], on='date', how='inner')
    n_matched = len(merged)

    cutoff = pd.Timestamp(POST_2019_CUTOFF)

    results = {'n_matched': n_matched}

    for subset_name, subset_df in [
        ('full', merged),
        ('pre2019', merged[merged['date'] < cutoff]),
        ('post2019', merged[merged['date'] >= cutoff]),
    ]:
        y_true = subset_df['signal'].values
        y_pred = subset_df['predicted'].values

        cm = confusion_matrix(y_true, y_pred, labels=CLASS_NAMES)
        report = classification_report(
            y_true, y_pred, labels=CLASS_NAMES, output_dict=True, zero_division=0
        )

        results[f'{subset_name}_cm'] = cm
        results[f'{subset_name}_report'] = report
        results[f'{subset_name}_accuracy'] = report.get('accuracy', 0.0)

    return results


def build_signal_diagnosis(hybrid_results, published_signals):
    """Build per-signal diagnosis with filter effect analysis.

    Args:
        hybrid_results: DataFrame from HybridEngine.run() with signal log columns.
        published_signals: DataFrame with date, signal columns.

    Returns:
        DataFrame with columns: date, signal, old_state, proposed, verdict,
        final_state, predicted, match, filter_effect.
    """
    pub = published_signals[['date', 'signal']].copy()
    hyb = hybrid_results[['date', 'old_state', 'proposed', 'verdict', 'state']].copy()
    hyb = hyb.rename(columns={'state': 'final_state'})

    merged = pd.merge(pub, hyb, on='date', how='inner')

    # Add predicted column (final state mapped to signal name)
    merged['predicted'] = merged['final_state'].map(STATE_TO_SIGNAL)

    # Add match column
    merged['match'] = merged['signal'] == merged['predicted']

    # Add filter_effect column
    # Map proposed state to signal name for comparison
    merged['proposed_signal'] = merged['proposed'].map(STATE_TO_SIGNAL)

    def classify_filter_effect(row):
        """Classify whether the filter helped, hurt, or was neutral."""
        proposed_sig = row['proposed_signal']
        predicted_sig = row['predicted']
        published_sig = row['signal']

        if proposed_sig == predicted_sig:
            return 'neutral'
        # Filter changed the outcome
        if predicted_sig == published_sig and proposed_sig != published_sig:
            return 'helped'
        if proposed_sig == published_sig and predicted_sig != published_sig:
            return 'hurt'
        return 'neutral'

    merged['filter_effect'] = merged.apply(classify_filter_effect, axis=1)

    # Drop helper column
    merged = merged.drop(columns=['proposed_signal'])

    return merged


def compute_v2_baseline(df, published_signals):
    """Run v2 engine and compute baseline match rates.

    Args:
        df: NASDAQ OHLCV DataFrame.
        published_signals: DataFrame with date, signal columns.

    Returns:
        Dict with full_match_rate, post2019_match_rate, per_type.
    """
    engine = MDMV2Engine(MDMV2Config())
    v2_results = engine.run(df)

    model_signals = extract_model_signals(v2_results)

    # Full match rate
    full_comparison = compare_signals(model_signals, published_signals)

    # Post-2019 match rate
    post2019_pub = published_signals[
        published_signals['date'] >= pd.Timestamp(POST_2019_CUTOFF)
    ].copy()
    post2019_comparison = compare_signals(model_signals, post2019_pub)

    return {
        'full_match_rate': full_comparison['match_rate'],
        'post2019_match_rate': post2019_comparison['match_rate'],
        'per_type': full_comparison['per_type'],
        'post2019_per_type': post2019_comparison['per_type'],
    }


def define_heldout_split(published_signals):
    """Define chronological held-out split for post-2019 signals.

    Args:
        published_signals: DataFrame with date, signal columns.

    Returns:
        Dict with tune_signals, heldout_signals, heldout_dates,
        tune_count, heldout_count.
    """
    post2019 = published_signals[
        published_signals['date'] >= pd.Timestamp(POST_2019_CUTOFF)
    ].sort_values('date').reset_index(drop=True)

    heldout = post2019.tail(HELDOUT_COUNT).copy()
    tune = post2019.iloc[:-HELDOUT_COUNT].copy()

    return {
        'tune_signals': tune,
        'heldout_signals': heldout,
        'heldout_dates': heldout['date'].tolist(),
        'tune_count': len(tune),
        'heldout_count': len(heldout),
    }


def format_confusion_matrix(cm, class_names):
    """Format confusion matrix as markdown table.

    Args:
        cm: numpy array confusion matrix.
        class_names: list of class label strings.

    Returns:
        Formatted markdown table string.
    """
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


def generate_report(cm_results, v2_baseline, diagnosis, heldout_split, hybrid_summary):
    """Generate full markdown validation report.

    Args:
        cm_results: Dict from build_confusion_matrices().
        v2_baseline: Dict from compute_v2_baseline().
        diagnosis: DataFrame from build_signal_diagnosis().
        heldout_split: Dict from define_heldout_split().
        hybrid_summary: Dict from HybridEngine.summary().

    Returns:
        Markdown report string.
    """
    lines = []
    lines.append("# Hybrid MDM Validation Report")
    lines.append("")
    lines.append(f"Generated: {date.today().isoformat()}")
    lines.append("")

    # --- Overall Accuracy ---
    lines.append("## Overall Accuracy")
    lines.append("")
    lines.append(f"- **Full (all signals):** {cm_results['full_accuracy']:.1%} "
                 f"({cm_results['n_matched']} signals matched)")
    lines.append(f"- **Pre-2019:** {cm_results['pre2019_accuracy']:.1%}")
    lines.append(f"- **Post-2019:** {cm_results['post2019_accuracy']:.1%}")
    lines.append("")

    # --- V2 Baseline Comparison ---
    lines.append("## V2 Baseline Comparison")
    lines.append("")
    hybrid_post = cm_results['post2019_accuracy'] * 100
    v2_post = v2_baseline['post2019_match_rate']
    delta = hybrid_post - v2_post
    lines.append(f"| Metric | Hybrid | V2 Baseline | Delta |")
    lines.append(f"| --- | --- | --- | --- |")
    lines.append(f"| Post-2019 Accuracy | {hybrid_post:.1f}% | {v2_post:.1f}% | {delta:+.1f}% |")
    lines.append(f"| Full Match Rate | {cm_results['full_accuracy']*100:.1f}% | {v2_baseline['full_match_rate']:.1f}% | {cm_results['full_accuracy']*100 - v2_baseline['full_match_rate']:+.1f}% |")
    lines.append("")

    # --- Confusion Matrices ---
    lines.append("## Confusion Matrices")
    lines.append("")
    lines.append("### Full (All Signals)")
    lines.append("")
    lines.append(format_confusion_matrix(cm_results['full_cm'], CLASS_NAMES))
    lines.append("")
    lines.append("### Post-2019")
    lines.append("")
    lines.append(format_confusion_matrix(cm_results['post2019_cm'], CLASS_NAMES))
    lines.append("")

    # --- Per-Type Accuracy ---
    lines.append("## Per-Type Accuracy")
    lines.append("")
    lines.append("### Full")
    lines.append("")
    lines.append(_format_classification_report(cm_results['full_report'], CLASS_NAMES))
    lines.append("")
    lines.append("### Post-2019")
    lines.append("")
    lines.append(_format_classification_report(cm_results['post2019_report'], CLASS_NAMES))
    lines.append("")

    # --- Held-Out Results ---
    lines.append("## Held-Out Results")
    lines.append("")
    lines.append(f"- **Held-out count:** {heldout_split['heldout_count']} "
                 f"(last {HELDOUT_COUNT} post-2019 signals)")
    lines.append(f"- **Tune set count:** {heldout_split['tune_count']}")

    # Compute tune and held-out accuracy from diagnosis
    tune_dates = set(pd.Timestamp(d) for d in heldout_split['tune_signals']['date'])
    heldout_dates = set(pd.Timestamp(d) for d in heldout_split['heldout_signals']['date'])

    tune_diag = diagnosis[diagnosis['date'].isin(tune_dates)]
    heldout_diag = diagnosis[diagnosis['date'].isin(heldout_dates)]

    if len(tune_diag) > 0:
        tune_acc = tune_diag['match'].mean()
        lines.append(f"- **Tune set accuracy:** {tune_acc:.1%} ({len(tune_diag)} signals)")
    if len(heldout_diag) > 0:
        heldout_acc = heldout_diag['match'].mean()
        lines.append(f"- **Held-out accuracy:** {heldout_acc:.1%} ({len(heldout_diag)} signals)")
    lines.append("")

    # --- Filter Effect Summary ---
    lines.append("## Filter Effect Summary")
    lines.append("")
    effect_counts = diagnosis['filter_effect'].value_counts()
    for effect in ['helped', 'hurt', 'neutral']:
        count = effect_counts.get(effect, 0)
        lines.append(f"- **{effect.capitalize()}:** {count}")
    lines.append("")

    # --- Signal Diagnosis Sample ---
    lines.append("## Signal Diagnosis Sample (Filter Non-Neutral)")
    lines.append("")
    non_neutral = diagnosis[diagnosis['filter_effect'] != 'neutral'].head(20)
    if len(non_neutral) > 0:
        lines.append("| Date | Published | Proposed | Verdict | Predicted | Effect |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for _, row in non_neutral.iterrows():
            d = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
            lines.append(
                f"| {d} | {row['signal']} | {row['proposed']} | "
                f"{row['verdict']} | {row['predicted']} | {row['filter_effect']} |"
            )
    else:
        lines.append("No filter-affected signals found.")
    lines.append("")

    # --- Hybrid Engine Summary ---
    lines.append("## Hybrid Engine Summary")
    lines.append("")
    for key, val in hybrid_summary.items():
        if isinstance(val, float):
            lines.append(f"- **{key}:** {val:.4f}")
        else:
            lines.append(f"- **{key}:** {val}")
    lines.append("")

    return "\n".join(lines)


def validate_hybrid_match_rates(hybrid_results, published_signals):
    """Compute hybrid match rates for convenience (used by tests).

    Args:
        hybrid_results: DataFrame from HybridEngine.run().
        published_signals: DataFrame with published signals.

    Returns:
        Dict with full and post-2019 match rates.
    """
    model_signals = extract_model_signals(hybrid_results)
    full = compare_signals(model_signals, published_signals)

    post2019_pub = published_signals[
        published_signals['date'] >= pd.Timestamp(POST_2019_CUTOFF)
    ].copy()
    post2019 = compare_signals(model_signals, post2019_pub)

    return {
        'full_match_rate': full['match_rate'],
        'post2019_match_rate': post2019['match_rate'],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Run the full hybrid validation pipeline."""
    # Resolve project root (handles git worktree paths)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # If running from a git worktree, data lives in the main repo
    if '.claude' in project_root and 'worktrees' in project_root:
        from pathlib import Path
        parts = Path(project_root).parts
        for i, part in enumerate(parts):
            if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
                project_root = str(Path(*parts[:i]))
                break

    print("=" * 60)
    print("HYBRID MDM VALIDATION PIPELINE")
    print("=" * 60)

    # Step 1: Load data
    print("\n[1/7] Loading NASDAQ data and published signals...")
    loader = DataLoader('nasdaq', data_dir=project_root)
    df = loader.load()
    print(f"  NASDAQ data: {len(df)} rows ({df['date'].min().date()} to {df['date'].max().date()})")

    signals_path = os.path.join(project_root, 'data', 'signals', 'nasdaq_signals_full.csv')
    published_signals = load_signal_fixture(signals_path)
    print(f"  Published signals: {len(published_signals)} signals")

    # Step 2: Run hybrid engine with filter enabled
    print("\n[2/7] Running hybrid engine (filter_enabled=True)...")
    hybrid_config = HybridConfig(filter_enabled=True)
    hybrid_engine = HybridEngine(hybrid_config)
    hybrid_results = hybrid_engine.run(df)
    hybrid_summary = hybrid_engine.summary()
    print(f"  Hybrid trades: {hybrid_summary['total_completed']}")

    # Step 3: Run v2 baseline
    print("\n[3/7] Computing V2 baseline...")
    v2_baseline = compute_v2_baseline(df, published_signals)
    print(f"  V2 full match rate: {v2_baseline['full_match_rate']:.1f}%")
    print(f"  V2 post-2019 match rate: {v2_baseline['post2019_match_rate']:.1f}%")

    # Step 4: Define held-out split
    print("\n[4/7] Defining held-out split...")
    heldout_split = define_heldout_split(published_signals)
    print(f"  Tune set: {heldout_split['tune_count']} signals")
    print(f"  Held-out: {heldout_split['heldout_count']} signals")

    # Step 5: Build confusion matrices
    print("\n[5/7] Building confusion matrices...")
    cm_results = build_confusion_matrices(hybrid_results, published_signals)
    print(f"  Full accuracy: {cm_results['full_accuracy']:.1%}")
    print(f"  Pre-2019 accuracy: {cm_results['pre2019_accuracy']:.1%}")
    print(f"  Post-2019 accuracy: {cm_results['post2019_accuracy']:.1%}")

    # Step 6: Build signal diagnosis
    print("\n[6/7] Building signal diagnosis...")
    diagnosis = build_signal_diagnosis(hybrid_results, published_signals)
    effect_counts = diagnosis['filter_effect'].value_counts()
    print(f"  Total diagnosed: {len(diagnosis)}")
    print(f"  Filter helped: {effect_counts.get('helped', 0)}")
    print(f"  Filter hurt: {effect_counts.get('hurt', 0)}")
    print(f"  Filter neutral: {effect_counts.get('neutral', 0)}")

    # Step 7: Generate report and save outputs
    print("\n[7/7] Generating report and saving outputs...")
    report = generate_report(cm_results, v2_baseline, diagnosis, heldout_split, hybrid_summary)

    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Save markdown report
    report_path = os.path.join(output_dir, 'hybrid_validation_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  Report saved: {report_path}")

    # Save signal diagnosis CSV
    diag_path = os.path.join(output_dir, 'hybrid_signal_diagnosis.csv')
    diagnosis.to_csv(diag_path, index=False)
    print(f"  Diagnosis saved: {diag_path}")

    # Save confusion matrices text file
    cm_path = os.path.join(output_dir, 'hybrid_confusion_matrix.txt')
    with open(cm_path, 'w', encoding='utf-8') as f:
        f.write("Full Confusion Matrix (Actual rows, Predicted columns)\n")
        f.write(f"Labels: {CLASS_NAMES}\n")
        f.write(str(cm_results['full_cm']))
        f.write("\n\nPost-2019 Confusion Matrix (Actual rows, Predicted columns)\n")
        f.write(f"Labels: {CLASS_NAMES}\n")
        f.write(str(cm_results['post2019_cm']))
    print(f"  Confusion matrices saved: {cm_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    hybrid_post = cm_results['post2019_accuracy'] * 100
    v2_post = v2_baseline['post2019_match_rate']
    delta = hybrid_post - v2_post
    print(f"\nPost-2019: Hybrid {hybrid_post:.1f}% vs V2 {v2_post:.1f}% (delta: {delta:+.1f}%)")
    print(f"Full accuracy: {cm_results['full_accuracy']:.1%} on {cm_results['n_matched']} signals")


if __name__ == '__main__':
    main()
