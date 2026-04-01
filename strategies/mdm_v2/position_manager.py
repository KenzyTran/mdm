"""
V2 Position Manager Module

3-state machine for MDM v2: BUY, CASH, SELL.
No SHORT or WAITING_SELL states (per D-03).
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
    fail_safe_threshold: float = 0.0


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
        """Enter BUY state."""
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

    def enter_sell(self, date: pd.Timestamp, reason: str, fail_safe_threshold: float = 0.0):
        """Enter SELL state from CASH (no position to close)."""
        self.trades.append({
            'type': 'SELL_SIGNAL',
            'date': date,
            'reason': reason,
        })
        self.position = V2Position(
            state=V2MarketState.SELL,
            days_in_cash=0,
            ma10_below_count=0,
            fail_safe_threshold=fail_safe_threshold,
        )

    def fail_safe_exit(self, date: pd.Timestamp, close: float):
        """Exit SELL state to CASH via fail-safe (SAFE-02)."""
        self.trades.append({
            'type': 'FAIL_SAFE_EXIT',
            'date': date,
            'price': close,
            'reason': f"Fail-safe: close {close:.2f} > standby-sell HIGH {self.position.fail_safe_threshold:.2f}",
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
        sma200: float = None,
        suppress_sell: bool = False,
        acceleration_met: bool = True,
        prev_high: float = 0.0,
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
            sma200: Current 200-day SMA (optional, for 200dma SELL trigger)
            suppress_sell: Whether to suppress CASH->SELL transitions (QE floor)
            acceleration_met: Whether sell acceleration conditions are met
            prev_high: High of previous day (for fail-safe threshold)

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
                if suppress_sell:
                    action = "SELL suppressed: QE floor (MA50 breakdown)"
                elif not acceleration_met:
                    action = "SELL deferred: no acceleration (MA50 breakdown)"
                else:
                    self.enter_sell(date, f"MA50 breakdown (close {close:.2f} < MA50 {ma50:.2f})", fail_safe_threshold=prev_high)
                    action = f"SELL signal: MA50 breakdown"
            # Check for CASH -> SELL: 200dma breakdown (per D-03, Scenario 5)
            elif self.config.ma200_enabled and sma200 is not None and close < sma200:
                if suppress_sell:
                    action = "SELL suppressed: QE floor (200dma breakdown)"
                elif not acceleration_met:
                    action = "SELL deferred: no acceleration (200dma breakdown)"
                else:
                    self.enter_sell(date, f"200dma breakdown (close {close:.2f} < 200dma {sma200:.2f})", fail_safe_threshold=prev_high)
                    action = "SELL signal: 200dma breakdown"
            # Check for CASH -> SELL: deterioration
            elif self.position.days_in_cash >= self.config.cash_deterioration_days:
                if suppress_sell:
                    action = "SELL suppressed: QE floor (cash deterioration)"
                elif not acceleration_met:
                    action = "SELL deferred: no acceleration (cash deterioration)"
                else:
                    self.enter_sell(date, f"Cash deterioration ({self.position.days_in_cash} days)", fail_safe_threshold=prev_high)
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
            # Check fail-safe first: close > standby-sell HIGH -> exit to CASH (SAFE-02)
            if (self.config.fail_safe_enabled
                and self.position.fail_safe_threshold > 0
                and close > self.position.fail_safe_threshold):
                self.fail_safe_exit(date, close)
                action = f"CASH: fail-safe triggered (close {close:.2f} > threshold {self.position.fail_safe_threshold:.2f})"
            # FTD -> BUY (from SELL)
            elif is_ftd:
                self.enter_buy(ftd_price, date, low, signal_type)
                action = f"BUY at {ftd_price:.2f} ({signal_type}) from SELL"

        return self.position.state, action

    def get_trades(self) -> list:
        """Get list of all trades."""
        return self.trades

    def reset(self):
        """Reset position manager."""
        self.position = V2Position()
        self.trades = []
