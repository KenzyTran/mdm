"""
Tests for Fail-Safe Mechanism (SAFE-01, SAFE-02).

SAFE-01: Record standby-sell day HIGH as fail_safe_threshold on SELL entry.
SAFE-02: Auto-exit SELL to CASH when close > fail_safe_threshold.
"""

import pytest
import pandas as pd

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.position_manager import V2PositionManager, V2MarketState


class TestFailSafe:
    """Unit tests for fail-safe mechanism."""

    def _make_manager(self, fail_safe_enabled: bool = True) -> V2PositionManager:
        """Create a V2PositionManager with specified fail-safe config."""
        config = MDMV2Config(fail_safe_enabled=fail_safe_enabled)
        return V2PositionManager(config)

    def _enter_sell_state(self, pm: V2PositionManager, threshold: float = 1200.0):
        """Put position manager into SELL state with given threshold."""
        date = pd.Timestamp("2024-01-15")
        pm.enter_sell(date, "test sell reason", fail_safe_threshold=threshold)

    def _process_day(self, pm: V2PositionManager, close: float, is_ftd: bool = False):
        """Call process_day with minimal args for SELL state testing."""
        date = pd.Timestamp("2024-01-16")
        return pm.process_day(
            date=date,
            high=close + 5.0,
            low=close - 5.0,
            close=close,
            is_ftd=is_ftd,
            ftd_price=close if is_ftd else 0.0,
            dd_count=0,
            is_dd=False,
            stop_loss_triggered=False,
            stop_loss_reason="",
            signal_type="FTD" if is_ftd else "",
            ma10=None,
            ma50=None,
            suppress_sell=False,
            acceleration_met=True,
        )

    def test_sell_records_threshold(self):
        """enter_sell records fail_safe_threshold in position."""
        pm = self._make_manager()
        self._enter_sell_state(pm, threshold=1200.5)
        assert pm.position.fail_safe_threshold == 1200.5

    def test_threshold_is_prev_day_high(self):
        """enter_sell with fail_safe_threshold=prev_high stores that value."""
        pm = self._make_manager()
        prev_high = 1155.75
        date = pd.Timestamp("2024-01-15")
        pm.enter_sell(date, "MA50 breakdown", fail_safe_threshold=prev_high)
        assert pm.position.fail_safe_threshold == prev_high
        # Threshold should be prev_high, NOT some other value
        assert pm.position.fail_safe_threshold != 0.0

    def test_fail_safe_triggers_cash(self):
        """Close > threshold in SELL state triggers transition to CASH."""
        pm = self._make_manager()
        self._enter_sell_state(pm, threshold=1200.0)
        assert pm.position.state == V2MarketState.SELL

        state, action = self._process_day(pm, close=1201.0)
        assert state == V2MarketState.CASH
        assert "fail-safe" in action.lower()

    def test_no_trigger_below_threshold(self):
        """Close <= threshold in SELL state keeps SELL state."""
        pm = self._make_manager()
        self._enter_sell_state(pm, threshold=1200.0)

        state, action = self._process_day(pm, close=1199.0)
        assert state == V2MarketState.SELL

    def test_fail_safe_trade_annotation(self):
        """Fail-safe exit creates trade record with FAIL_SAFE_EXIT type."""
        pm = self._make_manager()
        self._enter_sell_state(pm, threshold=1200.0)
        self._process_day(pm, close=1201.0)

        trades = pm.get_trades()
        fail_safe_trades = [t for t in trades if t['type'] == 'FAIL_SAFE_EXIT']
        assert len(fail_safe_trades) == 1
        assert "1200.00" in fail_safe_trades[0]['reason']

    def test_disabled_no_trigger(self):
        """fail_safe_enabled=False prevents fail-safe trigger."""
        pm = self._make_manager(fail_safe_enabled=False)
        self._enter_sell_state(pm, threshold=1200.0)

        state, action = self._process_day(pm, close=1201.0)
        assert state == V2MarketState.SELL

    def test_fail_safe_priority_over_ftd(self):
        """Fail-safe fires BEFORE FTD check: close > threshold AND is_ftd -> CASH, not BUY."""
        pm = self._make_manager()
        self._enter_sell_state(pm, threshold=1200.0)

        state, action = self._process_day(pm, close=1201.0, is_ftd=True)
        assert state == V2MarketState.CASH
        assert "fail-safe" in action.lower()
