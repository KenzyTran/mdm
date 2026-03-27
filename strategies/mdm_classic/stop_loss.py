"""
Stop Loss Module
Check stop loss conditions.
"""

from dataclasses import dataclass
from typing import Tuple

from .config import MDMConfig


@dataclass
class StopLossResult:
    """Result of stop loss check."""
    triggered: bool
    reason: str
    loss_pct: float


class StopLossChecker:
    """
    Check stop loss conditions for holdings.
    
    Rules:
    1. Price drops X% from buy price
    2. Close below buy price
    3. Break below MA50 with volume higher than previous session
    """
    
    def __init__(self, config: MDMConfig = None):
        """Initialize."""
        self.config = config if config else MDMConfig()
    
    def check(
        self,
        current_close: float,
        buy_price: float,
        buy_day_low: float,
        ma50: float = None,
        prev_close: float = None,
        prev_ma50: float = None,
        current_volume: float = None,
        prev_volume: float = None,
        signal_type: str = "FTD"
    ) -> StopLossResult:
        """
        Check if stop loss should be triggered.
        
        Args:
            current_close: Current close price
            buy_price: Original buy price
            buy_day_low: Low price of the buy day
            ma50: 50-day moving average (optional, for Rule 3)
            prev_close: Previous close price (optional, for Rule 3)
            prev_ma50: Previous MA50 (optional, for Rule 3)
            current_volume: Current session volume (optional, for Rule 3)
            prev_volume: Previous session volume (optional, for Rule 3)
            signal_type: Type of buy signal (FTD, MA50, 52WEEK)
            
        Returns:
            StopLossResult with trigger status and reason
        """
        if buy_price <= 0:
            return StopLossResult(
                triggered=False,
                reason="No buy price",
                loss_pct=0.0
            )
        
        # Calculate current loss
        loss_pct = (buy_price - current_close) / buy_price
        
        # Special Rule for 52-week Breakout
        if signal_type == "52WEEK":
            stop_price = buy_day_low * 0.99
            if current_close < stop_price:
                return StopLossResult(
                    triggered=True,
                    reason=f"52-Week Breakout Stop Loss (Close < 0.99 * DayLow {buy_day_low:.2f})",
                    loss_pct=loss_pct
                )
            # 52-Week breakout ONLY uses this specific stop loss (based on user request? or in addition?)
            # User request says: "đặt dừng lỗ là cách 1% so với mức thấp nhất của ngày hôm đó"
            # It implies this is THE rule.
            return StopLossResult(
                triggered=False,
                reason="OK",
                loss_pct=loss_pct
            )

        # Rule 1: Stop loss from buy price
        if current_close < buy_price * (1 - self.config.stop_loss_pct):
            return StopLossResult(
                triggered=True,
                reason=f"Stop loss: {loss_pct*100:.2f}% loss exceeds {self.config.stop_loss_pct*100}%",
                loss_pct=loss_pct
            )
        
        # Rule 2: Close below buy day low
        if current_close < buy_day_low:
            return StopLossResult(
                triggered=True,
                reason=f"Closed below buy day low ({buy_day_low:.2f}): {loss_pct*100:.2f}% loss",
                loss_pct=loss_pct
            )
        
        # Rule 3: Break below MA50 with higher volume
        # Only trigger if previous close was ABOVE or AT MA50, and now close is BELOW MA50
        if (ma50 is not None and prev_close is not None and prev_ma50 is not None 
            and current_volume is not None and prev_volume is not None):
            # Check if crossing DOWN from above MA50
            if prev_close >= prev_ma50 and current_close < ma50 and current_volume > prev_volume:
                return StopLossResult(
                    triggered=True,
                    reason=f"Break below MA50 ({ma50:.2f}) with high volume: {loss_pct*100:.2f}% loss",
                    loss_pct=loss_pct
                )
        
        return StopLossResult(
            triggered=False,
            reason="OK",
            loss_pct=loss_pct
        )
    
    def check_trigger_break(
        self,
        current_close: float,
        trigger_price: float
    ) -> bool:
        """
        Check if price broke below trigger (for WAITING_SELL state).
        
        Args:
            current_close: Current close price
            trigger_price: Trigger price to break
            
        Returns:
            True if trigger broken
        """
        return current_close < trigger_price
