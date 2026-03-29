"""Unit and integration tests for feature snapshot extraction.

Tests snap_to_trading_day and extract_feature_snapshot functions
that join indicator-enriched OHLCV data with signal dates to produce
a single DataFrame for rule discovery.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.data_loader import DataLoader
from core.feature_snapshot import extract_feature_snapshot, snap_to_trading_day
from core.indicators import build_indicator_dataframe
from core.signal_loader import load_signal_fixture


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


# ===========================================================================
# Integration Tests: real 962-signal NASDAQ data
# ===========================================================================

def _find_data_dir() -> str:
    """Find the data directory containing NASDAQ.csv.

    Checks the project root first, then traverses up to find the
    main repo (worktrees may not have gitignored data files).
    """
    project_root = Path(__file__).resolve().parent.parent
    if (project_root / "data" / "NASDAQ.csv").exists():
        return str(project_root)
    # In a worktree, find the main repo via .git file
    git_path = project_root / ".git"
    if git_path.is_file():
        content = git_path.read_text().strip()
        if content.startswith("gitdir:"):
            git_dir = Path(content.split("gitdir:", 1)[1].strip())
            main_repo = git_dir.resolve().parent.parent.parent
            if (main_repo / "data" / "NASDAQ.csv").exists():
                return str(main_repo)
    pytest.skip("NASDAQ.csv not found (data directory unavailable)")


@pytest.fixture(scope="module")
def full_snapshot():
    """Load full 962-signal feature snapshot from real NASDAQ data.

    This is expensive (~5s), so scope="module" ensures it runs once.
    """
    data_dir = _find_data_dir()
    ohlcv = DataLoader(market="nasdaq", data_dir=data_dir).load()
    indicators = build_indicator_dataframe(ohlcv)
    signals = load_signal_fixture(
        str(Path(data_dir) / "data" / "signals" / "nasdaq_signals_full.csv")
    )
    return extract_feature_snapshot(indicators, signals)


class TestFeatureSnapshotIntegration:
    """Integration tests using real 962-signal NASDAQ data."""

    @pytest.mark.integration
    def test_full_snapshot_row_count(self, full_snapshot):
        """Full snapshot has exactly 962 rows (all signals represented)."""
        assert len(full_snapshot) == 962, (
            f"Expected 962 rows, got {len(full_snapshot)}"
        )

    @pytest.mark.integration
    def test_full_snapshot_no_nan_after_warmup(self, full_snapshot):
        """After 1975-06-01 warmup, no NaN in any indicator column."""
        after_warmup = full_snapshot[
            full_snapshot["date"] >= pd.Timestamp("1975-06-01")
        ]
        indicator_cols = [
            "ema9", "ema21", "ema55", "ma200",
            "macd", "macd_signal", "macd_histogram",
            "ha_smooth_open", "ha_smooth_high", "ha_smooth_low", "ha_smooth_close",
        ]
        for col in indicator_cols:
            nan_count = after_warmup[col].isna().sum()
            assert nan_count == 0, (
                f"{col} has {nan_count} NaN values after warmup"
            )

    @pytest.mark.integration
    def test_full_snapshot_boolean_columns_complete(self, full_snapshot):
        """All 8 boolean columns have no NaN for signals after warmup."""
        after_warmup = full_snapshot[
            full_snapshot["date"] >= pd.Timestamp("1975-06-01")
        ]
        bool_cols = [
            "ema9_above_ema21", "ema21_above_ema55", "close_above_ma200",
            "close_above_ema9", "close_above_ema21", "close_above_ema55",
            "macd_histogram_positive", "macd_above_signal",
        ]
        for col in bool_cols:
            assert col in after_warmup.columns, f"Missing bool column: {col}"
            nan_count = after_warmup[col].isna().sum()
            assert nan_count == 0, (
                f"{col} has {nan_count} NaN values after warmup"
            )

    @pytest.mark.integration
    def test_weekend_signals_snapped(self, full_snapshot):
        """Weekend signal dates are present and have valid indicator values."""
        # Check that the snapshot contains dates that fall on weekends
        # (these were snapped but preserved with original date)
        weekend_rows = full_snapshot[
            full_snapshot["date"].dt.dayofweek >= 5
        ]
        # There are 10 known weekend signals in the dataset
        assert len(weekend_rows) == 10, (
            f"Expected 10 weekend signal dates, got {len(weekend_rows)}"
        )
        # All weekend-snapped rows should have valid indicator values
        # (ema9 is always computed, so check it as proxy)
        assert weekend_rows["ema9"].notna().all(), (
            "Some weekend-snapped rows have NaN ema9"
        )

    @pytest.mark.integration
    def test_signal_types_preserved(self, full_snapshot):
        """Signal column contains only Buy/Sell/Cash with all three present."""
        signal_values = set(full_snapshot["signal"].unique())
        assert signal_values == {"Buy", "Sell", "Cash"}, (
            f"Unexpected signal values: {signal_values}"
        )

    @pytest.mark.integration
    def test_full_snapshot_columns(self, full_snapshot):
        """Snapshot contains all required columns for rule discovery."""
        required_cols = [
            "date", "signal",
            "ema9", "ema21", "ema55", "ma200",
            "macd", "macd_signal", "macd_histogram",
            "ha_smooth_open", "ha_smooth_close",
            "ema9_above_ema21", "ema21_above_ema55", "close_above_ma200",
            "macd_histogram_positive", "macd_above_signal",
        ]
        for col in required_cols:
            assert col in full_snapshot.columns, (
                f"Missing required column: {col}"
            )
