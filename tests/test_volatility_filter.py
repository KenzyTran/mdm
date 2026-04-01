"""
Unit tests for Volatility Filter (v6.0, BAND-01, BAND-02).

Tests ATR computation, regime classification, and signal suppression logic.
"""

import pandas as pd
import numpy as np
import pytest

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.indicators import Indicators
from strategies.mdm_v2.volatility_filter import VolatilityFilter


# --- Config Tests ---

class TestVolatilityFilterConfig:
    """Test MDMV2Config volatility filter fields."""

    def test_volatility_filter_disabled_by_default(self):
        config = MDMV2Config()
        assert config.volatility_filter_enabled is False

    def test_volatility_low_threshold_default(self):
        config = MDMV2Config()
        assert config.volatility_low_threshold == 1.04

    def test_volatility_high_threshold_default(self):
        config = MDMV2Config()
        assert config.volatility_high_threshold == 1.73

    def test_atr_period_default(self):
        config = MDMV2Config()
        assert config.atr_period == 14

    def test_atr_period_zero_raises(self):
        with pytest.raises(AssertionError):
            MDMV2Config(atr_period=0)


# --- ATR Indicator Tests ---

def _make_ohlcv_df(n=20):
    """Create synthetic OHLCV DataFrame for testing."""
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    df = pd.DataFrame({
        'high': high,
        'low': low,
        'close': close,
    })
    df['prev_close'] = df['close'].shift(1)
    # Fill first row prev_close with close (no gap)
    df.loc[0, 'prev_close'] = df.loc[0, 'close']
    return df


class TestATRComputation:
    """Test Indicators.add_atr_column."""

    def test_atr_columns_created(self):
        df = _make_ohlcv_df(20)
        result = Indicators.add_atr_column(df)
        assert 'tr' in result.columns
        assert 'atr' in result.columns
        assert 'atr_pct' in result.columns

    def test_true_range_formula(self):
        """Verify TR = max(H-L, |H-prevC|, |L-prevC|) with hand-calculated row."""
        df = pd.DataFrame({
            'high': [105.0, 108.0],
            'low': [100.0, 102.0],
            'close': [103.0, 107.0],
            'prev_close': [101.0, 103.0],
        })
        result = Indicators.add_atr_column(df, period=14)
        # Row 1: H=108, L=102, prevC=103
        # H-L = 6, |H-prevC| = 5, |L-prevC| = 1
        # TR = max(6, 5, 1) = 6
        assert result.iloc[1]['tr'] == pytest.approx(6.0)

    def test_atr_pct_formula(self):
        """Verify ATR% = atr / close * 100."""
        df = pd.DataFrame({
            'high': [110.0],
            'low': [90.0],
            'close': [100.0],
            'prev_close': [100.0],
        })
        result = Indicators.add_atr_column(df, period=14)
        # TR = max(20, 10, 10) = 20, ATR = 20 (single row), ATR% = 20/100*100 = 20
        assert result.iloc[0]['atr_pct'] == pytest.approx(20.0)

    def test_atr_rolling_min_periods(self):
        """First row should have a value, not NaN (min_periods=1)."""
        df = _make_ohlcv_df(5)
        result = Indicators.add_atr_column(df, period=14)
        assert not pd.isna(result.iloc[0]['atr'])

    def test_atr_does_not_mutate_input(self):
        """add_atr_column should copy the DataFrame, not modify in place."""
        df = _make_ohlcv_df(5)
        _ = Indicators.add_atr_column(df)
        assert 'tr' not in df.columns


# --- VolatilityFilter Tests ---

class TestVolatilityFilter:
    """Test VolatilityFilter.should_suppress."""

    def test_disabled_returns_false(self):
        config = MDMV2Config(volatility_filter_enabled=False)
        vf = VolatilityFilter(config)
        assert vf.should_suppress(0.5) is False

    def test_enabled_low_vol_suppresses(self):
        config = MDMV2Config(volatility_filter_enabled=True)
        vf = VolatilityFilter(config)
        # 0.8 < 1.04 → should suppress
        assert vf.should_suppress(0.8) is True

    def test_enabled_normal_vol_no_suppress(self):
        config = MDMV2Config(volatility_filter_enabled=True)
        vf = VolatilityFilter(config)
        # 1.5 > 1.04 → should not suppress
        assert vf.should_suppress(1.5) is False

    def test_boundary_at_threshold_no_suppress(self):
        config = MDMV2Config(volatility_filter_enabled=True)
        vf = VolatilityFilter(config)
        # At exactly 1.04 → not below threshold → no suppress
        assert vf.should_suppress(1.04) is False
