"""
Tests for BUY Selectivity Gates (BUY-01, BUY-02).

BuyFilter: MA10/MA50 trend filter to reject weak FTD signals.
BuyConfirmation: Post-FTD confirmation window tracker.
"""

import pytest
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.buy_filter import BuyFilter
from strategies.mdm_v2.buy_confirmation import BuyConfirmation


# ---------------------------------------------------------------------------
# TestBuyFilter
# ---------------------------------------------------------------------------

class TestBuyFilter:
    """Unit tests for BuyFilter (BUY-01)."""

    def test_ftd_rejected_when_ma10_below_ma50(self):
        """FTD rejected when MA10 < MA50."""
        config = MDMV2Config(buy_filter_enabled=True)
        bf = BuyFilter(config)
        assert bf.check("FTD", 100.0, 105.0) is False

    def test_ftd_allowed_when_ma10_above_ma50(self):
        """FTD allowed when MA10 >= MA50."""
        config = MDMV2Config(buy_filter_enabled=True)
        bf = BuyFilter(config)
        assert bf.check("FTD", 110.0, 105.0) is True

    def test_ftd_allowed_when_ma10_equals_ma50(self):
        """FTD allowed when MA10 == MA50 (edge case)."""
        config = MDMV2Config(buy_filter_enabled=True)
        bf = BuyFilter(config)
        assert bf.check("FTD", 105.0, 105.0) is True

    def test_ma50_breakout_bypasses_filter(self):
        """MA50 breakout bypasses filter regardless of MA relationship (per D-01)."""
        config = MDMV2Config(buy_filter_enabled=True)
        bf = BuyFilter(config)
        assert bf.check("MA50", 100.0, 105.0) is True

    def test_52week_breakout_bypasses_filter(self):
        """52-week breakout bypasses filter regardless of MA relationship (per D-06)."""
        config = MDMV2Config(buy_filter_enabled=True)
        bf = BuyFilter(config)
        assert bf.check("52WEEK", 100.0, 105.0) is True

    def test_filter_disabled_allows_all(self):
        """When buy_filter_enabled=False, all signals pass."""
        config = MDMV2Config(buy_filter_enabled=False)
        bf = BuyFilter(config)
        assert bf.check("FTD", 100.0, 105.0) is True

    def test_none_ma_values_allow_ftd(self):
        """None MA values gracefully allow FTD."""
        config = MDMV2Config(buy_filter_enabled=True)
        bf = BuyFilter(config)
        assert bf.check("FTD", None, None) is True
        assert bf.check("FTD", 100.0, None) is True
        assert bf.check("FTD", None, 105.0) is True


# ---------------------------------------------------------------------------
# TestBuyConfirmation
# ---------------------------------------------------------------------------

class TestBuyConfirmation:
    """Unit tests for BuyConfirmation (BUY-02)."""

    def test_clean_window_confirms_after_3_days(self):
        """3 clean days -> confirmed with day-3 close."""
        config = MDMV2Config(buy_confirmation_enabled=True, confirmation_window_days=3, confirmation_max_dd=1)
        bc = BuyConfirmation(config)
        bc.submit_ftd("2024-01-01")
        confirmed, rejected, price = bc.process_day(is_dd=False, close=100.0)
        assert confirmed is False
        confirmed, rejected, price = bc.process_day(is_dd=False, close=101.0)
        assert confirmed is False
        confirmed, rejected, price = bc.process_day(is_dd=False, close=102.0)
        assert confirmed is True
        assert rejected is False
        assert price == 102.0

    def test_single_dd_tolerated(self):
        """One DD within window is tolerated (max_dd=1)."""
        config = MDMV2Config(buy_confirmation_enabled=True, confirmation_window_days=3, confirmation_max_dd=1)
        bc = BuyConfirmation(config)
        bc.submit_ftd("2024-01-01")
        bc.process_day(is_dd=True, close=99.0)   # 1 DD, still under max
        bc.process_day(is_dd=False, close=100.0)
        confirmed, rejected, price = bc.process_day(is_dd=False, close=101.0)
        assert confirmed is True
        assert rejected is False
        assert price == 101.0

    def test_two_dd_cancels(self):
        """Two DDs cancel the FTD (exceeds max_dd=1)."""
        config = MDMV2Config(buy_confirmation_enabled=True, confirmation_window_days=3, confirmation_max_dd=1)
        bc = BuyConfirmation(config)
        bc.submit_ftd("2024-01-01")
        bc.process_day(is_dd=True, close=99.0)
        confirmed, rejected, price = bc.process_day(is_dd=True, close=98.0)
        assert confirmed is False
        assert rejected is True
        assert price == 0.0

    def test_entry_price_is_day3_close(self):
        """Confirmed entry price is day-3 close, not FTD price."""
        config = MDMV2Config(buy_confirmation_enabled=True, confirmation_window_days=3, confirmation_max_dd=1)
        bc = BuyConfirmation(config)
        bc.submit_ftd("2024-01-01")
        bc.process_day(is_dd=False, close=500.0)
        bc.process_day(is_dd=False, close=510.0)
        confirmed, rejected, price = bc.process_day(is_dd=False, close=520.0)
        assert confirmed is True
        assert price == 520.0  # Day-3 close, not any earlier price

    def test_confirmation_disabled_noop(self):
        """When disabled, submit_ftd is noop, process_day returns (False, False, 0.0)."""
        config = MDMV2Config(buy_confirmation_enabled=False)
        bc = BuyConfirmation(config)
        bc.submit_ftd("2024-01-01")
        confirmed, rejected, price = bc.process_day(is_dd=False, close=100.0)
        assert confirmed is False
        assert rejected is False
        assert price == 0.0

    def test_new_ftd_resets_window(self):
        """Submitting a new FTD resets the counter."""
        config = MDMV2Config(buy_confirmation_enabled=True, confirmation_window_days=3, confirmation_max_dd=1)
        bc = BuyConfirmation(config)
        bc.submit_ftd("2024-01-01")
        bc.process_day(is_dd=False, close=100.0)  # day 1
        bc.submit_ftd("2024-01-03")  # reset
        bc.process_day(is_dd=False, close=101.0)  # day 1 again
        bc.process_day(is_dd=False, close=102.0)  # day 2
        confirmed, rejected, price = bc.process_day(is_dd=False, close=103.0)  # day 3
        assert confirmed is True
        assert price == 103.0

    def test_pending_state(self):
        """is_pending() tracks active confirmation window."""
        config = MDMV2Config(buy_confirmation_enabled=True, confirmation_window_days=3, confirmation_max_dd=1)
        bc = BuyConfirmation(config)
        assert bc.is_pending() is False
        bc.submit_ftd("2024-01-01")
        assert bc.is_pending() is True
        bc.process_day(is_dd=False, close=100.0)
        bc.process_day(is_dd=False, close=101.0)
        bc.process_day(is_dd=False, close=102.0)  # confirms
        assert bc.is_pending() is False

    def test_day3_dd_cancels_if_over_max(self):
        """Day-3 DD that pushes total over max -> rejected (DD checked before completion, per pitfall 4)."""
        config = MDMV2Config(buy_confirmation_enabled=True, confirmation_window_days=3, confirmation_max_dd=1)
        bc = BuyConfirmation(config)
        bc.submit_ftd("2024-01-01")
        bc.process_day(is_dd=True, close=99.0)   # 1 DD
        bc.process_day(is_dd=False, close=100.0)  # clean
        confirmed, rejected, price = bc.process_day(is_dd=True, close=101.0)  # 2nd DD on day 3
        assert confirmed is False
        assert rejected is True
        assert price == 0.0


# ---------------------------------------------------------------------------
# TestConfigBuySelectivity
# ---------------------------------------------------------------------------

class TestConfigBuySelectivity:
    """Tests for buy selectivity config fields."""

    def test_config_defaults(self):
        """Config has correct defaults for buy selectivity fields."""
        config = MDMV2Config()
        assert config.buy_filter_enabled is True
        assert config.buy_confirmation_enabled is True
        assert config.confirmation_window_days == 3
        assert config.confirmation_max_dd == 1

    def test_config_validation_window_zero(self):
        """confirmation_window_days=0 raises AssertionError."""
        with pytest.raises(AssertionError, match="Confirmation window must be positive"):
            MDMV2Config(confirmation_window_days=0)

    def test_config_validation_max_dd_negative(self):
        """confirmation_max_dd=-1 raises AssertionError."""
        with pytest.raises(AssertionError, match="Confirmation max DD must be non-negative"):
            MDMV2Config(confirmation_max_dd=-1)
