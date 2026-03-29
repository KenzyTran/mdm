import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from strategies.mdm_classic import MDMEngine
from strategies.mdm_classic.data_loader import DataLoader

# Load data and run engine
loader = DataLoader('data/vnindex_price.csv')
df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
engine = MDMEngine()
results = engine.run(df)

# Calculate equity curve
# Assume 100M initial capital
initial_capital = 100_000_000
equity = [initial_capital]
position = 0 # 0: Cash, 1: Invested
current_capital = initial_capital
shares = 0

trades = engine.get_trades()
trade_df = pd.DataFrame(trades)
if not trade_df.empty:
    trade_df['date'] = pd.to_datetime(trade_df['date'])

# We need to simulate equity day by day to get daily drawdown
equity_curve = []
dates = []

current_cash = initial_capital
current_shares = 0
last_price = 0

for idx, row in results.iterrows():
    date = row['date']
    close = row['close']
    state = row['state'] # CASH, HOLDING, WAITING_SELL, SHORT

    # Simple simulation matching the backtest logic implicitly
    # If state is HOLDING or WAITING_SELL, we are invested long
    # If state is SHORT, we are short
    # If state is CASH, we are in cash

    # NOTE: This is an approximation. The engine results don't store daily equity.
    # We will rely on the trade list to reconstruct exact entry/exit points
    # or just use the state from results to approximate.

    # Better approach: Calculate drawdown OF THE INDEX first,
    # then check what the system was doing during max drawdown periods of the index.
    pass

# Robust Portfolio Simulation
capital = initial_capital
current_shares = 0
current_short_value = 0 # Value of short position (liability)
short_entry_price = 0
is_short = False

portfolio_history = []

# We need to process sequentialy.
# The 'results' dataframe has daily state but not trade execution prices on that specific day easily accessible
# except via the 'action' string parsing or by mapping trade list back to dates.
# Let's map trades to dates for easier processing
buy_dates = {}
sell_dates = {}
short_dates = {}
cover_dates = {}

for trade in trades:
    d = pd.Timestamp(trade['date'])
    if trade['type'] == 'BUY':
        buy_dates[d] = trade['price']
        if 'signal_type' in trade:
             # Store signal type if needed
             pass
    elif trade['type'] == 'SELL':
        sell_dates[d] = {'price': trade['price'], 'reason': trade.get('reason', '')}
    elif trade['type'] == 'SHORT':
        short_dates[d] = trade['price']
    elif trade['type'] == 'COVER':
        cover_dates[d] = {'price': trade['price'], 'reason': trade.get('reason', '')}

for idx, row in results.iterrows():
    date = pd.Timestamp(row['date'])
    close = row['close']
    state = row['state']

    # Check for trade actions first
    if date in buy_dates:
        # EXECUTE BUY
        # If we have cash, buy shares
        if capital > 0:
            price = buy_dates[date]
            # Assuming we buy at CLOSE price of the signal day (as per engine logic)
            # engine.enter_holding uses ftd_price which is Close.
            current_shares = capital / price
            capital = 0
            is_short = False

    elif date in short_dates:
        # EXECUTE SHORT
        # If we have cash, open short
        if capital > 0:
            price = short_dates[date]
            # Simple short logic: We hold CASH = capital + short_proceeds
            # But we have liability = shares * price
            # MDM engine logic simplifies this.
            # Let's assume we "bet" the capital on short.
            # Value = Initial_Capital * (1 + (Entry - Current)/Entry)
            short_entry_price = price
            # We treat 'capital' as the BASIS for the short
            # We don't change capital variable, we just toggle is_short flag
            # and calculate value differently.
            is_short = True

    elif date in sell_dates:
        # EXECUTE SELL
        if current_shares > 0:
            price = sell_dates[date]['price']
            capital = current_shares * price
            current_shares = 0
            is_short = False

    elif date in cover_dates:
        # EXECUTE COVER
        if is_short:
            price = cover_dates[date]['price']
            # Calculate PnL
            pnl_pct = (short_entry_price - price) / short_entry_price
            capital = capital * (1 + pnl_pct)
            is_short = False
            short_entry_price = 0

    # Calculate End of Day Value
    daily_value = capital
    if current_shares > 0:
        daily_value = current_shares * close
    elif is_short:
        # Short value = Original Capital * (1 + (Entry - Current)/Entry)
        pnl_pct = (short_entry_price - close) / short_entry_price
        daily_value = capital * (1 + pnl_pct)

    portfolio_history.append({
        'date': date,
        'value': daily_value,
        'state': state,
        'close': close,
        'drawdown_pct': 0.0 # calculate later
    })

port_df = pd.DataFrame(portfolio_history)
port_df['peak'] = port_df['value'].cummax()
port_df['drawdown_pct'] = (port_df['value'] - port_df['peak']) / port_df['peak']

# Find Max Drawdown
max_dd_row = port_df.loc[port_df['drawdown_pct'].idxmin()]
print(f"Max Portfolio Drawdown: {max_dd_row['drawdown_pct']*100:.2f}% on {max_dd_row['date']}")

# Find top 5 drawdown periods
# Group by continuous drawdown periods?
# Let's just print the worst days.
print("\nTop 10 Worst Drawdown Days:")
print(port_df.sort_values('drawdown_pct').head(10)[['date', 'value', 'drawdown_pct', 'state', 'close']])

# Analyze specific bad trades
print("\n=== Trade Analysis ===")
trade_df = engine.get_trade_df()
if not trade_df.empty:
    trade_df['pnl_pct'] = trade_df['pnl'] * 100
    print("\nWorst 10 Trades:")
    print(trade_df.sort_values('pnl').head(10)[['date', 'type', 'price', 'pnl_pct', 'reason', 'signal_type' if 'signal_type' in trade_df.columns else 'type']])

# Check shorts specifically
short_trades = trade_df[trade_df['type'] == 'COVER']
if not short_trades.empty:
    print("\nShort Trades Stats:")
    print(f"Total: {len(short_trades)}")
    print(f"Win Rate: {len(short_trades[short_trades['pnl']>0]) / len(short_trades) * 100:.2f}%")
    print(f"Avg PnL: {short_trades['pnl'].mean()*100:.2f}%")
