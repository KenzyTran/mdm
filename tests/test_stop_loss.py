"""
Tests for stop loss with 1.5% default and volatility-adaptive scaling.

Covers RISK-01 (1.5% long stop loss) and RISK-02 (ATR-based adaptive scaling).
"""

import pandas as pd
import numpy as np
import pytest

from strategies.mdm_hybrid.config import MDMV2Config
from strategies.mdm_hybrid.stop_loss import StopLossChecker, StopLossResult
from strategies.mdm_hybrid.indicators import Indicators


class TestConfigDefaults:
    """Test MDMV2Config stop loss defaults."""

    def test_config_stop_loss_default(self):
        """RISK-01: Default stop_loss_pct should be 0.015 (1.5%)."""
        config = MDMV2Config()
        assert config.stop_loss_pct == 0.015

    def test_config_atr_defaults(self):
        """RISK-02: ATR-related config defaults."""
        config = MDMV2Config()
        assert config.atr_period == 14
        assert config.atr_baseline_period == 50
        assert config.volatility_adaptive is True
        assert config.stop_loss_min_multiplier == 0.5
        assert config.stop_loss_max_multiplier == 2.5


class TestLongStopLoss:
    """Test basic stop loss at 1.5% threshold."""

    def test_long_stop_loss_default_1_5_pct(self):
        """RISK-01: Stop loss triggers when close < buy_price * 0.985."""
        config = MDMV2Config()
        checker = StopLossChecker(config)

        buy_price = 100.0
        buy_day_low = 95.0  # Low enough to not trigger Rule 2

        # Close at 98.4 = 1.6% loss -> should trigger (> 1.5%)
        result = checker.check(98.4, buy_price, buy_day_low)
        assert result.triggered is True

        # Close at 98.6 = 1.4% loss -> should NOT trigger (< 1.5%)
        result = checker.check(98.6, buy_price, buy_day_low)
        assert result.triggered is False


class TestATRIndicator:
    """Test ATR column computation."""

    def _make_ohlcv(self, n=20):
        """Create synthetic OHLCV DataFrame with n rows."""
        np.random.seed(42)
        closes = 100 + np.cumsum(np.random.randn(n))
        highs = closes + np.abs(np.random.randn(n)) * 2
        lows = closes - np.abs(np.random.randn(n)) * 2
        opens = closes + np.random.randn(n) * 0.5
        volumes = np.random.randint(1000, 5000, n)
        return pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
        })

    def test_atr_column_computation(self):
        """ATR column is computed correctly as rolling mean of true range."""
        df = self._make_ohlcv(20)
        result = Indicators.add_atr_column(df, period=14)

        assert 'atr' in result.columns
        assert 'true_range' in result.columns
        assert len(result) == 20

        # Verify row 14 (index 14) = mean of true_range[1:15] (14 rows)
        # true_range at row 0 uses just H-L (no prev close)
        expected_atr_14 = result['true_range'].iloc[1:15].mean()
        assert abs(result['atr'].iloc[14] - expected_atr_14) < 1e-10

    def test_atr_column_first_row(self):
        """ATR at row 0 uses min_periods=1, not NaN."""
        df = self._make_ohlcv(5)
        result = Indicators.add_atr_column(df, period=14)

        # First row ATR should not be NaN
        assert pd.notna(result['atr'].iloc[0])


class TestVolatilityAdaptive:
    """Test volatility-adaptive stop loss scaling."""

    def test_volatility_adaptive_high_vol(self):
        """High volatility (ATR 2x baseline) widens stop loss."""
        config = MDMV2Config()  # stop_loss_pct=0.015
        checker = StopLossChecker(config)

        # ATR=30, baseline=15 -> ratio=2.0 -> effective=0.015*2.0=0.03
        buy_price = 100.0
        buy_day_low = 95.0  # won't trigger Rule 2

        # Close at 97.5 = 2.5% loss -> should NOT trigger (effective is 3%)
        result = checker.check(97.5, buy_price, buy_day_low, atr=30.0, atr_baseline=15.0)
        assert result.triggered is False

        # Close at 96.9 = 3.1% loss -> should trigger (> 3%)
        result = checker.check(96.9, buy_price, buy_day_low, atr=30.0, atr_baseline=15.0)
        assert result.triggered is True

    def test_volatility_adaptive_low_vol(self):
        """Low volatility (ATR 0.5x baseline) tightens stop loss."""
        config = MDMV2Config()
        checker = StopLossChecker(config)

        # ATR=7.5, baseline=15 -> ratio=0.5 -> effective=0.015*0.5=0.0075
        buy_price = 100.0
        buy_day_low = 95.0

        # Close at 99.3 = 0.7% loss -> should NOT trigger (< 0.75%)
        result = checker.check(99.3, buy_price, buy_day_low, atr=7.5, atr_baseline=15.0)
        assert result.triggered is False

        # Close at 99.2 = 0.8% loss -> should trigger (> 0.75%)
        result = checker.check(99.2, buy_price, buy_day_low, atr=7.5, atr_baseline=15.0)
        assert result.triggered is True

    def test_volatility_adaptive_clamped_max(self):
        """Extreme high volatility clamped to max multiplier (2.5x)."""
        config = MDMV2Config()
        checker = StopLossChecker(config)

        # ATR=60, baseline=15 -> ratio=4.0 -> clamped to 2.5 -> effective=0.015*2.5=0.0375
        buy_price = 100.0
        buy_day_low = 90.0

        # Close at 96.3 = 3.7% loss -> should NOT trigger (< 3.75%)
        result = checker.check(96.3, buy_price, buy_day_low, atr=60.0, atr_baseline=15.0)
        assert result.triggered is False

        # Close at 96.2 = 3.8% loss -> should trigger (> 3.75%)
        result = checker.check(96.2, buy_price, buy_day_low, atr=60.0, atr_baseline=15.0)
        assert result.triggered is True

    def test_volatility_adaptive_clamped_min(self):
        """Extreme low volatility clamped to min multiplier (0.5x)."""
        config = MDMV2Config()
        checker = StopLossChecker(config)

        # ATR=1.5, baseline=15 -> ratio=0.1 -> clamped to 0.5 -> effective=0.015*0.5=0.0075
        buy_price = 100.0
        buy_day_low = 95.0

        # Close at 99.3 = 0.7% loss -> should NOT trigger (< 0.75%)
        result = checker.check(99.3, buy_price, buy_day_low, atr=1.5, atr_baseline=15.0)
        assert result.triggered is False

        # Close at 99.2 = 0.8% loss -> should trigger (> 0.75%)
        result = checker.check(99.2, buy_price, buy_day_low, atr=1.5, atr_baseline=15.0)
        assert result.triggered is True

    def test_volatility_adaptive_disabled(self):
        """When volatility_adaptive=False, uses base 1.5% stop loss."""
        config = MDMV2Config(volatility_adaptive=False)
        checker = StopLossChecker(config)

        buy_price = 100.0
        buy_day_low = 95.0

        # Even with high ATR, should use base 1.5%
        # Close at 98.4 = 1.6% loss -> triggers at 1.5%
        result = checker.check(98.4, buy_price, buy_day_low, atr=60.0, atr_baseline=15.0)
        assert result.triggered is True

        # Close at 98.6 = 1.4% loss -> does NOT trigger
        result = checker.check(98.6, buy_price, buy_day_low, atr=60.0, atr_baseline=15.0)
        assert result.triggered is False

    def test_check_with_atr_none(self):
        """When atr=None, falls back to base stop_loss_pct without crash."""
        config = MDMV2Config()
        checker = StopLossChecker(config)

        buy_price = 100.0
        buy_day_low = 95.0

        # Should use base 1.5% when atr is None
        result = checker.check(98.4, buy_price, buy_day_low, atr=None, atr_baseline=None)
        assert result.triggered is True

        result = checker.check(98.6, buy_price, buy_day_low, atr=None, atr_baseline=None)
        assert result.triggered is False


class TestDD5HighTracking:
    """Test DD5 high tracking in DistributionDayCounter (RISK-03)."""

    def _make_config(self):
        return MDMV2Config(dd_window_size=20, dd_price_drop_threshold=-0.002)

    def _make_dates(self, n=25):
        return [pd.Timestamp(f"2020-01-{i+1:02d}") for i in range(n)]

    def test_dd_history_stores_date_and_high(self):
        """After check_distribution_day with DD detected, dd_history contains (date, high) tuple."""
        from strategies.mdm_hybrid.distribution_day import DistributionDayCounter
        config = self._make_config()
        counter = DistributionDayCounter(config)
        date = pd.Timestamp("2020-01-05")
        high = 15100.0

        is_dd, dd_type = counter.check_distribution_day(date, high, -0.005, True, 0.5)
        assert is_dd is True
        assert len(counter.dd_history) == 1
        assert counter.dd_history[0] == (date, high)

    def test_dd5_high_returns_5th_dd_high(self):
        """With 5+ DDs in window, get_dd5_high returns the high of the 5th DD day specifically."""
        from strategies.mdm_hybrid.distribution_day import DistributionDayCounter
        config = self._make_config()
        counter = DistributionDayCounter(config)
        dates = self._make_dates(25)
        highs = [15000 + i * 100 for i in range(5)]  # 15000, 15100, 15200, 15300, 15400

        for i in range(5):
            counter.check_distribution_day(dates[i], highs[i], -0.005, True, 0.5)

        dd5_high = counter.get_dd5_high(dates[4], dates)
        assert dd5_high == 15400.0  # High of the 5th DD (index 4)

    def test_dd5_high_returns_zero_when_fewer_than_5(self):
        """With only 3 DDs, get_dd5_high returns 0.0."""
        from strategies.mdm_hybrid.distribution_day import DistributionDayCounter
        config = self._make_config()
        counter = DistributionDayCounter(config)
        dates = self._make_dates(25)

        for i in range(3):
            counter.check_distribution_day(dates[i], 15000 + i * 100, -0.005, True, 0.5)

        dd5_high = counter.get_dd5_high(dates[2], dates)
        assert dd5_high == 0.0

    def test_dd_count_in_window_still_works(self):
        """get_dd_count_in_window returns correct count after dd_history format change."""
        from strategies.mdm_hybrid.distribution_day import DistributionDayCounter
        config = self._make_config()
        counter = DistributionDayCounter(config)
        dates = self._make_dates(25)

        for i in range(3):
            counter.check_distribution_day(dates[i], 15000.0, -0.005, True, 0.5)

        count = counter.get_dd_count_in_window(dates[2], dates)
        assert count == 3

    def test_dd_reset_clears_dd5_high(self):
        """After reset(), dd5_high == 0.0 and dd_history is empty."""
        from strategies.mdm_hybrid.distribution_day import DistributionDayCounter
        config = self._make_config()
        counter = DistributionDayCounter(config)
        dates = self._make_dates(25)

        for i in range(5):
            counter.check_distribution_day(dates[i], 15000 + i * 100, -0.005, True, 0.5)
        counter.get_dd5_high(dates[4], dates)
        assert counter.dd5_high > 0

        counter.reset()
        assert counter.dd5_high == 0.0
        assert len(counter.dd_history) == 0


class TestShortStopLoss:
    """Test check_short() for short position stop loss (RISK-03, SHORT-03)."""

    def test_short_stop_loss_dd5_high(self):
        """check_short(close=15200, dd5_high=15000) triggers (15200 > 15000 * 1.01 = 15150)."""
        config = MDMV2Config()
        checker = StopLossChecker(config)
        result = checker.check_short(15200, 15000)
        assert result.triggered is True

    def test_short_stop_loss_below_threshold(self):
        """check_short(close=15100, dd5_high=15000) does NOT trigger (15100 < 15150)."""
        config = MDMV2Config()
        checker = StopLossChecker(config)
        result = checker.check_short(15100, 15000)
        assert result.triggered is False

    def test_short_stop_loss_no_dd5_high(self):
        """check_short(close=15200, dd5_high=0) returns triggered=False."""
        config = MDMV2Config()
        checker = StopLossChecker(config)
        result = checker.check_short(15200, 0)
        assert result.triggered is False

    def test_short_stop_triggers_cover(self):
        """check_short returns StopLossResult with triggered=True and reason containing 'Short stop loss'."""
        config = MDMV2Config()
        checker = StopLossChecker(config)
        result = checker.check_short(15200, 15000)
        assert result.triggered is True
        assert "Short stop loss" in result.reason

    def test_short_stop_loss_pct_calculation(self):
        """check_short(close=15200, dd5_high=15000, short_entry_price=14800) returns correct loss_pct."""
        config = MDMV2Config()
        checker = StopLossChecker(config)
        result = checker.check_short(15200, 15000, short_entry_price=14800)
        expected_loss = (15200 - 14800) / 14800  # ~0.027
        assert abs(result.loss_pct - expected_loss) < 0.001
