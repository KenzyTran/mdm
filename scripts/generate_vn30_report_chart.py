"""
VN30 Report Chart Generator - Individual charts per strategy.

Generates 3 separate charts, one per model:
- output/vn30_chart_v2.png: V2 State Machine
- output/vn30_chart_hybrid.png: Hybrid (3 Filters)
- output/vn30_chart_p15.png: Phase 15 (HA Smoothed + Contextual)

Each chart has 2 panels:
- Top: VN30 price with Buy/Sell/Cash signal markers
- Bottom: Equity curve (model vs Buy & Hold)

Usage:
    uv run python scripts/generate_vn30_report_chart.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
from strategies.mdm_hybrid.indicator_filter import FilterConfig


START_DATE = '2015-01-01'
END_DATE = '2026-01-16'

MODELS = {
    'v2': {
        'label': 'V2 State Machine',
        'color': 'blue',
        'filename': 'vn30_chart_v2.png',
        'config': lambda: HybridConfig(
            v2_config=MDMV2Config(),
            two_phase_enabled=True,
            filter_enabled=False,
        ),
    },
    'hybrid': {
        'label': 'Hybrid (3 Filters)',
        'color': 'orangered',
        'filename': 'vn30_chart_hybrid.png',
        'config': lambda: HybridConfig(
            v2_config=MDMV2Config(),
            two_phase_enabled=True,
            filter_enabled=True,
            filter_config=FilterConfig(),
        ),
    },
    'p15': {
        'label': 'Phase 15 (HA Smoothed + Context)',
        'color': 'purple',
        'filename': 'vn30_chart_p15.png',
        'config': lambda: HybridConfig(
            v2_config=MDMV2Config(),
            two_phase_enabled=True,
            filter_enabled=True,
            filter_config=FilterConfig(ha_smooth_enabled=True),
        ),
    },
}


def load_data() -> pd.DataFrame:
    """Load VN30 data and build indicators."""
    loader = DataLoader('vn30')
    df = loader.load(start_date=START_DATE, end_date=END_DATE)
    return build_indicator_dataframe(df)


def compute_equity(results: pd.DataFrame) -> pd.Series:
    """Compute equity curve: long on BUY, short (inverse) on SELL."""
    closes = results['close'].values
    states = results['state'].shift().values  # previous-day state drives today's return
    n = len(closes)
    equity = np.ones(n, dtype=float)
    for i in range(1, n):
        if states[i] == 'BUY':
            equity[i] = equity[i - 1] * (closes[i] / closes[i - 1])
        elif states[i] == 'SELL':
            equity[i] = equity[i - 1] * (closes[i - 1] / closes[i])
        else:
            equity[i] = equity[i - 1]
    return pd.Series(equity, index=results.index)


def compute_metrics(results: pd.DataFrame) -> dict:
    """Compute CAGR, MaxDD, trades, % invested."""
    equity = compute_equity(results)
    years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
    total_return = (equity.iloc[-1] - 1) * 100
    cagr = (equity.iloc[-1] ** (1 / years) - 1) * 100

    peak = equity.cummax()
    dd = (equity - peak) / peak
    max_dd = dd.min() * 100

    buy_days = (results['state'] == 'BUY').sum()
    invested_pct = buy_days / len(results) * 100
    trades = ((results['state'] == 'BUY') & (results['state'].shift() != 'BUY')).sum()

    return {
        'return': total_return,
        'cagr': cagr,
        'max_dd': max_dd,
        'invested': invested_pct,
        'trades': int(trades),
    }


def detect_signals(results: pd.DataFrame) -> dict:
    """Detect state transitions for signal markers."""
    signals = {'buy': [], 'sell': [], 'cash': []}
    states = results['state'].values
    dates = results['date'].values
    closes = results['close'].values

    for i in range(1, len(states)):
        if states[i] != states[i - 1]:
            d, p = dates[i], closes[i]
            if states[i] == 'BUY':
                signals['buy'].append((d, p))
            elif states[i] == 'SELL':
                signals['sell'].append((d, p))
            elif states[i] == 'CASH':
                signals['cash'].append((d, p))

    return signals


def generate_single_chart(df: pd.DataFrame, results: pd.DataFrame,
                          model_info: dict, output_path: str):
    """Generate a 2-panel chart for a single model."""
    dates = df['date']
    label = model_info['label']
    color = model_info['color']

    # Equity
    model_equity = compute_equity(results)
    bh_equity = df['close'] / df['close'].iloc[0]

    # Metrics
    m = compute_metrics(results)
    bh_return = (bh_equity.iloc[-1] - 1) * 100
    years = (dates.iloc[-1] - dates.iloc[0]).days / 365.25
    bh_cagr = ((1 + bh_return / 100) ** (1 / years) - 1) * 100
    bh_peak = df['close'].cummax()
    bh_max_dd = ((df['close'] - bh_peak) / bh_peak).min() * 100

    # Signals
    signals = detect_signals(results)

    # Create figure
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(16, 10),
        gridspec_kw={'height_ratios': [3, 2]}
    )

    # --- Panel 1: VN30 Price + Signals ---
    ax1.plot(dates, df['close'].values, color='black', linewidth=1.0)

    for d, p in signals['buy']:
        ax1.plot(d, p, '^', color='green', markersize=11, alpha=0.9, zorder=5)
    for d, p in signals['sell']:
        ax1.plot(d, p, 'v', color='red', markersize=11, alpha=0.9, zorder=5)
    for d, p in signals['cash']:
        ax1.plot(d, p, 'D', color='goldenrod', markersize=8, alpha=0.9, zorder=5)

    legend_elements = [
        Line2D([0], [0], color='black', linewidth=1.0, label='VN30'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='green',
               markersize=10, label='BUY'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='red',
               markersize=10, label='SELL'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='goldenrod',
               markersize=8, label='CASH'),
    ]
    ax1.legend(handles=legend_elements, loc='upper left', fontsize=10)
    ax1.set_title(f'VN30 {label} (2015-2026)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('VN30 Index', fontsize=11)
    ax1.grid(True, alpha=0.3)

    # Shade BUY periods with light green
    states = results['state'].values
    for i in range(1, len(states)):
        if states[i] == 'BUY':
            ax1.axvspan(dates.iloc[i - 1], dates.iloc[i],
                        alpha=0.08, color='green', linewidth=0)

    # --- Panel 2: Equity Curve ---
    ax2.plot(dates, model_equity.values, label=label,
             color=color, linewidth=2.0)
    ax2.plot(dates, bh_equity.values, label='Buy & Hold',
             color='gray', linewidth=1.0, linestyle='--', alpha=0.7)

    # End annotations
    last_date = dates.iloc[-1]
    ax2.annotate(f'+{m["return"]:.0f}%',
                 xy=(last_date, model_equity.iloc[-1]),
                 fontsize=10, fontweight='bold', color=color,
                 xytext=(5, 0), textcoords='offset points', va='center')
    ax2.annotate(f'+{bh_return:.0f}%',
                 xy=(last_date, bh_equity.iloc[-1]),
                 fontsize=10, fontweight='bold', color='gray',
                 xytext=(5, 0), textcoords='offset points', va='center')

    ax2.set_ylabel('Growth of $1', fontsize=11)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # Summary text box
    summary_text = (
        f"{label}\n"
        f"Return: +{m['return']:.1f}%  |  CAGR: {m['cagr']:.1f}%\n"
        f"MaxDD: {m['max_dd']:.1f}%  |  Trades: {m['trades']}\n"
        f"Invested: {m['invested']:.0f}% of time\n"
        f"---\n"
        f"Buy & Hold: +{bh_return:.0f}%, MaxDD {bh_max_dd:.1f}%"
    )
    ax2.text(0.98, 0.05, summary_text, transform=ax2.transAxes,
             fontsize=9, verticalalignment='bottom', horizontalalignment='right',
             family='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.85))

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"  [{label}] Return {m['return']:.1f}%, CAGR {m['cagr']:.1f}%, MaxDD {m['max_dd']:.1f}%, {m['trades']} trades -> {output_path}")


def main():
    """Generate individual VN30 report charts."""
    output_dir = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
        'output'
    )

    print("=" * 60)
    print("VN30 REPORT CHART GENERATOR")
    print("=" * 60)

    print("\n[1/3] Loading VN30 data + indicators...")
    df = load_data()
    print(f"  Loaded {len(df)} rows ({df['date'].min().date()} to {df['date'].max().date()})")

    print("\n[2/3] Running models...")
    all_results = {}
    for key, info in MODELS.items():
        engine = HybridEngine(info['config']())
        all_results[key] = engine.run(df.copy())
        print(f"  {info['label']}: done")

    print("\n[3/3] Generating charts...")
    for key, info in MODELS.items():
        path = os.path.join(output_dir, info['filename'])
        generate_single_chart(df, all_results[key], info, path)

    print("\n" + "=" * 60)
    print("DONE - 3 charts generated")
    print("=" * 60)


if __name__ == '__main__':
    main()
