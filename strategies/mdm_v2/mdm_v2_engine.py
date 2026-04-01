"""
MDM V2 Engine Module

Main engine combining all components for the v2 3-state strategy.
Uses BUY/CASH/SELL states instead of classic HOLDING/CASH/WAITING_SELL/SHORT.
"""

import pandas as pd
from typing import Optional

from .indicators import Indicators
from .distribution_day import DistributionDayCounter
from .rally_attempt import RallyAttemptTracker
from .ftd_signal import FTDSignalDetector
from .stop_loss import StopLossChecker
from .position_manager import V2PositionManager, V2MarketState
from .config import MDMV2Config
from .liquidity import LiquidityLoader
from .sell_acceleration import SellAccelerationGate
from .buy_filter import BuyFilter
from .buy_confirmation import BuyConfirmation
from .buy_entry import BuyEntryFilter


class MDMV2Engine:
    """
    Market Direction Model V2 Engine.

    Combines all components to run the MDM v2 strategy:
    1. Calculate indicators
    2. Detect rally attempts and FTD signals
    3. Manage positions with 3-state machine (BUY/CASH/SELL)
    4. Track trades and performance
    """

    def __init__(self, config: MDMV2Config = None):
        """Initialize MDM V2 Engine with all components."""
        self.config = config if config else MDMV2Config()

        self.dd_counter = DistributionDayCounter(self.config)
        self.rally_tracker = RallyAttemptTracker(self.config)
        self.ftd_detector = FTDSignalDetector(self.config)
        self.stop_loss_checker = StopLossChecker(self.config)
        self.position_manager = V2PositionManager(self.config)

        self.liquidity_loader = None
        if self.config.qe_floor_enabled:
            self.liquidity_loader = LiquidityLoader(self.config.liquidity_csv_path)

        self.sell_acceleration_gate = None
        if self.config.sell_acceleration_enabled:
            self.sell_acceleration_gate = SellAccelerationGate(self.config)

        self.buy_filter = None
        if self.config.buy_filter_enabled:
            self.buy_filter = BuyFilter(self.config)

        self.buy_confirmation = None
        if self.config.buy_confirmation_enabled:
            self.buy_confirmation = BuyConfirmation(self.config)

        self.buy_entry_filter = None
        if self.config.gap_filter_enabled or self.config.rally_threshold_enabled:
            self.buy_entry_filter = BuyEntryFilter(self.config)

        self.results: Optional[pd.DataFrame] = None

    def reset(self):
        """Reset all components."""
        self.dd_counter.reset()
        self.rally_tracker.full_reset()
        self.ftd_detector.reset()
        self.position_manager.reset()
        if self.buy_confirmation is not None:
            self.buy_confirmation.reset()
        self.results = None

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run MDM v2 strategy on data.

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

        # Add 200dma indicator if replacement mode enabled (MAREVIEW, D-03)
        if self.config.ma200_enabled:
            df = Indicators.add_sma200_column(df)
            df['prev_sma200'] = df['sma200'].shift(1)

        # Merge global liquidity data if QE floor enabled (LIQ-01, LIQ-02)
        if self.config.qe_floor_enabled and self.liquidity_loader is not None:
            df = self.liquidity_loader.load_and_merge(df, self.config.publication_lag_days)

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
        df['is_200dma_breakout'] = False
        df['is_dd'] = False
        df['dd_type'] = 0
        df['dd_count'] = 0
        df['state'] = V2MarketState.CASH.value
        df['action'] = ''
        df['buy_price'] = 0.0
        df['drawdown_pct'] = 0.0
        df['buy_rejected'] = False
        df['buy_pending'] = False
        df['buy_confirmed'] = False

        all_dates = df['date'].tolist()

        # Process each day
        for idx in range(len(df)):
            row = df.iloc[idx]

            # Skip first row (no previous data)
            if idx == 0:
                continue

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
                # Rally threshold: allow early FTD in shallow pullbacks (RALLY-01, per D-06)
                allow_early = (self.buy_entry_filter is not None
                               and self.buy_entry_filter.should_allow_early_ftd(drawdown_pct))

                # Check traditional FTD
                if rally_day >= 4 or allow_early:
                    # Pitfall 2: when early FTD allowed, pass adjusted rally_day to
                    # satisfy FTDSignalDetector's internal min_rally_day check
                    ftd_rally_day = rally_day
                    if allow_early and rally_day < self.config.ftd_min_rally_day:
                        ftd_rally_day = self.config.ftd_min_rally_day
                    is_ftd, signal = self.ftd_detector.check_ftd(
                        ftd_rally_day, price_change_pct, volume_up, date, close
                    )
                    if is_ftd and signal:
                        ftd_price = signal.price
                        self.dd_counter.reset()

                # Check MA50 breakout signal (alternative buy signal)
                if not is_ftd and self.config.ma50_breakout_enabled:
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

                # Check 200dma breakout signal (replaces MA50 breakout when ma200_enabled, per D-03)
                if not is_ftd and self.config.ma200_enabled:
                    sma200 = row['sma200'] if 'sma200' in row.index else None
                    prev_sma200 = row['prev_sma200'] if 'prev_sma200' in row.index else None
                    if sma200 is not None and prev_sma200 is not None:
                        is_200dma, signal = self.ftd_detector.check_200dma_breakout(
                            close, prev_close, sma200, prev_sma200, volume_up, drawdown_pct, date
                        )
                        if is_200dma and signal:
                            is_ftd = True
                            ftd_price = signal.price
                            signal_type = signal.signal_type
                            self.dd_counter.reset()
                            df.at[df.index[idx], 'is_200dma_breakout'] = True

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

            # 2b. BUY selectivity gates (BUY-01, BUY-02, per D-08)
            buy_rejected = False
            buy_pending = False
            buy_confirmed = False

            # If a strong breakout fires while FTD is pending confirmation, cancel the pending FTD (per pitfall 2)
            if is_ftd and signal_type in ("MA50", "52WEEK") and self.buy_confirmation is not None:
                self.buy_confirmation.reset()

            # Determine signal_type for filter if not already set
            if is_ftd and not signal_type:
                signal_type = "FTD"  # Classic FTD (no signal_type set by breakout checks)

            # Gate 0: Gap-up filter (GAP-01, per D-01, D-02)
            if is_ftd and signal_type == "FTD" and self.buy_entry_filter is not None:
                if not self.buy_entry_filter.check_gap(signal_type, low, prev_close):
                    is_ftd = False
                    buy_rejected = True

            # Gate 1: MA10/MA50 trend filter (BUY-01, per D-01)
            if is_ftd and signal_type == "FTD" and self.buy_filter is not None:
                ma10_val = row['ma10'] if 'ma10' in row else None
                ma50_check = row['ma50'] if 'ma50' in row else None
                if not self.buy_filter.check("FTD", ma10_val, ma50_check):
                    is_ftd = False
                    buy_rejected = True

            # Gate 2: Confirmation window (BUY-02, per D-03 to D-06)
            if is_ftd and signal_type == "FTD" and self.buy_confirmation is not None:
                self.buy_confirmation.submit_ftd(date)
                is_ftd = False  # Suppress immediate entry, wait for confirmation
                buy_pending = True

            # Process pending confirmation (every day, per D-03)
            if self.buy_confirmation is not None and self.buy_confirmation.is_pending():
                # Detect DD for confirmation window WITHOUT side effects
                # Use the same conditions as DistributionDayCounter but do NOT append to dd_history
                confirm_is_dd = (
                    self.dd_counter.is_distribution_day_type1(price_change_pct, volume_up)
                    or self.dd_counter.is_distribution_day_type2(price_change_pct, volume_up, p_loc)
                )
                confirmed, rejected, entry_price = self.buy_confirmation.process_day(
                    confirm_is_dd, close
                )
                if confirmed:
                    is_ftd = True
                    ftd_price = entry_price  # Day-3 close per D-05
                    signal_type = "FTD"
                    buy_confirmed = True
                elif rejected:
                    buy_rejected = True  # FTD canceled due to DD threshold

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

            # 4b. Compute QE floor SELL suppression (LIQ-02)
            suppress_sell = False
            if self.config.qe_floor_enabled and 'qe_floor' in df.columns:
                qe_val = df.iloc[idx]['qe_floor']
                suppress_sell = bool(qe_val == 1) if pd.notna(qe_val) else False

            # 4c. Compute sell acceleration gate (SELL-01, per D-05)
            acceleration_met = True  # default: allow SELL
            if self.config.sell_acceleration_enabled and self.sell_acceleration_gate is not None:
                acceleration_met = self.sell_acceleration_gate.check(
                    close=close,
                    closes_history=df['close'].iloc[max(0, idx - self.config.roc_window):idx + 1],
                    dd_dates=self.dd_counter.dd_history,
                    date=date,
                    volume=row['volume'],
                    prev_volume=row['prev_volume'],
                    ma50=row['ma50'] if 'ma50' in row else None,
                    prev_close=prev_close,
                    prev_ma50=row['prev_ma50'] if 'prev_ma50' in row else None,
                )

            # 5. Update position
            ma10 = row['ma10'] if 'ma10' in row else None
            ma50_val = row['ma50'] if 'ma50' in row else None
            prev_high = row['prev_high'] if 'prev_high' in row.index else 0.0

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
                sma200=row.get('sma200') if hasattr(row, 'get') else (row['sma200'] if 'sma200' in row.index else None),
                suppress_sell=suppress_sell,
                acceleration_met=acceleration_met,
                prev_high=prev_high if pd.notna(prev_high) else 0.0,
            )

            # If FTD triggered, reset rally tracker
            if is_ftd:
                self.rally_tracker.full_reset()

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
            df.at[idx, 'acceleration_met'] = acceleration_met
            df.at[idx, 'buy_rejected'] = buy_rejected
            df.at[idx, 'buy_pending'] = buy_pending
            df.at[idx, 'buy_confirmed'] = buy_confirmed

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
