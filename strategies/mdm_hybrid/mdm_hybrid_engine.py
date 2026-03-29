"""
Hybrid MDM Engine Module

Main engine combining v2 state machine components with two-phase commit
snapshot/restore mechanism. Uses BUY/CASH/SELL states identical to v2,
but wraps daily processing with snapshot before and decide/restore after.

Phase 11: snapshot/restore infrastructure only (filter_enabled=False).
Phase 12 will add indicator filter decision logic in the commit block.
"""

import copy
import pandas as pd
from typing import Optional

from .indicators import Indicators
from .distribution_day import DistributionDayCounter
from .rally_attempt import RallyAttemptTracker
from .ftd_signal import FTDSignalDetector
from .stop_loss import StopLossChecker
from .position_manager import V2PositionManager, V2MarketState
from .config import HybridConfig, MDMV2Config
from .indicator_filter import IndicatorFilter, Verdict


class HybridEngine:
    """
    Hybrid Market Direction Model Engine with two-phase commit.

    Combines all v2 components to run the MDM strategy with snapshot/restore:
    1. Calculate indicators
    2. Snapshot all 4 mutable components before daily processing
    3. Detect rally attempts and FTD signals
    4. Manage positions with 3-state machine (BUY/CASH/SELL)
    5. Decide: keep mutations (confirm) or restore snapshot (veto)
    6. Track trades and performance
    """

    def __init__(self, config: HybridConfig = None):
        """Initialize Hybrid MDM Engine with two-phase commit support."""
        self.config = config if config else HybridConfig()
        v2 = self.config.v2_config

        self.dd_counter = DistributionDayCounter(v2)
        self.rally_tracker = RallyAttemptTracker(v2)
        self.ftd_detector = FTDSignalDetector(v2)
        self.stop_loss_checker = StopLossChecker(v2)
        self.position_manager = V2PositionManager(v2)

        self.results: Optional[pd.DataFrame] = None
        self.indicator_filter = IndicatorFilter(self.config.filter_config) if self.config.filter_enabled else None

    def reset(self):
        """Reset all components."""
        self.dd_counter.reset()
        self.rally_tracker.full_reset()
        self.ftd_detector.reset()
        self.position_manager.reset()
        self.results = None

    def _snapshot_components(self) -> dict:
        """Snapshot all mutable state machine components for two-phase commit."""
        return {
            'dd_counter': copy.deepcopy(self.dd_counter),
            'rally_tracker': copy.deepcopy(self.rally_tracker),
            'ftd_detector': copy.deepcopy(self.ftd_detector),
            'position_manager': copy.deepcopy(self.position_manager),
        }

    def _restore_components(self, snapshot: dict):
        """Restore all mutable state machine components from snapshot (rollback)."""
        self.dd_counter = snapshot['dd_counter']
        self.rally_tracker = snapshot['rally_tracker']
        self.ftd_detector = snapshot['ftd_detector']
        self.position_manager = snapshot['position_manager']

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run Hybrid MDM strategy on data.

        Args:
            df: DataFrame with OHLCV data (date, open, high, low, close, volume)

        Returns:
            DataFrame with signals and states. State column uses
            V2MarketState values: BUY, CASH, SELL.
        """
        self.reset()

        # Prepare data with indicators
        df = df.copy()
        df = Indicators.add_price_location_column(df)
        df = Indicators.add_prev_columns(df)
        df = Indicators.add_change_columns(df)
        df = Indicators.add_ma50_column(df)
        df = Indicators.add_ma10_column(df)
        df = Indicators.add_ma50_volume_column(df)
        df = Indicators.calculate_rolling_high(df)
        df = Indicators.add_52week_high_column(df)
        df['prev_ma50'] = df['ma50'].shift(1)
        df['prev_ma10'] = df['ma10'].shift(1)

        # Add EMA/MACD indicator columns for filter evaluation (per D-03, Phase 13)
        if self.config.filter_enabled:
            from core.indicators import build_indicator_dataframe
            df = build_indicator_dataframe(df)

        # Suppress DD counting on derivative expiry days (VN30 microstructure, per D-05)
        # Guard: only apply if is_expiry_day column exists (NASDAQ runs without it, per Pitfall 5)
        if 'is_expiry_day' in df.columns:
            df.loc[df['is_expiry_day'] == True, 'volume_up'] = False

        # Initialize result columns
        df['in_correction'] = False
        df['rally_day'] = 0
        df['is_day1'] = False
        df['is_ftd'] = False
        df['is_ma50_breakout'] = False
        df['is_dd'] = False
        df['dd_type'] = 0
        df['dd_count'] = 0
        df['state'] = V2MarketState.CASH.value
        df['action'] = ''
        df['buy_price'] = 0.0
        df['drawdown_pct'] = 0.0

        # Signal log columns for Phase 14 diagnosis (per D-09, D-10)
        df['old_state'] = ''
        df['proposed'] = ''
        df['verdict'] = ''
        df['confidence'] = 0.0

        all_dates = df['date'].tolist()

        # Process each day
        for idx in range(len(df)):
            row = df.iloc[idx]

            # Skip first row (no previous data)
            if idx == 0:
                continue

            # Two-phase commit: snapshot before processing
            snapshot = None
            if self.config.two_phase_enabled:
                snapshot = self._snapshot_components()

            date = row['date']
            high = row['high']
            low = row['low']
            close = row['close']
            prev_close = row['prev_close']
            p_loc = row['p_loc']
            price_change_pct = row['price_change_pct']
            volume_up = row['volume_up']

            current_state = self.position_manager.get_state()
            buy_price = self.position_manager.get_buy_price()
            buy_day_low = self.position_manager.get_buy_day_low()

            # 1. Track rally attempt (when in CASH or SELL - need FTD)
            in_correction = False
            rally_day = 0
            is_day1 = False

            if current_state in [V2MarketState.CASH, V2MarketState.SELL]:
                in_correction, rally_day, is_day1 = self.rally_tracker.process_day(
                    date, high, low, close, prev_close, p_loc
                )

            # 2. Detect FTD (only when in CASH or SELL and in correction)
            is_ftd = False
            is_ma50_breakout = False
            ftd_price = 0.0
            signal_type = ""

            # Calculate drawdown from peak
            rolling_high = row['rolling_high'] if 'rolling_high' in row else close
            drawdown_pct = Indicators.drawdown_from_peak(close, rolling_high)

            if current_state in [V2MarketState.CASH, V2MarketState.SELL]:
                # Check traditional FTD
                if rally_day >= 4:
                    is_ftd, signal = self.ftd_detector.check_ftd(
                        rally_day, price_change_pct, volume_up, date, close
                    )
                    if is_ftd and signal:
                        ftd_price = signal.price
                        self.dd_counter.reset()

                # Check MA50 breakout signal (alternative buy signal)
                if not is_ftd:
                    ma50 = row['ma50'] if 'ma50' in row else None
                    prev_ma50 = row['prev_ma50'] if 'prev_ma50' in row else None
                    if ma50 is not None and prev_ma50 is not None:
                        is_ma50_breakout, signal = self.ftd_detector.check_ma50_breakout(
                            close, prev_close, ma50, prev_ma50, volume_up, drawdown_pct, date
                        )
                        if is_ma50_breakout and signal:
                            is_ftd = True
                            ftd_price = signal.price
                            signal_type = signal.signal_type
                            self.dd_counter.reset()

                # Check 52-Week Breakout signal
                if not is_ftd:
                    high_52w = row['high_52w'] if 'high_52w' in row else None
                    is_52w, signal = self.ftd_detector.check_52week_breakout(
                        close, high_52w, date
                    )
                    if is_52w and signal:
                        is_ftd = True
                        ftd_price = signal.price
                        signal_type = signal.signal_type
                        self.dd_counter.reset()

            # 3. Count distribution days (only when in BUY state)
            is_dd = False
            dd_type = 0
            dd_count = 0

            if current_state == V2MarketState.BUY:
                is_dd, dd_type = self.dd_counter.check_distribution_day(
                    date, price_change_pct, volume_up, p_loc
                )
                dd_count = self.dd_counter.get_dd_count_in_window(date, all_dates)

            # 4. Check stop loss (long only, no SHORT stop loss)
            ma50 = row['ma50'] if 'ma50' in row else None
            prev_ma50_val = row['prev_ma50'] if 'prev_ma50' in row else None
            current_volume = row['volume']
            prev_volume = row['prev_volume']
            signal_type_held = self.position_manager.get_signal_type()
            stop_loss_result = self.stop_loss_checker.check(
                close, buy_price, buy_day_low,
                ma50=ma50, prev_close=prev_close, prev_ma50=prev_ma50_val,
                current_volume=current_volume, prev_volume=prev_volume,
                signal_type=signal_type_held
            )

            # 5. Update position
            ma10 = row['ma10'] if 'ma10' in row else None
            ma50_val = row['ma50'] if 'ma50' in row else None

            new_state, action = self.position_manager.process_day(
                date=date,
                high=high,
                low=low,
                close=close,
                is_ftd=is_ftd,
                ftd_price=ftd_price,
                dd_count=dd_count,
                is_dd=is_dd,
                stop_loss_triggered=stop_loss_result.triggered,
                stop_loss_reason=stop_loss_result.reason,
                signal_type=signal_type,
                ma10=ma10,
                ma50=ma50_val,
            )

            # If FTD triggered, reset rally tracker
            if is_ftd:
                self.rally_tracker.full_reset()

            # Two-phase commit: Propose-Filter-Decide pipeline (Phase 13)
            if self.config.two_phase_enabled and self.config.filter_enabled:
                old_state = snapshot['position_manager'].get_state()

                # Derive proposal from diff (D-01)
                if new_state != old_state:
                    # State changed: proposal is the new state
                    proposal = new_state.value  # "BUY", "CASH", or "SELL"
                else:
                    # No change: proposal is "confirm current state" (D-02)
                    proposal = old_state.value

                verdict, confidence = self.indicator_filter.evaluate(row, proposal, old_state)
                df.at[idx, 'confidence'] = confidence

                if new_state != old_state:
                    # State machine proposed a change
                    if verdict == Verdict.VETO:
                        # Rollback: restore snapshot, discard mutations (D-01)
                        self._restore_components(snapshot)
                        new_state = self.position_manager.get_state()
                        action = ''
                    elif verdict == Verdict.OVERRIDE:
                        # OVERRIDE = force Cash (D-04)
                        if new_state == V2MarketState.CASH:
                            # Already going to Cash -- keep state machine's transition (Pitfall 4)
                            pass
                        else:
                            # Force to Cash regardless of proposal
                            self._restore_components(snapshot)
                            if old_state == V2MarketState.BUY:
                                self.position_manager.exit_to_cash(close, date, "OVERRIDE: indicator disagreement")
                            else:
                                self.position_manager.degrade_to_cash(date, "OVERRIDE: indicator disagreement")
                            new_state = V2MarketState.CASH
                            action = "CASH exit: filter override"
                    # verdict == Verdict.CONFIRM: keep mutations as-is
                else:
                    # No state change proposed -- check for cash insertion (D-06)
                    if verdict in (Verdict.VETO, Verdict.OVERRIDE):
                        if old_state == V2MarketState.BUY:
                            # BUY degradation: exit with P&L (D-07)
                            self.position_manager.exit_to_cash(close, date, "indicator degradation")
                            new_state = V2MarketState.CASH
                            action = "CASH exit: indicator degradation"
                        elif old_state == V2MarketState.SELL:
                            # SELL degradation: no P&L (D-07 symmetric)
                            self.position_manager.degrade_to_cash(date, "indicator degradation from SELL")
                            new_state = V2MarketState.CASH
                            action = "CASH: indicator degradation from SELL"
                        # old_state == CASH: skip -- already in CASH, nothing to degrade (Pitfall 5)

                # Record signal log columns for every trading day (D-09, D-10)
                df.at[idx, 'old_state'] = old_state.value
                df.at[idx, 'proposed'] = proposal
                df.at[idx, 'verdict'] = verdict.value
            else:
                # Filter disabled: default to full confidence
                df.at[idx, 'confidence'] = 1.0

            # Update DataFrame
            df.at[idx, 'in_correction'] = in_correction
            df.at[idx, 'rally_day'] = rally_day
            df.at[idx, 'is_day1'] = is_day1
            df.at[idx, 'is_ftd'] = is_ftd
            df.at[idx, 'is_ma50_breakout'] = is_ma50_breakout
            df.at[idx, 'is_dd'] = is_dd
            df.at[idx, 'dd_type'] = dd_type
            df.at[idx, 'dd_count'] = dd_count
            df.at[idx, 'state'] = new_state.value
            df.at[idx, 'action'] = action
            df.at[idx, 'buy_price'] = self.position_manager.get_buy_price()
            df.at[idx, 'drawdown_pct'] = drawdown_pct

        self.results = df
        return df

    def get_trades(self) -> list:
        """Get list of all trades."""
        return self.position_manager.get_trades()

    def get_trade_df(self) -> pd.DataFrame:
        """Get trades as DataFrame."""
        trades = self.get_trades()
        if not trades:
            return pd.DataFrame()
        return pd.DataFrame(trades)

    def get_signals(self) -> pd.DataFrame:
        """Get DataFrame with only signal rows."""
        if self.results is None:
            return pd.DataFrame()

        signals = self.results[
            (self.results['is_ftd']) |
            (self.results['is_day1']) |
            (self.results['action'] != '')
        ]
        return signals[['date', 'close', 'state', 'action', 'rally_day', 'dd_count']]

    def summary(self) -> dict:
        """Get summary statistics."""
        trades = self.get_trades()

        buy_trades = [t for t in trades if t['type'] == 'BUY']
        cash_exits = [t for t in trades if t['type'] == 'CASH_EXIT']
        sell_signals = [t for t in trades if t['type'] == 'SELL_SIGNAL']

        # Long trades P&L
        long_wins = [t for t in cash_exits if t.get('pnl', 0) > 0]
        long_losses = [t for t in cash_exits if t.get('pnl', 0) <= 0]
        long_pnl = sum(t.get('pnl', 0) for t in cash_exits)

        total_completed = len(cash_exits)
        total_wins = len(long_wins)

        return {
            'total_buy_signals': len(buy_trades),
            'total_cash_exits': len(cash_exits),
            'total_sell_signals': len(sell_signals),
            'long_wins': len(long_wins),
            'long_losses': len(long_losses),
            'long_pnl': long_pnl,
            'total_completed': total_completed,
            'total_wins': total_wins,
            'win_rate': total_wins / total_completed if total_completed else 0,
            'avg_pnl': long_pnl / total_completed if total_completed else 0,
        }
