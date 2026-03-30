"""
Tests for short position mechanics in V2PositionManager.

Covers requirements:
- SHORT-01: Short entry price tracking on SELL
- SHORT-04: Cover short with P&L calculation
- TRANS-01: enter_buy() guard preventing direct SELL->BUY
"""

import pytest
import pandas as pd

from strategies.mdm_hybrid.position_manager import (
    V2PositionManager,
    V2Position,
    V2MarketState,
)
from strategies.mdm_hybrid.config import MDMV2Config, HybridConfig


@pytest.fixture
def manager():
    """Create a fresh V2PositionManager with default config."""
    return V2PositionManager(MDMV2Config())


TEST_DATE = pd.Timestamp("2024-01-15")
COVER_DATE = pd.Timestamp("2024-02-01")


class TestV2PositionShortFields:
    """Tests for V2Position short entry fields (SHORT-01)."""

    def test_v2position_has_short_fields(self):
        """V2Position() has short_entry_price=0.0 and short_entry_date=None."""
        pos = V2Position()
        assert pos.short_entry_price == 0.0
        assert pos.short_entry_date is None

    def test_enter_sell_records_short_fields(self, manager):
        """After enter_sell with price, position tracks short entry."""
        manager.enter_sell(TEST_DATE, "test reason", price=1000.0)
        assert manager.position.short_entry_price == 1000.0
        assert manager.position.short_entry_date == TEST_DATE

    def test_enter_sell_without_price_defaults_zero(self, manager):
        """enter_sell without price keeps backward compatibility."""
        manager.enter_sell(TEST_DATE, "test reason")
        assert manager.position.short_entry_price == 0.0
        assert manager.position.state == V2MarketState.SELL


class TestShortModeConfig:
    """Tests for HybridConfig.short_mode (D-10)."""

    def test_short_mode_config(self):
        """HybridConfig has short_mode defaulting to 'direct'."""
        config = HybridConfig()
        assert config.short_mode == "direct"

        config2 = HybridConfig(short_mode="inverse_etf")
        assert config2.short_mode == "inverse_etf"


class TestCoverShort:
    """Tests for cover_short() method (SHORT-04)."""

    def test_cover_short_transitions_to_cash(self, manager):
        """After enter_sell then cover_short, state is CASH."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(950.0, COVER_DATE, "test cover")
        assert manager.position.state == V2MarketState.CASH

    def test_short_pnl_gain_on_market_drop(self, manager):
        """Short at 1000, cover at 950 -> P&L = +5%."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(950.0, COVER_DATE, "market drop")
        trade = manager.trades[-1]
        assert trade["pnl"] == pytest.approx(0.05)

    def test_short_pnl_loss_on_market_rise(self, manager):
        """Short at 1000, cover at 1030 -> P&L = -3%."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(1030.0, COVER_DATE, "market rise")
        trade = manager.trades[-1]
        assert trade["pnl"] == pytest.approx(-0.03)

    def test_cover_short_trade_record(self, manager):
        """cover_short appends trade with correct keys."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(960.0, COVER_DATE, "cover reason")
        trade = manager.trades[-1]
        assert trade["type"] == "SHORT_COVER"
        assert trade["entry_price"] == 1000.0
        assert "pnl" in trade
        assert trade["reason"] == "cover reason"
        assert trade["date"] == COVER_DATE
        assert trade["price"] == 960.0

    def test_cover_short_resets_short_fields(self, manager):
        """After cover_short, short fields are reset."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(960.0, COVER_DATE, "cover reason")
        assert manager.position.short_entry_price == 0.0
        assert manager.position.short_entry_date is None


class TestEnterBuyGuard:
    """Tests for enter_buy() SELL state guard (TRANS-01)."""

    def test_enter_buy_guard_raises_from_sell(self, manager):
        """enter_buy() when state==SELL raises ValueError."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        with pytest.raises(ValueError, match="Must cover_short"):
            manager.enter_buy(1010.0, COVER_DATE, 1005.0, "FTD")

    def test_enter_buy_works_from_cash(self, manager):
        """enter_buy() from CASH works normally."""
        manager.enter_buy(1010.0, TEST_DATE, 1005.0, "FTD")
        assert manager.position.state == V2MarketState.BUY
        assert manager.position.buy_price == 1010.0
