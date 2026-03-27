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
