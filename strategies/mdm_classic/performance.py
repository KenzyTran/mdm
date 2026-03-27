"""
Performance Analyzer Module
Calculate and compare performance metrics.
"""

import pandas as pd
import numpy as np
from typing import Optional


class PerformanceAnalyzer:
    """
    Analyze and compare MDM strategy performance vs buy-and-hold.
    
    Metrics:
    - Total return
    - Annualized return
    - Max drawdown
    - Win rate
    - Number of trades
    """
    
    TRADING_DAYS_PER_YEAR = 252
    
    def __init__(self, df: pd.DataFrame, trades: list):
        """
        Initialize analyzer.
        
        Args:
            df: Results DataFrame from MDM engine
            trades: List of trade records
        """
        self.df = df
        self.trades = trades
        self.equity_curve: Optional[pd.Series] = None
    
    def calculate_buy_and_hold(self) -> dict:
        """
        Calculate buy-and-hold performance.
        
        Returns:
            Dictionary with performance metrics
        """
        if len(self.df) == 0:
            return {}
        
        start_price = self.df.iloc[0]['close']
        end_price = self.df.iloc[-1]['close']
        
        total_return = (end_price - start_price) / start_price
        
        # Calculate number of years
        days = (self.df.iloc[-1]['date'] - self.df.iloc[0]['date']).days
        years = days / 365.25
        
        # Annualized return
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Max drawdown
        cummax = self.df['close'].cummax()
        drawdown = (self.df['close'] - cummax) / cummax
        max_drawdown = drawdown.min()
        
        return {
            'strategy': 'Buy and Hold',
            'total_return': total_return,
            'total_return_pct': f"{total_return * 100:.2f}%",
            'annualized_return': annualized_return,
            'annualized_return_pct': f"{annualized_return * 100:.2f}%",
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': f"{max_drawdown * 100:.2f}%",
            'start_price': start_price,
            'end_price': end_price,
            'years': years
        }
    
    def calculate_mdm_performance(self) -> dict:
        """
        Calculate MDM strategy performance.
        
        Returns:
            Dictionary with performance metrics
        """
        if len(self.trades) == 0:
            return {
                'strategy': 'MDM',
                'total_return': 0,
                'total_return_pct': '0.00%',
                'num_trades': 0,
                'note': 'No trades executed'
            }
        
        # Build equity curve
        equity = 1.0  # Start with $1
        equity_history = []
        
        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        
        for i, sell in enumerate(sell_trades):
            pnl = sell.get('pnl', 0)
            equity *= (1 + pnl)
            equity_history.append({
                'trade_num': i + 1,
                'date': sell['date'],
                'pnl': pnl,
                'equity': equity
            })
        
        total_return = equity - 1
        
        # Win rate
        wins = sum(1 for t in sell_trades if t.get('pnl', 0) > 0)
        win_rate = wins / len(sell_trades) if sell_trades else 0
        
        # Average win/loss
        win_pnls = [t.get('pnl', 0) for t in sell_trades if t.get('pnl', 0) > 0]
        loss_pnls = [t.get('pnl', 0) for t in sell_trades if t.get('pnl', 0) <= 0]
        
        avg_win = np.mean(win_pnls) if win_pnls else 0
        avg_loss = np.mean(loss_pnls) if loss_pnls else 0
        
        # Max drawdown from equity curve
        if equity_history:
            equities = [e['equity'] for e in equity_history]
            cummax = pd.Series(equities).cummax()
            drawdown = (pd.Series(equities) - cummax) / cummax
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0
        
        # Annualized return
        if len(self.df) > 0:
            days = (self.df.iloc[-1]['date'] - self.df.iloc[0]['date']).days
            years = days / 365.25
            annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        else:
            years = 0
            annualized_return = 0
        
        return {
            'strategy': 'MDM',
            'total_return': total_return,
            'total_return_pct': f"{total_return * 100:.2f}%",
            'annualized_return': annualized_return,
            'annualized_return_pct': f"{annualized_return * 100:.2f}%",
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': f"{max_drawdown * 100:.2f}%",
            'num_trades': len(sell_trades),
            'wins': wins,
            'losses': len(sell_trades) - wins,
            'win_rate': win_rate,
            'win_rate_pct': f"{win_rate * 100:.2f}%",
            'avg_win': avg_win,
            'avg_win_pct': f"{avg_win * 100:.2f}%",
            'avg_loss': avg_loss,
            'avg_loss_pct': f"{avg_loss * 100:.2f}%",
            'equity_history': equity_history
        }
    
    def compare(self) -> pd.DataFrame:
        """
        Compare MDM vs Buy-and-Hold.
        
        Returns:
            DataFrame with comparison
        """
        bh = self.calculate_buy_and_hold()
        mdm = self.calculate_mdm_performance()
        
        comparison = {
            'Metric': [
                'Total Return',
                'Annualized Return',
                'Max Drawdown',
                'Number of Trades',
                'Win Rate'
            ],
            'Buy & Hold': [
                bh.get('total_return_pct', 'N/A'),
                bh.get('annualized_return_pct', 'N/A'),
                bh.get('max_drawdown_pct', 'N/A'),
                'N/A (always in)',
                'N/A'
            ],
            'MDM Strategy': [
                mdm.get('total_return_pct', 'N/A'),
                mdm.get('annualized_return_pct', 'N/A'),
                mdm.get('max_drawdown_pct', 'N/A'),
                str(mdm.get('num_trades', 0)),
                mdm.get('win_rate_pct', 'N/A')
            ]
        }
        
        return pd.DataFrame(comparison)
    
    def print_report(self):
        """Print a formatted performance report."""
        bh = self.calculate_buy_and_hold()
        mdm = self.calculate_mdm_performance()
        
        print("=" * 60)
        print("MDM PERFORMANCE REPORT")
        print("=" * 60)
        
        print("\n📊 BUY & HOLD BENCHMARK")
        print("-" * 40)
        print(f"  Start Price:      {bh.get('start_price', 0):,.2f}")
        print(f"  End Price:        {bh.get('end_price', 0):,.2f}")
        print(f"  Total Return:     {bh.get('total_return_pct', 'N/A')}")
        print(f"  Annualized:       {bh.get('annualized_return_pct', 'N/A')}")
        print(f"  Max Drawdown:     {bh.get('max_drawdown_pct', 'N/A')}")
        
        print("\n📈 MDM STRATEGY")
        print("-" * 40)
        print(f"  Total Return:     {mdm.get('total_return_pct', 'N/A')}")
        print(f"  Annualized:       {mdm.get('annualized_return_pct', 'N/A')}")
        print(f"  Max Drawdown:     {mdm.get('max_drawdown_pct', 'N/A')}")
        print(f"  Trades:           {mdm.get('num_trades', 0)}")
        print(f"  Wins/Losses:      {mdm.get('wins', 0)}/{mdm.get('losses', 0)}")
        print(f"  Win Rate:         {mdm.get('win_rate_pct', 'N/A')}")
        print(f"  Avg Win:          {mdm.get('avg_win_pct', 'N/A')}")
        print(f"  Avg Loss:         {mdm.get('avg_loss_pct', 'N/A')}")
        
        print("\n" + "=" * 60)
        
        # Outperformance
        mdm_return = mdm.get('total_return', 0)
        bh_return = bh.get('total_return', 0)
        
        if mdm_return > bh_return:
            outperform = (mdm_return - bh_return) * 100
            print(f"✅ MDM OUTPERFORMS by {outperform:.2f}%")
        else:
            underperform = (bh_return - mdm_return) * 100
            print(f"❌ MDM UNDERPERFORMS by {underperform:.2f}%")
        
        print("=" * 60)
