"""
Long-Only vs Long/Short Backtest Comparison

Compares performance of MDM Hybrid engine with and without short position
returns on NASDAQ and VN30. Uses single engine run per market with
long_only_equity flag to isolate short position contribution.

Usage:
    uv run python analysis/compare_long_short.py
    uv run python analysis/compare_long_short.py --market nasdaq
    uv run python analysis/compare_long_short.py --market vn30
    uv run python analysis/compare_long_short.py --output-dir results/
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
from strategies.mdm_hybrid.performance import V2PerformanceAnalyzer
from core.data_loader import DataLoader


def run_comparison(market: str, output_dir: str) -> dict:
    """Run long-only vs long/short comparison for a single market.

    Args:
        market: Market identifier ('nasdaq' or 'vn30').
        output_dir: Directory for output files.

    Returns:
        Dict with keys: market, long_short_summary, long_only_summary, trades.
    """
    print(f"\n{'='*60}")
    print(f"  {market.upper()} - Long-Only vs Long/Short Comparison")
    print(f"{'='*60}\n")

    # Load data
    loader = DataLoader(market)
    df = loader.load()
    print(f"Loaded {len(df)} rows for {market.upper()}")
    print(f"Date range: {df['date'].iloc[0].strftime('%Y-%m-%d')} to "
          f"{df['date'].iloc[-1].strftime('%Y-%m-%d')}")

    # Run engine once with short_mode enabled
    config = HybridConfig(
        v2_config=MDMV2Config(),
        filter_enabled=False,
        short_mode='direct',
    )
    engine = HybridEngine(config)
    results = engine.run(df)
    trades = engine.get_trades()

    print(f"Engine produced {len(trades)} trades")

    # Create two analyzers from SAME results
    long_short = V2PerformanceAnalyzer(results, trades, long_only_equity=False)
    long_only = V2PerformanceAnalyzer(results, trades, long_only_equity=True)

    ls_summary = long_short.summary()
    lo_summary = long_only.summary()

    # Print metrics table
    print_metrics_table(market, ls_summary, lo_summary)

    # Print short trade details
    print_short_trade_summary(trades)

    # Save metrics to text file
    save_metrics_file(market, ls_summary, lo_summary, trades, output_dir)

    # Generate chart
    generate_chart(market, results, long_short, long_only, output_dir)

    return {
        "market": market,
        "long_short_summary": ls_summary,
        "long_only_summary": lo_summary,
        "trades": trades,
    }


def print_metrics_table(market: str, ls: dict, lo: dict):
    """Print side-by-side metrics table to stdout.

    Args:
        market: Market name for header.
        ls: Long/short summary dict.
        lo: Long-only summary dict.
    """
    print(f"\n  {market.upper()} Performance Comparison")
    print(f"  {'Metric':<22} {'Long/Short':>14} {'Long-Only':>14}")
    print(f"  {'-'*50}")
    print(f"  {'Total Return':<22} {ls['total_return']:>+13.1%} {lo['total_return']:>+13.1%}")
    print(f"  {'Annualized Return':<22} {ls['annualized_return']:>+13.1%} {lo['annualized_return']:>+13.1%}")
    print(f"  {'Max Drawdown':<22} {ls['max_drawdown']:>+13.1%} {lo['max_drawdown']:>+13.1%}")
    print(f"  {'Sharpe Ratio':<22} {ls['sharpe_ratio']:>14.2f} {lo['sharpe_ratio']:>14.2f}")
    print(f"  {'Win Rate':<22} {ls['win_rate']:>13.1%} {lo['win_rate']:>13.1%}")
    print()


def print_short_trade_summary(trades: list):
    """Print summary of SHORT_COVER trades.

    Args:
        trades: List of trade dicts from engine.
    """
    short_covers = [t for t in trades if t.get("type") == "SHORT_COVER"]
    if not short_covers:
        print("  No SHORT_COVER trades found.\n")
        return

    short_pnls = [t.get("pnl", 0) for t in short_covers]
    short_wins = sum(1 for p in short_pnls if p > 0)

    print(f"  Short Trade Details")
    print(f"  {'-'*40}")
    print(f"  {'Short trades:':<25} {len(short_covers)}")
    print(f"  {'Short win rate:':<25} {short_wins / len(short_covers):.1%}")
    print(f"  {'Avg short P&L:':<25} {np.mean(short_pnls):+.2%}")
    print(f"  {'Best short:':<25} {max(short_pnls):+.2%}")
    print(f"  {'Worst short:':<25} {min(short_pnls):+.2%}")
    print()


def save_metrics_file(market: str, ls: dict, lo: dict, trades: list,
                      output_dir: str):
    """Save metrics comparison to text file.

    Args:
        market: Market name.
        ls: Long/short summary dict.
        lo: Long-only summary dict.
        trades: Trade list for short details.
        output_dir: Output directory.
    """
    filepath = os.path.join(output_dir, f"compare_{market}.txt")
    with open(filepath, 'w') as f:
        f.write(f"{market.upper()} - Long-Only vs Long/Short Performance Comparison\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"{'Metric':<22} {'Long/Short':>14} {'Long-Only':>14}\n")
        f.write(f"{'-'*50}\n")
        f.write(f"{'Total Return':<22} {ls['total_return']:>+13.1%} {lo['total_return']:>+13.1%}\n")
        f.write(f"{'Annualized Return':<22} {ls['annualized_return']:>+13.1%} {lo['annualized_return']:>+13.1%}\n")
        f.write(f"{'Max Drawdown':<22} {ls['max_drawdown']:>+13.1%} {lo['max_drawdown']:>+13.1%}\n")
        f.write(f"{'Sharpe Ratio':<22} {ls['sharpe_ratio']:>14.2f} {lo['sharpe_ratio']:>14.2f}\n")
        f.write(f"{'Win Rate':<22} {ls['win_rate']:>13.1%} {lo['win_rate']:>13.1%}\n")

        short_covers = [t for t in trades if t.get("type") == "SHORT_COVER"]
        if short_covers:
            short_pnls = [t.get("pnl", 0) for t in short_covers]
            short_wins = sum(1 for p in short_pnls if p > 0)
            f.write(f"\nShort Trade Details\n")
            f.write(f"{'-'*40}\n")
            f.write(f"{'Short trades:':<25} {len(short_covers)}\n")
            f.write(f"{'Short win rate:':<25} {short_wins / len(short_covers):.1%}\n")
            f.write(f"{'Avg short P&L:':<25} {np.mean(short_pnls):+.2%}\n")

    print(f"  Metrics saved to: {filepath}")


def generate_chart(market: str, results: pd.DataFrame,
                   long_short: V2PerformanceAnalyzer,
                   long_only: V2PerformanceAnalyzer,
                   output_dir: str):
    """Generate equity curve comparison chart.

    Args:
        market: Market name for title.
        results: Engine results DataFrame with date column.
        long_short: Analyzer with short inverse returns.
        long_only: Analyzer with flat SELL returns.
        output_dir: Output directory for PNG.
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    dates = results['date'].values

    ax.plot(dates, long_short.equity.values, color='blue', linewidth=1.2,
            label='Long/Short', alpha=0.9)
    ax.plot(dates, long_only.equity.values, color='orange', linewidth=1.2,
            label='Long-Only', alpha=0.9)

    ax.set_title(f"{market.upper()} - Long-Only vs Long/Short Performance",
                 fontsize=14, fontweight='bold')
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Equity (normalized to 1.0)", fontsize=11)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)

    # Format x-axis dates
    fig.autofmt_xdate()

    filepath = os.path.join(output_dir, f"compare_{market}.png")
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Chart saved to: {filepath}")


def main():
    """Main entry point with argparse CLI."""
    parser = argparse.ArgumentParser(
        description="Compare long-only vs long/short MDM Hybrid performance"
    )
    parser.add_argument(
        '--market',
        choices=['nasdaq', 'vn30'],
        default=None,
        help="Run comparison for specific market only (default: both)"
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help="Output directory for charts and metrics (default: output/)"
    )
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    markets = [args.market] if args.market else ['nasdaq', 'vn30']
    results = {}

    for market in markets:
        try:
            result = run_comparison(market, args.output_dir)
            results[market] = result
        except Exception as e:
            print(f"\n  ERROR running {market}: {e}")
            import traceback
            traceback.print_exc()

    # Print final summary if both markets ran
    if len(results) == 2:
        print(f"\n{'='*60}")
        print(f"  CROSS-MARKET SUMMARY")
        print(f"{'='*60}")
        for market, r in results.items():
            ls = r['long_short_summary']
            lo = r['long_only_summary']
            diff = ls['total_return'] - lo['total_return']
            print(f"  {market.upper()}: Short contribution = {diff:+.1%} total return")
        print()


if __name__ == '__main__':
    main()
