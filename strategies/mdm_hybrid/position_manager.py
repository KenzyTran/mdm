"""
V2 Position Manager Module

3-state machine for MDM v2: BUY, CASH, SELL.
SELL state represents active short position (Phase 16).
"""

import pandas as pd
from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass, field

from .config import MDMV2Config


class V2MarketState(Enum):
    """Market position states for v2 engine."""
    BUY = "BUY"
    CASH = "CASH"
    SELL = "SELL"


@dataclass
class V2Position:
    """Current position information for v2 engine."""
    state: V2MarketState = V2MarketState.CASH
    buy_price: float = 0.0
    buy_date: Optional[pd.Timestamp] = None
    buy_day_low: float = 0.0
    signal_type: str = "FTD"
    days_in_cash: int = 0
    ma10_below_count: int = 0
    short_entry_price: float = 0.0
    short_entry_date: Optional[pd.Timestamp] = None


class V2PositionManager:
    """
    Manage trading positions with 3-state machine.

    State Transitions (per D-01/D-02/D-03):
    - CASH -> BUY: FTD signal or MA50 breakout
    - BUY -> CASH: dd_count >= dd_cash_threshold (on DD day),
                    OR stop_loss_triggered,
                    OR close < MA10 for ma10_cash_consecutive days
    - CASH -> SELL: MA50 breakdown (close < ma50),
                     OR days_in_cash >= cash_deterioration_days
    - SELL -> BUY: FTD signal or MA50 breakout
    """

    def __init__(self, config: MDMV2Config):
        """Initialize position manager with config."""
        self.config = config
        self.position = V2Position()
        self.trades = []

    def get_state(self) -> V2MarketState:
        """Get current state."""
        return self.position.state

    def get_buy_price(self) -> float:
        """Get current buy price."""
        return self.position.buy_price

    def get_buy_day_low(self) -> float:
        """Get low price of buy day."""
        return self.position.buy_day_low

    def get_signal_type(self) -> str:
        """Get signal type of current position."""
        return self.position.signal_type

    def enter_buy(
        self,
        buy_price: float,
        buy_date: pd.Timestamp,
        buy_day_low: float,
        signal_type: str = "FTD"
    ):
        """Enter BUY state. Raises if currently in SELL (must cover first)."""
        if self.position.state == V2MarketState.SELL:
            raise ValueError(
                f"Cannot enter BUY directly from SELL state. "
                f"Must cover_short() first. Date: {buy_date}"
            )
        self.position = V2Position(
            state=V2MarketState.BUY,
            buy_price=buy_price,
            buy_date=buy_date,
            buy_day_low=buy_day_low,
            signal_type=signal_type,
            days_in_cash=0,
            ma10_below_count=0,
        )
        self.trades.append({
            'type': 'BUY',
            'date': buy_date,
            'price': buy_price,
            'signal_type': signal_type,
        })

    def exit_to_cash(
        self,
        sell_price: float,
        sell_date: pd.Timestamp,
        reason: str
    ):
        """Exit position to CASH state."""
        buy_price = self.position.buy_price
        pnl = (sell_price - buy_price) / buy_price if buy_price > 0 else 0

        self.trades.append({
            'type': 'CASH_EXIT',
            'date': sell_date,
            'price': sell_price,
            'reason': reason,
            'pnl': pnl,
        })

        self.position = V2Position(
            state=V2MarketState.CASH,
            days_in_cash=0,
            ma10_below_count=0,
        )

    def enter_sell(self, date: pd.Timestamp, reason: str, price: float = 0.0):
        """Enter SELL state and open short position.

        Args:
            date: Date of sell signal.
            reason: Reason for entering sell.
            price: Entry price for short position (0.0 if not tracking).
        """
        self.trades.append({
            'type': 'SELL_SIGNAL',
            'date': date,
            'price': price,
            'reason': reason,
        })
        self.position = V2Position(
            state=V2MarketState.SELL,
            days_in_cash=0,
            ma10_below_count=0,
            short_entry_price=price,
            short_entry_date=date,
        )

    def cover_short(self, cover_price: float, cover_date: pd.Timestamp, reason: str):
        """Cover short position and return to CASH state.

        P&L = (entry - cover) / entry. Positive when market drops (gain).

        Args:
            cover_price: Price at which short is covered.
            cover_date: Date of cover.
            reason: Reason for covering.
        """
        entry = self.position.short_entry_price
        pnl = (entry - cover_price) / entry if entry > 0 else 0

        self.trades.append({
            'type': 'SHORT_COVER',
            'date': cover_date,
            'price': cover_price,
            'reason': reason,
            'pnl': pnl,
            'entry_price': entry,
        })

        self.position = V2Position(
            state=V2MarketState.CASH,
            days_in_cash=0,
            ma10_below_count=0,
        )

    def degrade_to_cash(self, date: pd.Timestamp, reason: str):
        """Degrade current state to CASH without P&L calculation.

        Used for indicator-driven cash insertion (D-06/D-07) when there is
        no position to close (e.g., SELL->CASH) or when override forces
        Cash independent of state machine logic.

        Args:
            date: Current date.
            reason: Reason for degradation.
        """
        self.trades.append({
            'type': 'STATE_DEGRADE',
            'date': date,
            'reason': reason,
        })
        self.position = V2Position(
            state=V2MarketState.CASH,
            days_in_cash=0,
            ma10_below_count=0,
        )

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
        ma50: float = None,
    ) -> Tuple[V2MarketState, str]:
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
            ma10: Current 10-day MA
            ma50: Current 50-day MA

        Returns:
            Tuple of (new_state, action_taken)
        """
        current_state = self.position.state
        action = ""

        if current_state == V2MarketState.CASH:
            # Increment days_in_cash counter
            self.position.days_in_cash += 1

            # Check for FTD -> BUY
            if is_ftd:
                self.enter_buy(ftd_price, date, low, signal_type)
                action = f"BUY at {ftd_price:.2f} ({signal_type})"
            # Check for CASH -> SELL: MA50 breakdown
            elif self.config.ma50_sell_enabled and ma50 is not None and close < ma50:
                self.enter_sell(date, f"MA50 breakdown (close {close:.2f} < MA50 {ma50:.2f})")
                action = f"SELL signal: MA50 breakdown"
            # Check for CASH -> SELL: deterioration
            elif self.position.days_in_cash >= self.config.cash_deterioration_days:
                self.enter_sell(date, f"Cash deterioration ({self.position.days_in_cash} days)")
                action = f"SELL signal: cash deterioration"

        elif current_state == V2MarketState.BUY:
            # Track MA10 below count
            if ma10 is not None and close < ma10:
                self.position.ma10_below_count += 1
            elif ma10 is not None:
                self.position.ma10_below_count = 0

            # Check stop loss first (highest priority)
            if stop_loss_triggered:
                self.exit_to_cash(close, date, stop_loss_reason)
                action = f"CASH exit at {close:.2f} ({stop_loss_reason})"
            # Check DD threshold (on a DD day)
            elif dd_count >= self.config.dd_cash_threshold and is_dd:
                self.exit_to_cash(close, date, f"DD count {dd_count} >= threshold {self.config.dd_cash_threshold}")
                action = f"CASH exit: DD count {dd_count}"
            # Check MA10 consecutive below
            elif (self.config.ma10_cash_enabled
                  and self.position.ma10_below_count >= self.config.ma10_cash_consecutive):
                self.exit_to_cash(close, date, f"Close below MA10 for {self.position.ma10_below_count} days")
                action = f"CASH exit: MA10 below count {self.position.ma10_below_count}"

        elif current_state == V2MarketState.SELL:
            # Phase 16: cover short first, then buy (SELL->CASH->BUY per D-09)
            if is_ftd:
                self.cover_short(close, date, f"FTD detected ({signal_type})")
                self.enter_buy(ftd_price, date, low, signal_type)
                action = f"SHORT_COVER + BUY at {ftd_price:.2f} ({signal_type})"

        return self.position.state, action

    def get_trades(self) -> list:
        """Get list of all trades."""
        return self.trades

    def reset(self):
        """Reset position manager."""
        self.position = V2Position()
        self.trades = []
