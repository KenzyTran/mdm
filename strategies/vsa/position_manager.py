"""
Position Manager Module
Handles portfolio allocation, position tracking, and trade execution
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from .config import (
    MAX_POSITIONS, POSITION_WEIGHT, INITIAL_NAV, TAKE_PROFIT_PCT, MA10_WEEKS_IN_DAYS,
    KELLY_MIN_TRADES_PHASE1, KELLY_MIN_TRADES_PHASE2, KELLY_WINDOW_SMALL, KELLY_WINDOW_LARGE
)
from .kelly import calculate_rolling_kelly


@dataclass
class Position:
    """Represents a stock position."""
    stock_code: str
    buy_date: pd.Timestamp
    buy_price: float
    quantity: float
    spike_high: float
    spike_low: float
    initial_quantity: float = field(default=0)
    took_profit: bool = field(default=False)
    days_held: int = field(default=0)
    # Track if MA10 was ever violated during first 7 weeks
    violated_ma10: bool = field(default=False)
    # After 7 weeks, lock in which MA to use
    trailing_stop_ma: str = field(default='MA10')  # 'MA10' or 'MA50'
    # Last known price for NAV calculation (handling missing data)
    last_price: float = field(default=0.0)
    
    def __post_init__(self):
        if self.initial_quantity == 0:
            self.initial_quantity = self.quantity
        if self.last_price == 0:
            self.last_price = self.buy_price
    
    def current_value(self, current_price: float) -> float:
        """Calculate current value of this position."""
        return self.quantity * current_price
    
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized profit/loss."""
        return (current_price - self.buy_price) * self.quantity
    
    def unrealized_pnl_pct(self, current_price: float) -> float:
        """Calculate unrealized P&L percentage."""
        if self.buy_price <= 0:
            return 0.0
        return (current_price - self.buy_price) / self.buy_price
    
    def check_ma10_violation(self, current_close: float, ma10: float):
        """
        Check and record if stock violates MA10.
        Called during first 7 weeks to track behavior.
        """
        if pd.isna(ma10):
            return
        
        # If stock closes below MA10, mark as violated
        if current_close < ma10:
            self.violated_ma10 = True
            self.trailing_stop_ma = 'MA50'
    
    def finalize_trailing_stop_type(self):
        """
        Called after 7 weeks to lock in the trailing stop type.
        """
        if self.violated_ma10:
            self.trailing_stop_ma = 'MA50'
        else:
            self.trailing_stop_ma = 'MA10'


@dataclass
class Trade:
    """Represents a completed trade."""
    stock_code: str
    buy_date: pd.Timestamp
    buy_price: float
    sell_date: pd.Timestamp
    sell_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    exit_reason: str


class PositionManager:
    """Manages portfolio positions and executes trades."""
    
    def __init__(self, initial_nav: float = None, max_positions: int = None, 
                 position_weight: float = None):
        self.initial_nav = initial_nav or INITIAL_NAV
        self.nav = self.initial_nav
        self.cash = self.initial_nav
        self.max_positions = max_positions or MAX_POSITIONS
        self.position_weight = position_weight or POSITION_WEIGHT  # Default 15%
        
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.nav_history: List[Dict] = []
    
    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        return len(self.positions) < self.max_positions
    
    def get_position_size(self) -> float:
        """
        Calculate position size using Rolling Kelly Criterion.
        
        Phases:
        - Trade 1-20: Fixed 15% (not enough data)
        - Trade 21-50: Kelly from last 20 trades
        - Trade 51+: Kelly from last 50 trades
        """
        trade_count = len(self.trades)
        
        if trade_count < KELLY_MIN_TRADES_PHASE1:
            # Phase 1: Fixed 15%
            weight = self.position_weight
        elif trade_count < KELLY_MIN_TRADES_PHASE2:
            # Phase 2: Kelly from 20 trades
            weight = calculate_rolling_kelly(self.trades, KELLY_WINDOW_SMALL)
        else:
            # Phase 3: Kelly from 50 trades
            weight = calculate_rolling_kelly(self.trades, KELLY_WINDOW_LARGE)
        
        return self.nav * weight
    
    def open_position(self, stock_code: str, buy_date: pd.Timestamp, 
                      buy_price: float, spike_high: float, spike_low: float) -> bool:
        """Open a new position."""
        if not self.can_open_position():
            return False
        
        if stock_code in self.positions:
            return False  # Already have this stock
        
        # Calculate quantity based on position size
        position_value = self.get_position_size()
        quantity = position_value / buy_price
        
        # Check if we have enough cash
        if position_value > self.cash:
            return False
        
        # Open position
        self.positions[stock_code] = Position(
            stock_code=stock_code,
            buy_date=buy_date,
            buy_price=buy_price,
            quantity=quantity,
            spike_high=spike_high,
            spike_low=spike_low,
            last_price=buy_price # Initialize last price
        )
        
        # Deduct cash
        self.cash -= position_value
        
        return True
    
    def close_position(self, stock_code: str, sell_date: pd.Timestamp, 
                       sell_price: float, exit_reason: str, 
                       partial: bool = False, partial_pct: float = 0.5) -> Optional[Trade]:
        """Close a position (fully or partially)."""
        if stock_code not in self.positions:
            return None
        
        position = self.positions[stock_code]
        
        if partial:
            sell_quantity = position.quantity * partial_pct
            position.quantity -= sell_quantity
            position.took_profit = True
        else:
            sell_quantity = position.quantity
            del self.positions[stock_code]
        
        # Calculate P&L
        pnl = (sell_price - position.buy_price) * sell_quantity
        pnl_pct = (sell_price - position.buy_price) / position.buy_price
        
        # Record trade
        trade = Trade(
            stock_code=stock_code,
            buy_date=position.buy_date,
            buy_price=position.buy_price,
            sell_date=sell_date,
            sell_price=sell_price,
            quantity=sell_quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason
        )
        self.trades.append(trade)
        
        # Add cash back
        self.cash += sell_price * sell_quantity
        
        return trade
    
    def update_nav(self, date: pd.Timestamp, current_prices: Dict[str, float]):
        """
        Update NAV based on current prices.
        Handled missing data by using last known price.
        """
        portfolio_value = 0
        for stock_code, position in self.positions.items():
            # Update last known price if available
            if stock_code in current_prices and current_prices[stock_code] > 0:
                position.last_price = current_prices[stock_code]
            
            # Use last price for valuation
            if position.last_price > 0:
                portfolio_value += position.quantity * position.last_price
            else:
                # Should not happen given post_init, but strictly safe
                portfolio_value += position.quantity * position.buy_price
        
        self.nav = self.cash + portfolio_value
        
        self.nav_history.append({
            'date': date,
            'nav': self.nav,
            'cash': self.cash,
            'portfolio_value': portfolio_value,
            'num_positions': len(self.positions)
        })
    
    def update_days_held(self):
        """Increment days_held for all positions."""
        for position in self.positions.values():
            position.days_held += 1
    
    def update_ma10_tracking(self, stock_code: str, current_close: float, ma10: float):
        """Update MA10 violation tracking."""
        if stock_code not in self.positions:
            return
        
        position = self.positions[stock_code]
        
        # Only track during first 7 weeks
        if position.days_held <= MA10_WEEKS_IN_DAYS:
            position.check_ma10_violation(current_close, ma10)
            
            # At the end of 7 weeks, finalize the trailing stop type
            if position.days_held == MA10_WEEKS_IN_DAYS:
                position.finalize_trailing_stop_type()
    
    def get_positions_to_check(self) -> List[str]:
        """Get list of stock codes with open positions."""
        return list(self.positions.keys())
    
    def check_take_profit(self, stock_code: str, current_price: float, 
                          sell_date: pd.Timestamp) -> Optional[Trade]:
        """Check and execute take profit."""
        if stock_code not in self.positions:
            return None
        
        position = self.positions[stock_code]
        
        # Skip if already took profit
        if position.took_profit:
            return None
        
        pnl_pct = position.unrealized_pnl_pct(current_price)
        
        if pnl_pct >= TAKE_PROFIT_PCT:
            return self.close_position(
                stock_code, sell_date, current_price,
                exit_reason=f"Take Profit {TAKE_PROFIT_PCT*100:.0f}%",
                partial=True, partial_pct=0.5
            )
        
        return None
    
    def get_nav_df(self) -> pd.DataFrame:
        """Get NAV history as DataFrame."""
        return pd.DataFrame(self.nav_history)
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get trades history as DataFrame."""
        return pd.DataFrame([
            {
                'stock_code': t.stock_code,
                'buy_date': t.buy_date,
                'buy_price': t.buy_price,
                'sell_date': t.sell_date,
                'sell_price': t.sell_price,
                'quantity': t.quantity,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'exit_reason': t.exit_reason
            }
            for t in self.trades
        ])
