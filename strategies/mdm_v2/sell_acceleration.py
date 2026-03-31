"""
SELL Acceleration Gate Module (v5.0, SELL-01)

Gates CASH->SELL transitions by requiring at least one downside
acceleration condition before allowing SELL. Three conditions (OR logic, per D-02):
1. Price ROC below threshold (bearish momentum)
2. DD clustering (institutional distribution)
3. Volume-confirmed MA50 breakdown

When disabled (sell_acceleration_enabled=False), check() returns True
(always allow SELL) for backward compatibility.
"""

import pandas as pd
from .config import MDMV2Config


class SellAccelerationGate:
    """Gates SELL transitions on confirmed downside momentum."""

    def __init__(self, config: MDMV2Config):
        self.config = config

    def check(
        self,
        close: float,
        closes_history: pd.Series,
        dd_dates: list,
        date: pd.Timestamp,
        volume: float,
        prev_volume: float,
        ma50: float,
        prev_close: float,
        prev_ma50: float,
    ) -> bool:
        """Return True if at least one acceleration condition is met.

        When sell_acceleration_enabled=False, returns True (allow all SELLs).

        Args:
            close: Current closing price
            closes_history: Series of recent close prices (length >= roc_window + 1)
            dd_dates: List of pd.Timestamp dates from dd_counter.dd_history
            date: Current trading date
            volume: Current day's volume
            prev_volume: Previous day's volume
            ma50: Current 50-day MA value (can be None)
            prev_close: Previous day's close
            prev_ma50: Previous day's MA50 (can be None)

        Returns:
            True if acceleration confirmed (SELL allowed), False otherwise.
        """
        if not self.config.sell_acceleration_enabled:
            return True  # Disabled = always allow SELL

        roc_met = self._check_price_roc(close, closes_history)
        dd_cluster_met = self._check_dd_clustering(dd_dates, date)
        vol_ma50_met = self._check_volume_ma50_breakdown(
            close, ma50, prev_close, prev_ma50, volume, prev_volume
        )
        return roc_met or dd_cluster_met or vol_ma50_met

    def _check_price_roc(self, close: float, closes_history: pd.Series) -> bool:
        """Price rate-of-change below threshold = bearish momentum."""
        if len(closes_history) < self.config.roc_window + 1:
            return False
        past_close = closes_history.iloc[-(self.config.roc_window + 1)]
        if past_close == 0:
            return False
        roc = (close - past_close) / past_close
        return roc < self.config.roc_threshold

    def _check_dd_clustering(self, dd_dates: list, current_date: pd.Timestamp) -> bool:
        """N DDs within M sessions = institutional distribution."""
        if not dd_dates:
            return False
        # Use calendar days * 1.5 to approximate trading days
        window_start = current_date - pd.Timedelta(
            days=int(self.config.dd_cluster_window * 1.5)
        )
        recent_dds = [d for d in dd_dates if d >= window_start]
        return len(recent_dds) >= self.config.dd_cluster_count

    def _check_volume_ma50_breakdown(
        self, close, ma50, prev_close, prev_ma50, volume, prev_volume
    ) -> bool:
        """MA50 breakdown with volume confirmation."""
        if ma50 is None or prev_ma50 is None:
            return False
        breakdown = close < ma50 and prev_close >= prev_ma50
        volume_confirmed = volume > prev_volume
        return breakdown and volume_confirmed
