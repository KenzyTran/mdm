"""
Signal Divergence Analysis Script

Runs the full MDM classic pipeline, compares model signals against published
Dr. K signals, classifies divergences, and produces three output artifacts:
  - output/divergence_report.csv (per-divergence rows)
  - output/divergence_summary.txt (human-readable summary)
  - output/signal_overlay.png (three-panel chart)

Usage:
    python analysis/signal_divergence.py
"""

import sys
import os
import subprocess

# Anchor paths to project root regardless of working directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

# In a git worktree, data CSVs (gitignored) live in the main repo only.
DATA_ROOT = PROJECT_ROOT
if not os.path.exists(os.path.join(DATA_ROOT, 'data', 'NASDAQ.csv')):
    try:
        _git_common = subprocess.check_output(
            ['git', 'rev-parse', '--git-common-dir'],
            cwd=PROJECT_ROOT, text=True
        ).strip()
        DATA_ROOT = os.path.dirname(os.path.abspath(os.path.join(PROJECT_ROOT, _git_common)))
    except Exception:
        pass

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for script
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec

from core.data_loader import DataLoader
from core.signal_loader import load_signal_fixture
from core.signal_comparator import (
    extract_model_signals, align_signals, compare_signals,
    classify_divergences, generate_divergence_context, STATE_TO_SIGNAL
)
from strategies.mdm_classic import MDMEngine
from strategies.mdm_classic.config import MDMConfig


SIGNAL_COLORS = {
    'Buy': '#2ca02c',
    'Sell': '#d62728',
    'Cash': '#7f7f7f',
}


def expand_to_daily(signals_df, date_range):
    """Expand sparse signal transitions to daily states via forward-fill.

    Args:
        signals_df: DataFrame with [date, signal] columns (transition rows only).
        date_range: DatetimeIndex of all dates to fill.

    Returns:
        DataFrame with [date, signal] for every date in date_range, forward-filled.
    """
    daily = pd.DataFrame({'date': date_range})
    daily = daily.merge(signals_df[['date', 'signal']], on='date', how='left')
    daily['signal'] = daily['signal'].ffill()
    return daily


def find_divergence_periods(pub_signals, mod_signals):
    """Return list of (start_date, end_date) tuples where signals disagree.

    Args:
        pub_signals: Series of published signal states aligned to daily dates.
        mod_signals: Series of model signal states aligned to daily dates.

    Returns:
        List of (start_date, end_date) tuples for contiguous divergence periods.
    """
    divergent = pub_signals != mod_signals
    # Group contiguous True values
    groups = divergent.ne(divergent.shift()).cumsum()
    periods = []
    for _, group in divergent.groupby(groups):
        if group.iloc[0]:  # divergent period
            periods.append((group.index[0], group.index[-1]))
    return periods


def render_signal_track(ax, daily_df, label):
    """Render a color-coded signal track using axvspan bands.

    Args:
        ax: Matplotlib axes object.
        daily_df: DataFrame with [date, signal] at daily frequency.
        label: Y-axis label for the panel.
    """
    dates = daily_df['date'].values
    signals = daily_df['signal'].values

    # Find contiguous signal periods and render as colored bands
    if len(signals) == 0:
        return

    current_signal = signals[0]
    start_idx = 0

    for i in range(1, len(signals)):
        if signals[i] != current_signal or i == len(signals) - 1:
            end_idx = i if signals[i] != current_signal else i + 1
            if pd.notna(current_signal) and current_signal in SIGNAL_COLORS:
                start_date = pd.Timestamp(dates[start_idx])
                end_date = pd.Timestamp(dates[min(end_idx, len(dates) - 1)])
                ax.axvspan(start_date, end_date, alpha=0.7,
                           color=SIGNAL_COLORS[current_signal], linewidth=0)
            current_signal = signals[i]
            start_idx = i

    # Handle last segment if it didn't get drawn
    if pd.notna(current_signal) and current_signal in SIGNAL_COLORS:
        start_date = pd.Timestamp(dates[start_idx])
        end_date = pd.Timestamp(dates[-1])
        ax.axvspan(start_date, end_date, alpha=0.7,
                   color=SIGNAL_COLORS[current_signal], linewidth=0)

    ax.set_ylabel(label, fontsize=10, fontweight=600)
    ax.set_yticks([])


def main():
    """Run the full divergence analysis pipeline and produce output files."""
    # 1. Load data
    print("Loading NASDAQ data...")
    loader = DataLoader('nasdaq', data_dir=DATA_ROOT)
    nasdaq_df = loader.load(start_date='2017-01-01')

    print("Loading published signals...")
    published = load_signal_fixture(
        os.path.join(DATA_ROOT, 'data', 'signals', 'nasdaq_signals.csv')
    )

    print("Running MDM classic engine...")
    engine = MDMEngine()
    results = engine.run(nasdaq_df)

    print("Extracting model signals...")
    model_signals = extract_model_signals(results)

    # 2. Comparison period: clip to overlap of published signals (2019-2026)
    pub_start = published['date'].min()
    pub_end = published['date'].max()
    print(f"Published signal range: {pub_start.date()} to {pub_end.date()}")

    # 3. Compare signals
    print("Comparing signals...")
    metrics = compare_signals(model_signals, published)
    aligned = align_signals(model_signals, published)
    config = MDMConfig()
    classified = classify_divergences(aligned, model_signals, results, config)

    # Add context column for divergence rows
    classified['context'] = ''
    for idx, row in classified.iterrows():
        if pd.notna(row.get('divergence_type')):
            classified.at[idx, 'context'] = generate_divergence_context(
                row, model_signals, results, config
            )

    # 4. CSV output
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Filter to divergence rows only
    divergence_rows = classified[
        classified['divergence_type'].notna()
    ].copy()

    csv_df = divergence_rows[['date', 'published', 'model', 'divergence_type', 'context']].copy()
    csv_df = csv_df.rename(columns={'published': 'published_signal', 'model': 'model_signal'})
    csv_df['date'] = csv_df['date'].dt.strftime('%Y-%m-%d')
    csv_path = os.path.join(OUTPUT_DIR, 'divergence_report.csv')
    csv_df.to_csv(csv_path, index=False)
    print(f"Wrote {len(csv_df)} divergence rows to {csv_path}")

    # 5. Text summary
    total_divergences = len(divergence_rows)
    div_type_counts = divergence_rows['divergence_type'].value_counts().to_dict()

    summary_path = os.path.join(OUTPUT_DIR, 'divergence_summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("Signal Divergence Report -- MDM Classic vs Published NASDAQ Signals\n")
        f.write("=" * 70 + "\n\n")

        model_count = len(model_signals)
        pub_count = metrics['total_published']
        rate = metrics['match_rate']
        f.write(f"Period: {pub_start.date()} to {pub_end.date()} | "
                f"Published signals: {pub_count} | "
                f"Model signals: {model_count} | "
                f"Match rate: {rate:.1f}%\n\n")

        f.write("Per-type match rates:\n")
        for sig_type in ['Buy', 'Sell', 'Cash']:
            info = metrics['per_type'].get(sig_type, {})
            f.write(f"  {sig_type}: {info.get('matched', 0)}/{info.get('published', 0)} "
                    f"({info.get('rate', 0):.1f}%)\n")
        f.write("\n")

        f.write("Divergences by type:\n")
        for dtype in ['THRESHOLD', 'TIMING', 'STRUCTURAL', 'IRREPRODUCIBLE']:
            count = div_type_counts.get(dtype, 0)
            pct = (count / total_divergences * 100) if total_divergences > 0 else 0
            f.write(f"  {dtype:<16} {count} ({pct:.1f}%)\n")
        f.write("\n")

        # Find longest consecutive divergence streak
        # Build daily divergence mask
        comparison_dates = results[
            (results['date'] >= pub_start) & (results['date'] <= pub_end)
        ]['date']
        if len(comparison_dates) > 0:
            date_range = comparison_dates.values
            daily_pub = expand_to_daily(published, date_range)
            daily_mod = expand_to_daily(model_signals, date_range)

            pub_series = daily_pub.set_index('date')['signal']
            mod_series = daily_mod.set_index('date')['signal']
            # Align indices
            common_idx = pub_series.index.intersection(mod_series.index)
            pub_aligned = pub_series.reindex(common_idx)
            mod_aligned = mod_series.reindex(common_idx)

            divergent = pub_aligned != mod_aligned
            if divergent.any():
                groups = divergent.ne(divergent.shift()).cumsum()
                longest_streak = 0
                longest_start = None
                longest_end = None
                for _, group in divergent.groupby(groups):
                    if group.iloc[0] and len(group) > longest_streak:
                        longest_streak = len(group)
                        longest_start = group.index[0]
                        longest_end = group.index[-1]

                if longest_start is not None:
                    start_str = pd.Timestamp(longest_start).strftime('%Y-%m-%d')
                    end_str = pd.Timestamp(longest_end).strftime('%Y-%m-%d')
                    f.write(f"Longest divergence streak: {longest_streak} days "
                            f"({start_str} to {end_str})\n")
            else:
                f.write("No divergence streaks found (perfect match on daily basis).\n")
        else:
            f.write("No comparison dates available.\n")

    print(f"Wrote summary to {summary_path}")

    # 6. Visual overlay chart
    print("Generating signal overlay chart...")

    # Prepare daily signal data for the comparison period
    comparison_df = results[
        (results['date'] >= pub_start) & (results['date'] <= pub_end)
    ].copy()
    date_range = comparison_df['date'].values

    daily_pub = expand_to_daily(published, date_range)
    daily_mod = expand_to_daily(model_signals, date_range)

    fig = plt.figure(figsize=(20, 10))
    fig.patch.set_facecolor('#ffffff')
    gs = GridSpec(3, 1, height_ratios=[4, 1, 1], hspace=0.05)

    # Price panel
    ax_price = fig.add_subplot(gs[0])
    ax_price.plot(comparison_df['date'], comparison_df['close'],
                  color='#1f1f1f', linewidth=0.8)
    ax_price.set_ylabel('NASDAQ', fontsize=10, fontweight=600)
    ax_price.grid(True, color='#e0e0e0', alpha=0.5)
    ax_price.set_facecolor('#ffffff')

    # Divergence shading on price panel
    pub_series = daily_pub.set_index('date')['signal']
    mod_series = daily_mod.set_index('date')['signal']
    common_idx = pub_series.index.intersection(mod_series.index)
    pub_aligned = pub_series.reindex(common_idx)
    mod_aligned = mod_series.reindex(common_idx)
    periods = find_divergence_periods(pub_aligned, mod_aligned)
    for start, end in periods:
        ax_price.axvspan(pd.Timestamp(start), pd.Timestamp(end),
                         alpha=0.12, color='#d62728', linewidth=0)

    # Spines
    for spine in ['top', 'right']:
        ax_price.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax_price.spines[spine].set_color('#cccccc')

    # Published signals panel
    ax_pub = fig.add_subplot(gs[1], sharex=ax_price)
    render_signal_track(ax_pub, daily_pub, 'Published')
    ax_pub.set_facecolor('#ffffff')
    for spine in ['top', 'right']:
        ax_pub.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax_pub.spines[spine].set_color('#cccccc')

    # Model signals panel
    ax_mod = fig.add_subplot(gs[2], sharex=ax_price)
    render_signal_track(ax_mod, daily_mod, 'Model (Classic)')
    ax_mod.set_facecolor('#ffffff')
    for spine in ['top', 'right']:
        ax_mod.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax_mod.spines[spine].set_color('#cccccc')

    # X-axis formatting on bottom panel only
    plt.setp(ax_price.get_xticklabels(), visible=False)
    plt.setp(ax_pub.get_xticklabels(), visible=False)
    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax_mod.xaxis.set_major_locator(locator)
    ax_mod.xaxis.set_major_formatter(formatter)

    # Title
    start_year = pd.Timestamp(date_range[0]).year
    end_year = pd.Timestamp(date_range[-1]).year
    fig.suptitle(
        f'MDM Classic vs Published Signals -- NASDAQ {start_year}-{end_year}',
        fontsize=14, fontweight=600, y=0.98
    )

    # Annotation box with stats
    threshold_count = div_type_counts.get('THRESHOLD', 0)
    timing_count = div_type_counts.get('TIMING', 0)
    structural_count = div_type_counts.get('STRUCTURAL', 0)
    irreproducible_count = div_type_counts.get('IRREPRODUCIBLE', 0)
    annotation_text = (
        f"Match rate: {metrics['match_rate']:.1f}% | "
        f"Divergences: {total_divergences} "
        f"({threshold_count}T / {timing_count}Ti / "
        f"{structural_count}S / {irreproducible_count}I)\n"
        f"Green=Buy  Red=Sell  Gray=Cash  Pink bands=Divergence"
    )
    fig.text(0.5, 0.02, annotation_text, ha='center', va='bottom',
             fontsize=9, fontweight=400,
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#f5f5f5',
                       edgecolor='#cccccc', alpha=0.9))

    chart_path = os.path.join(OUTPUT_DIR, 'signal_overlay.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"Wrote chart to {chart_path}")

    print("Done.")


if __name__ == '__main__':
    main()
