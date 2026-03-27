"""
Performance Metrics Module
Calculates and displays backtest performance statistics
"""

import pandas as pd
import numpy as np
from typing import Dict


def calculate_performance_metrics(nav_df: pd.DataFrame, trades_df: pd.DataFrame,
                                   initial_nav: float) -> Dict:
    """
    Calculate comprehensive performance metrics.
    
    Args:
        nav_df: DataFrame with NAV history
        trades_df: DataFrame with trade history
        initial_nav: Initial portfolio value
        
    Returns:
        Dictionary with performance metrics
    """
    if len(nav_df) == 0:
        return {}
    
    final_nav = nav_df['nav'].iloc[-1]
    
    # Returns
    total_return = (final_nav - initial_nav) / initial_nav
    
    # Calculate daily returns
    nav_df = nav_df.copy()
    nav_df['daily_return'] = nav_df['nav'].pct_change()
    
    # Time in market
    days_in_market = len(nav_df)
    years_in_market = days_in_market / 252  # Trading days per year
    
    # CAGR
    if years_in_market > 0:
        cagr = (final_nav / initial_nav) ** (1 / years_in_market) - 1
    else:
        cagr = 0
    
    # Volatility (annualized)
    daily_vol = nav_df['daily_return'].std()
    annual_vol = daily_vol * np.sqrt(252)
    
    # Sharpe Ratio (assuming risk-free rate = 5%)
    risk_free_rate = 0.05
    excess_return = cagr - risk_free_rate
    sharpe_ratio = excess_return / annual_vol if annual_vol > 0 else 0
    
    # Drawdown analysis
    nav_df['peak'] = nav_df['nav'].cummax()
    nav_df['drawdown'] = (nav_df['nav'] - nav_df['peak']) / nav_df['peak']
    max_drawdown = nav_df['drawdown'].min()
    
    # Find drawdown periods
    drawdown_days = (nav_df['drawdown'] < 0).sum()
    
    # Calmar Ratio
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Trade statistics
    if len(trades_df) > 0:
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        total_trades = len(trades_df)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        avg_win_pct = winning_trades['pnl_pct'].mean() * 100 if len(winning_trades) > 0 else 0
        avg_loss_pct = losing_trades['pnl_pct'].mean() * 100 if len(losing_trades) > 0 else 0
        
        max_win_pct = winning_trades['pnl_pct'].max() * 100 if len(winning_trades) > 0 else 0
        max_loss_pct = losing_trades['pnl_pct'].min() * 100 if len(losing_trades) > 0 else 0
        
        total_pnl = trades_df['pnl'].sum()
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Average holding period
        trades_df = trades_df.copy()
        trades_df['holding_days'] = (trades_df['sell_date'] - trades_df['buy_date']).dt.days
        avg_holding_days = trades_df['holding_days'].mean()
    else:
        total_trades = win_count = loss_count = 0
        win_rate = avg_win_pct = avg_loss_pct = 0
        max_win_pct = max_loss_pct = 0
        total_pnl = gross_profit = gross_loss = 0
        profit_factor = 0
        avg_holding_days = 0
    
    return {
        # Portfolio metrics
        'initial_nav': initial_nav,
        'final_nav': final_nav,
        'total_return_pct': total_return * 100,
        'cagr_pct': cagr * 100,
        'annual_volatility_pct': annual_vol * 100,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_drawdown * 100,
        'calmar_ratio': calmar_ratio,
        
        # Trade metrics
        'total_trades': total_trades,
        'winning_trades': win_count,
        'losing_trades': loss_count,
        'win_rate_pct': win_rate * 100,
        'avg_win_pct': avg_win_pct,
        'avg_loss_pct': avg_loss_pct,
        'max_win_pct': max_win_pct,
        'max_loss_pct': max_loss_pct,
        'profit_factor': profit_factor,
        'avg_holding_days': avg_holding_days,
        
        # P&L metrics
        'total_pnl': total_pnl,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        
        # Time metrics
        'trading_days': days_in_market,
        'drawdown_days': drawdown_days,
    }


def print_performance_report(metrics: Dict):
    """
    Print a formatted performance report.
    
    Args:
        metrics: Dictionary of performance metrics
    """
    print("\n" + "=" * 60)
    print("           VSA STRATEGY BACKTEST REPORT")
    print("=" * 60)
    
    print("\n📊 PORTFOLIO PERFORMANCE")
    print("-" * 40)
    print(f"  Initial NAV:        {metrics.get('initial_nav', 0):>15,.0f}")
    print(f"  Final NAV:          {metrics.get('final_nav', 0):>15,.0f}")
    print(f"  Total Return:       {metrics.get('total_return_pct', 0):>14.2f}%")
    print(f"  CAGR:               {metrics.get('cagr_pct', 0):>14.2f}%")
    print(f"  Annual Volatility:  {metrics.get('annual_volatility_pct', 0):>14.2f}%")
    print(f"  Sharpe Ratio:       {metrics.get('sharpe_ratio', 0):>15.2f}")
    print(f"  Max Drawdown:       {metrics.get('max_drawdown_pct', 0):>14.2f}%")
    print(f"  Calmar Ratio:       {metrics.get('calmar_ratio', 0):>15.2f}")
    
    print("\n📈 TRADE STATISTICS")
    print("-" * 40)
    print(f"  Total Trades:       {metrics.get('total_trades', 0):>15}")
    print(f"  Winning Trades:     {metrics.get('winning_trades', 0):>15}")
    print(f"  Losing Trades:      {metrics.get('losing_trades', 0):>15}")
    print(f"  Win Rate:           {metrics.get('win_rate_pct', 0):>14.2f}%")
    print(f"  Avg Win:            {metrics.get('avg_win_pct', 0):>14.2f}%")
    print(f"  Avg Loss:           {metrics.get('avg_loss_pct', 0):>14.2f}%")
    print(f"  Max Win:            {metrics.get('max_win_pct', 0):>14.2f}%")
    print(f"  Max Loss:           {metrics.get('max_loss_pct', 0):>14.2f}%")
    print(f"  Profit Factor:      {metrics.get('profit_factor', 0):>15.2f}")
    print(f"  Avg Holding Days:   {metrics.get('avg_holding_days', 0):>15.1f}")
    
    print("\n💰 PROFIT/LOSS")
    print("-" * 40)
    print(f"  Total P&L:          {metrics.get('total_pnl', 0):>15,.0f}")
    print(f"  Gross Profit:       {metrics.get('gross_profit', 0):>15,.0f}")
    print(f"  Gross Loss:         {metrics.get('gross_loss', 0):>15,.0f}")
    
    print("\n" + "=" * 60)


def analyze_trades_by_exit_reason(trades_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze trade performance by exit reason.
    
    Args:
        trades_df: DataFrame with trade history
        
    Returns:
        DataFrame with statistics grouped by exit reason
    """
    if len(trades_df) == 0:
        return pd.DataFrame()
    
    summary = trades_df.groupby('exit_reason').agg({
        'pnl': ['count', 'sum', 'mean'],
        'pnl_pct': 'mean'
    }).round(2)
    
    summary.columns = ['Count', 'Total P&L', 'Avg P&L', 'Avg P&L %']
    summary['Avg P&L %'] = (summary['Avg P&L %'] * 100).round(2)
    
    return summary.sort_values('Count', ascending=False)


def analyze_trades_by_stock(trades_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze trade performance by stock.
    
    Args:
        trades_df: DataFrame with trade history
        
    Returns:
        DataFrame with statistics grouped by stock
    """
    if len(trades_df) == 0:
        return pd.DataFrame()
    
    summary = trades_df.groupby('stock_code').agg({
        'pnl': ['count', 'sum', 'mean'],
        'pnl_pct': 'mean'
    }).round(2)
    
    summary.columns = ['Trades', 'Total P&L', 'Avg P&L', 'Avg P&L %']
    summary['Avg P&L %'] = (summary['Avg P&L %'] * 100).round(2)
    
    return summary.sort_values('Total P&L', ascending=False)
