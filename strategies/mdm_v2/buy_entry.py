"""
Buy Entry Filter Module (v6.0, GAP-01, RALLY-01)

Handles two buy-entry refinements:
1. Gap-up invalidation: rejects FTD when intraday low < previous close (per D-02)
2. Rally threshold: allows early FTD in shallow pullbacks < 6% (per D-06)

MA50 breakout and 52-week breakout bypass gap filter (per D-01).
When disabled, methods return permissive defaults for backward compatibility.
"""

from .config import MDMV2Config


class BuyEntryFilter:
    """Buy entry refinement: gap-up invalidation and rally threshold."""

    def __init__(self, config: MDMV2Config):
        self.config = config

    def check_gap(self, signal_type: str, low: float, prev_close: float) -> bool:
        """Check if buy signal passes gap-up filter.

        Args:
            signal_type: Type of signal ("FTD", "MA50", "52WEEK")
            low: Intraday low of the signal day
            prev_close: Previous day's close price

        Returns:
            True if signal is allowed, False if gap-up broken (reject).
        """
        if not self.config.gap_filter_enabled:
            return True
        if signal_type in ("MA50", "52WEEK"):
            return True
        return low >= prev_close

    def should_allow_early_ftd(self, drawdown_pct: float) -> bool:
        """Check if FTD can trigger without day-3+ requirement.

        Args:
            drawdown_pct: Current drawdown from peak (negative value, e.g. -0.04 = 4%)

        Returns:
            True if shallow pullback (decline < 6%), allowing early FTD.
            False if deep correction or feature disabled.
        """
        if not self.config.rally_threshold_enabled:
            return False
        return drawdown_pct > self.config.rally_threshold_pct
