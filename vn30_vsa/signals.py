"""
Signal Detection Module
Handles volume spike detection, buy signals, and distribution signals
"""

import pandas as pd
import numpy as np
from .config import VOLUME_SPIKE_MULTIPLIER, LOOKBACK_DAYS


def detect_volume_spike(volume: float, mav20: float, multiplier: float = None) -> bool:
    """
    Check if current volume is a spike (V >= multiplier * MAV20).
    
    Args:
        volume: Current volume
        mav20: 20-day average volume
        multiplier: Volume spike multiplier (default from config)
        
    Returns:
        True if volume spike detected
    """
    if multiplier is None:
        multiplier = VOLUME_SPIKE_MULTIPLIER
    
    if pd.isna(mav20) or mav20 <= 0:
        return False
    
    return volume >= multiplier * mav20


def find_spike_in_lookback(stock_df: pd.DataFrame, current_idx: int, lookback: int = None) -> dict:
    """
    Find volume spike in the lookback window (t-1 to t-lookback).
    
    Args:
        stock_df: DataFrame with stock data including 'is_volume_spike' column
        current_idx: Current row index
        lookback: Number of days to look back (default from config)
        
    Returns:
        Dict with spike info: {'found': bool, 'spike_high': float, 'spike_low': float, 'spike_idx': int}
    """
    if lookback is None:
        lookback = LOOKBACK_DAYS
    
    result = {'found': False, 'spike_high': None, 'spike_low': None, 'spike_idx': None, 'volume_ratio': 0}
    
    # Look back from t-1 to t-lookback
    for i in range(1, lookback + 1):
        check_idx = current_idx - i
        if check_idx < 0:
            continue
        
        row = stock_df.iloc[check_idx]
        if row.get('is_volume_spike', False):
            # Found a spike - keep track of the one with highest volume ratio
            if row['volume_ratio'] > result['volume_ratio']:
                result = {
                    'found': True,
                    'spike_high': row['highestprice'],
                    'spike_low': row['lowestprice'],
                    'spike_idx': check_idx,
                    'volume_ratio': row['volume_ratio'],
                    'spike_date': row['tradingdate']
                }
    
    return result


def detect_buy_signal(stock_df: pd.DataFrame, current_idx: int) -> dict:
    """
    Detect buy signal based on VSA rules:
    1. Volume spike in lookback window (t-1 to t-5)
    2. Current high > High of spike day (breakout)
    
    Args:
        stock_df: DataFrame with stock data and indicators
        current_idx: Current row index
        
    Returns:
        Dict with signal info: {'signal': bool, 'spike_high': float, 'spike_low': float, ...}
    """
    result = {
        'signal': False,
        'spike_high': None,
        'spike_low': None,
        'volume_ratio': 0,
        'spike_date': None
    }
    
    if current_idx < LOOKBACK_DAYS:
        return result
    
    current_row = stock_df.iloc[current_idx]
    current_high = current_row['highestprice']
    
    # Check for MAV20 availability
    if pd.isna(current_row.get('mav20')):
        return result
    
    # Find spike in lookback window
    spike_info = find_spike_in_lookback(stock_df, current_idx)
    
    if not spike_info['found']:
        return result
    
    # Check breakout: Current High > Spike High
    if current_high > spike_info['spike_high']:
        result = {
            'signal': True,
            'spike_high': spike_info['spike_high'],
            'spike_low': spike_info['spike_low'],
            'volume_ratio': spike_info['volume_ratio'],
            'spike_date': spike_info['spike_date']
        }
    
    return result


def detect_distribution_signal(close: float, prev_close: float, volume: float, mav20: float) -> bool:
    """
    Detect distribution signal (forced exit):
    - Close < Previous Close (down day)
    - Volume >= 4x MAV20 (volume spike)
    
    Args:
        close: Current close price
        prev_close: Previous close price
        volume: Current volume
        mav20: 20-day average volume
        
    Returns:
        True if distribution signal detected
    """
    if pd.isna(prev_close) or pd.isna(mav20) or mav20 <= 0:
        return False
    
    is_down_day = close < prev_close
    is_volume_spike = detect_volume_spike(volume, mav20)
    
    return is_down_day and is_volume_spike


def scan_for_buy_signals(stock_data: dict, date: pd.Timestamp) -> list:
    """
    Scan all stocks for buy signals on a specific date.
    
    Args:
        stock_data: Dictionary mapping stock_code -> DataFrame with indicators
        date: Trading date to scan
        
    Returns:
        List of dicts with stock_code and signal info, sorted by volume_ratio descending
    """
    signals = []
    
    for stock_code, df in stock_data.items():
        # Find the index for this date
        date_mask = df['tradingdate'] == date
        if not date_mask.any():
            continue
        
        idx = df[date_mask].index[0]
        signal_info = detect_buy_signal(df, df.index.get_loc(idx))
        
        if signal_info['signal']:
            signals.append({
                'stock_code': stock_code,
                'buy_price': df.loc[idx, 'closeprice'],
                'spike_high': signal_info['spike_high'],
                'spike_low': signal_info['spike_low'],
                'volume_ratio': signal_info['volume_ratio'],
                'spike_date': signal_info['spike_date'],
                'date': date
            })
    
    # Sort by volume ratio descending (higher ratio = higher priority)
    signals.sort(key=lambda x: x['volume_ratio'], reverse=True)
    
    return signals
