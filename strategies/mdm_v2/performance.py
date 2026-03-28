"""
V2 Performance Analyzer Module

Computes performance metrics for the MDM V2 engine:
- Daily equity curve (using previous day's state for return capture)
- Maximum drawdown (peak-to-trough from daily equity)
- Sharpe ratio (0% risk-free, sqrt(252) annualization)
- Win rate (profitable CASH_EXIT trades vs total)
- Total return and annualized return

Also provides check_degradation() for PERF-03 train/held-out validation.
"""

import pandas as pd
import numpy as np


def check_degradation(
    train_rate: float,
    heldout_rate: float,
    threshold: float = 0.10,
) -> tuple:
    """Check if held-out match rate degrades more than threshold relative to training.

    Per D-01: degradation = (train - heldout) / train, pass if <= threshold.

    Args:
        train_rate: Match rate on training data (0-1 scale or 0-100 scale).
        heldout_rate: Match rate on held-out data (same scale as train_rate).
        threshold: Maximum acceptable relative degradation (default 10%).

    Returns:
        Tuple of (degradation_pct, degradation_pass).
        degradation_pct is the relative degradation fraction.
        degradation_pass is True if degradation <= threshold.
    """
    if train_rate == 0:
        return (0.0, True)
    degradation = (train_rate - heldout_rate) / train_rate
    return (degradation, degradation <= threshold)


class V2PerformanceAnalyzer:
    """Analyze performance of MDM V2 engine results.

    Computes daily equity curve, drawdown, Sharpe ratio, win rate,
    total return, and annualized return from engine output.

    Uses previous day's state to determine if today's return is captured:
    - If previous day state is BUY, today's return is captured
    - If previous day state is CASH or SELL, today's return is not captured
    - The day state changes to BUY does NOT capture that day's return
    """

    TRADING_DAYS_PER_YEAR = 252

    def __init__(self, results_df: pd.DataFrame, trades: list = None):
        """Initialize analyzer.

        Args:
            results_df: Engine results DataFrame with columns: date, close, state.
                State values: 'BUY', 'CASH', 'SELL'.
            trades: List of trade dicts from engine.get_trades().
                Each dict has 'type' (BUY, CASH_EXIT, SELL_SIGNAL) and 'pnl' for exits.
        """
        self.results = results_df
        self.trades = trades or []
        self.equity = self._build_daily_equity()

    def _build_daily_equity(self) -> pd.Series:
        """Build daily equity curve from engine results.

        Per D-05: 100% invested on BUY, 0% on CASH/SELL.
        Per Pitfall 1: use PREVIOUS day's state for today's return.

        Returns:
            pd.Series of equity values, starting at 1.0.
        """
        closes = self.results["close"].values
        states = self.results["state"].values
        n = len(closes)

        equity = np.ones(n, dtype=float)

        for i in range(1, n):
            prev_state = states[i - 1]
            if prev_state == "BUY":
                # Capture today's return
                equity[i] = equity[i - 1] * (closes[i] / closes[i - 1])
            else:
                # Not invested, equity unchanged
                equity[i] = equity[i - 1]

        return pd.Series(equity, index=self.results.index)

    def total_return(self) -> float:
        """Compute total return from equity curve endpoints.

        Returns:
            Total return as a fraction (e.g., 0.25 for 25%).
        """
        return (self.equity.iloc[-1] / self.equity.iloc[0]) - 1.0

    def annualized_return(self) -> float:
        """Compute annualized return from equity curve.

        Uses trading days (252/year) for annualization.

        Returns:
            Annualized return as a fraction.
        """
        n_days = len(self.equity)
        years = n_days / self.TRADING_DAYS_PER_YEAR
        tr = self.total_return()
        if years > 0:
            return (1 + tr) ** (1 / years) - 1
        return 0.0

    def max_drawdown(self) -> float:
        """Compute maximum drawdown from daily equity series.

        Peak-to-trough drawdown as a negative fraction.

        Returns:
            Maximum drawdown (negative value, e.g., -0.0609 for -6.09%).
        """
        cummax = self.equity.cummax()
        drawdown = (self.equity - cummax) / cummax
        return drawdown.min()

    def drawdown_series(self) -> pd.Series:
        """Compute drawdown series from daily equity.

        Returns:
            pd.Series of drawdown values (<= 0) with same length as equity.
        """
        cummax = self.equity.cummax()
        return (self.equity - cummax) / cummax

    def sharpe_ratio(self) -> float:
        """Compute annualized Sharpe ratio.

        Per D-06: 0% risk-free rate, annualized with sqrt(252).

        Returns:
            Annualized Sharpe ratio. Returns 0.0 if no volatility.
        """
        daily_returns = self.equity.pct_change().dropna()
        if len(daily_returns) == 0 or daily_returns.std() == 0:
            return 0.0
        return (daily_returns.mean() / daily_returns.std()) * np.sqrt(
            self.TRADING_DAYS_PER_YEAR
        )

    def win_rate(self) -> float:
        """Compute win rate from CASH_EXIT trades.

        Counts profitable CASH_EXIT trades vs total CASH_EXIT trades.

        Returns:
            Win rate as a fraction (e.g., 0.667 for 66.7%). Returns 0.0 if no exits.
        """
        exits = [t for t in self.trades if t.get("type") == "CASH_EXIT"]
        if not exits:
            return 0.0
        wins = sum(1 for t in exits if t.get("pnl", 0) > 0)
        return wins / len(exits)

    def summary(self) -> dict:
        """Get summary of all performance metrics.

        Returns:
            Dict with keys: total_return, annualized_return, max_drawdown,
            sharpe_ratio, win_rate, equity_curve.
        """
        return {
            "total_return": self.total_return(),
            "annualized_return": self.annualized_return(),
            "max_drawdown": self.max_drawdown(),
            "sharpe_ratio": self.sharpe_ratio(),
            "win_rate": self.win_rate(),
            "equity_curve": self.equity,
        }
