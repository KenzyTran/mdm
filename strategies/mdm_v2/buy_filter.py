"""
BUY Filter Module (v5.0, BUY-01)

Stateless MA10/MA50 trend filter that rejects weak FTD signals
when the short-term trend is bearish (MA10 < MA50).

MA50 breakout and 52-week breakout signals bypass the filter entirely
(per D-01, D-06) since they indicate strong trend confirmation.

When disabled (buy_filter_enabled=False), check() returns True
(allow all signals) for backward compatibility.
"""

from .config import MDMV2Config


class BuyFilter:
    """Gates FTD signals on MA10/MA50 trend alignment."""

    def __init__(self, config: MDMV2Config):
        self.config = config

    def check(self, signal_type: str, ma10: float, ma50: float) -> bool:
        """Check if a buy signal passes the trend filter.

        Args:
            signal_type: Type of signal ("FTD", "MA50", "52WEEK")
            ma10: Current 10-day moving average value (can be None)
            ma50: Current 50-day moving average value (can be None)

        Returns:
            True if signal is allowed, False if rejected.
        """
        if not self.config.buy_filter_enabled:
            return True  # Disabled = allow all

        # MA50 breakout and 52-week breakout bypass the filter (per D-01, D-06)
        if signal_type in ("MA50", "52WEEK"):
            return True

        # Graceful handling of missing MA values
        if ma10 is None or ma50 is None:
            return True

        # Reject FTD when short-term trend is bearish
        return ma10 >= ma50
