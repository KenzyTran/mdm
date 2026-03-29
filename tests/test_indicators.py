"""Unit tests for core indicator functions.

Tests EMA, SMA, MACD, Heikin Ashi, Heikin Ashi Smoothed, and
build_indicator_dataframe against known values using small synthetic data.
"""

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose

from core.indicators import (
    build_indicator_dataframe,
    compute_ema,
    compute_heikin_ashi,
    compute_heikin_ashi_smoothed,
    compute_macd,
    compute_sma,
)


class TestComputeEma:
    """Tests for compute_ema function."""

    def test_compute_ema_basic(self):
        """compute_ema on [1,2,3,4,5] with span=3 produces expected recursive EMA values.

        alpha = 2/(3+1) = 0.5
        EMA[0] = 1.0
        EMA[1] = 0.5*2 + 0.5*1.0 = 1.5
        EMA[2] = 0.5*3 + 0.5*1.5 = 2.25
        EMA[3] = 0.5*4 + 0.5*2.25 = 3.125
        EMA[4] = 0.5*5 + 0.5*3.125 = 4.0625
        """
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = compute_ema(series, span=3)
        expected = [1.0, 1.5, 2.25, 3.125, 4.0625]
        assert_allclose(result.values, expected, rtol=1e-6)

    def test_compute_ema_adjust_false(self):
        """First EMA value equals first input (adjust=False behavior)."""
        series = pd.Series([42.0, 43.0, 44.0, 45.0, 46.0])
        result = compute_ema(series, span=5)
        assert result.iloc[0] == 42.0


class TestComputeSma:
    """Tests for compute_sma function."""

    def test_compute_sma_min_periods(self):
        """SMA with window=5 produces NaN for first 4 elements."""
        series = pd.Series(range(1, 11), dtype=float)
        result = compute_sma(series, window=5)
        assert result.iloc[:4].isna().all()
        assert result.iloc[4:].notna().all()

    def test_compute_sma_value(self):
        """SMA([10,20,30,40,50], window=3) last value = (30+40+50)/3 = 40.0."""
        series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result = compute_sma(series, window=3)
        assert_allclose(result.iloc[-1], 40.0, rtol=1e-6)


class TestComputeMacd:
    """Tests for compute_macd function."""

    def test_compute_macd_columns(self):
        """compute_macd returns DataFrame with correct columns."""
        close = pd.Series(np.random.randn(50).cumsum() + 100)
        result = compute_macd(close)
        assert list(result.columns) == ["macd", "macd_signal", "macd_histogram"]

    def test_compute_macd_histogram_identity(self):
        """histogram == macd - macd_signal for all rows."""
        close = pd.Series(np.random.randn(100).cumsum() + 100)
        result = compute_macd(close)
        expected_hist = result["macd"] - result["macd_signal"]
        assert_allclose(result["macd_histogram"].values, expected_hist.values, rtol=1e-10)


class TestComputeHeikinAshi:
    """Tests for compute_heikin_ashi function."""

    def test_compute_heikin_ashi_close(self):
        """HA close = (O+H+L+C)/4 for every row."""
        df = pd.DataFrame({
            "open": [10.0, 11.0, 12.0],
            "high": [12.0, 13.0, 14.0],
            "low": [9.0, 10.0, 11.0],
            "close": [11.0, 12.0, 13.0],
        })
        result = compute_heikin_ashi(df)
        expected_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
        assert_allclose(result["ha_close"].values, expected_close.values, rtol=1e-6)

    def test_compute_heikin_ashi_open_recursive(self):
        """HA open[0] = (O[0]+C[0])/2, HA open[i] = (ha_open[i-1]+ha_close[i-1])/2."""
        df = pd.DataFrame({
            "open": [10.0, 11.0, 12.0],
            "high": [12.0, 13.0, 14.0],
            "low": [9.0, 10.0, 11.0],
            "close": [11.0, 12.0, 13.0],
        })
        result = compute_heikin_ashi(df)
        ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

        # ha_open[0] = (10 + 11) / 2 = 10.5
        assert_allclose(result["ha_open"].iloc[0], 10.5, rtol=1e-6)

        # ha_open[1] = (ha_open[0] + ha_close[0]) / 2 = (10.5 + 10.5) / 2 = 10.5
        expected_1 = (result["ha_open"].iloc[0] + ha_close.iloc[0]) / 2
        assert_allclose(result["ha_open"].iloc[1], expected_1, rtol=1e-6)

        # ha_open[2] = (ha_open[1] + ha_close[1]) / 2
        expected_2 = (result["ha_open"].iloc[1] + ha_close.iloc[1]) / 2
        assert_allclose(result["ha_open"].iloc[2], expected_2, rtol=1e-6)


class TestComputeHeikinAshiSmoothed:
    """Tests for compute_heikin_ashi_smoothed function."""

    def test_compute_heikin_ashi_smoothed_returns_4_columns(self):
        """Returns ha_open, ha_high, ha_low, ha_close columns."""
        np.random.seed(42)
        df = pd.DataFrame({
            "open": np.random.randn(100).cumsum() + 100,
            "high": np.random.randn(100).cumsum() + 102,
            "low": np.random.randn(100).cumsum() + 98,
            "close": np.random.randn(100).cumsum() + 100,
        })
        result = compute_heikin_ashi_smoothed(df, period=10)
        assert list(result.columns) == ["ha_open", "ha_high", "ha_low", "ha_close"]
        assert len(result) == len(df)


class TestBuildIndicatorDataframe:
    """Tests for build_indicator_dataframe function."""

    @pytest.fixture
    def sample_ohlcv(self):
        """Create a sample OHLCV DataFrame with 300 rows."""
        np.random.seed(42)
        n = 300
        close = np.random.randn(n).cumsum() + 100
        return pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=n, freq="B"),
            "open": close + np.random.randn(n) * 0.5,
            "high": close + abs(np.random.randn(n)),
            "low": close - abs(np.random.randn(n)),
            "close": close,
            "volume": np.random.randint(1000000, 5000000, size=n).astype(float),
        })

    def test_build_indicator_dataframe_columns(self, sample_ohlcv):
        """build_indicator_dataframe adds all expected indicator columns."""
        result = build_indicator_dataframe(sample_ohlcv)
        expected_cols = [
            "ema9", "ema21", "ema55", "ma200",
            "macd", "macd_signal", "macd_histogram",
            "ha_smooth_open", "ha_smooth_high", "ha_smooth_low", "ha_smooth_close",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_build_indicator_dataframe_preserves_original(self, sample_ohlcv):
        """Original columns still present after adding indicators."""
        result = build_indicator_dataframe(sample_ohlcv)
        for col in ["date", "open", "high", "low", "close", "volume"]:
            assert col in result.columns, f"Original column missing: {col}"

    def test_ma200_nan_count(self, sample_ohlcv):
        """First 199 rows of ma200 are NaN, row 200 onwards is not NaN."""
        result = build_indicator_dataframe(sample_ohlcv)
        assert result["ma200"].iloc[:199].isna().all()
        assert result["ma200"].iloc[199:].notna().all()
