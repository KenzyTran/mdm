"""Integration tests for Phase 7 data foundation.

Tests that NASDAQ OHLCV and full 962-signal history work together:
- Date alignment gap report identifies weekend-only gaps
- Signal dates align with OHLCV trading dates (except known weekend gaps)
- Full pipeline produces consistent, usable data for Phase 8
"""

import pandas as pd
import pytest

from core.data_loader import DataLoader
from core.signal_loader import check_signal_date_alignment, load_signal_fixture


FULL_SIGNALS_PATH = "data/signals/nasdaq_signals_full.csv"


class TestSignalDateAlignment:
    """Test signal-to-OHLCV date alignment gap report."""

    @pytest.fixture
    def nasdaq_df(self):
        return DataLoader("nasdaq").load()

    @pytest.fixture
    def full_signals(self):
        return load_signal_fixture(FULL_SIGNALS_PATH)

    def test_gap_report_returns_dataframe(self, full_signals, nasdaq_df):
        """Gap report returns a DataFrame with expected columns."""
        gaps = check_signal_date_alignment(full_signals, nasdaq_df)
        assert isinstance(gaps, pd.DataFrame)
        assert list(gaps.columns) == ["date", "signal", "day_of_week"]

    def test_gap_report_exactly_10_gaps(self, full_signals, nasdaq_df):
        """Exactly 10 signal dates have no matching OHLCV row."""
        gaps = check_signal_date_alignment(full_signals, nasdaq_df)
        assert len(gaps) == 10, (
            f"Expected 10 gaps, got {len(gaps)}. "
            f"Dates: {gaps['date'].tolist()}"
        )

    def test_gap_report_weekend_dates(self, full_signals, nasdaq_df):
        """All gap dates are Saturday or Sunday (not missing trading days)."""
        gaps = check_signal_date_alignment(full_signals, nasdaq_df)
        weekend_days = {"Saturday", "Sunday"}
        for _, row in gaps.iterrows():
            assert row["day_of_week"] in weekend_days, (
                f"Gap date {row['date']} is {row['day_of_week']}, "
                f"expected weekend"
            )

    def test_gap_report_known_dates(self, full_signals, nasdaq_df):
        """Gap report includes known weekend signal dates."""
        gaps = check_signal_date_alignment(full_signals, nasdaq_df)
        gap_dates = set(gaps["date"].dt.strftime("%Y-%m-%d"))
        # Spot-check a few known weekend dates from research
        assert "2000-03-10" not in gap_dates  # Friday, should align
        assert "1979-10-06" in gap_dates  # Saturday, known gap

    def test_gap_report_warns(self, full_signals, nasdaq_df):
        """Gap report emits a UserWarning about mismatched dates."""
        with pytest.warns(UserWarning, match="signal date"):
            check_signal_date_alignment(full_signals, nasdaq_df)

    def test_aligned_count(self, full_signals, nasdaq_df):
        """952 of 962 signal dates have matching OHLCV rows."""
        gaps = check_signal_date_alignment(full_signals, nasdaq_df)
        aligned = len(full_signals) - len(gaps)
        assert aligned == 952, f"Expected 952 aligned, got {aligned}"


class TestEmptyGapReport:
    """Test gap report with perfectly aligned data."""

    def test_no_gaps_returns_empty(self):
        """When all signal dates match OHLCV dates, return empty DataFrame."""
        signals = pd.DataFrame({
            "date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
            "signal": ["Buy", "Sell"],
        })
        ohlcv = pd.DataFrame({
            "date": pd.to_datetime(
                ["2020-01-02", "2020-01-03", "2020-01-06"]
            ),
        })
        gaps = check_signal_date_alignment(signals, ohlcv)
        assert len(gaps) == 0
        assert list(gaps.columns) == ["date", "signal", "day_of_week"]


class TestFullPipelineIntegration:
    """End-to-end test that both loaders produce compatible data."""

    def test_signal_dates_within_ohlcv_range(self):
        """All signal dates fall within the OHLCV date range."""
        nasdaq = DataLoader("nasdaq").load()
        signals = load_signal_fixture(FULL_SIGNALS_PATH)
        ohlcv_min = nasdaq["date"].min()
        ohlcv_max = nasdaq["date"].max()
        assert signals["date"].min() >= ohlcv_min, (
            f"First signal {signals['date'].min()} before first OHLCV "
            f"{ohlcv_min}"
        )
        assert signals["date"].max() <= ohlcv_max + pd.Timedelta(days=5), (
            f"Last signal {signals['date'].max()} after last OHLCV "
            f"{ohlcv_max} + 5 days"
        )

    def test_ohlcv_covers_signal_era(self):
        """NASDAQ data spans the full 1974-2026 signal era."""
        nasdaq = DataLoader("nasdaq").load()
        assert nasdaq["date"].min() <= pd.Timestamp("1974-07-17"), (
            "OHLCV must start before first signal date 1974-07-17"
        )
        assert nasdaq["date"].max() >= pd.Timestamp("2026-02-01"), (
            "OHLCV must extend to at least Feb 2026"
        )
