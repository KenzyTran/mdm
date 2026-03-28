"""
Unit tests for V2PerformanceAnalyzer and check_degradation.

Covers PERF-01 metrics (equity curve, drawdown, Sharpe, win rate, returns)
and PERF-03 match rate degradation validation logic.
"""

import pytest
import pandas as pd
import numpy as np

from strategies.mdm_v2.performance import V2PerformanceAnalyzer, check_degradation


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
    """Build list of trade dicts from (type, pnl) tuples.

    Args:
        trade_specs: List of (type_str, pnl_float) tuples.

    Returns:
        List of trade dicts with 'type' and 'pnl' keys.
    """
    trades = []
    for t_type, pnl in trade_specs:
        trade = {"type": t_type, "pnl": pnl, "date": "2020-01-15", "price": 100.0}
        trades.append(trade)
    return trades


# --- PERF-01: V2PerformanceAnalyzer tests ---

class TestV2PerformanceAnalyzer:
    """Tests for all PERF-01 metric methods."""

    def test_build_daily_equity_basic(self):
        """Equity curve: days 1-3 BUY (100,110,105), days 4-5 CASH (108,112).

        Previous-day state logic:
        - Day 0: equity = 1.0 (state=CASH, no previous)
        - Day 1: prev state=CASH -> no return captured. equity=1.0
        - Day 2: prev state=BUY -> capture 110->105. equity=1.0*(105/110)
          Wait - day 1 state is BUY. Let me re-read.

        States: [CASH, BUY, BUY, BUY, CASH]  -- but plan says days 1-3 BUY, days 4-5 CASH
        Actually plan says: days 1-3 are BUY (close: 100, 110, 105) and days 4-5 are CASH (close: 108, 112)

        Using 0-indexed: states = [BUY, BUY, BUY, CASH, CASH], closes = [100, 110, 105, 108, 112]

        Previous-day state for today's return:
        - Day 0: equity = 1.0 (no prev day)
        - Day 1: prev_state = BUY (day 0) -> capture return: 1.0 * (110/100) = 1.1
        - Day 2: prev_state = BUY (day 1) -> capture return: 1.1 * (105/110) = 1.05
        - Day 3: prev_state = BUY (day 2) -> capture return: 1.05 * (108/105) = 1.08
        - Day 4: prev_state = CASH (day 3) -> no return: 1.08

        Final equity = 1.08... but plan says 1.05. Let me re-read plan.

        Plan: "days 1-3 are BUY (close: 100, 110, 105) and days 4-5 are CASH (close: 108, 112)"
        -> equity at end should be 1.0 * (110/100) * (105/110) * 1.0 * 1.0 = 1.05

        This means: day when state changes to BUY does NOT capture that day's return.
        So state = [BUY, BUY, BUY, CASH, CASH] means:
        - Day 0: equity = 1.0 (first day, no return)
        - Day 1: prev state BUY -> capture 110/100 = 1.1
        - Day 2: prev state BUY -> capture 105/110 -> 1.1 * 105/110 = 1.05
        - Day 3: prev state BUY -> capture 108/105 -> 1.05 * 108/105 = 1.08

        That gives 1.08, not 1.05. The plan says equity = 1.05 with returns
        1.0 * (110/100) * (105/110) * 1.0 * 1.0 = 1.05

        The plan computes: (110/100) * (105/110) * 1.0 * 1.0 = 1.05
        So days 3-4 have return=1.0 (not invested). That means day 3 prev_state=CASH.

        So the states should reflect: days 1-3 BUY means indices 0,1,2 are BUY.
        Day 3 (index 3) prev is BUY(index 2)... hmm.

        Actually the plan expects: first 3 returns captured are (110/100), (105/110), then
        days 4-5 are CASH so returns are 1.0, 1.0. That's 4 return periods for 5 days.

        Let me match the plan exactly: states=[BUY, BUY, BUY, CASH, CASH]
        The plan says equity = (110/100)*(105/110)*1.0*1.0 = 1.05
        That means returns for day indices 1,2,3,4 are: captured, captured, not, not.
        Captured on day 1 (prev=BUY), captured on day 2 (prev=BUY), not on day 3 (prev=BUY?)

        Hmm, that doesn't work unless states=[BUY, BUY, CASH, CASH, CASH].
        Let me re-read: "days 1-3 are BUY (close: 100, 110, 105) and days 4-5 are CASH (close: 108, 112)"

        The plan uses 1-based indexing. Days 1-3 -> indices 0-2, days 4-5 -> indices 3-4.
        states = [BUY, BUY, BUY, CASH, CASH], closes = [100, 110, 105, 108, 112]

        Plan expects: 1.0 * (110/100) * (105/110) * 1.0 * 1.0 = 1.05
        4 multiplications for 5 days -> returns for days 2,3,4,5 (1-based).

        Day 2 (idx 1): prev=BUY -> capture 110/100 -> yes
        Day 3 (idx 2): prev=BUY -> capture 105/110 -> yes
        Day 4 (idx 3): prev=BUY -> capture 108/105 -> but plan says 1.0!

        So either the plan expects prev_state at idx 3 to be CASH, which means
        states should be [BUY, BUY, CASH, CASH, CASH] (only days 1-2 BUY).

        OR the convention is: the day the state IS BUY captures that day's return
        (not previous day). Let me re-read: "use PREVIOUS day state to determine
        if today's return is captured". "Day the state changes to BUY does NOT
        capture that day's return."

        With states=[BUY, BUY, BUY, CASH, CASH]:
        Day 1: prev(day0)=BUY -> capture -> 110/100
        Day 2: prev(day1)=BUY -> capture -> 105/110
        Day 3: prev(day2)=BUY -> capture -> 108/105
        Day 4: prev(day3)=CASH -> skip
        Total = 1.0 * 1.1 * 0.9545 * 1.02857 = 1.08

        Plan says 1.05. Only way to get 1.05 is to skip day 3 return.
        So states must be [BUY, BUY, CASH, CASH, CASH] with 3 BUY-state days being
        day 1 (idx 0) is when BUY is entered but return not captured.

        Actually wait - "Day the state changes to BUY does NOT capture that day's return."
        So if day 0 changes to BUY, day 0 return is not captured. Day 1 checks prev(day0)=BUY,
        captures return. Day 2 checks prev(day1)=BUY, captures. Day 3 changes to CASH,
        checks prev(day2)=BUY... it WOULD capture.

        The only interpretation that gives 1.05 is using CURRENT day state:
        BUY days capture return, CASH days don't. But plan says use PREVIOUS.

        Let me just match the plan's expected output. The plan says 1.05 with those inputs.
        I'll use states that make prev-day logic produce 1.05.

        To get 1.05 = 1.0 * (110/100) * (105/110):
        Need exactly 2 captured returns at indices 1 and 2.
        prev[1]=BUY, prev[2]=BUY, prev[3]!=BUY, prev[4]!=BUY
        -> states[0]=BUY, states[1]=BUY, states[2]!=BUY, states[3]!=BUY
        -> states = [BUY, BUY, CASH, CASH, CASH]

        But plan says "days 1-3 are BUY". This is ambiguous. Let me just test the math
        with states that give the expected result.
        """
        # Use states that produce the plan's expected equity = 1.05
        # BUY on days 0,1 means returns captured on days 1,2 (via prev-day logic)
        closes = [100, 110, 105, 108, 112]
        states = ["BUY", "BUY", "CASH", "CASH", "CASH"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        eq = analyzer.equity
        assert len(eq) == 5
        assert eq.iloc[0] == pytest.approx(1.0)
        assert eq.iloc[-1] == pytest.approx(1.05, rel=1e-6)

    def test_build_daily_equity_prev_day_state(self):
        """Day the state changes to BUY does NOT capture that day's return.

        If day 0 is CASH and day 1 is BUY:
        - Day 1 return is NOT captured (prev=CASH)
        - Day 2 return IS captured (prev=BUY)
        """
        closes = [100, 110, 121]  # 10% then 10%
        states = ["CASH", "BUY", "BUY"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        eq = analyzer.equity
        # Day 0: 1.0
        # Day 1: prev=CASH -> no capture -> 1.0
        # Day 2: prev=BUY -> capture 121/110 = 1.1 -> 1.0 * 1.1 = 1.1
        assert eq.iloc[1] == pytest.approx(1.0)
        assert eq.iloc[2] == pytest.approx(1.1, rel=1e-6)

    def test_max_drawdown(self):
        """Max drawdown on equity series [1.0, 1.1, 1.05, 1.15, 1.08].
        Drawdown from 1.15 to 1.08 = (1.08-1.15)/1.15 = -6.09%.
        """
        # Build a scenario where equity matches [1.0, 1.1, 1.05, 1.15, 1.08]
        # All BUY state so equity tracks close ratios
        # close[0]=100, close[1]=110, close[2]=105, close[3]=115, close[4]=108
        closes = [100, 110, 105, 115, 108]
        states = ["BUY", "BUY", "BUY", "BUY", "BUY"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        # Equity: 1.0, 1.1, 1.05, 1.15 (approx), 1.08
        dd = analyzer.max_drawdown()
        expected = (1.08 - 1.15) / 1.15
        assert dd == pytest.approx(expected, rel=1e-3)

    def test_sharpe_ratio_constant_equity(self):
        """Sharpe ratio on constant equity (no volatility) returns 0.0."""
        closes = [100, 100, 100, 100, 100]
        states = ["CASH", "CASH", "CASH", "CASH", "CASH"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        assert analyzer.sharpe_ratio() == 0.0

    def test_sharpe_ratio_known_returns(self):
        """Sharpe ratio on known returns series.

        With daily returns of [0.01, 0.02, -0.01, 0.015, 0.005]:
        mean = 0.008, std = ~0.01095
        sharpe = (0.008 / 0.01095) * sqrt(252) ~ 11.6
        """
        # Build equity from known daily returns
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        equity_values = [1.0]
        for r in returns:
            equity_values.append(equity_values[-1] * (1 + r))

        # We need closes that produce these equity values when all BUY
        closes = [100.0]
        for r in returns:
            closes.append(closes[-1] * (1 + r))

        states = ["BUY"] * len(closes)
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)

        sharpe = analyzer.sharpe_ratio()
        # Compute expected
        daily_ret = pd.Series(equity_values).pct_change().dropna()
        expected = (daily_ret.mean() / daily_ret.std()) * np.sqrt(252)
        assert sharpe == pytest.approx(expected, rel=1e-3)

    def test_win_rate_mixed(self):
        """Win rate with trades [pnl=0.05, pnl=-0.02, pnl=0.03] -> 2/3."""
        trades = make_trades([
            ("CASH_EXIT", 0.05),
            ("CASH_EXIT", -0.02),
            ("CASH_EXIT", 0.03),
        ])
        closes = [100, 100]
        states = ["CASH", "CASH"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df, trades)
        assert analyzer.win_rate() == pytest.approx(2.0 / 3.0, rel=1e-6)

    def test_win_rate_empty(self):
        """Win rate with empty trade list returns 0.0."""
        closes = [100, 100]
        states = ["CASH", "CASH"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df, [])
        assert analyzer.win_rate() == 0.0

    def test_win_rate_ignores_non_cash_exit(self):
        """Win rate only counts CASH_EXIT trades, ignores BUY and SELL_SIGNAL."""
        trades = make_trades([
            ("BUY", 0.0),
            ("CASH_EXIT", 0.05),
            ("SELL_SIGNAL", -0.01),
            ("CASH_EXIT", -0.02),
        ])
        closes = [100, 100]
        states = ["CASH", "CASH"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df, trades)
        # Only CASH_EXIT: pnl=0.05 (win), pnl=-0.02 (loss) -> 1/2
        assert analyzer.win_rate() == pytest.approx(0.5)

    def test_total_return(self):
        """Total return on equity ending at 1.25 -> 0.25 (25%)."""
        # equity 1.0 -> 1.25 means close goes from 100 to 125, all BUY
        closes = [100, 125]
        states = ["BUY", "BUY"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        assert analyzer.total_return() == pytest.approx(0.25, rel=1e-6)

    def test_annualized_return(self):
        """Annualized return: 504 trading days, total return 44% -> ~20%."""
        # 504 days = 2 years, total_return = 0.44
        # annualized = (1.44)^(1/2) - 1 = 0.2
        # Build a 504-day DataFrame with steady growth
        n = 504
        total_growth = 1.44
        daily_growth = total_growth ** (1.0 / (n - 1))
        closes = [100.0 * daily_growth ** i for i in range(n)]
        states = ["BUY"] * n
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        ann = analyzer.annualized_return()
        assert ann == pytest.approx(0.2, rel=0.01)

    def test_summary_keys(self):
        """summary() returns dict with required keys."""
        closes = [100, 110, 105]
        states = ["BUY", "BUY", "BUY"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        s = analyzer.summary()
        required_keys = {
            "total_return", "annualized_return", "max_drawdown",
            "sharpe_ratio", "win_rate", "equity_curve",
        }
        assert required_keys.issubset(s.keys())

    def test_drawdown_series(self):
        """drawdown_series returns pd.Series of same length with values <= 0."""
        closes = [100, 110, 105, 115, 108]
        states = ["BUY", "BUY", "BUY", "BUY", "BUY"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        dd_series = analyzer.drawdown_series()
        assert isinstance(dd_series, pd.Series)
        assert len(dd_series) == len(analyzer.equity)
        assert (dd_series <= 0).all()

    def test_equity_with_sell_state(self):
        """SELL state also means not invested (same as CASH)."""
        closes = [100, 110, 105]
        states = ["BUY", "SELL", "SELL"]
        df = make_results_df(closes, states)
        analyzer = V2PerformanceAnalyzer(df)
        eq = analyzer.equity
        # Day 0: 1.0
        # Day 1: prev=BUY -> capture 110/100 -> 1.1
        # Day 2: prev=SELL -> no capture -> 1.1
        assert eq.iloc[1] == pytest.approx(1.1)
        assert eq.iloc[2] == pytest.approx(1.1)


# --- PERF-03: Match Rate Validation tests ---

class TestMatchRateValidation:
    """Tests for check_degradation function (PERF-03)."""

    def test_validate_match_rates(self):
        """Train=0.60, held-out=0.56 -> degradation=6.67%, pass=True (< 10%)."""
        degradation, passed = check_degradation(0.60, 0.56, threshold=0.10)
        expected_deg = (0.60 - 0.56) / 0.60  # 0.0667
        assert degradation == pytest.approx(expected_deg, rel=1e-3)
        assert passed is True

    def test_train_heldout_validation(self):
        """Train=0.60, held-out=0.50 -> degradation=16.67%, pass=False (> 10%)."""
        degradation, passed = check_degradation(0.60, 0.50, threshold=0.10)
        expected_deg = (0.60 - 0.50) / 0.60  # 0.1667
        assert degradation == pytest.approx(expected_deg, rel=1e-3)
        assert passed is False

    def test_check_degradation_zero_train(self):
        """Edge case: train_rate=0 should return (0.0, True)."""
        degradation, passed = check_degradation(0.0, 0.0, threshold=0.10)
        assert degradation == 0.0
        assert passed is True
