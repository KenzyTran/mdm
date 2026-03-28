"""
Tests for VN30 microstructure filter module.

Tests limit day detection, expiry day computation, DD suppression,
and the combined filter pipeline.
"""

import pandas as pd
import numpy as np
import pytest

from strategies.mdm_v2.vn30_filters import (
    add_limit_day_column,
    add_expiry_day_column,
    suppress_dd_on_expiry,
    apply_vn30_filters,
)


def _make_df(dates, closes, highs=None, lows=None, volumes=None):
    """Helper to create a minimal OHLCV DataFrame."""
    n = len(dates)
    if highs is None:
        highs = closes
    if lows is None:
        lows = closes
    if volumes is None:
        volumes = [1000000] * n
    return pd.DataFrame({
        'date': pd.to_datetime(dates),
        'open': closes,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
    })


class TestLimitDayDetection:
    """Test is_limit_day column based on 6.5% threshold from previous close."""

    def test_limit_day_detection(self):
        """High pct >= 6.5% or low pct <= -6.5% flags limit day."""
        # prev_close=100, high=106.6 -> +6.6% -> limit day
        # prev_close=106.6, high=111 -> +4.13% -> not limit day
        # prev_close=111, low=103.78 -> -6.5% -> limit day (low pct from prev close)
        df = _make_df(
            dates=['2024-01-15', '2024-01-16', '2024-01-17', '2024-01-18'],
            closes=[100.0, 106.6, 111.0, 104.0],
            highs=[100.0, 106.6, 111.0, 111.0],
            lows=[100.0, 100.0, 111.0, 103.785],  # 103.785 = 111 * (1 - 0.065)
        )
        result = add_limit_day_column(df)

        assert 'is_limit_day' in result.columns
        # Row 0: no prev_close, should be False (NaN comparison)
        assert result.iloc[0]['is_limit_day'] == False
        # Row 1: high=106.6, prev_close=100 -> +6.6% >= 6.5% -> True
        assert result.iloc[1]['is_limit_day'] == True
        # Row 2: high=111, prev_close=106.6 -> +4.13% -> False
        assert result.iloc[2]['is_limit_day'] == False
        # Row 3: low=103.785, prev_close=111 -> -6.5% -> True
        assert result.iloc[3]['is_limit_day'] == True

    def test_limit_day_threshold(self):
        """Exactly 6.5% boundary -> True; 6.49% -> False."""
        # prev_close=1000
        # high=1065 -> exactly +6.5% -> True
        # high=1064.9 -> +6.49% -> False
        df_exact = _make_df(
            dates=['2024-01-15', '2024-01-16'],
            closes=[1000.0, 1065.0],
            highs=[1000.0, 1065.0],
            lows=[1000.0, 1000.0],
        )
        result_exact = add_limit_day_column(df_exact)
        assert result_exact.iloc[1]['is_limit_day'] == True

        df_below = _make_df(
            dates=['2024-01-15', '2024-01-16'],
            closes=[1000.0, 1064.9],
            highs=[1000.0, 1064.9],
            lows=[1000.0, 1000.0],
        )
        result_below = add_limit_day_column(df_below)
        assert result_below.iloc[1]['is_limit_day'] == False

    def test_limit_day_does_not_modify_existing_columns(self):
        """Adding limit day column should not alter original data."""
        df = _make_df(
            dates=['2024-01-15', '2024-01-16'],
            closes=[100.0, 107.0],
            highs=[100.0, 107.0],
            lows=[100.0, 100.0],
        )
        original_close = df['close'].tolist()
        result = add_limit_day_column(df)
        assert result['close'].tolist() == original_close


class TestExpiryDayComputation:
    """Test is_expiry_day column based on 3rd Thursday of each month."""

    def test_expiry_day_computation(self):
        """3rd Thursday 2024-01-18 -> True; other days -> False."""
        # 2024-01-18 is the 3rd Thursday of January 2024
        # 2024-01-17 is Wednesday
        # 2024-01-25 is 4th Thursday
        df = _make_df(
            dates=['2024-01-17', '2024-01-18', '2024-01-19', '2024-01-25'],
            closes=[100.0, 101.0, 102.0, 103.0],
        )
        result = add_expiry_day_column(df)

        assert 'is_expiry_day' in result.columns
        assert result.iloc[0]['is_expiry_day'] == False   # Wed Jan 17
        assert result.iloc[1]['is_expiry_day'] == True    # Thu Jan 18 (3rd Thu)
        assert result.iloc[2]['is_expiry_day'] == False   # Fri Jan 19
        assert result.iloc[3]['is_expiry_day'] == False   # Thu Jan 25 (4th Thu)

    def test_expiry_day_holiday_fallback(self):
        """If 3rd Thursday not in trading dates, preceding trading day gets flag."""
        # 3rd Thursday of Jan 2024 is Jan 18
        # Remove Jan 18 from data -> Jan 17 should get the flag
        df = _make_df(
            dates=['2024-01-15', '2024-01-16', '2024-01-17', '2024-01-19'],
            closes=[100.0, 101.0, 102.0, 103.0],
        )
        result = add_expiry_day_column(df)

        # Jan 17 (last trading day before Jan 18) should be expiry
        assert result.iloc[2]['is_expiry_day'] == True   # Jan 17 fallback
        assert result.iloc[0]['is_expiry_day'] == False   # Jan 15
        assert result.iloc[1]['is_expiry_day'] == False   # Jan 16
        assert result.iloc[3]['is_expiry_day'] == False   # Jan 19

    def test_expiry_day_multiple_months(self):
        """Expiry day computed correctly across multiple months."""
        # Feb 2024: 3rd Thursday = Feb 15
        # Mar 2024: 3rd Thursday = Mar 21
        df = _make_df(
            dates=['2024-02-14', '2024-02-15', '2024-02-16',
                   '2024-03-20', '2024-03-21', '2024-03-22'],
            closes=[100.0] * 6,
        )
        result = add_expiry_day_column(df)

        assert result.iloc[0]['is_expiry_day'] == False   # Feb 14
        assert result.iloc[1]['is_expiry_day'] == True    # Feb 15 (3rd Thu)
        assert result.iloc[2]['is_expiry_day'] == False   # Feb 16
        assert result.iloc[3]['is_expiry_day'] == False   # Mar 20
        assert result.iloc[4]['is_expiry_day'] == True    # Mar 21 (3rd Thu)
        assert result.iloc[5]['is_expiry_day'] == False   # Mar 22


class TestDDSuppressionOnExpiry:
    """Test volume_up override on expiry days."""

    def test_dd_suppression_on_expiry(self):
        """Expiry day rows have volume_up=False; non-expiry keep original."""
        df = _make_df(
            dates=['2024-01-17', '2024-01-18', '2024-01-19'],
            closes=[100.0, 101.0, 102.0],
        )
        df['volume_up'] = [True, True, False]
        df['is_expiry_day'] = [False, True, False]

        result = suppress_dd_on_expiry(df)

        assert result.iloc[0]['volume_up'] == True    # Not expiry, keep True
        assert result.iloc[1]['volume_up'] == False   # Expiry -> forced False
        assert result.iloc[2]['volume_up'] == False   # Not expiry, keep False

    def test_dd_suppression_without_expiry_column(self):
        """If is_expiry_day column missing, volume_up unchanged (NASDAQ guard)."""
        df = _make_df(
            dates=['2024-01-17', '2024-01-18'],
            closes=[100.0, 101.0],
        )
        df['volume_up'] = [True, True]
        # No is_expiry_day column

        result = suppress_dd_on_expiry(df)

        assert result.iloc[0]['volume_up'] == True
        assert result.iloc[1]['volume_up'] == True


class TestApplyVN30FiltersPipeline:
    """Test the combined filter pipeline."""

    def test_apply_vn30_filters_pipeline(self):
        """apply_vn30_filters adds both is_limit_day and is_expiry_day columns."""
        df = _make_df(
            dates=['2024-01-17', '2024-01-18', '2024-01-19'],
            closes=[100.0, 101.0, 102.0],
            highs=[100.0, 107.0, 102.0],
            lows=[100.0, 101.0, 102.0],
        )
        result = apply_vn30_filters(df)

        assert 'is_limit_day' in result.columns
        assert 'is_expiry_day' in result.columns
        # Verify is_expiry_day: Jan 18 is 3rd Thursday
        assert result.iloc[1]['is_expiry_day'] == True

    def test_apply_vn30_filters_does_not_call_suppress(self):
        """Pipeline does NOT suppress DD (that happens after engine indicators)."""
        df = _make_df(
            dates=['2024-01-17', '2024-01-18'],
            closes=[100.0, 101.0],
        )
        df['volume_up'] = [True, True]
        result = apply_vn30_filters(df)

        # volume_up should be untouched
        assert result.iloc[0]['volume_up'] == True
        assert result.iloc[1]['volume_up'] == True
