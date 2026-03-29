"""Tests for the unified DataLoader class."""

import pytest
import pandas as pd

from core.data_loader import DataLoader


class TestLoaderConstruction:
    """Test DataLoader construction and market validation."""

    def test_loader_accepts_nasdaq(self):
        loader = DataLoader('nasdaq')
        assert loader is not None

    def test_loader_accepts_sp500(self):
        loader = DataLoader('sp500')
        assert loader is not None

    def test_loader_accepts_vn30(self):
        loader = DataLoader('vn30')
        assert loader is not None

    def test_loader_rejects_invalid_market(self):
        with pytest.raises(ValueError):
            DataLoader('invalid')


class TestOutputSchema:
    """Test that loaded DataFrames have correct columns and dtypes."""

    @pytest.fixture(params=['nasdaq', 'sp500', 'vn30'])
    def loaded_df(self, request):
        loader = DataLoader(request.param)
        return loader.load()

    def test_output_columns(self, loaded_df):
        expected = ['date', 'open', 'high', 'low', 'close', 'volume']
        assert list(loaded_df.columns) == expected

    def test_date_dtype(self, loaded_df):
        assert pd.api.types.is_datetime64_any_dtype(loaded_df['date'])

    def test_close_dtype(self, loaded_df):
        assert loaded_df['close'].dtype == 'float64'

    def test_volume_dtype(self, loaded_df):
        assert loaded_df['volume'].dtype == 'float64'

    def test_no_nulls(self, loaded_df):
        assert loaded_df.isnull().sum().sum() == 0

    def test_date_sort_ascending(self, loaded_df):
        assert loaded_df['date'].is_monotonic_increasing


class TestNasdaqNormalization:
    """Test NASDAQ price normalization (divide OHLC by 1000)."""

    @pytest.fixture
    def nasdaq_df(self):
        return DataLoader('nasdaq').load()

    def test_nasdaq_close_2020_01_02(self, nasdaq_df):
        row = nasdaq_df[nasdaq_df['date'] == '2020-01-02']
        assert len(row) == 1
        assert row['close'].iloc[0] == pytest.approx(9092.19, rel=0.001)

    def test_nasdaq_volume_not_normalized(self, nasdaq_df):
        """Volume should be in billions, not divided by 1000."""
        row = nasdaq_df[nasdaq_df['date'] == '2020-01-02']
        assert row['volume'].iloc[0] > 1_000_000_000


class TestSP500Normalization:
    """Test S&P500 price normalization (divide OHLC by 1000)."""

    @pytest.fixture
    def sp500_df(self):
        return DataLoader('sp500').load()

    def test_sp500_close_2020_01_02(self, sp500_df):
        row = sp500_df[sp500_df['date'] == '2020-01-02']
        assert len(row) == 1
        assert row['close'].iloc[0] == pytest.approx(3257.85, rel=0.001)


class TestVN30NoNormalization:
    """Test VN30 data stays at native scale."""

    @pytest.fixture
    def vn30_df(self):
        return DataLoader('vn30').load()

    def test_vn30_native_scale(self, vn30_df):
        """VN30 close values should be in the ~1000-1800 range, not divided."""
        latest_close = vn30_df['close'].iloc[-1]
        assert 500 < latest_close < 3000


class TestDateRangeFilter:
    """Test date range filtering."""

    def test_date_range_filter(self):
        df = DataLoader('nasdaq').load(
            start_date='2020-01-01', end_date='2020-12-31'
        )
        assert df['date'].min() >= pd.Timestamp('2020-01-01')
        assert df['date'].max() <= pd.Timestamp('2020-12-31')
        assert len(df) > 0


class TestSpotCheckNasdaq:
    """Spot-check NASDAQ normalized prices against known reference values."""

    @pytest.fixture
    def nasdaq_df(self):
        return DataLoader('nasdaq').load()

    def test_nasdaq_2020_01_02(self, nasdaq_df):
        row = nasdaq_df[nasdaq_df['date'] == '2020-01-02']
        assert row['close'].iloc[0] == pytest.approx(9092.19, rel=0.001)

    def test_nasdaq_2020_03_23(self, nasdaq_df):
        """COVID low."""
        row = nasdaq_df[nasdaq_df['date'] == '2020-03-23']
        assert row['close'].iloc[0] == pytest.approx(6860.67, rel=0.001)

    def test_nasdaq_1974_10_03(self, nasdaq_df):
        """1974 bear market bottom area."""
        row = nasdaq_df[nasdaq_df['date'] == '1974-10-03']
        assert len(row) == 1
        assert row['close'].iloc[0] == pytest.approx(54.87, rel=0.001)

    def test_nasdaq_2000_03_10(self, nasdaq_df):
        """Dot-com peak."""
        row = nasdaq_df[nasdaq_df['date'] == '2000-03-10']
        assert len(row) == 1
        assert row['close'].iloc[0] == pytest.approx(5048.62, rel=0.001)

    def test_nasdaq_2008_11_20(self, nasdaq_df):
        """Financial crisis low."""
        row = nasdaq_df[nasdaq_df['date'] == '2008-11-20']
        assert len(row) == 1
        assert row['close'].iloc[0] == pytest.approx(1316.12, rel=0.001)

    def test_nasdaq_2021_11_19(self, nasdaq_df):
        """Near all-time high."""
        row = nasdaq_df[nasdaq_df['date'] == '2021-11-19']
        assert row['close'].iloc[0] == pytest.approx(16057.4375, rel=0.001)


class TestFullNasdaqRange:
    """Test NASDAQ data covers full 1974+ range for indicator computation."""

    @pytest.fixture
    def nasdaq_df(self):
        return DataLoader('nasdaq').load()

    def test_earliest_date_before_1974(self, nasdaq_df):
        """Data starts in 1973 or earlier."""
        assert nasdaq_df['date'].min() <= pd.Timestamp('1974-01-01')

    def test_row_count_over_13000(self, nasdaq_df):
        """Full dataset has 13000+ trading days."""
        assert len(nasdaq_df) > 13000

    def test_no_gaps_over_5_trading_days(self, nasdaq_df):
        """No gaps longer than 5 calendar days (weekends + holidays)."""
        date_diffs = nasdaq_df['date'].diff().dropna()
        max_gap = date_diffs.max()
        # Longest gap should be ~9 days (holiday + weekend combo)
        assert max_gap <= pd.Timedelta(days=10), f"Max gap: {max_gap}"


class TestSpotCheckSP500:
    """Spot-check S&P500 normalized prices against known reference values."""

    @pytest.fixture
    def sp500_df(self):
        return DataLoader('sp500').load()

    def test_sp500_2020_01_02(self, sp500_df):
        row = sp500_df[sp500_df['date'] == '2020-01-02']
        assert row['close'].iloc[0] == pytest.approx(3257.85, rel=0.001)

    def test_sp500_2020_03_23(self, sp500_df):
        """COVID low."""
        row = sp500_df[sp500_df['date'] == '2020-03-23']
        assert row['close'].iloc[0] == pytest.approx(2237.40, rel=0.001)

    def test_sp500_2021_12_31(self, sp500_df):
        row = sp500_df[sp500_df['date'] == '2021-12-31']
        assert row['close'].iloc[0] == pytest.approx(4766.19, rel=0.001)
