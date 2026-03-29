"""
Indicator Filter Module for MDM Hybrid Engine

Stateless filter layer that evaluates EMA/MACD conditions to confirm or veto
state machine proposals via majority-vote logic. The filter never originates
signals -- it only judges proposals from the v2 state machine.

Phase 12: FilterConfig (per-condition toggles), Verdict enum (CONFIRM/VETO/OVERRIDE),
IndicatorFilter class (6 boolean conditions + evaluate).

Design decisions referenced:
  D-02: Stateless boolean conditions mirroring feature_snapshot.py
  D-03: FilterConfig with per-condition toggle fields
  D-04: Max 2-3 conditions recommended to avoid overfitting
  D-05: evaluate() takes (row, proposal, current_state) -> Verdict
  D-06: Bearish conditions are NOT simple negation (NaN -> False for both)
  D-07: Verdict enum with CONFIRM/VETO/OVERRIDE
  D-11: majority_threshold default 0.67 (2/3 agreement)
  D-12: HybridConfig composes FilterConfig
  D-13: NaN-safe via pd.notna() checks before every comparison
"""

import warnings
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Verdict(Enum):
    """Result of indicator filter evaluation on a state machine proposal.

    CONFIRM: Majority of indicator conditions agree with the proposal.
    VETO: Fewer than majority agree -- proposal should be blocked.
    OVERRIDE: Zero conditions agree (all disagree) with 3+ active -- strong counter-signal.
    """
    CONFIRM = "CONFIRM"
    VETO = "VETO"
    OVERRIDE = "OVERRIDE"


@dataclass
class FilterConfig:
    """Per-condition toggle configuration for the indicator filter.

    Defaults enable the 3 most important conditions identified in Phase 9/10
    rule discovery: close_above_ema55 (importance=0.687), macd_histogram,
    and ema9_above_ema21.

    Args:
        ema55_enabled: Enable close > EMA55 condition.
        macd_enabled: Enable MACD histogram > 0 condition.
        ema9_21_enabled: Enable EMA9 > EMA21 condition.
        ma200_enabled: Enable close > MA200 condition.
        ema9_enabled: Enable close > EMA9 condition.
        macd_signal_enabled: Enable MACD > signal line condition.
        majority_threshold: Fraction of agreeing conditions for CONFIRM (0, 1].
    """
    ema55_enabled: bool = True
    macd_enabled: bool = True
    ema9_21_enabled: bool = True
    ma200_enabled: bool = False
    ema9_enabled: bool = False
    macd_signal_enabled: bool = False
    ha_smooth_enabled: bool = False
    majority_threshold: float = 2 / 3  # 0.6667: 2-out-of-3 majority

    def __post_init__(self):
        assert 0.0 < self.majority_threshold <= 1.0, (
            f"majority_threshold must be in (0, 1], got {self.majority_threshold}"
        )
        active = self.active_count()
        if active > 3:
            warnings.warn(
                f"FilterConfig has {active} active conditions. "
                "Max 2-3 recommended to avoid overfitting (D-04).",
                UserWarning,
                stacklevel=2,
            )

    def active_count(self) -> int:
        """Return the number of enabled condition toggles.

        Returns:
            Count of True-valued boolean toggle fields.
        """
        return sum([
            self.ema55_enabled,
            self.macd_enabled,
            self.ema9_21_enabled,
            self.ma200_enabled,
            self.ema9_enabled,
            self.macd_signal_enabled,
            self.ha_smooth_enabled,
        ])


class IndicatorFilter:
    """Stateless indicator filter for the hybrid engine's two-phase commit.

    Evaluates technical indicator conditions against a data row to produce
    a Verdict (CONFIRM/VETO/OVERRIDE) for a state machine proposal.

    The filter uses majority-vote logic: if enough enabled conditions agree
    with the proposal direction, the proposal is confirmed. Otherwise it is
    vetoed. If ALL conditions disagree (with 3+ active), an override is issued.

    Args:
        config: FilterConfig with per-condition toggles and threshold.
    """

    def __init__(self, config: FilterConfig = None):
        self.config = config or FilterConfig()

    # ------------------------------------------------------------------
    # Bullish boolean conditions (mirror core/feature_snapshot.py)
    # Each returns True when the bullish condition holds, False otherwise.
    # NaN in any required field -> False (never True on missing data).
    # ------------------------------------------------------------------

    @staticmethod
    def close_above_ema55(row) -> bool:
        """Check if close price is above EMA 55.

        Args:
            row: pandas Series with 'close' and 'ema55' fields.

        Returns:
            True if close > ema55 and ema55 is not NaN, False otherwise.
        """
        return bool(pd.notna(row['ema55']) and row['close'] > row['ema55'])

    @staticmethod
    def macd_histogram_positive(row) -> bool:
        """Check if MACD histogram is positive.

        Args:
            row: pandas Series with 'macd_histogram' field.

        Returns:
            True if macd_histogram > 0 and not NaN, False otherwise.
        """
        return bool(pd.notna(row['macd_histogram']) and row['macd_histogram'] > 0)

    @staticmethod
    def ema9_above_ema21(row) -> bool:
        """Check if EMA 9 is above EMA 21.

        Args:
            row: pandas Series with 'ema9' and 'ema21' fields.

        Returns:
            True if ema9 > ema21 and neither is NaN, False otherwise.
        """
        return bool(
            pd.notna(row['ema9'])
            and pd.notna(row['ema21'])
            and row['ema9'] > row['ema21']
        )

    @staticmethod
    def close_above_ma200(row) -> bool:
        """Check if close price is above MA 200.

        Args:
            row: pandas Series with 'close' and 'ma200' fields.

        Returns:
            True if close > ma200 and ma200 is not NaN, False otherwise.
        """
        return bool(pd.notna(row['ma200']) and row['close'] > row['ma200'])

    @staticmethod
    def close_above_ema9(row) -> bool:
        """Check if close price is above EMA 9.

        Args:
            row: pandas Series with 'close' and 'ema9' fields.

        Returns:
            True if close > ema9 and ema9 is not NaN, False otherwise.
        """
        return bool(pd.notna(row['ema9']) and row['close'] > row['ema9'])

    @staticmethod
    def macd_above_signal(row) -> bool:
        """Check if MACD line is above signal line.

        Args:
            row: pandas Series with 'macd' and 'macd_signal' fields.

        Returns:
            True if macd > macd_signal and neither is NaN, False otherwise.
        """
        return bool(
            pd.notna(row['macd'])
            and pd.notna(row['macd_signal'])
            and row['macd'] > row['macd_signal']
        )

    @staticmethod
    def ha_smooth_bullish(row) -> bool:
        """Check if Heikin Ashi Smoothed 55 candle is bullish (green).

        Args:
            row: pandas Series with 'ha_smooth_close' and 'ha_smooth_open' fields.

        Returns:
            True if ha_smooth_close > ha_smooth_open and neither is NaN, False otherwise.
        """
        return bool(
            pd.notna(row.get('ha_smooth_close'))
            and pd.notna(row.get('ha_smooth_open'))
            and row['ha_smooth_close'] > row['ha_smooth_open']
        )

    @staticmethod
    def ha_smooth_bearish(row) -> bool:
        """Check if Heikin Ashi Smoothed 55 candle is bearish (red).

        Args:
            row: pandas Series with 'ha_smooth_close' and 'ha_smooth_open' fields.

        Returns:
            True if ha_smooth_close < ha_smooth_open and neither is NaN, False otherwise.
        """
        return bool(
            pd.notna(row.get('ha_smooth_close'))
            and pd.notna(row.get('ha_smooth_open'))
            and row['ha_smooth_close'] < row['ha_smooth_open']
        )

    # ------------------------------------------------------------------
    # Vote aggregation
    # ------------------------------------------------------------------

    def _get_bullish_votes(self, row) -> list:
        """Collect bullish condition results for all enabled conditions.

        Each enabled condition contributes one boolean vote. Disabled
        conditions are excluded entirely (not counted as False).

        Args:
            row: pandas Series with indicator fields.

        Returns:
            List of bool values, one per enabled condition.
        """
        votes = []
        if self.config.ema55_enabled:
            votes.append(self.close_above_ema55(row))
        if self.config.macd_enabled:
            votes.append(self.macd_histogram_positive(row))
        if self.config.ema9_21_enabled:
            votes.append(self.ema9_above_ema21(row))
        if self.config.ma200_enabled:
            votes.append(self.close_above_ma200(row))
        if self.config.ema9_enabled:
            votes.append(self.close_above_ema9(row))
        if self.config.macd_signal_enabled:
            votes.append(self.macd_above_signal(row))
        if self.config.ha_smooth_enabled:
            votes.append(self.ha_smooth_bullish(row))
        return votes

    def _get_bearish_votes(self, row) -> list:
        """Collect bearish condition results for all enabled conditions.

        Bearish conditions are NOT simple negation of bullish conditions.
        NaN returns False for BOTH bullish and bearish (per D-06). Each
        bearish condition explicitly checks for the bearish direction
        (close < ema55, not just 'not close > ema55').

        Args:
            row: pandas Series with indicator fields.

        Returns:
            List of bool values, one per enabled condition.
        """
        votes = []
        if self.config.ema55_enabled:
            votes.append(bool(
                pd.notna(row['ema55']) and row['close'] < row['ema55']
            ))
        if self.config.macd_enabled:
            votes.append(bool(
                pd.notna(row['macd_histogram']) and row['macd_histogram'] < 0
            ))
        if self.config.ema9_21_enabled:
            votes.append(bool(
                pd.notna(row['ema9'])
                and pd.notna(row['ema21'])
                and row['ema9'] < row['ema21']
            ))
        if self.config.ma200_enabled:
            votes.append(bool(
                pd.notna(row['ma200']) and row['close'] < row['ma200']
            ))
        if self.config.ema9_enabled:
            votes.append(bool(
                pd.notna(row['ema9']) and row['close'] < row['ema9']
            ))
        if self.config.macd_signal_enabled:
            votes.append(bool(
                pd.notna(row['macd'])
                and pd.notna(row['macd_signal'])
                and row['macd'] < row['macd_signal']
            ))
        if self.config.ha_smooth_enabled:
            votes.append(self.ha_smooth_bearish(row))
        return votes

    # ------------------------------------------------------------------
    # Main evaluation
    # ------------------------------------------------------------------

    def evaluate(self, row, proposal: str, current_state=None) -> tuple:
        """Evaluate indicator conditions against a state machine proposal.

        For BUY proposals, checks bullish conditions (close above EMAs,
        positive MACD). For SELL/CASH proposals, checks bearish conditions
        (close below EMAs, negative MACD).

        Verdict logic:
          - 0 enabled conditions (or all NaN) -> CONFIRM (no opinion)
          - agree_ratio == 0.0 with 3+ active -> OVERRIDE (strong disagreement)
          - agree_ratio >= majority_threshold -> CONFIRM
          - Otherwise -> VETO

        Args:
            row: pandas Series with indicator fields (close, ema9, ema21,
                ema55, ma200, macd, macd_signal, macd_histogram).
            proposal: Signal proposal from state machine ('BUY', 'SELL', 'CASH').
            current_state: Current engine state (reserved for future use).

        Returns:
            Tuple of (Verdict, float) where float is the confidence score
            (agree_count / total_active_conditions, range 0.0-1.0).
        """
        if proposal == "BUY":
            conditions = self._get_bullish_votes(row)
        elif proposal in ("SELL", "CASH"):
            conditions = self._get_bearish_votes(row)
        else:
            return Verdict.CONFIRM, 1.0

        if len(conditions) == 0:
            return Verdict.CONFIRM, 1.0

        agree_count = sum(conditions)
        agree_ratio = agree_count / len(conditions)

        if agree_ratio == 0.0 and len(conditions) >= 3:
            return Verdict.OVERRIDE, 0.0

        if agree_ratio >= self.config.majority_threshold:
            return Verdict.CONFIRM, agree_ratio

        return Verdict.VETO, agree_ratio
