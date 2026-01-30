"""
Position Manager Module
State machine for managing trading positions.
"""

import pandas as pd
from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass


class MarketState(Enum):
    """Market position states."""
    CASH = "CASH"              # 100% cash, looking for opportunities
    HOLDING = "HOLDING"        # Holding positions
    WAITING_SELL = "WAITING_SELL"  # 5 DD reached, waiting to sell
    SHORT = "SHORT"            # Short position


@dataclass
class Position:
    """Current position information."""
    state: MarketState
    buy_price: float
    buy_date: Optional[pd.Timestamp]
    buy_day_low: float    # Low price of day bought
    trigger_price: float  # For WAITING_SELL state
    dd5_high: float       # High of 5th DD (for invalidation)
    short_price: float = 0.0      # Short sell price
    short_date: Optional[pd.Timestamp] = None  # Short sell date
    signal_type: str = "FTD"  # Type of signal that initiated position


class PositionManager:
    """
    Manage trading positions with state machine.
    
    State Transitions:
    - CASH → HOLDING: FTD signal
    - HOLDING → CASH: Stop loss or trigger break
    - HOLDING → WAITING_SELL: Count_DD == 5
    - WAITING_SELL → HOLDING: Price > H_DD5 or new FTD
    - WAITING_SELL → SHORT: C < P_trigger (trigger break → open short)
    - SHORT → CASH: Stop loss (1%) or FTD (cover)
    """
    
    DD_THRESHOLD = 5  # Number of DD to trigger warning
    SHORT_STOP_LOSS_PCT = 0.01  # 1% stop loss for short
    
    def __init__(self):
        """Initialize position manager."""
        self.position = Position(
            state=MarketState.CASH,
            buy_price=0.0,
            buy_date=None,
            buy_day_low=0.0,
            trigger_price=0.0,
            dd5_high=0.0,
            short_price=0.0,
            short_date=None
        )
        self.trades = []  # List of trade records
    
    def get_state(self) -> MarketState:
        """Get current state."""
        return self.position.state
    
    def get_buy_price(self) -> float:
        """Get current buy price."""
        return self.position.buy_price

    def get_buy_day_low(self) -> float:
        """Get low price of buy day."""
        return self.position.buy_day_low
    
    def get_short_price(self) -> float:
        """Get current short price."""
        return self.position.short_price
    
    def get_signal_type(self) -> str:
        """Get signal type of current position."""
        return self.position.signal_type
    
    def enter_holding(
        self,
        buy_price: float,
        buy_date: pd.Timestamp,
        buy_day_low: float,
        signal_type: str = "FTD"
    ):
        """
        Enter HOLDING state (buy signal).
        
        Args:
            buy_price: Price at which to buy
            buy_date: Date of buy
            buy_day_low: Low price of the buy day
            signal_type: Type of signal (FTD, MA50, 52WEEK)
        """
        self.position = Position(
            state=MarketState.HOLDING,
            buy_price=buy_price,
            buy_date=buy_date,
            buy_day_low=buy_day_low,
            trigger_price=0.0,
            dd5_high=0.0,
            short_price=0.0,
            short_date=None,
            signal_type=signal_type
        )
        self.trades.append({
            'type': 'BUY',
            'date': buy_date,
            'price': buy_price,
            'signal_type': signal_type
        })
    
    def exit_to_cash(
        self,
        sell_price: float,
        sell_date: pd.Timestamp,
        reason: str
    ):
        """
        Exit to CASH state (sell).
        
        Args:
            sell_price: Price at which to sell
            sell_date: Date of sell
            reason: Reason for selling
        """
        buy_price = self.position.buy_price
        pnl = (sell_price - buy_price) / buy_price if buy_price > 0 else 0
        
        self.trades.append({
            'type': 'SELL',
            'date': sell_date,
            'price': sell_price,
            'reason': reason,
            'pnl': pnl
        })
        
        self.position = Position(
            state=MarketState.CASH,
            buy_price=0.0,
            buy_date=None,
            buy_day_low=0.0,
            trigger_price=0.0,
            dd5_high=0.0,
            short_price=0.0,
            short_date=None
        )
    
    def enter_waiting_sell(
        self,
        trigger_price: float,
        dd5_high: float
    ):
        """
        Enter WAITING_SELL state (5 DD warning).
        
        Args:
            trigger_price: Low of 5th DD (trigger for sell)
            dd5_high: High of 5th DD (for invalidation)
        """
        self.position.state = MarketState.WAITING_SELL
        self.position.trigger_price = trigger_price
        self.position.dd5_high = dd5_high
    
    def return_to_holding(self):
        """Return to HOLDING state from WAITING_SELL."""
        self.position.state = MarketState.HOLDING
        # Don't reset buy_day_low here as we are still in the same trade
        self.position.trigger_price = 0.0
        self.position.dd5_high = 0.0
    
    def enter_short(
        self,
        short_price: float,
        short_date: pd.Timestamp,
        sell_long_first: bool = True
    ):
        """
        Enter SHORT state (open short position).
        
        Args:
            short_price: Price at which to short
            short_date: Date of short
            sell_long_first: Whether to sell long position first
        """
        # First, close any long position
        if sell_long_first and self.position.buy_price > 0:
            pnl = (short_price - self.position.buy_price) / self.position.buy_price
            self.trades.append({
                'type': 'SELL',
                'date': short_date,
                'price': short_price,
                'reason': 'Trigger break → Open Short',
                'pnl': pnl
            })
        
        # Open short position
        self.position = Position(
            state=MarketState.SHORT,
            buy_price=0.0,
            buy_date=None,
            buy_day_low=0.0,
            trigger_price=0.0,
            dd5_high=0.0,
            short_price=short_price,
            short_date=short_date
        )
        self.trades.append({
            'type': 'SHORT',
            'date': short_date,
            'price': short_price
        })
    
    def cover_short(
        self,
        cover_price: float,
        cover_date: pd.Timestamp,
        reason: str
    ):
        """
        Cover short position (exit SHORT state).
        
        Args:
            cover_price: Price at which to cover
            cover_date: Date of cover
            reason: Reason for covering
        """
        short_price = self.position.short_price
        # PnL for short: profit when price goes down
        pnl = (short_price - cover_price) / short_price if short_price > 0 else 0
        
        self.trades.append({
            'type': 'COVER',
            'date': cover_date,
            'price': cover_price,
            'reason': reason,
            'pnl': pnl
        })
        
        self.position = Position(
            state=MarketState.CASH,
            buy_price=0.0,
            buy_date=None,
            buy_day_low=0.0,
            trigger_price=0.0,
            dd5_high=0.0,
            short_price=0.0,
            short_date=None
        )
    
    def check_short_stop_loss(self, current_close: float) -> Tuple[bool, str]:
        """
        Check if short position should be stopped out.
        
        Args:
            current_close: Current close price
            
        Returns:
            Tuple of (triggered, reason)
        """
        # Use H_DD5 (dd5_high) for stop loss calculation
        dd5_high = self.position.dd5_high
        if dd5_high <= 0:
            return False, ""
        
        # Stop loss: price rises 1% above DD5 high
        if current_close > dd5_high * 1.01:
            loss_pct = (current_close - self.position.short_price) / self.position.short_price if self.position.short_price > 0 else 0
            return True, f"Short stop loss: Close > H_DD5 * 1.01 ({dd5_high:.2f}), loss: {loss_pct*100:.2f}%"
        
        return False, ""
    
    def process_day(
        self,
        date: pd.Timestamp,
        high: float,
        low: float,
        close: float,
        is_ftd: bool,
        ftd_price: float,
        dd_count: int,
        is_dd: bool,
        stop_loss_triggered: bool,
        stop_loss_reason: str,
        signal_type: str = "FTD",
        ma10: float = None,
        prev_ma10: float = None,
        prev_close: float = None,
        volume_up: bool = False
    ) -> Tuple[MarketState, str]:
        """
        Process a trading day and update state.
        
        Args:
            date: Current date
            high: Current high
            low: Current low
            close: Current close
            is_ftd: Whether FTD signal occurred
            ftd_price: FTD price if signal occurred
            dd_count: Current DD count in window
            is_dd: Whether today is a DD
            stop_loss_triggered: Whether stop loss triggered
            stop_loss_reason: Stop loss reason
            signal_type: Type of buy signal
            ma10: Current 10-day MA (for short entry)
            prev_ma10: Previous 10-day MA (for short entry)
            prev_close: Previous close (for short entry)
            volume_up: Whether volume increased (for short entry)
            
        Returns:
            Tuple of (new_state, action_taken)
        """
        current_state = self.position.state
        action = ""
        
        if current_state == MarketState.CASH:
            # Looking for FTD signal to buy
            if is_ftd:
                self.enter_holding(ftd_price, date, low, signal_type)
                action = f"BUY at {ftd_price:.2f} ({signal_type})"
        
        elif current_state == MarketState.HOLDING:
            # Check stop loss first (highest priority)
            if stop_loss_triggered:
                self.exit_to_cash(close, date, stop_loss_reason)
                action = f"SELL at {close:.2f} ({stop_loss_reason})"
            
            # Check for 5 DD warning
            elif dd_count >= self.DD_THRESHOLD and is_dd:
                # Special exception: If just after FTD and DD count hits 5 (stale count)
                # Stay in HOLDING but monitor for stop loss
                # We enter WAITING_SELL only on fresh 5th DD
                self.enter_waiting_sell(low, high)
                action = f"WARNING: 5 DD reached, trigger at {low:.2f}"
        
        elif current_state == MarketState.WAITING_SELL:
            # Check for invalidation first
            if close > self.position.dd5_high:
                self.return_to_holding()
                action = "INVALIDATE: Close > DD5 high, back to HOLDING"
            
            # Check for new FTD
            elif is_ftd:
                # New FTD - reset DD count and stay in holding
                self.return_to_holding()
                action = "INVALIDATE: New FTD signal, back to HOLDING"
            
            # Check for MA10 breakdown → Open SHORT
            # Conditions: prev_close >= prev_ma10 AND close < ma10 AND volume_up
            elif ma10 is not None and prev_ma10 is not None:
                if prev_close >= prev_ma10 and close < ma10 and volume_up:
                    self.enter_short(close, date, sell_long_first=True)
                    action = f"SHORT at {close:.2f} (MA10 breakdown)"
            
            # Also check stop loss
            elif stop_loss_triggered:
                self.exit_to_cash(close, date, stop_loss_reason)
                action = f"SELL at {close:.2f} ({stop_loss_reason})"
        
        elif current_state == MarketState.SHORT:
            # Check for FTD → Cover short
            if is_ftd:
                self.cover_short(close, date, "FTD signal")
                action = f"COVER at {close:.2f} (FTD signal)"
            else:
                # Check short stop loss
                short_stop_triggered, short_stop_reason = self.check_short_stop_loss(close)
                if short_stop_triggered:
                    self.cover_short(close, date, short_stop_reason)
                    action = f"COVER at {close:.2f} ({short_stop_reason})"
        
        return self.position.state, action
    
    def get_trades(self) -> list:
        """Get list of all trades."""
        return self.trades
    
    def reset(self):
        """Reset position manager."""
        self.position = Position(
            state=MarketState.CASH,
            buy_price=0.0,
            buy_date=None,
            buy_day_low=0.0,
            trigger_price=0.0,
            dd5_high=0.0,
            short_price=0.0,
            short_date=None
        )
        self.trades = []
