"""
Hybrid MDM Backtest Entry Point

Runs the hybrid MDM engine with indicator filter enabled on NASDAQ data.
Produces:
  1. Detailed CSV signal log (date, old_state, proposed, verdict, final_state, action)
  2. Console summary with performance metrics (win rate, drawdown, trade count)

Usage:
    uv run python scripts/run_hybrid_backtest.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Resolve main repo root for data access (handles git worktree paths)
MAIN_REPO = PROJECT_ROOT
if '.claude' in str(PROJECT_ROOT) and 'worktrees' in str(PROJECT_ROOT):
    parts = PROJECT_ROOT.parts
    for i, part in enumerate(parts):
        if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
            MAIN_REPO = Path(*parts[:i])
            break

from core.data_loader import DataLoader
from strategies.mdm_hybrid.config import HybridConfig
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine


def run_hybrid_backtest():
    """Run hybrid MDM backtest and produce signal log + console summary."""
    # Load NASDAQ data
    loader = DataLoader('nasdaq')
    loader.data_dir = MAIN_REPO
    df = loader.load()

    if df is None or df.empty:
        print("ERROR: Could not load NASDAQ data")
        sys.exit(1)

    # Configure hybrid engine with filter enabled
    config = HybridConfig(filter_enabled=True)
    engine = HybridEngine(config)

    # Run backtest
    results = engine.run(df)

    # 1. Signal log CSV (D-09, D-10)
    signal_cols = ['date', 'old_state', 'proposed', 'verdict', 'state', 'action']
    signal_log = results[signal_cols].copy()
    signal_log = signal_log.rename(columns={'state': 'final_state'})

    output_path = PROJECT_ROOT / 'results' / 'hybrid_signal_log.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    signal_log.to_csv(output_path, index=False)
    print(f"Signal log saved to {output_path} ({len(signal_log)} rows)")

    # 2. Console summary
    summary = engine.summary()
    trades = engine.get_trades()

    print("\n=== Hybrid MDM Backtest Summary ===")
    print(f"Total BUY signals:  {summary['total_buy_signals']}")
    print(f"Total CASH exits:   {summary['total_cash_exits']}")
    print(f"Total SELL signals: {summary['total_sell_signals']}")
    print(f"Completed trades:   {summary['total_completed']}")
    print(f"Win rate:           {summary['win_rate']:.1%}")
    print(f"Total P&L:          {summary['long_pnl']:.4f}")
    print(f"Avg P&L per trade:  {summary['avg_pnl']:.4f}")

    # Verdict distribution
    if 'verdict' in results.columns:
        verdict_counts = results[results['verdict'] != '']['verdict'].value_counts()
        print("\n--- Verdict Distribution ---")
        for verdict, count in verdict_counts.items():
            print(f"  {verdict}: {count}")

    # Trade type distribution
    trade_types = {}
    for t in trades:
        tt = t['type']
        trade_types[tt] = trade_types.get(tt, 0) + 1
    print("\n--- Trade Types ---")
    for tt, count in sorted(trade_types.items()):
        print(f"  {tt}: {count}")

    print(f"\nDone. Signal log at: {output_path.resolve()}")


if __name__ == '__main__':
    run_hybrid_backtest()
