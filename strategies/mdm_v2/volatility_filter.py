"""
Volatility Filter Module (v6.0, BAND-01, BAND-02)

Suppresses signal switching during low-volatility regimes.
Uses ATR-14 as percentage of close price with percentile-based
thresholds calibrated to VN30's historical ATR distribution.

When disabled, should_suppress() returns False for backward compatibility.
"""

from .config import MDMV2Config


class VolatilityFilter:
    """Suppress signal switching during low-volatility regimes (BAND-02)."""

    def __init__(self, config: MDMV2Config):
        self.config = config

    def should_suppress(self, atr_pct: float) -> bool:
        """Check if current volatility regime is too low for reliable signals.

        Args:
            atr_pct: Current ATR-14 as percentage of close price.

        Returns:
            True if signals should be suppressed (low volatility regime).
        """
        if not self.config.volatility_filter_enabled:
            return False
        return atr_pct < self.config.volatility_low_threshold
