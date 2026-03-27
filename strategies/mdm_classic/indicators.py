"""
Indicators Module
Calculate technical indicators for MDM system.
"""

import pandas as pd
import numpy as np


class Indicators:
    """Calculate technical indicators for price data."""
    
    @staticmethod
    def price_location(high: float, low: float, close: float) -> float:
        """
        Calculate Price Location (P_loc).
        
        Formula: P_loc = (C - L) / (H - L)
        
        This indicates where the close price is within the daily range.
        - P_loc = 1.0: Close at high (bullish)
        - P_loc = 0.5: Close at midpoint
        - P_loc = 0.0: Close at low (bearish)
        
        Args:
            high: Highest price
            low: Lowest price
            close: Close price
            
        Returns:
            Price location value between 0 and 1
        """
        # Handle edge case: flat candle (H == L)
        if high == low:
            return 0.5  # Default to midpoint
        
        p_loc = (close - low) / (high - low)
        return max(0.0, min(1.0, p_loc))  # Clamp to [0, 1]
    
    @staticmethod
    def add_price_location_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add price location column to DataFrame.
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            
        Returns:
            DataFrame with 'p_loc' column added
        """
        df = df.copy()
        df['p_loc'] = df.apply(
            lambda row: Indicators.price_location(row['high'], row['low'], row['close']),
            axis=1
        )
        return df
    
    @staticmethod
    def add_prev_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add previous day's close and volume columns.
        
        Args:
            df: DataFrame with 'close' and 'volume' columns
            
        Returns:
            DataFrame with 'prev_close' and 'prev_volume' columns added
        """
        df = df.copy()
        df['prev_close'] = df['close'].shift(1)
        df['prev_volume'] = df['volume'].shift(1)
        return df
    
    @staticmethod
    def price_change_pct(current: float, previous: float) -> float:
        """
        Calculate percentage change.
        
        Args:
            current: Current price
            previous: Previous price
            
        Returns:
            Percentage change (e.g., 0.01 = 1%)
        """
        if previous == 0:
            return 0.0
        return (current - previous) / previous
    
    @staticmethod
    def add_change_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add price and volume change columns.
        
        Args:
            df: DataFrame with 'close', 'volume', 'prev_close', 'prev_volume' columns
            
        Returns:
            DataFrame with change columns added
        """
        df = df.copy()
        
        # Price change percentage
        df['price_change_pct'] = (df['close'] - df['prev_close']) / df['prev_close']
        
        # Price increased?
        df['price_up'] = df['close'] > df['prev_close']
        
        # Volume increased?
        df['volume_up'] = df['volume'] > df['prev_volume']
        
        return df
    
    @staticmethod
    def add_ma50_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add 50-day Moving Average column.
        
        Args:
            df: DataFrame with 'close' column
            
        Returns:
            DataFrame with 'ma50' column added
        """
        df = df.copy()
        df['ma50'] = df['close'].rolling(window=50, min_periods=1).mean()
        return df
    
    @staticmethod
    def add_ma10_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add 10-day Moving Average column.
        
        Args:
            df: DataFrame with 'close' column
            
        Returns:
            DataFrame with 'ma10' column added
        """
        df = df.copy()
        df['ma10'] = df['close'].rolling(window=10, min_periods=1).mean()
        return df
    
    @staticmethod
    def add_ma50_volume_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add 50-day Moving Average Volume column.
        
        Args:
            df: DataFrame with 'volume' column
            
        Returns:
            DataFrame with 'vol_ma50' column added
        """
        df = df.copy()
        df['vol_ma50'] = df['volume'].rolling(window=50, min_periods=1).mean()
        return df
    
    @staticmethod
    def calculate_rolling_high(df: pd.DataFrame, window: int = 252) -> pd.DataFrame:
        """
        Calculate rolling highest high for peak detection.
        
        Args:
            df: DataFrame with 'high' column
            window: Rolling window size
            
        Returns:
            DataFrame with 'rolling_high' column
        """
        df = df.copy()
        df['rolling_high'] = df['high'].rolling(window=window, min_periods=1).max()
        return df

    @staticmethod
    def add_52week_high_column(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add 52-week high column (approx 252 trading days).
        
        Args:
            df: DataFrame with 'high' column
            
        Returns:
            DataFrame with 'high_52w' column added
        """
        df = df.copy()
        # Use shift(1) to get the high of previous 252 days NOT including today
        # Because we want to check if TODAY breaks the previous high
        df['high_52w'] = df['high'].rolling(window=252, min_periods=1).max().shift(1)
        return df
    
    @staticmethod
    def drawdown_from_peak(current_close: float, peak_high: float) -> float:
        """
        Calculate drawdown from peak.
        
        Args:
            current_close: Current close price
            peak_high: Recent peak high
            
        Returns:
            Drawdown percentage (negative value)
        """
        if peak_high == 0:
            return 0.0
        return (current_close - peak_high) / peak_high
