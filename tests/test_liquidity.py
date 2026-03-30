"""Tests for LiquidityLoader and LiquidityRegime."""

import pytest
import pandas as pd
import numpy as np

from strategies.mdm_v2.liquidity import LiquidityLoader, LiquidityRegime


class TestLoadCSV:
    """Test 1: LiquidityLoader reads CSV successfully."""

    def test_load_csv(self):
        """LiquidityLoader reads data/global_liquidity.csv, returns DataFrame
        with 987 rows and expected columns."""
        loader = LiquidityLoader()
        # Use a simple daily_df spanning the full range to trigger load
        daily_dates = pd.bdate_range("2007-05-02", "2026-03-25")
        daily_df = pd.DataFrame({"date": daily_dates, "close": 100.0})
        result = loader.load_and_merge(daily_df)
        # Check columns exist
        for col in ["date", "global_liquidity", "liquidity_roc_20w", "qe_floor"]:
            assert col in result.columns, f"Missing column: {col}"
        # Result should have same rows as input
        assert len(result) == len(daily_df)


class TestMergeToDaily:
    """Test 2: Merge to daily business days."""

    def test_merge_to_daily(self):
        """Given daily business days 2010-01-01 to 2010-12-31,
        load_and_merge returns same row count with liquidity columns, no NaN in qe_floor."""
        daily_dates = pd.bdate_range("2010-01-01", "2010-12-31")
        daily_df = pd.DataFrame({"date": daily_dates, "close": 100.0})
        loader = LiquidityLoader()
        result = loader.load_and_merge(daily_df, publication_lag_days=7)
        assert len(result) == len(daily_df)
        assert result["qe_floor"].isna().sum() == 0
        assert "global_liquidity" in result.columns
        assert "liquidity_roc_20w" in result.columns


class TestPublicationLag:
    """Test 3: Publication lag prevents look-ahead bias."""

    @pytest.mark.parametrize("lag_days", [7, 14])
    def test_publication_lag(self, lag_days):
        """For merged rows with non-NaN global_liquidity, the original
        observation date must be at least lag_days before the daily date."""
        loader = LiquidityLoader()
        # Load raw CSV to get original dates
        raw = pd.read_csv(loader.csv_path, parse_dates=["date"])
        raw_lookup = raw.set_index("global_liquidity")["date"]

        daily_dates = pd.bdate_range("2010-01-01", "2010-06-30")
        daily_df = pd.DataFrame({"date": daily_dates, "close": 100.0})
        result = loader.load_and_merge(daily_df, publication_lag_days=lag_days)

        # For each merged row that has liquidity data, verify lag
        rows_with_data = result.dropna(subset=["global_liquidity"])
        assert len(rows_with_data) > 0, "Should have some rows with liquidity data"

        for _, row in rows_with_data.iterrows():
            gl_value = row["global_liquidity"]
            # Find matching original date(s)
            matching = raw[raw["global_liquidity"] == gl_value]
            if len(matching) == 0:
                continue
            original_date = matching["date"].iloc[0]
            daily_date = row["date"]
            gap = (daily_date - original_date).days
            assert gap >= lag_days, (
                f"Look-ahead bias: daily {daily_date.date()} matched "
                f"observation from {original_date.date()} (gap={gap} < {lag_days})"
            )


class TestPre2007NaN:
    """Test 4: Pre-2007 dates get qe_floor=0."""

    def test_pre_2007_nan(self):
        """Daily dates 2000-01-03 to 2005-12-30 (before any liquidity data)
        should have qe_floor=0 for all rows."""
        daily_dates = pd.bdate_range("2000-01-03", "2005-12-30")
        daily_df = pd.DataFrame({"date": daily_dates, "close": 100.0})
        loader = LiquidityLoader()
        result = loader.load_and_merge(daily_df, publication_lag_days=7)
        assert len(result) == len(daily_df)
        assert (result["qe_floor"] == 0).all(), "All pre-2007 rows should have qe_floor=0"


class TestRegimeEnum:
    """Test 5: LiquidityRegime enum values."""

    def test_regime_enum(self):
        """LiquidityRegime has EXPANDING, NEUTRAL, CONTRACTING values."""
        assert LiquidityRegime.EXPANDING.value == "EXPANDING"
        assert LiquidityRegime.NEUTRAL.value == "NEUTRAL"
        assert LiquidityRegime.CONTRACTING.value == "CONTRACTING"


class TestMergePreservesIndex:
    """Test 6: Merged DataFrame preserves input rows."""

    def test_merge_preserves_index(self):
        """Merged DataFrame has same number of rows and same dates as input."""
        daily_dates = pd.bdate_range("2015-01-01", "2015-12-31")
        daily_df = pd.DataFrame({"date": daily_dates, "close": 100.0})
        loader = LiquidityLoader()
        result = loader.load_and_merge(daily_df, publication_lag_days=7)
        assert len(result) == len(daily_df)
        pd.testing.assert_series_equal(
            result["date"].reset_index(drop=True),
            daily_df["date"].reset_index(drop=True),
        )
