"""
MDM Engine Module
Main engine combining all components.
"""

import pandas as pd
from typing import Optional

from .data_loader import DataLoader
from .indicators import Indicators
from .distribution_day import DistributionDayCounter
from .rally_attempt import RallyAttemptTracker
from .ftd_signal import FTDSignalDetector
from .stop_loss import StopLossChecker
from .position_manager import PositionManager, MarketState
from .config import MDMConfig


class MDMEngine:
    """
    Market Direction Model Engine.
    
    Combines all components to run the MDM strategy:
    1. Load and preprocess data
    2. Calculate indicators
    3. Detect rally attempts and FTD signals
    4. Manage positions with state machine
    5. Track trades and performance
    """
    
    def __init__(self, config: MDMConfig = None):
        """Initialize MDM Engine with all components."""
        self.config = config if config else MDMConfig()
        
        self.data_loader = DataLoader()
        self.dd_counter = DistributionDayCounter(self.config)
        self.rally_tracker = RallyAttemptTracker(self.config)
        self.ftd_detector = FTDSignalDetector(self.config)
        self.stop_loss_checker = StopLossChecker(self.config)
        self.position_manager = PositionManager()  # No config needed yet for simple state machine
        
        self.results: Optional[pd.DataFrame] = None
    
    def reset(self):
        """Reset all components."""
        self.dd_counter.reset()
        self.rally_tracker.full_reset()
        self.ftd_detector.reset()
        self.position_manager.reset()
        self.results = None
    
    def load_data(
        self, 
        file_path: str = 'data/vnindex_price.csv',
        start_date: str = '2016-01-16',
        end_date: str = '2026-01-16'
    ) -> pd.DataFrame:
        """
        Load data from CSV.
        
        Args:
            file_path: Path to CSV file
            start_date: Start date
            end_date: End date
            
        Returns:
            Loaded DataFrame
        """
        self.data_loader = DataLoader(file_path)
        return self.data_loader.load(start_date, end_date)
    
    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run MDM strategy on data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with signals and states
        """
        self.reset()
        
        # Prepare data with indicators
        df = df.copy()
        df = Indicators.add_price_location_column(df)
        df = Indicators.add_prev_columns(df)
        df = Indicators.add_change_columns(df)
        df = Indicators.add_ma50_column(df)
        df = Indicators.add_ma10_column(df)
        df = Indicators.add_ma50_volume_column(df)
        df = Indicators.calculate_rolling_high(df)
        df = Indicators.add_52week_high_column(df)
        df['prev_ma50'] = df['ma50'].shift(1)
        df['prev_ma10'] = df['ma10'].shift(1)
        
        # Initialize result columns
        df['in_correction'] = False
        df['rally_day'] = 0
        df['is_day1'] = False
        df['is_ftd'] = False
        df['is_ma50_breakout'] = False
        df['is_dd'] = False
        df['dd_type'] = 0
        df['dd_count'] = 0
        df['state'] = MarketState.CASH.value
        df['action'] = ''
        df['buy_price'] = 0.0
        df['short_price'] = 0.0
        df['drawdown_pct'] = 0.0
        
        all_dates = df['date'].tolist()
        
        # Process each day
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # Skip first row (no previous data)
            if idx == 0:
                continue
            
            date = row['date']
            high = row['high']
            low = row['low']
            close = row['close']
            prev_close = row['prev_close']
            p_loc = row['p_loc']
            price_change_pct = row['price_change_pct']
            volume_up = row['volume_up']
            
            current_state = self.position_manager.get_state()
            buy_price = self.position_manager.get_buy_price()
            buy_day_low = self.position_manager.get_buy_day_low()
            
            # 1. Track rally attempt (when in CASH or SHORT - need FTD to cover short)
            in_correction = False
            rally_day = 0
            is_day1 = False
            
            if current_state in [MarketState.CASH, MarketState.SHORT]:
                in_correction, rally_day, is_day1 = self.rally_tracker.process_day(
                    date, high, low, close, prev_close, p_loc
                )
            
            # 2. Detect FTD (only when in CASH and in correction)
            is_ftd = False
            is_ma50_breakout = False
            ftd_price = 0.0
            signal_type = ""
            
            # Calculate drawdown from peak
            rolling_high = row['rolling_high'] if 'rolling_high' in row else close
            drawdown_pct = Indicators.drawdown_from_peak(close, rolling_high)
            
            if current_state == MarketState.CASH:
                # Check traditional FTD
                if rally_day >= 4:
                    is_ftd, signal = self.ftd_detector.check_ftd(
                        rally_day, price_change_pct, volume_up, date, close
                    )
                    if is_ftd and signal:
                        ftd_price = signal.price
                        self.dd_counter.reset()
                
                # Check MA50 breakout signal (alternative buy signal)
                if not is_ftd:
                    ma50 = row['ma50'] if 'ma50' in row else None
                    prev_ma50 = row['prev_ma50'] if 'prev_ma50' in row else None
                    if ma50 is not None and prev_ma50 is not None:
                        is_ma50_breakout, signal = self.ftd_detector.check_ma50_breakout(
                            close, prev_close, ma50, prev_ma50, volume_up, drawdown_pct, date
                        )
                        if is_ma50_breakout and signal:
                            is_ftd = True  # Treat as FTD for position management
                            ftd_price = signal.price
                            signal_type = signal.signal_type
                            self.dd_counter.reset()
                
                # Check 52-Week Breakout signal
                if not is_ftd:
                    high_52w = row['high_52w'] if 'high_52w' in row else None
                    is_52w, signal = self.ftd_detector.check_52week_breakout(
                        close, high_52w, date
                    )
                    if is_52w and signal:
                        is_ftd = True
                        ftd_price = signal.price
                        signal_type = signal.signal_type
                        self.dd_counter.reset()
            
            # Check FTD or MA50 breakout when in SHORT state (to cover)
            if current_state == MarketState.SHORT:
                # Check traditional FTD
                if rally_day >= 4:
                    is_ftd, signal = self.ftd_detector.check_ftd(
                        rally_day, price_change_pct, volume_up, date, close
                    )
                    if is_ftd and signal:
                        ftd_price = signal.price
                        self.dd_counter.reset()
                
                # Check MA50 breakout for cover signal
                if not is_ftd:
                    ma50 = row['ma50'] if 'ma50' in row else None
                    prev_ma50 = row['prev_ma50'] if 'prev_ma50' in row else None
                    if ma50 is not None and prev_ma50 is not None:
                        # Check volume condition: V > V_prev OR V > 1.1 * MA50_Vol
                        current_volume = row['volume']
                        vol_ma50 = row['vol_ma50'] if 'vol_ma50' in row else 0
                        vol_condition = volume_up or (current_volume > 1.1 * vol_ma50)
                        
                        # Simpler check: just price crossing above MA50 with volume logic
                        if prev_close <= prev_ma50 and close > ma50 and vol_condition:
                            is_ftd = True  # Treat as cover signal
                            is_ma50_breakout = True
                            ftd_price = close
                            self.dd_counter.reset()
            
            # 3. Count distribution days (only when HOLDING or WAITING_SELL)
            is_dd = False
            dd_type = 0
            dd_count = 0
            
            if current_state in [MarketState.HOLDING, MarketState.WAITING_SELL]:
                is_dd, dd_type = self.dd_counter.check_distribution_day(
                    date, price_change_pct, volume_up, p_loc
                )
                dd_count = self.dd_counter.get_dd_count_in_window(date, all_dates)
            
            # 4. Check stop loss
            ma50 = row['ma50'] if 'ma50' in row else None
            prev_ma50_val = row['prev_ma50'] if 'prev_ma50' in row else None
            current_volume = row['volume']
            prev_volume = row['prev_volume']
            signal_type_held = self.position_manager.get_signal_type()
            stop_loss_result = self.stop_loss_checker.check(
                close, buy_price, buy_day_low,
                ma50=ma50, prev_close=prev_close, prev_ma50=prev_ma50_val,
                current_volume=current_volume, prev_volume=prev_volume,
                signal_type=signal_type_held
            )
            
            # 5. Update position
            ma10 = row['ma10'] if 'ma10' in row else None
            prev_ma10 = row['prev_ma10'] if 'prev_ma10' in row else None
            
            new_state, action = self.position_manager.process_day(
                date=date,
                high=high,
                low=low,
                close=close,
                is_ftd=is_ftd,
                ftd_price=ftd_price,
                dd_count=dd_count,
                is_dd=is_dd,
                stop_loss_triggered=stop_loss_result.triggered,
                stop_loss_reason=stop_loss_result.reason,
                signal_type=signal_type,
                ma10=ma10,
                prev_ma10=prev_ma10,
                prev_close=prev_close,
                volume_up=volume_up
            )
            
            # If FTD triggered, reset rally tracker
            if is_ftd:
                self.rally_tracker.full_reset()
            
            # Update DataFrame
            df.at[idx, 'in_correction'] = in_correction
            df.at[idx, 'rally_day'] = rally_day
            df.at[idx, 'is_day1'] = is_day1
            df.at[idx, 'is_ftd'] = is_ftd
            df.at[idx, 'is_ma50_breakout'] = is_ma50_breakout
            df.at[idx, 'is_dd'] = is_dd
            df.at[idx, 'dd_type'] = dd_type
            df.at[idx, 'dd_count'] = dd_count
            df.at[idx, 'state'] = new_state.value
            df.at[idx, 'action'] = action
            df.at[idx, 'buy_price'] = self.position_manager.get_buy_price()
            df.at[idx, 'short_price'] = self.position_manager.get_short_price()
            df.at[idx, 'drawdown_pct'] = drawdown_pct
        
        self.results = df
        return df
    
    def get_trades(self) -> list:
        """Get list of all trades."""
        return self.position_manager.get_trades()
    
    def get_trade_df(self) -> pd.DataFrame:
        """Get trades as DataFrame."""
        trades = self.get_trades()
        if not trades:
            return pd.DataFrame()
        return pd.DataFrame(trades)
    
    def get_signals(self) -> pd.DataFrame:
        """Get DataFrame with only signal rows."""
        if self.results is None:
            return pd.DataFrame()
        
        signals = self.results[
            (self.results['is_ftd']) | 
            (self.results['is_day1']) | 
            (self.results['action'] != '')
        ]
        return signals[['date', 'close', 'state', 'action', 'rally_day', 'dd_count']]
    
    def summary(self) -> dict:
        """Get summary statistics."""
        trades = self.get_trades()
        
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        short_trades = [t for t in trades if t['type'] == 'SHORT']
        cover_trades = [t for t in trades if t['type'] == 'COVER']
        
        # Long trades
        long_wins = [t for t in sell_trades if t.get('pnl', 0) > 0]
        long_losses = [t for t in sell_trades if t.get('pnl', 0) <= 0]
        long_pnl = sum(t.get('pnl', 0) for t in sell_trades)
        
        # Short trades
        short_wins = [t for t in cover_trades if t.get('pnl', 0) > 0]
        short_losses = [t for t in cover_trades if t.get('pnl', 0) <= 0]
        short_pnl = sum(t.get('pnl', 0) for t in cover_trades)
        
        total_completed = len(sell_trades) + len(cover_trades)
        total_wins = len(long_wins) + len(short_wins)
        total_pnl = long_pnl + short_pnl
        
        return {
            'total_long_trades': len(buy_trades),
            'completed_long_trades': len(sell_trades),
            'long_wins': len(long_wins),
            'long_losses': len(long_losses),
            'long_pnl': long_pnl,
            'total_short_trades': len(short_trades),
            'completed_short_trades': len(cover_trades),
            'short_wins': len(short_wins),
            'short_losses': len(short_losses),
            'short_pnl': short_pnl,
            'total_completed': total_completed,
            'total_wins': total_wins,
            'win_rate': total_wins / total_completed if total_completed else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / total_completed if total_completed else 0
        }
