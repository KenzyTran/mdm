"""
V2 Stop Loss Module

Check stop loss conditions for long positions with volatility-adaptive scaling.
When enabled, ATR ratio adjusts the effective stop loss percentage.
No SHORT-related stop loss logic (per D-03).
"""

from dataclasses import dataclass

from .config import MDMV2Config


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
    2. Close below buy day low
    3. Break below MA50 with volume higher than previous session
    """

    def __init__(self, config: MDMV2Config = None):
        """Initialize."""
        self.config = config if config else MDMV2Config()

    def _get_effective_stop_pct(self, atr: float = None, atr_baseline: float = None) -> float:
        """Scale stop loss by ATR ratio when volatility_adaptive is enabled.

        Formula: effective_pct = base_pct * (current_atr / baseline_atr)
        Clamped to [base * min_multiplier, base * max_multiplier].

        Args:
            atr: Current ATR value.
            atr_baseline: Baseline ATR (rolling mean).

        Returns:
            Effective stop loss percentage.
        """
        if not self.config.volatility_adaptive:
            return self.config.stop_loss_pct
        if atr is None or atr_baseline is None or atr_baseline <= 0:
            return self.config.stop_loss_pct

        ratio = atr / atr_baseline
        effective = self.config.stop_loss_pct * ratio
        min_pct = self.config.stop_loss_pct * self.config.stop_loss_min_multiplier
        max_pct = self.config.stop_loss_pct * self.config.stop_loss_max_multiplier
        return max(min_pct, min(max_pct, effective))

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
        signal_type: str = "FTD",
        atr: float = None,
        atr_baseline: float = None,
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
            atr: Current ATR value (optional, for volatility-adaptive scaling)
            atr_baseline: Baseline ATR (optional, for volatility-adaptive scaling)

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
            return StopLossResult(
                triggered=False,
                reason="OK",
                loss_pct=loss_pct
            )

        # Rule 1: Stop loss from buy price (volatility-adaptive)
        effective_pct = self._get_effective_stop_pct(atr, atr_baseline)
        if current_close < buy_price * (1 - effective_pct):
            return StopLossResult(
                triggered=True,
                reason=f"Stop loss: {loss_pct*100:.2f}% loss exceeds {effective_pct*100:.1f}%",
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
        if (ma50 is not None and prev_close is not None and prev_ma50 is not None
            and current_volume is not None and prev_volume is not None):
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

    def check_short(
        self,
        current_close: float,
        dd5_high: float,
        short_entry_price: float = 0.0,
    ) -> StopLossResult:
        """Check short position stop loss.

        Rule: Cover short if close > DD5 high * 1.01 (1% above DD5 high).
        Per MDM classic rules section IV.4.

        Args:
            current_close: Current close price.
            dd5_high: High price of the day when DD count reached 5.
            short_entry_price: Entry price for loss calculation.

        Returns:
            StopLossResult with trigger status and reason.
        """
        if dd5_high <= 0:
            return StopLossResult(triggered=False, reason="No DD5 high", loss_pct=0.0)

        short_stop_pct = getattr(self.config, 'short_stop_pct_above_dd5', 0.01)
        stop_price = dd5_high * (1 + short_stop_pct)
        loss_pct = (current_close - short_entry_price) / short_entry_price if short_entry_price > 0 else 0.0

        if current_close > stop_price:
            return StopLossResult(
                triggered=True,
                reason=f"Short stop loss: close {current_close:.2f} > DD5 high {dd5_high:.2f} * {1+short_stop_pct:.2f} = {stop_price:.2f}",
                loss_pct=loss_pct,
            )

        return StopLossResult(triggered=False, reason="OK", loss_pct=loss_pct)
