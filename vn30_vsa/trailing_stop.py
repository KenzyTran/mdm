"""
Trailing Stop Module
Implements MA10 and MA50 trailing stop logic

NEW LOGIC (Corrected):
- During first 7 weeks: Track if stock ever closes below MA10
- If stock NEVER violates MA10 in 7 weeks -> Use MA10 as trailing stop
- If stock violates MA10 (even once) -> Switch to MA50 as trailing stop
- Stop loss rules (7%, spike low) still apply separately
"""

import pandas as pd
import numpy as np
from .config import MA10_WEEKS_IN_DAYS


def check_ma10_trailing_stop(current_close: float, ma10: float) -> bool:
    """
    Check if MA10 trailing stop is triggered.
    Sell if close price drops below MA10.
    
    Args:
        current_close: Current close price
        ma10: 10-day moving average
        
    Returns:
        True if MA10 stop triggered
    """
    if pd.isna(ma10):
        return False
    return current_close < ma10


def check_ma50_trailing_stop(current_close: float, ma50: float) -> bool:
    """
    Check if MA50 trailing stop is triggered.
    Sell if close price drops below MA50.
    
    Args:
        current_close: Current close price
        ma50: 50-day moving average
        
    Returns:
        True if MA50 stop triggered
    """
    if pd.isna(ma50):
        return False
    return current_close < ma50


def check_trailing_stop(stock_df: pd.DataFrame, current_idx: int, 
                        days_held: int, trailing_stop_ma: str = 'MA10',
                        violated_ma10: bool = False) -> dict:
    """
    Check trailing stop based on position's assigned MA.
    
    CORRECTED LOGIC:
    - If position has trailing_stop_ma = 'MA10' and never violated -> use MA10
    - If position has trailing_stop_ma = 'MA50' or violated -> use MA50
    - During first 7 weeks, if violated_ma10=True -> already using MA50
    - Robustness fix: After 7 weeks, if violated_ma10 is True, force MA50 even if trailing_stop_ma failed to update
    
    Args:
        stock_df: DataFrame with stock data
        current_idx: Current index in the DataFrame
        days_held: Number of days position has been held
        trailing_stop_ma: Which MA to use ('MA10' or 'MA50')
        violated_ma10: Whether MA10 was violated during observation period
        
    Returns:
        Dict with triggered status and stop type
    """
    result = {
        'triggered': False,
        'stop_type': None
    }
    
    if current_idx < 0:
        return result
    
    current_row = stock_df.iloc[current_idx]
    current_close = current_row['closeprice']
    ma10 = current_row.get('ma10')
    ma50 = current_row.get('ma50')
    
    # During first 7 weeks - observe and apply trailing stop
    if days_held <= MA10_WEEKS_IN_DAYS:
        if violated_ma10:
            # Already violated MA10 -> use MA50
            if check_ma50_trailing_stop(current_close, ma50):
                result['triggered'] = True
                result['stop_type'] = 'Trailing Stop MA50'
        else:
            # Still respecting MA10 -> use MA10
            if check_ma10_trailing_stop(current_close, ma10):
                result['triggered'] = True
                result['stop_type'] = 'Trailing Stop MA10'
    else:
        # After 7 weeks - use the locked-in MA
        # Prioritize violation history for robustness
        should_use_ma50 = (trailing_stop_ma == 'MA50') or violated_ma10
        
        if not should_use_ma50:
            # Use MA10
            if check_ma10_trailing_stop(current_close, ma10):
                result['triggered'] = True
                result['stop_type'] = 'Trailing Stop MA10'
        else:
            # Use MA50
            if check_ma50_trailing_stop(current_close, ma50):
                result['triggered'] = True
                result['stop_type'] = 'Trailing Stop MA50'
    
    return result
