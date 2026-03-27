"""
Technical Indicators Module
Calculates MAV20, MA10, MA50 and volume ratios
"""

import pandas as pd
import numpy as np


def calculate_mav20(volume_series: pd.Series) -> pd.Series:
    """
    Calculate 20-day Simple Moving Average of Volume.
    
    MAV20 = Sum(V_i for i=1 to 20) / 20
    
    Args:
        volume_series: Series of volume data
        
    Returns:
        Series with MAV20 values
    """
    return volume_series.rolling(window=20, min_periods=20).mean()


def calculate_ma10(close_series: pd.Series) -> pd.Series:
    """
    Calculate 10-day Simple Moving Average of Close Price.
    
    Args:
        close_series: Series of closing prices
        
    Returns:
        Series with MA10 values
    """
    return close_series.rolling(window=10, min_periods=10).mean()


def calculate_ma50(close_series: pd.Series) -> pd.Series:
    """
    Calculate 50-day Simple Moving Average of Close Price.
    
    Args:
        close_series: Series of closing prices
        
    Returns:
        Series with MA50 values
    """
    return close_series.rolling(window=50, min_periods=50).mean()


def calculate_volume_ratio(volume: float, mav20: float) -> float:
    """
    Calculate the volume ratio V / MAV20.
    
    Args:
        volume: Current volume
        mav20: 20-day average volume
        
    Returns:
        Volume ratio, or 0 if mav20 is invalid
    """
    if pd.isna(mav20) or mav20 <= 0:
        return 0.0
    return volume / mav20


def add_indicators_to_stock(stock_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to a stock's DataFrame.
    
    Args:
        stock_df: DataFrame with OHLCV data for a single stock
        
    Returns:
        DataFrame with added indicator columns
    """
    df = stock_df.copy()
    
    # Calculate moving averages
    df['mav20'] = calculate_mav20(df['totalvol'])
    df['ma10'] = calculate_ma10(df['closeprice'])
    df['ma50'] = calculate_ma50(df['closeprice'])
    
    # Calculate volume ratio
    df['volume_ratio'] = df.apply(
        lambda row: calculate_volume_ratio(row['totalvol'], row['mav20']),
        axis=1
    )
    
    # Mark volume spike days (V >= 4x MAV20)
    from .config import VOLUME_SPIKE_MULTIPLIER
    df['is_volume_spike'] = df['volume_ratio'] >= VOLUME_SPIKE_MULTIPLIER
    
    return df


def calculate_indicators_for_all(stock_data: dict) -> dict:
    """
    Calculate indicators for all stocks in the data dictionary.
    
    Args:
        stock_data: Dictionary mapping stock_code -> DataFrame
        
    Returns:
        Updated dictionary with indicators added
    """
    result = {}
    for stock_code, df in stock_data.items():
        result[stock_code] = add_indicators_to_stock(df)
    return result
