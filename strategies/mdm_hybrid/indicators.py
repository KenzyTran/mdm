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
    def add_atr_column(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Average True Range column.

        True Range = max(H-L, |H-prev_C|, |L-prev_C|)
        ATR = rolling mean of True Range over period.

        Args:
            df: DataFrame with 'high', 'low', 'close' columns.
            period: ATR lookback period (default 14).

        Returns:
            DataFrame with 'atr' and 'true_range' columns added.
        """
        df = df.copy()
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['true_range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = df['true_range'].rolling(window=period, min_periods=1).mean()
        return df

    @staticmethod
    def add_violation_threshold_column(
        df: pd.DataFrame,
        k: float = 0.5,
        period: int = 14,
    ) -> pd.DataFrame:
        """Add ATR buffer violation threshold column for MA50 breakdown filter.

        Computes: violation_threshold = MA50 - k * ATR_N

        Uses column names 'atr_buf' and 'true_range_buf' (not 'atr'/'true_range')
        to avoid overwriting the stop-loss ATR columns.

        Args:
            df: DataFrame with 'high', 'low', 'close', 'ma50' columns.
            k: ATR multiplier (buffer depth). Default 0.5.
            period: ATR lookback period. Default 14.

        Returns:
            DataFrame with 'violation_threshold' column added.
            Intermediate columns 'atr_buf' and 'true_range_buf' are also present.
        """
        df = df.copy()
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['true_range_buf'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_buf'] = df['true_range_buf'].rolling(window=period, min_periods=1).mean()
        df['violation_threshold'] = df['ma50'] - k * df['atr_buf']
        return df

    @staticmethod
    def add_volume_ma_column(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """Add volume moving average column (per D-03, Phase 39).

        Used by refined Distribution Day rule to compare current volume
        against an N-day moving average baseline.

        Args:
            df: DataFrame with 'volume' column.
            period: MA lookback period (default 20).

        Returns:
            DataFrame with 'vol_ma20' column added.
        """
        df = df.copy()
        df['vol_ma20'] = df['volume'].rolling(window=period, min_periods=1).mean()
        return df

    @staticmethod
    def add_volume_percentile_column(
        df: pd.DataFrame, lookback: int = 50, percentile: int = 5
    ) -> pd.DataFrame:
        """Add volume percentile rank boolean column (per D-03, Phase 39).

        For each row, checks whether the volume is in the top ``percentile``%
        of the last ``lookback`` trading days. Used by the refined Distribution
        Day rule to detect "small drop + extreme volume" scenarios.

        Uses ``min_periods=1`` (consistent with all other rolling indicators
        in this module — see Pitfall 2 in 39-RESEARCH.md). Early rows use
        whatever data is available rather than producing NaN.

        Args:
            df: DataFrame with 'volume' column.
            lookback: Rolling window size (default 50).
            percentile: Top N percent threshold (default 5 = top 5%).

        Returns:
            DataFrame with 'vol_top_pct' boolean column added.
        """
        df = df.copy()
        # Top 5% means >= 95th percentile of the rolling window
        threshold_quantile = 1.0 - (percentile / 100.0)
        rolling_threshold = df['volume'].rolling(
            window=lookback, min_periods=1
        ).quantile(threshold_quantile)
        df['vol_top_pct'] = (df['volume'] >= rolling_threshold).astype(bool)
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
