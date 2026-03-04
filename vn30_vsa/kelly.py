"""
Kelly Criterion Module
Implements Rolling Kelly for dynamic position sizing
"""

from typing import List, Any
from .config import (
    KELLY_FRACTION, 
    KELLY_MIN_WEIGHT, 
    KELLY_MAX_WEIGHT,
    POSITION_WEIGHT
)


def calculate_rolling_kelly(trades: List[Any], window_size: int = 50, 
                            kelly_fraction: float = None) -> float:
    """
    Calculate position weight using Rolling Kelly Criterion.
    
    Args:
        trades: List of Trade objects with pnl_pct attribute
        window_size: Number of recent trades to consider (20 or 50)
        kelly_fraction: Fraction of Kelly to use (default: Half Kelly = 0.5)
    
    Returns:
        float: Position weight (between KELLY_MIN_WEIGHT and KELLY_MAX_WEIGHT)
    
    Example:
        After 30 trades with 50% win rate, Avg Win=22%, Avg Loss=5%:
        - R = 22/5 = 4.4
        - Kelly = 0.50 - (0.50/4.4) = 38.6%
        - Half Kelly = 19.3%
    """
    if kelly_fraction is None:
        kelly_fraction = KELLY_FRACTION
    
    # Get recent trades
    recent_trades = trades[-window_size:] if len(trades) >= window_size else trades
    
    if len(recent_trades) == 0:
        return POSITION_WEIGHT  # Default 15%
    
    # Separate wins and losses
    wins = [t for t in recent_trades if t.pnl_pct > 0]
    losses = [t for t in recent_trades if t.pnl_pct <= 0]
    
    # Calculate Win Rate
    win_rate = len(wins) / len(recent_trades) if len(recent_trades) > 0 else 0
    
    # Calculate Avg Win and Avg Loss
    avg_win = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t.pnl_pct for t in losses) / len(losses)) if losses else 0.01  # Avoid division by zero
    
    # Calculate R-ratio (Reward/Risk)
    r_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    # Calculate Full Kelly: f* = p - (1-p)/R
    if r_ratio > 0:
        full_kelly = win_rate - ((1 - win_rate) / r_ratio)
    else:
        full_kelly = 0
    
    # Apply Kelly fraction (Half Kelly by default)
    position_weight = full_kelly * kelly_fraction
    
    # Apply limits: min 5%, max 25%
    position_weight = max(KELLY_MIN_WEIGHT, min(KELLY_MAX_WEIGHT, position_weight))
    
    return round(position_weight, 4)


def get_kelly_phase(trade_count: int) -> str:
    """
    Determine which Kelly phase based on trade count.
    
    Returns:
        'FIXED': Trades 1-20, use fixed 15%
        'SMALL_WINDOW': Trades 21-50, use 20-trade window
        'LARGE_WINDOW': Trades 51+, use 50-trade window
    """
    from .config import KELLY_MIN_TRADES_PHASE1, KELLY_MIN_TRADES_PHASE2
    
    if trade_count < KELLY_MIN_TRADES_PHASE1:
        return 'FIXED'
    elif trade_count < KELLY_MIN_TRADES_PHASE2:
        return 'SMALL_WINDOW'
    else:
        return 'LARGE_WINDOW'
