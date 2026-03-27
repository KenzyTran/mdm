"""
VSA Trading Engine
Main backtest engine that orchestrates the strategy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .data_loader import load_vn30_data, preprocess_stock_data, get_all_trading_dates
from .indicators import calculate_indicators_for_all
from .signals import scan_for_buy_signals, detect_distribution_signal
from .position_manager import PositionManager
from .stop_loss import check_all_stops
from .trailing_stop import check_trailing_stop
from .config import INITIAL_NAV


class VSAEngine:
    """Main backtest engine for VSA strategy."""
    
    def __init__(self, initial_nav: float = None, 
                 start_date: str = None, end_date: str = None):
        """
        Initialize the VSA Engine.
        
        Args:
            initial_nav: Initial portfolio value
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
        """
        self.initial_nav = initial_nav or INITIAL_NAV
        self.start_date = pd.to_datetime(start_date) if start_date else None
        self.end_date = pd.to_datetime(end_date) if end_date else None
        
        self.raw_data = None
        self.stock_data = None
        self.trading_dates = None
        self.position_manager = None
        self.is_loaded = False
    
    def load_data(self, filepath: str = None):
        """
        Load and preprocess data.
        
        Args:
            filepath: Optional path to CSV file
        """
        # Load raw data
        self.raw_data = load_vn30_data(filepath)
        
        # Apply date filters
        if self.start_date:
            self.raw_data = self.raw_data[self.raw_data['tradingdate'] >= self.start_date]
        if self.end_date:
            self.raw_data = self.raw_data[self.raw_data['tradingdate'] <= self.end_date]
        
        # Get trading dates
        self.trading_dates = get_all_trading_dates(self.raw_data)
        
        # Preprocess and calculate indicators
        self.stock_data = preprocess_stock_data(self.raw_data)
        self.stock_data = calculate_indicators_for_all(self.stock_data)
        
        # Initialize position manager
        self.position_manager = PositionManager(initial_nav=self.initial_nav)
        
        self.is_loaded = True
        
        print(f"Loaded data for {len(self.stock_data)} stocks")
        print(f"Date range: {self.trading_dates[0].date()} to {self.trading_dates[-1].date()}")
        print(f"Total trading days: {len(self.trading_dates)}")
    
    def get_current_prices(self, date: pd.Timestamp) -> Dict[str, float]:
        """Get close prices for all stocks on a given date."""
        prices = {}
        for stock_code, df in self.stock_data.items():
            mask = df['tradingdate'] == date
            if mask.any():
                prices[stock_code] = df[mask].iloc[0]['closeprice']
        return prices
    
    def get_stock_row(self, stock_code: str, date: pd.Timestamp) -> Optional[pd.Series]:
        """Get data for a stock on a specific date."""
        if stock_code not in self.stock_data:
            return None
        df = self.stock_data[stock_code]
        mask = df['tradingdate'] == date
        if mask.any():
            return df[mask].iloc[0]
        return None
    
    def get_stock_idx(self, stock_code: str, date: pd.Timestamp) -> int:
        """Get index of a date in the stock's DataFrame."""
        if stock_code not in self.stock_data:
            return -1
        df = self.stock_data[stock_code]
        mask = df['tradingdate'] == date
        if mask.any():
            return df.index.get_loc(df[mask].index[0])
        return -1
    
    def update_ma10_tracking(self, date: pd.Timestamp):
        """
        Update MA10 violation tracking for all open positions.
        Called daily to track if any position closes below MA10 during first 7 weeks.
        
        Args:
            date: Current trading date
        """
        for stock_code in self.position_manager.get_positions_to_check():
            if stock_code not in self.position_manager.positions:
                continue
            
            row = self.get_stock_row(stock_code, date)
            if row is None:
                continue
            
            current_close = row['closeprice']
            ma10 = row.get('ma10')
            
            self.position_manager.update_ma10_tracking(stock_code, current_close, ma10)
    
    def process_exits(self, date: pd.Timestamp):
        """
        Process all exit conditions for open positions.
        
        Args:
            date: Current trading date
        """
        positions_to_check = self.position_manager.get_positions_to_check()
        
        for stock_code in positions_to_check.copy():
            if stock_code not in self.position_manager.positions:
                continue  # Already closed
            
            position = self.position_manager.positions[stock_code]
            row = self.get_stock_row(stock_code, date)
            
            if row is None:
                continue  # No data for this date
            
            current_close = row['closeprice']
            
            # 1. Check forced exit (distribution signal)
            df = self.stock_data[stock_code]
            idx = self.get_stock_idx(stock_code, date)
            if idx > 0:
                prev_row = df.iloc[idx - 1]
                if detect_distribution_signal(
                    current_close, prev_row['closeprice'],
                    row['totalvol'], row['mav20']
                ):
                    self.position_manager.close_position(
                        stock_code, date, current_close,
                        exit_reason='Distribution Signal'
                    )
                    continue
            
            # 2. Check stop losses (7%, spike low)
            stop_result = check_all_stops(
                position.buy_price, position.spike_low, current_close
            )
            if stop_result['triggered']:
                self.position_manager.close_position(
                    stock_code, date, current_close,
                    exit_reason=stop_result['stop_type']
                )
                continue
            
            # 3. Check trailing stop (MA10/MA50) - with updated logic
            trailing_result = check_trailing_stop(
                df, idx, position.days_held,
                trailing_stop_ma=position.trailing_stop_ma,
                violated_ma10=position.violated_ma10
            )
            if trailing_result['triggered']:
                self.position_manager.close_position(
                    stock_code, date, current_close,
                    exit_reason=trailing_result['stop_type']
                )
                continue
            
            # 4. Check take profit (20% -> sell 50%)
            self.position_manager.check_take_profit(stock_code, current_close, date)
    
    def process_entries(self, date: pd.Timestamp):
        """
        Process buy signals and open new positions.
        
        Args:
            date: Current trading date
        """
        if not self.position_manager.can_open_position():
            return
        
        # Scan for buy signals
        signals = scan_for_buy_signals(self.stock_data, date)
        
        for signal in signals:
            if not self.position_manager.can_open_position():
                break
            
            stock_code = signal['stock_code']
            
            # Skip if already holding this stock
            if stock_code in self.position_manager.positions:
                continue
            
            # Open position
            self.position_manager.open_position(
                stock_code=stock_code,
                buy_date=date,
                buy_price=signal['buy_price'],
                spike_high=signal['spike_high'],
                spike_low=signal['spike_low']
            )
    
    def run(self) -> pd.DataFrame:
        """
        Run the backtest.
        
        Returns:
            DataFrame with NAV history
        """
        if not self.is_loaded:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        print(f"\nRunning backtest from {self.trading_dates[0].date()} to {self.trading_dates[-1].date()}")
        print(f"Initial NAV: {self.initial_nav:,.0f}")
        print("-" * 50)
        
        for i, date in enumerate(self.trading_dates):
            # Update days held for existing positions
            self.position_manager.update_days_held()
            
            # Update MA10 tracking for first 7 weeks
            self.update_ma10_tracking(date)
            
            # Process exits first
            self.process_exits(date)
            
            # Process entries
            self.process_entries(date)
            
            # Update NAV
            current_prices = self.get_current_prices(date)
            self.position_manager.update_nav(date, current_prices)
            
            # Progress indicator
            if (i + 1) % 500 == 0 or i == len(self.trading_dates) - 1:
                print(f"Processed {i+1}/{len(self.trading_dates)} days, "
                      f"NAV: {self.position_manager.nav:,.0f}, "
                      f"Positions: {len(self.position_manager.positions)}")
        
        print("-" * 50)
        print(f"Final NAV: {self.position_manager.nav:,.0f}")
        print(f"Total trades: {len(self.position_manager.trades)}")
        
        return self.position_manager.get_nav_df()
    
    def get_trades(self) -> pd.DataFrame:
        """Get trade history."""
        return self.position_manager.get_trades_df()
    
    def get_nav_history(self) -> pd.DataFrame:
        """Get NAV history."""
        return self.position_manager.get_nav_df()
    
    def get_summary(self) -> dict:
        """Get backtest summary."""
        nav_df = self.position_manager.get_nav_df()
        trades_df = self.position_manager.get_trades_df()
        
        if len(nav_df) == 0:
            return {}
        
        final_nav = nav_df['nav'].iloc[-1]
        total_return = (final_nav - self.initial_nav) / self.initial_nav
        
        # Calculate drawdown
        nav_df['peak'] = nav_df['nav'].cummax()
        nav_df['drawdown'] = (nav_df['nav'] - nav_df['peak']) / nav_df['peak']
        max_drawdown = nav_df['drawdown'].min()
        
        # Trade statistics
        if len(trades_df) > 0:
            winning_trades = trades_df[trades_df['pnl'] > 0]
            win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0
            avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
            
            losing_trades = trades_df[trades_df['pnl'] <= 0]
            avg_loss = abs(losing_trades['pnl_pct'].mean()) if len(losing_trades) > 0 else 0
            
            profit_factor = (winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum())
                           if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else 0)
        else:
            win_rate = avg_win = avg_loss = profit_factor = 0
        
        # Calculate CAGR
        days = (nav_df['date'].iloc[-1] - nav_df['date'].iloc[0]).days
        years = days / 365.25
        cagr = ((final_nav / self.initial_nav) ** (1 / years) - 1) if years > 0 else 0
        
        return {
            'initial_nav': self.initial_nav,
            'final_nav': final_nav,
            'total_return': total_return,
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
