"""
Drawdown Analysis Script for VN30 VSA Strategy
"""
import pandas as pd
import numpy as np
from vn30_vsa.vsa_engine import VSAEngine

# Run full backtest
engine = VSAEngine(
    initial_nav=1_000_000_000,
    start_date='2016-01-01',
    end_date='2026-01-24'
)
engine.load_data('VN30_STOCKS_PRICE.csv')
nav_df = engine.run()
trades_df = engine.get_trades()

# Calculate drawdown
nav_df['peak'] = nav_df['nav'].cummax()
nav_df['drawdown'] = (nav_df['nav'] - nav_df['peak']) / nav_df['peak'] * 100

print('='*60)
print('DRAWDOWN ANALYSIS')
print('='*60)

# Max drawdown
max_dd = nav_df['drawdown'].min()
max_dd_idx = nav_df['drawdown'].idxmin()
max_dd_date = nav_df.loc[max_dd_idx, 'date']
print(f'Max Drawdown: {max_dd:.2f}%')
print(f'Max Drawdown Date: {max_dd_date.date()}')

# Find peak before max drawdown
peak_before_dd = nav_df[nav_df.index <= max_dd_idx]['peak'].max()
peak_date = nav_df[nav_df['nav'] == peak_before_dd]['date'].iloc[0]
print(f'Peak before Drawdown: {peak_before_dd:,.0f} on {peak_date.date()}')
bottom_nav = nav_df.loc[max_dd_idx, 'nav']
print(f'Bottom NAV: {bottom_nav:,.0f}')

# Yearly drawdowns
print('')
print('-'*40)
print('MAX DRAWDOWN BY YEAR')
print('-'*40)
nav_df['year'] = nav_df['date'].dt.year
yearly_dd = nav_df.groupby('year')['drawdown'].min()
for year, dd in yearly_dd.items():
    emoji = 'X' if dd < -15 else 'O' if dd < -10 else '+'
    print(f'{emoji} {year}: {dd:.1f}%')

# Contributing factors
print('')
print('-'*40)
print('TRADES BY EXIT REASON')
print('-'*40)

for reason in trades_df['exit_reason'].unique():
    subset = trades_df[trades_df['exit_reason']==reason]
    avg_pnl = subset['pnl_pct'].mean()*100
    print(f'{reason}: {len(subset)} trades, avg {avg_pnl:+.1f}%')

# Stop loss analysis
print('')
print('-'*40)
print('STOP LOSS ANALYSIS')
print('-'*40)
sl_trades = trades_df[trades_df['exit_reason'].str.contains('Stop Loss|Spike Low', case=False, na=False)]
print(f'Stop loss trades: {len(sl_trades)} ({len(sl_trades)/len(trades_df)*100:.1f}%)')
if len(sl_trades) > 0:
    avg_sl = sl_trades['pnl_pct'].mean()*100
    total_sl = sl_trades['pnl'].sum()
    print(f'Avg stop loss: {avg_sl:.1f}%')
    print(f'Total loss from stops: {total_sl:,.0f}')

# Worst trades
print('')
print('-'*40)
print('TOP 10 WORST TRADES')
print('-'*40)
worst = trades_df.nsmallest(10, 'pnl_pct')
for _, t in worst.iterrows():
    pnl_pct = t['pnl_pct']*100
    print(f'{t["stock_code"]} {t["buy_date"].date()}: {pnl_pct:+.1f}% ({t["exit_reason"]})')

# Drawdown during market crash periods
print('')
print('-'*40)
print('ANALYSIS: WHY DRAWDOWN IS HIGH')
print('-'*40)

# 2020 COVID crash
trades_2020 = trades_df[(trades_df['sell_date'] >= '2020-01-01') & (trades_df['sell_date'] <= '2020-04-30')]
if len(trades_2020) > 0:
    print(f'\n2020 COVID Crash (Jan-Apr):')
    print(f'  Trades: {len(trades_2020)}')
    sl_2020 = trades_2020[trades_2020['exit_reason'].str.contains('Stop|Spike', case=False, na=False)]
    print(f'  Stop losses: {len(sl_2020)}')
    print(f'  Avg P/L: {trades_2020["pnl_pct"].mean()*100:.1f}%')

# 2022 bear market
trades_2022 = trades_df[(trades_df['sell_date'] >= '2022-01-01') & (trades_df['sell_date'] <= '2022-12-31')]
if len(trades_2022) > 0:
    print(f'\n2022 Bear Market:')
    print(f'  Trades: {len(trades_2022)}')
    sl_2022 = trades_2022[trades_2022['exit_reason'].str.contains('Stop|Spike', case=False, na=False)]
    print(f'  Stop losses: {len(sl_2022)}')
    win_2022 = len(trades_2022[trades_2022['pnl'] > 0])
    print(f'  Win rate: {win_2022/len(trades_2022)*100:.1f}%')
    print(f'  Avg P/L: {trades_2022["pnl_pct"].mean()*100:.1f}%')
