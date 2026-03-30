"""
Tests for short position equity curve tracking in V2PerformanceAnalyzer.

Covers requirements:
- SHORT-02: Inverse return calculation during SELL state
- TRANS-02: long_only_equity flag for comparison baseline
"""

import pytest
import pandas as pd
import numpy as np

from strategies.mdm_hybrid.performance import V2PerformanceAnalyzer


# --- Test helpers ---

def make_results_df(closes, states):
    """Build a synthetic results DataFrame.

    Args:
        closes: List of close prices.
        states: List of state strings (BUY, CASH, SELL).

    Returns:
        DataFrame with columns: date, close, state.
    """
    n = len(closes)
    dates = pd.bdate_range(start="2020-01-02", periods=n)
    return pd.DataFrame({
        "date": dates,
        "close": closes,
        "state": states,
    })


def make_trades(trade_specs):
    """Build list of trade dicts from (type, pnl) tuples."""
    trades = []
    for t_type, pnl in trade_specs:
        trade = {"type": t_type, "pnl": pnl, "date": "2020-01-15", "price": 100.0}
        trades.append(trade)
    return trades


# --- SHORT-02: Short equity curve tests ---


class TestShortEquityCurve:
    """Tests for short position inverse return in equity curve."""

    def test_sell_state_market_drop_equity_increases(self):
        """SELL state with market drop (close 100->95) produces equity increase.

        Short position gains when market drops.
        equity[1] = 1.0 * (100/95) = 1.05263...
        """
        closes = [100, 95]
        states = ["SELL", "SELL"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        eq = analyzer.equity
        expected = 1.0 * (100 / 95)
        assert eq.iloc[1] == pytest.approx(expected, rel=1e-6)

    def test_sell_state_market_rise_equity_decreases(self):
        """SELL state with market rise (close 100->105) produces equity decrease.

        Short position loses when market rises.
        equity[1] = 1.0 * (100/105) = 0.95238...
        """
        closes = [100, 105]
        states = ["SELL", "SELL"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        eq = analyzer.equity
        expected = 1.0 * (100 / 105)
        assert eq.iloc[1] == pytest.approx(expected, rel=1e-6)

    def test_mixed_sequence_buy_sell_cash(self):
        """Mixed sequence BUY->SELL->CASH captures correct returns.

        States: [BUY, BUY, SELL, CASH, CASH]
        Closes: [100, 110, 105, 100, 102]

        Day 0: equity = 1.0
        Day 1: prev=BUY -> long return: 1.0 * (110/100) = 1.1
        Day 2: prev=BUY -> long return: 1.1 * (105/110) = 1.05
        Day 3: prev=SELL -> short (inverse) return: 1.05 * (105/100) = 1.1025
        Day 4: prev=CASH -> flat: 1.1025
        """
        closes = [100, 110, 105, 100, 102]
        states = ["BUY", "BUY", "SELL", "CASH", "CASH"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        eq = analyzer.equity

        assert eq.iloc[0] == pytest.approx(1.0)
        assert eq.iloc[1] == pytest.approx(1.1, rel=1e-6)
        assert eq.iloc[2] == pytest.approx(1.05, rel=1e-6)
        # Day 3: prev=SELL, inverse return: closes[2]/closes[3] = 105/100 = 1.05
        assert eq.iloc[3] == pytest.approx(1.05 * (105 / 100), rel=1e-6)
        # Day 4: prev=CASH -> flat
        assert eq.iloc[4] == pytest.approx(1.05 * (105 / 100), rel=1e-6)

    def test_long_only_equity_sell_treated_as_cash(self):
        """long_only_equity=True makes SELL days behave like CASH (equity unchanged).

        Same data as test_sell_state_market_drop but with long_only_equity=True.
        """
        closes = [100, 95]
        states = ["SELL", "SELL"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df, long_only_equity=True)
        eq = analyzer.equity
        # SELL treated as flat -> equity unchanged
        assert eq.iloc[1] == pytest.approx(1.0)

    def test_manual_short_trade_verification(self):
        """Manual verification: SHORT_COVER trades match equity curve movement.

        Scenario: 5 days in SELL, market drops 100->95->90->92->88
        Then cover at 88.

        Trade: short entry at 100, cover at 88 -> pnl = (100-88)/100 = 0.12

        Equity curve should show:
        Day 0: 1.0
        Day 1: 1.0 * (100/95) = 1.05263
        Day 2: 1.05263 * (95/90) = 1.11111
        Day 3: 1.11111 * (90/92) = 1.08696 (market bounced up, short loses)
        Day 4: 1.08696 * (92/88) = 1.13636

        Total short equity gain: 1.13636 - 1.0 = 0.13636 (13.6%)
        Cumulative: closes[0]/closes[4] = 100/88 = 1.13636 -- matches!
        """
        closes = [100, 95, 90, 92, 88]
        states = ["SELL", "SELL", "SELL", "SELL", "SELL"]
        trades = [
            {"type": "SELL_SIGNAL", "pnl": 0, "date": "2020-01-02", "price": 100.0},
            {"type": "SHORT_COVER", "pnl": 0.12, "date": "2020-01-08",
             "price": 88.0, "entry_price": 100.0},
        ]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df, trades=trades)
        eq = analyzer.equity

        # Verify each day
        assert eq.iloc[0] == pytest.approx(1.0)
        assert eq.iloc[1] == pytest.approx(100 / 95, rel=1e-5)
        assert eq.iloc[2] == pytest.approx(100 / 90, rel=1e-5)
        assert eq.iloc[3] == pytest.approx(100 / 92, rel=1e-5)
        assert eq.iloc[4] == pytest.approx(100 / 88, rel=1e-5)

    def test_win_rate_includes_short_cover_trades(self):
        """win_rate() includes SHORT_COVER trades when computing combined rate.

        Trades: 2 CASH_EXIT (1 win, 1 loss), 2 SHORT_COVER (2 wins)
        Combined: 3 wins / 4 exits = 0.75
        """
        trades = make_trades([
            ("CASH_EXIT", 0.05),      # win
            ("CASH_EXIT", -0.02),     # loss
            ("SHORT_COVER", 0.03),    # win
            ("SHORT_COVER", 0.01),    # win
            ("BUY", 0.0),            # ignored
            ("SELL_SIGNAL", 0.0),    # ignored
        ])
        closes = [100, 100]
        states = ["CASH", "CASH"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df, trades)
        assert analyzer.win_rate() == pytest.approx(3.0 / 4.0, rel=1e-6)
