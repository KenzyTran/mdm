"""
Stop Loss Module
Implements fixed stop loss and spike low stop loss rules
"""

import pandas as pd
from .config import FIXED_STOP_LOSS_PCT


def check_fixed_stop_loss(buy_price: float, current_close: float, 
                          stop_loss_pct: float = None) -> bool:
    """
    Check if fixed stop loss is triggered.
    Sell if price drops 7% from buy price: C <= P_buy * 0.93
    
    Args:
        buy_price: Original buy price
        current_close: Current close price
        stop_loss_pct: Stop loss percentage (default 7%)
        
    Returns:
        True if stop loss triggered
    """
    if stop_loss_pct is None:
        stop_loss_pct = FIXED_STOP_LOSS_PCT
    
    stop_price = buy_price * (1 - stop_loss_pct)
    return current_close <= stop_price


def check_spike_low_stop(spike_low: float, current_close: float) -> bool:
    """
    Check if spike low stop is triggered.
    Sell if close price is below the low of the spike candle.
    
    Args:
        spike_low: Low price of the spike candle
        current_close: Current close price
        
    Returns:
        True if spike low stop triggered
    """
    return current_close < spike_low


def check_all_stops(buy_price: float, spike_low: float, current_close: float) -> dict:
    """
    Check all stop loss conditions.
    
    Args:
        buy_price: Original buy price
        spike_low: Low price of the spike candle
        current_close: Current close price
        
    Returns:
        Dict with stop type and triggered status
    """
    result = {
        'triggered': False,
        'stop_type': None
    }
    
    # Check fixed stop loss first (priority)
    if check_fixed_stop_loss(buy_price, current_close):
        result['triggered'] = True
        result['stop_type'] = f'Fixed Stop Loss -{FIXED_STOP_LOSS_PCT*100:.0f}%'
        return result
    
    # Check spike low stop
    if check_spike_low_stop(spike_low, current_close):
        result['triggered'] = True
        result['stop_type'] = 'Spike Low Stop'
        return result
    
    return result
