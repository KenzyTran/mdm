"""Tests for signal fixture loading and validation."""

import pandas as pd
import pytest

from core.signal_loader import load_signal_fixture


class TestSignalFixtureLoader:
    """Tests for load_signal_fixture function."""

    def _write_csv(self, tmp_path, content: str) -> str:
        """Helper to write a CSV file and return its path."""
        filepath = tmp_path / "test_signals.csv"
        filepath.write_text(content)
        return str(filepath)

    def test_load_valid_fixture(self, tmp_path):
        """load_signal_fixture returns DataFrame with correct columns."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-04-02,Buy,\n"
            "2020-06-24,Sell,15.3\n"
            "2020-06-29,Buy,\n"
            "2020-09-04,Sell,22.1\n"
        ))
        df = load_signal_fixture(csv)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["date", "signal", "gain_loss_pct"]

    def test_date_dtype(self, tmp_path):
        """date column has dtype datetime64[ns]."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-04-02,Buy,\n"
            "2020-06-24,Sell,15.3\n"
        ))
        df = load_signal_fixture(csv)
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_date_sorted_ascending(self, tmp_path):
        """Dates are monotonically increasing."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-09-04,Sell,22.1\n"
            "2020-04-02,Buy,\n"
            "2020-06-24,Sell,15.3\n"
        ))
        df = load_signal_fixture(csv)
        assert df["date"].is_monotonic_increasing

    def test_valid_signal_types(self, tmp_path):
        """All signal values are in {Buy, Sell, Cash}."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-04-02,Buy,\n"
            "2020-05-01,Cash,\n"
            "2020-06-24,Sell,15.3\n"
        ))
        df = load_signal_fixture(csv)
        valid_signals = {"Buy", "Sell", "Cash"}
        assert set(df["signal"].unique()).issubset(valid_signals)

    def test_invalid_signal_raises(self, tmp_path):
        """A fixture CSV containing signal type 'Hold' raises ValueError."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-04-02,Buy,\n"
            "2020-06-24,Hold,15.3\n"
        ))
        with pytest.raises(ValueError, match="Invalid signal types"):
            load_signal_fixture(csv)

    def test_gain_loss_numeric(self, tmp_path):
        """gain_loss_pct column has dtype float64 (NaN for missing)."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-04-02,Buy,\n"
            "2020-06-24,Sell,15.3\n"
        ))
        df = load_signal_fixture(csv)
        assert df["gain_loss_pct"].dtype == "float64"
        assert pd.isna(df.loc[df["signal"] == "Buy", "gain_loss_pct"].iloc[0])
        assert df.loc[df["signal"] == "Sell", "gain_loss_pct"].iloc[0] == 15.3

    def test_whitespace_stripped(self, tmp_path):
        """Signal values with leading/trailing whitespace are stripped."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-04-02, Buy ,\n"
            "2020-06-24, Sell ,15.3\n"
        ))
        df = load_signal_fixture(csv)
        assert df["signal"].iloc[0] == "Buy"
        assert df["signal"].iloc[1] == "Sell"

    def test_load_4_column_csv(self, tmp_path):
        """load_signal_fixture handles 4-column CSV with dollar_becomes."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct,dollar_becomes\n"
            "2020-04-02,Buy,,1000.00\n"
            "2020-06-24,Sell,15.3,1153.00\n"
        ))
        df = load_signal_fixture(csv)
        assert "dollar_becomes" in df.columns
        assert df["dollar_becomes"].dtype == "float64"
        assert df["dollar_becomes"].iloc[1] == pytest.approx(1153.00)

    def test_3_column_csv_no_dollar_becomes(self, tmp_path):
        """3-column CSV does not produce dollar_becomes column."""
        csv = self._write_csv(tmp_path, (
            "date,signal,gain_loss_pct\n"
            "2020-04-02,Buy,\n"
            "2020-06-24,Sell,15.3\n"
        ))
        df = load_signal_fixture(csv)
        assert "dollar_becomes" not in df.columns


class TestFullSignalHistory:
    """Integration tests for the full 962-signal NASDAQ history."""

    FULL_PATH = "data/signals/nasdaq_signals_full.csv"

    def test_full_signal_history_loads(self):
        """Full 962-signal CSV loads successfully."""
        df = load_signal_fixture(self.FULL_PATH)
        assert len(df) == 962, f"Expected 962 signals, got {len(df)}"

    def test_full_signal_has_dollar_becomes(self):
        """Full signal file includes dollar_becomes column."""
        df = load_signal_fixture(self.FULL_PATH)
        assert "dollar_becomes" in df.columns

    def test_full_signal_dollar_becomes_all_populated(self):
        """All 962 signals have dollar_becomes values (no NaN)."""
        df = load_signal_fixture(self.FULL_PATH)
        assert df["dollar_becomes"].notna().all()

    def test_full_signal_date_range(self):
        """Signals span from 1974 to 2026."""
        df = load_signal_fixture(self.FULL_PATH)
        assert df["date"].min() >= pd.Timestamp("1974-01-01")
        assert df["date"].min() <= pd.Timestamp("1975-01-01")
        assert df["date"].max() >= pd.Timestamp("2026-01-01")

    def test_full_signal_gain_loss_partial(self):
        """gain_loss_pct has ~623 non-null values (Buy/Cash lack this)."""
        df = load_signal_fixture(self.FULL_PATH)
        non_null = df["gain_loss_pct"].notna().sum()
        assert 600 <= non_null <= 650, f"Expected ~623, got {non_null}"

    def test_full_signal_types(self):
        """All signals are Buy, Sell, or Cash."""
        df = load_signal_fixture(self.FULL_PATH)
        assert set(df["signal"].unique()) == {"Buy", "Sell", "Cash"}

    def test_backward_compat_partial_nasdaq(self):
        """Existing 3-column nasdaq_signals.csv still loads correctly."""
        df = load_signal_fixture("data/signals/nasdaq_signals.csv")
        assert len(df) > 10
        assert "dollar_becomes" not in df.columns

    def test_backward_compat_tecl(self):
        """Existing 3-column tecl_signals.csv still loads correctly."""
        df = load_signal_fixture("data/signals/tecl_signals.csv")
        assert len(df) > 10
        assert "dollar_becomes" not in df.columns


class TestSignalFixtureIntegration:
    """Integration tests for actual signal fixture CSV files."""

    TECL_PATH = "data/signals/tecl_signals.csv"
    NASDAQ_PATH = "data/signals/nasdaq_signals.csv"

    def test_tecl_fixture_loads(self):
        """TECL fixture loads and has >10 rows."""
        df = load_signal_fixture(self.TECL_PATH)
        assert len(df) > 10, f"TECL fixture has only {len(df)} rows"

    def test_nasdaq_fixture_loads(self):
        """NASDAQ fixture loads and has >10 rows."""
        df = load_signal_fixture(self.NASDAQ_PATH)
        assert len(df) > 10, f"NASDAQ fixture has only {len(df)} rows"

    def test_tecl_fixture_date_range(self):
        """TECL fixture dates span expected range."""
        df = load_signal_fixture(self.TECL_PATH)
        assert df["date"].min() >= pd.Timestamp("2017-01-01")
        assert df["date"].max() <= pd.Timestamp("2026-12-31")

    def test_nasdaq_fixture_date_range(self):
        """NASDAQ fixture dates span expected range."""
        df = load_signal_fixture(self.NASDAQ_PATH)
        assert df["date"].min() >= pd.Timestamp("2017-01-01")
        assert df["date"].max() <= pd.Timestamp("2026-12-31")

    def test_no_duplicate_dates_tecl(self):
        """TECL fixture has no duplicate dates."""
        df = load_signal_fixture(self.TECL_PATH)
        assert df["date"].is_unique, "TECL fixture contains duplicate dates"

    def test_no_duplicate_dates_nasdaq(self):
        """NASDAQ fixture has no duplicate dates."""
        df = load_signal_fixture(self.NASDAQ_PATH)
        assert df["date"].is_unique, "NASDAQ fixture contains duplicate dates"
