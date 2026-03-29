"""Unit and integration tests for feature snapshot extraction.

Tests snap_to_trading_day and extract_feature_snapshot functions
that join indicator-enriched OHLCV data with signal dates to produce
a single DataFrame for rule discovery.
"""

import numpy as np
import pandas as pd
import pytest

from core.feature_snapshot import extract_feature_snapshot, snap_to_trading_day


# ---------------------------------------------------------------------------
# Helpers: build small synthetic DataFrames for unit tests
# ---------------------------------------------------------------------------

def _make_trading_dates(start: str, periods: int) -> pd.DatetimeIndex:
    """Generate weekday-only DatetimeIndex (Mon-Fri)."""
    return pd.bdate_range(start=start, periods=periods)


def _make_ohlcv(n: int = 30, start: str = "2020-01-06") -> pd.DataFrame:
    """Build a minimal synthetic OHLCV DataFrame with n business days."""
    dates = _make_trading_dates(start, n)
    base = 100.0 + np.arange(n, dtype=float) * 0.5
    return pd.DataFrame({
        "date": dates,
        "open": base - 0.5,
        "high": base + 1.0,
        "low": base - 1.0,
        "close": base,
        "volume": np.full(n, 1e6),
    })


def _make_indicators_df(n: int = 30, start: str = "2020-01-06") -> pd.DataFrame:
    """Build a synthetic indicators DataFrame matching build_indicator_dataframe output."""
    ohlcv = _make_ohlcv(n, start)
    base = ohlcv["close"]
    ohlcv["ema9"] = base - 0.1
    ohlcv["ema21"] = base - 0.3
    ohlcv["ema55"] = base - 0.5
    ohlcv["ma200"] = base - 1.0
    ohlcv["macd"] = pd.Series(np.linspace(0.1, 0.5, n))
    ohlcv["macd_signal"] = pd.Series(np.linspace(0.05, 0.4, n))
    ohlcv["macd_histogram"] = ohlcv["macd"] - ohlcv["macd_signal"]
    ohlcv["ha_smooth_open"] = base - 0.2
    ohlcv["ha_smooth_high"] = base + 0.8
    ohlcv["ha_smooth_low"] = base - 0.8
    ohlcv["ha_smooth_close"] = base + 0.1
    return ohlcv


def _make_signals(dates, signal_types=None) -> pd.DataFrame:
    """Build a small signals DataFrame."""
    if signal_types is None:
        signal_types = ["Buy"] * len(dates)
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "signal": signal_types,
        "gain_loss_pct": [0.0] * len(dates),
    })


# ===========================================================================
# Unit Tests: snap_to_trading_day
# ===========================================================================

class TestSnapToTradingDay:
    """Tests for the snap_to_trading_day helper."""

    def test_snap_weekend_to_friday(self):
        """Saturday Jan 11 2020 snaps to Friday Jan 10 2020."""
        # Mon Jan 6 through Fri Jan 10
        trading_dates = _make_trading_dates("2020-01-06", 5)
        signal_date = pd.Timestamp("2020-01-11")  # Saturday
        result = snap_to_trading_day(signal_date, trading_dates)
        assert result == pd.Timestamp("2020-01-10")

    def test_snap_weekday_unchanged(self):
        """Wednesday Jan 8 2020 with matching OHLCV returns unchanged."""
        trading_dates = _make_trading_dates("2020-01-06", 5)
        signal_date = pd.Timestamp("2020-01-08")  # Wednesday
        result = snap_to_trading_day(signal_date, trading_dates)
        assert result == pd.Timestamp("2020-01-08")

    def test_snap_searches_backward(self):
        """If Friday is missing (holiday), snaps to Thursday."""
        # Only Mon-Thu (Jan 6-9), no Friday
        trading_dates = pd.DatetimeIndex([
            pd.Timestamp("2020-01-06"),
            pd.Timestamp("2020-01-07"),
            pd.Timestamp("2020-01-08"),
            pd.Timestamp("2020-01-09"),
        ])
        signal_date = pd.Timestamp("2020-01-11")  # Saturday
        result = snap_to_trading_day(signal_date, trading_dates)
        assert result == pd.Timestamp("2020-01-09")  # Thursday

    def test_snap_no_match_returns_nat(self):
        """When no match within max_lookback, returns NaT."""
        trading_dates = pd.DatetimeIndex([pd.Timestamp("2020-01-02")])
        signal_date = pd.Timestamp("2020-01-20")
        result = snap_to_trading_day(signal_date, trading_dates, max_lookback=5)
        assert pd.isna(result)


# ===========================================================================
# Unit Tests: extract_feature_snapshot
# ===========================================================================

class TestExtractFeatureSnapshot:
    """Tests for extract_feature_snapshot function."""

    def test_extract_feature_snapshot_row_count(self):
        """With 5 signal dates all matching OHLCV, returns exactly 5 rows."""
        indicators = _make_indicators_df(30)
        signal_dates = indicators["date"].iloc[5:10].tolist()
        signals = _make_signals(signal_dates)
        result = extract_feature_snapshot(indicators, signals)
        assert len(result) == 5

    def test_extract_feature_snapshot_has_indicator_columns(self):
        """Result contains all expected indicator columns."""
        indicators = _make_indicators_df(30)
        signal_dates = indicators["date"].iloc[5:10].tolist()
        signals = _make_signals(signal_dates)
        result = extract_feature_snapshot(indicators, signals)
        for col in ["ema9", "ema21", "ema55", "ma200", "macd", "macd_signal", "macd_histogram"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_extract_feature_snapshot_has_boolean_features(self):
        """Result contains all 8 derived boolean feature columns."""
        indicators = _make_indicators_df(30)
        signal_dates = indicators["date"].iloc[5:10].tolist()
        signals = _make_signals(signal_dates)
        result = extract_feature_snapshot(indicators, signals)
        bool_cols = [
            "ema9_above_ema21", "ema21_above_ema55", "close_above_ma200",
            "close_above_ema9", "close_above_ema21", "close_above_ema55",
            "macd_histogram_positive", "macd_above_signal",
        ]
        for col in bool_cols:
            assert col in result.columns, f"Missing boolean column: {col}"

    def test_extract_feature_snapshot_has_ha_columns(self):
        """Result contains Heikin Ashi Smoothed columns."""
        indicators = _make_indicators_df(30)
        signal_dates = indicators["date"].iloc[5:10].tolist()
        signals = _make_signals(signal_dates)
        result = extract_feature_snapshot(indicators, signals)
        for col in ["ha_smooth_open", "ha_smooth_high", "ha_smooth_low", "ha_smooth_close"]:
            assert col in result.columns, f"Missing HA column: {col}"

    def test_extract_feature_snapshot_has_signal_column(self):
        """Result contains signal column with values from input."""
        indicators = _make_indicators_df(30)
        signal_dates = indicators["date"].iloc[5:10].tolist()
        signals = _make_signals(signal_dates, ["Buy", "Sell", "Cash", "Buy", "Sell"])
        result = extract_feature_snapshot(indicators, signals)
        assert "signal" in result.columns
        assert set(result["signal"].unique()) == {"Buy", "Sell", "Cash"}

    def test_boolean_features_are_bool_dtype(self):
        """All 8 boolean feature columns have dtype bool."""
        indicators = _make_indicators_df(30)
        signal_dates = indicators["date"].iloc[5:10].tolist()
        signals = _make_signals(signal_dates)
        result = extract_feature_snapshot(indicators, signals)
        bool_cols = [
            "ema9_above_ema21", "ema21_above_ema55", "close_above_ma200",
            "close_above_ema9", "close_above_ema21", "close_above_ema55",
            "macd_histogram_positive", "macd_above_signal",
        ]
        for col in bool_cols:
            assert result[col].dtype == bool, f"{col} dtype is {result[col].dtype}, expected bool"

    def test_no_nan_after_warmup(self):
        """For signal dates after row 250, all indicator columns have no NaN.

        Uses a 300-row synthetic DataFrame to test warmup behavior.
        (ma200 needs 200 rows, so row 250 is well past warmup.)
        """
        # Build 300-row indicators with real NaN for ma200 in first 199 rows
        n = 300
        ohlcv = _make_ohlcv(n, start="2019-01-02")
        base = ohlcv["close"]
        ohlcv["ema9"] = base - 0.1
        ohlcv["ema21"] = base - 0.3
        ohlcv["ema55"] = base - 0.5
        # Realistic: first 199 rows NaN for ma200
        ma200 = pd.Series(np.nan, index=ohlcv.index)
        ma200.iloc[199:] = base.iloc[199:] - 1.0
        ohlcv["ma200"] = ma200
        ohlcv["macd"] = pd.Series(np.linspace(0.1, 0.5, n))
        ohlcv["macd_signal"] = pd.Series(np.linspace(0.05, 0.4, n))
        ohlcv["macd_histogram"] = ohlcv["macd"] - ohlcv["macd_signal"]
        ohlcv["ha_smooth_open"] = base - 0.2
        ohlcv["ha_smooth_high"] = base + 0.8
        ohlcv["ha_smooth_low"] = base - 0.8
        ohlcv["ha_smooth_close"] = base + 0.1

        # Signal dates at rows 250, 260, 270 (well past warmup)
        signal_dates = ohlcv["date"].iloc[[250, 260, 270]].tolist()
        signals = _make_signals(signal_dates)
        result = extract_feature_snapshot(ohlcv, signals)

        indicator_cols = [
            "ema9", "ema21", "ema55", "ma200",
            "macd", "macd_signal", "macd_histogram",
            "ha_smooth_open", "ha_smooth_high", "ha_smooth_low", "ha_smooth_close",
        ]
        for col in indicator_cols:
            assert result[col].notna().all(), f"NaN found in {col} after warmup"
