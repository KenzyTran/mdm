"""Tests for V2PositionManager state machine transitions."""

import pytest
import pandas as pd
from strategies.mdm_v2.position_manager import V2MarketState, V2PositionManager
from strategies.mdm_v2.config import MDMV2Config


class TestV2MarketStateEnum:
    """Test V2MarketState enum definition."""

    def test_has_buy_state(self):
        assert V2MarketState.BUY.value == "BUY"

    def test_has_cash_state(self):
        assert V2MarketState.CASH.value == "CASH"

    def test_has_sell_state(self):
        assert V2MarketState.SELL.value == "SELL"

    def test_exactly_three_members(self):
        assert len(V2MarketState) == 3

    def test_no_short_state(self):
        member_names = [m.name for m in V2MarketState]
        assert "SHORT" not in member_names

    def test_no_waiting_sell_state(self):
        member_names = [m.name for m in V2MarketState]
        assert "WAITING_SELL" not in member_names


class TestV2PositionManagerInit:
    """Test initial state."""

    def test_initial_state_is_cash(self):
        pm = V2PositionManager(MDMV2Config())
        assert pm.get_state() == V2MarketState.CASH


class TestCashToBuyTransition:
    """Test CASH -> BUY transitions."""

    def test_ftd_triggers_buy(self):
        pm = V2PositionManager(MDMV2Config())
        date = pd.Timestamp("2020-01-15")
        state, action = pm.process_day(
            date=date, high=105, low=99, close=103,
            is_ftd=True, ftd_price=103, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )
        assert state == V2MarketState.BUY
        assert "BUY" in action


class TestBuyToCashTransition:
    """Test BUY -> CASH transitions."""

    def _enter_buy(self, pm):
        """Helper to enter BUY state."""
        date = pd.Timestamp("2020-01-15")
        pm.process_day(
            date=date, high=105, low=99, close=103,
            is_ftd=True, ftd_price=103, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )

    def test_dd_threshold_triggers_cash(self):
        config = MDMV2Config(dd_cash_threshold=5)
        pm = V2PositionManager(config)
        self._enter_buy(pm)

        date = pd.Timestamp("2020-02-01")
        state, action = pm.process_day(
            date=date, high=104, low=98, close=100,
            is_ftd=False, ftd_price=0, dd_count=5, is_dd=True,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )
        assert state == V2MarketState.CASH
        assert "CASH" in action

    def test_ma10_consecutive_triggers_cash(self):
        config = MDMV2Config(ma10_cash_consecutive=2)
        pm = V2PositionManager(config)
        self._enter_buy(pm)

        # Day 1: close below MA10
        date1 = pd.Timestamp("2020-02-01")
        state1, _ = pm.process_day(
            date=date1, high=104, low=98, close=99,
            is_ftd=False, ftd_price=0, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )
        assert state1 == V2MarketState.BUY  # not yet 2 consecutive

        # Day 2: close below MA10 again
        date2 = pd.Timestamp("2020-02-02")
        state2, action = pm.process_day(
            date=date2, high=104, low=98, close=98,
            is_ftd=False, ftd_price=0, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )
        assert state2 == V2MarketState.CASH

    def test_stop_loss_triggers_cash_not_sell(self):
        pm = V2PositionManager(MDMV2Config())
        self._enter_buy(pm)

        date = pd.Timestamp("2020-02-01")
        state, action = pm.process_day(
            date=date, high=104, low=95, close=96,
            is_ftd=False, ftd_price=0, dd_count=0, is_dd=False,
            stop_loss_triggered=True, stop_loss_reason="Stop loss hit",
            ma10=101, ma50=100
        )
        assert state == V2MarketState.CASH
        assert state != V2MarketState.SELL


class TestCashToSellTransition:
    """Test CASH -> SELL transitions."""

    def _enter_cash_from_buy(self, pm):
        """Helper: enter BUY then exit to CASH via DD threshold."""
        # Enter BUY
        pm.process_day(
            date=pd.Timestamp("2020-01-15"), high=105, low=99, close=103,
            is_ftd=True, ftd_price=103, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )
        # Exit to CASH via DD threshold
        pm.process_day(
            date=pd.Timestamp("2020-02-01"), high=104, low=98, close=100,
            is_ftd=False, ftd_price=0, dd_count=5, is_dd=True,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )

    def test_ma50_breakdown_triggers_sell(self):
        config = MDMV2Config(ma50_sell_enabled=True)
        pm = V2PositionManager(config)
        self._enter_cash_from_buy(pm)

        date = pd.Timestamp("2020-02-05")
        state, action = pm.process_day(
            date=date, high=99, low=88, close=89,
            is_ftd=False, ftd_price=0, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=95, ma50=92
        )
        assert state == V2MarketState.SELL

    def test_cash_deterioration_triggers_sell(self):
        config = MDMV2Config(cash_deterioration_days=3, ma50_sell_enabled=False)
        pm = V2PositionManager(config)
        self._enter_cash_from_buy(pm)

        # Spend 3 days in CASH (days_in_cash increments each process_day while in CASH)
        for i in range(3):
            date = pd.Timestamp(f"2020-02-0{2+i}")
            state, action = pm.process_day(
                date=date, high=102, low=99, close=101,
                is_ftd=False, ftd_price=0, dd_count=0, is_dd=False,
                stop_loss_triggered=False, stop_loss_reason="",
                ma10=101, ma50=100
            )

        assert state == V2MarketState.SELL


class TestSellToBuyTransition:
    """Test SELL -> BUY transitions."""

    def _enter_sell_state(self, pm):
        """Helper: enter BUY -> CASH -> SELL."""
        # Enter BUY
        pm.process_day(
            date=pd.Timestamp("2020-01-15"), high=105, low=99, close=103,
            is_ftd=True, ftd_price=103, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )
        # Exit to CASH
        pm.process_day(
            date=pd.Timestamp("2020-02-01"), high=104, low=98, close=100,
            is_ftd=False, ftd_price=0, dd_count=5, is_dd=True,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=101, ma50=100
        )
        # Enter SELL via MA50 breakdown
        pm.process_day(
            date=pd.Timestamp("2020-02-05"), high=99, low=88, close=89,
            is_ftd=False, ftd_price=0, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=95, ma50=92
        )

    def test_ftd_in_sell_transitions_to_buy(self):
        pm = V2PositionManager(MDMV2Config())
        self._enter_sell_state(pm)
        assert pm.get_state() == V2MarketState.SELL

        date = pd.Timestamp("2020-03-01")
        state, action = pm.process_day(
            date=date, high=95, low=90, close=94,
            is_ftd=True, ftd_price=94, dd_count=0, is_dd=False,
            stop_loss_triggered=False, stop_loss_reason="",
            ma10=91, ma50=90
        )
        assert state == V2MarketState.BUY
        assert "BUY" in action
