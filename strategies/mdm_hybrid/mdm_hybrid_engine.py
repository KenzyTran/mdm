"""
Hybrid MDM Engine Module

Main engine combining v2 state machine components with two-phase commit
snapshot/restore mechanism. Uses BUY/CASH/SELL states identical to v2,
but wraps daily processing with snapshot before and decide/restore after.

Phase 11: snapshot/restore infrastructure only (filter_enabled=False).
Phase 12: indicator filter decision logic in the commit block.
Phase 16: Short position support -- SELL state = active short, cover_short()
           triggers on MA50 breakout and indicator OVERRIDE/VETO, close price
           passed to enter_sell for short entry tracking.
"""

import copy
import pandas as pd
from typing import Optional

from .indicators import Indicators
from .distribution_day import DistributionDayCounter
from .rally_attempt import RallyAttemptTracker
from .ftd_signal import FTDSignalDetector
from .stop_loss import StopLossChecker, StopLossResult
from .position_manager import V2PositionManager, V2MarketState
from .config import HybridConfig, MDMV2Config
from .indicator_filter import IndicatorFilter, Verdict
from .macro_filter import MacroFilter, MacroVerdict, add_macro_columns


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

        # Phase 44 D-09 — instantiate MacroFilter only when feature enabled
        self.macro_filter = (
            MacroFilter(self.config)
            if self.config.v2_config.macro_filter_enabled
            else None
        )

        # DD5 high locked for short stop loss (Phase 17, RISK-03/SHORT-03)
        self._dd5_high_locked = 0.0

        # State history tracking (Phase 15, Plan 02 -- ADV-01)
        self.state_history = []  # List of dicts: {state, entered_date, duration}
        self._current_state_name = "CASH"
        self._current_state_start = None
        self._days_in_current_state = 0

    def reset(self):
        """Reset all components."""
        self.dd_counter.reset()
        self.rally_tracker.full_reset()
        self.ftd_detector.reset()
        self.position_manager.reset()
        self.results = None
        self._dd5_high_locked = 0.0
        self.state_history = []
        self._current_state_name = "CASH"
        self._current_state_start = None
        self._days_in_current_state = 0

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

    def _get_contextual_threshold(self, proposal: str) -> float:
        """Compute context-adjusted majority threshold for filter evaluation.

        Implements Dr. K's 'favor cash positions' philosophy:
        - BUY proposals from long Cash (> cash_deterioration_days): require 100% agreement
        - BUY proposals from Cash entered via Sell (> 5 days): require 100% agreement
        - All other proposals: use default threshold

        Args:
            proposal: Signal proposal from state machine ('BUY', 'SELL', 'CASH').

        Returns:
            Majority threshold float (default or 1.0 for stricter context).
        """
        base_threshold = self.config.filter_config.majority_threshold

        if proposal != "BUY":
            return base_threshold

        # Only affects BUY proposals when currently in CASH
        if self._current_state_name != "CASH":
            return base_threshold

        # Rule 1: Long Cash duration -> stricter BUY threshold
        cash_limit = self.config.v2_config.cash_deterioration_days  # default 10
        if self._days_in_current_state > cash_limit:
            return 1.0  # Require unanimous agreement

        # Rule 2: Cash entered from Sell -> bearish regime, stricter after 5 days
        if len(self.state_history) > 0:
            prior_state = self.state_history[-1]['state']
            if prior_state == "SELL" and self._days_in_current_state > 5:
                return 1.0  # Require unanimous agreement

        return base_threshold

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

        # ATR for volatility-adaptive stop loss (Phase 17, RISK-02)
        df = Indicators.add_atr_column(df, period=self.config.v2_config.atr_period)
        df['atr_baseline'] = df['atr'].rolling(
            window=self.config.v2_config.atr_baseline_period, min_periods=1
        ).mean()

        # ATR Buffer Zone: precompute violation_threshold column (Phase 38, ATR-01/ATR-02)
        # Only when enabled -- D-08: no side effects when disabled (protects ATR-04)
        if self.config.v2_config.atr_buffer_enabled:
            df = Indicators.add_violation_threshold_column(
                df,
                k=self.config.v2_config.atr_buffer_k,
                period=self.config.v2_config.atr_buffer_period,
            )

        # Refined DD volume columns (Phase 39, DD-01/DD-02)
        # Only when enabled -- D-05: no side effects when disabled (protects DD-04)
        if self.config.v2_config.refined_dd_enabled:
            df = Indicators.add_volume_ma_column(df, period=20)
            df = Indicators.add_volume_percentile_column(
                df,
                lookback=self.config.v2_config.refined_dd_small_vol_lookback,
                percentile=self.config.v2_config.refined_dd_small_vol_percentile,
            )

        # Macro Filter columns (Phase 44, MACRO-01/02/03)
        # Only when enabled -- D-09: no side effects when disabled (protects MACRO-04 / VAL-04)
        if self.config.v2_config.macro_filter_enabled:
            df = add_macro_columns(
                df,
                dxy_window_days=self.config.v2_config.dxy_window_days,
                eem_window_days=self.config.v2_config.eem_window_days,
                sbv_decay_days=self.config.v2_config.sbv_decay_days,
            )

        # Add EMA/MACD indicator columns for filter evaluation (per D-03, Phase 13)
        if self.config.filter_enabled:
            from core.indicators import build_indicator_dataframe
            df = build_indicator_dataframe(df)

        # Suppress DD counting on derivative expiry days (VN30 microstructure, per D-05)
        # Guard: only apply if is_expiry_day column exists (NASDAQ runs without it, per Pitfall 5)
        if 'is_expiry_day' in df.columns:
            df.loc[df['is_expiry_day'] == True, 'volume_up'] = False

        # Suppress refined DD volume signals on expiry days (Phase 39, Pitfall 1).
        # Classic DD is already suppressed above via volume_up=False, but the
        # refined rule reads vol_top_pct directly and would otherwise fire on
        # expiry days. vol_above_ma20 is computed per-row in the daily loop
        # (no column to mask), so suppression only needs to reach vol_top_pct.
        if (
            'is_expiry_day' in df.columns
            and self.config.v2_config.refined_dd_enabled
            and 'vol_top_pct' in df.columns
        ):
            df.loc[df['is_expiry_day'] == True, 'vol_top_pct'] = False

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
                        signal_type = "FTD"
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
                # Refined DD inputs (Phase 39, DD-02). Only meaningful when
                # refined_dd_enabled=True; defaults False otherwise so the
                # classic v6.0 rule path is unaffected (D-05, DD-04).
                vol_above_ma20 = False
                vol_top_pct_val = False
                if self.config.v2_config.refined_dd_enabled:
                    # Pitfall 1: on expiry days, suppress refined DD volume
                    # inputs (matches the spirit of the existing volume_up
                    # expiry filter that protects classic DD).
                    is_expiry = bool(row.get('is_expiry_day', False))
                    if not is_expiry:
                        vol_ma20_val = row.get('vol_ma20', 0.0)
                        vol_above_ma20 = bool(row['volume'] > vol_ma20_val)
                        vol_top_pct_val = bool(row.get('vol_top_pct', False))

                is_dd, dd_type = self.dd_counter.check_distribution_day(
                    date, high, price_change_pct, volume_up, p_loc,
                    vol_above_ma20=vol_above_ma20,
                    vol_top_pct=vol_top_pct_val,
                )
                dd_count = self.dd_counter.get_dd_count_in_window(date, all_dates)

                # Cache DD5 high when DD count reaches threshold (for short stop loss)
                if dd_count >= self.config.v2_config.dd_cash_threshold:
                    dd5_h = self.dd_counter.get_dd5_high(date, all_dates)
                    if dd5_h > 0:
                        self._dd5_high_locked = dd5_h

            # 4. Check stop loss (long only, no SHORT stop loss)
            ma50 = row['ma50'] if 'ma50' in row else None
            prev_ma50_val = row['prev_ma50'] if 'prev_ma50' in row else None
            current_volume = row['volume']
            prev_volume = row['prev_volume']
            signal_type_held = self.position_manager.get_signal_type()

            # Get ATR values for volatility-adaptive stop loss (Phase 17, RISK-02)
            current_atr = row['atr'] if 'atr' in row and pd.notna(row['atr']) else None
            current_atr_baseline = row['atr_baseline'] if 'atr_baseline' in row and pd.notna(row['atr_baseline']) else None

            # Phase 44 D-02/D-03/D-08: compute MacroVerdict ONCE per row.
            # Verdict.effective_max_multiplier flows to stop_loss check below.
            # Verdict.effective_dd_threshold flows to position_manager.process_day below.
            # Verdict.veto_sell handled at INSERTION 6 (after IndicatorFilter block).
            macro_verdict = (
                self.macro_filter.apply(row, current_state)
                if self.macro_filter is not None
                else MacroVerdict.pass_through()
            )

            stop_loss_result = self.stop_loss_checker.check(
                close, buy_price, buy_day_low,
                ma50=ma50, prev_close=prev_close, prev_ma50=prev_ma50_val,
                current_volume=current_volume, prev_volume=prev_volume,
                signal_type=signal_type_held,
                atr=current_atr,
                atr_baseline=current_atr_baseline,
                effective_max_multiplier=macro_verdict.effective_stop_loss_max_multiplier,
            )

            # 5. Short stop loss check (SELL state only, Phase 17 RISK-03/SHORT-03)
            short_stop_result = StopLossResult(triggered=False, reason="OK", loss_pct=0.0)
            if current_state == V2MarketState.SELL:
                short_entry = self.position_manager.position.short_entry_price
                short_stop_result = self.stop_loss_checker.check_short(
                    close, self._dd5_high_locked, short_entry
                )
                if short_stop_result.triggered:
                    # Short stop loss has highest priority -- cover immediately
                    self.position_manager.cover_short(close, date, short_stop_result.reason)
                    new_state = V2MarketState.CASH
                    action = f"SHORT_COVER: {short_stop_result.reason}"
                    # Reset rally tracker since we're no longer in SELL
                    self.rally_tracker.full_reset()
                    self._dd5_high_locked = 0.0

            # 6. Update position (skip if short stop loss already triggered)
            if not (current_state == V2MarketState.SELL and short_stop_result.triggered):
                ma10 = row['ma10'] if 'ma10' in row else None
                ma50_val = row['ma50'] if 'ma50' in row else None

                # prev_high for fail-safe threshold (SAFE-01)
                prev_high = df.iloc[idx - 1]['high'] if idx > 0 else 0.0

                # ATR Buffer Zone: read precomputed column for current row (ATR-02)
                violation_threshold_val = None
                if self.config.v2_config.atr_buffer_enabled:
                    violation_threshold_val = (
                        row['violation_threshold'] if 'violation_threshold' in row.index else None
                    )
                    if violation_threshold_val is not None and pd.notna(violation_threshold_val):
                        violation_threshold_val = float(violation_threshold_val)
                    else:
                        violation_threshold_val = None

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
                    prev_high=prev_high,
                    violation_threshold=violation_threshold_val,   # NEW: ATR-02
                    effective_dd_threshold=macro_verdict.effective_dd_threshold,   # Phase 44 D-02
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

                # Contextual threshold adjustment (Phase 15, Plan 02 -- ADV-01)
                ctx_threshold = self._get_contextual_threshold(proposal)
                if ctx_threshold != self.config.filter_config.majority_threshold:
                    from .indicator_filter import FilterConfig, IndicatorFilter as _IF
                    ctx_config = FilterConfig(
                        ema55_enabled=self.config.filter_config.ema55_enabled,
                        macd_enabled=self.config.filter_config.macd_enabled,
                        ema9_21_enabled=self.config.filter_config.ema9_21_enabled,
                        ma200_enabled=self.config.filter_config.ma200_enabled,
                        ema9_enabled=self.config.filter_config.ema9_enabled,
                        macd_signal_enabled=self.config.filter_config.macd_signal_enabled,
                        ha_smooth_enabled=self.config.filter_config.ha_smooth_enabled,
                        majority_threshold=ctx_threshold,
                    )
                    ctx_filter = _IF(ctx_config)
                    verdict, confidence = ctx_filter.evaluate(row, proposal, old_state)
                else:
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
                            elif old_state == V2MarketState.SELL:
                                self.position_manager.cover_short(close, date, "OVERRIDE: indicator disagreement")
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
                            # SELL degradation: cover short with P&L (Phase 16, Pitfall 1)
                            self.position_manager.cover_short(close, date, "indicator degradation from SELL")
                            new_state = V2MarketState.CASH
                            action = "SHORT_COVER: indicator degradation from SELL"
                        # old_state == CASH: skip -- already in CASH, nothing to degrade (Pitfall 5)

                # Record signal log columns for every trading day (D-09, D-10)
                df.at[idx, 'old_state'] = old_state.value
                df.at[idx, 'proposed'] = proposal
                df.at[idx, 'verdict'] = verdict.value
            else:
                # Filter disabled: default to full confidence
                df.at[idx, 'confidence'] = 1.0

            # Phase 44 D-01 / INSERTION 6: MacroFilter VETO_SELL handling
            # Applies AFTER IndicatorFilter (D-08 hook order: macro overrules
            # local indicator consensus). Only fires when state machine
            # actually proposed a transition INTO SELL — D-01 explicitly says
            # "block the SELL transition, keep current state HOLD/BUY unchanged".
            # Snapshot may be None when two_phase_enabled=False; in that case
            # the veto is a no-op (RESEARCH Open Q1 — current research recommends
            # documenting this constraint; for now, silently no-op when snapshot
            # is unavailable since macro_filter_enabled=True with two_phase=False
            # is not a supported configuration in v10.0).
            if (
                macro_verdict.veto_sell
                and new_state == V2MarketState.SELL
                and current_state != V2MarketState.SELL
                and snapshot is not None
            ):
                self._restore_components(snapshot)
                new_state = self.position_manager.get_state()
                action = ''
                # Diagnostic — overwrites verdict column when present (D-09 signal log)
                if self.config.two_phase_enabled and self.config.filter_enabled:
                    df.at[idx, 'verdict'] = 'MACRO_VETO_SELL'

            # State history tracking (Phase 15, Plan 02 -- ADV-01)
            # Track only on state CHANGES, not every day
            final_state_str = new_state.value
            if final_state_str != self._current_state_name:
                # Record completed state
                if self._current_state_start is not None:
                    self.state_history.append({
                        'state': self._current_state_name,
                        'entered_date': self._current_state_start,
                        'duration': self._days_in_current_state,
                    })
                self._current_state_name = final_state_str
                self._current_state_start = date
                self._days_in_current_state = 1
            else:
                self._days_in_current_state += 1

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
