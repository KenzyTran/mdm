"""
Unified Data Loader Module

Load and normalize OHLCV data from NASDAQ, S&P500, and VN30 CSV files
into a consistent DataFrame format.

US market data (NASDAQ, S&P500) has OHLC prices scaled by ~1000x in the
source CSVs. This loader normalizes them by dividing OHLC by 1000.
Volume is never divided.
VN30 data is at native scale and not modified.
"""

import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    """Unified loader for NASDAQ, S&P500, and VN30 market data.

    Usage:
        loader = DataLoader('nasdaq')
        df = loader.load(start_date='2020-01-01', end_date='2023-12-31')

    Output DataFrame columns: [date, open, high, low, close, volume]
    """

    COLUMN_MAPS = {
        'nasdaq': {
            'tradingdate': 'date',
            'openprice': 'open',
            'closeprice': 'close',
            'highestprice': 'high',
            'lowestprice': 'low',
            'totalvol': 'volume',
        },
        'sp500': {
            'tradingdate': 'date',
            'openprice': 'open',
            'closeprice': 'close',
            'highestprice': 'high',
            'lowestprice': 'low',
            'totalvol': 'volume',
        },
        'vn30': {
            'tradingdate': 'date',
            'openindex': 'open',
            'closeindex': 'close',
            'highestindex': 'high',
            'lowestindex': 'low',
            'totalvol': 'volume',
        },
    }

    FILE_PATHS = {
        'nasdaq': 'data/NASDAQ.csv',
        'sp500': 'data/s&p500.csv',
        'vn30': 'data/vn30.csv',
    }

    US_MARKETS = {'nasdaq', 'sp500'}
    OHLC_COLS = ['open', 'high', 'low', 'close']
    OUTPUT_COLS = ['date', 'open', 'high', 'low', 'close', 'volume']

    # Reference values for spot-check validation (market -> [(date, close_price)])
    SPOT_CHECKS = {
        'nasdaq': [
            # 1974 bear market bottom area
            ('1974-10-03', 54.87),
            # Dot-com peak (March 10, 2000)
            ('2000-03-10', 5048.62),
            # Financial crisis low (Nov 20, 2008)
            ('2008-11-20', 1316.12),
            # Existing 2020-2021 checks
            ('2020-01-02', 9092.19),
            ('2020-03-23', 6860.67),
            ('2021-11-19', 16057.4375),
        ],
        'sp500': [
            ('2020-01-02', 3257.85),
            ('2020-03-23', 2237.40),
            ('2021-12-31', 4766.19),
        ],
    }

    def __init__(self, market: str, data_dir: Optional[str] = None):
        """Initialize DataLoader for a specific market.

        Args:
            market: Market identifier ('nasdaq', 'sp500', or 'vn30').
            data_dir: Base directory containing the data/ folder.
                      Defaults to current working directory.

        Raises:
            ValueError: If market is not one of the supported markets.
        """
        market = market.lower()
        if market not in self.COLUMN_MAPS:
            supported = ', '.join(sorted(self.COLUMN_MAPS.keys()))
            raise ValueError(
                f"Unsupported market '{market}'. "
                f"Supported markets: {supported}"
            )
        self.market = market
        self.data_dir = Path(data_dir) if data_dir else Path('.')

    def load(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load and normalize market data from CSV.

        Args:
            start_date: Start date filter in 'YYYY-MM-DD' format (inclusive).
            end_date: End date filter in 'YYYY-MM-DD' format (inclusive).

        Returns:
            DataFrame with columns [date, open, high, low, close, volume],
            sorted by date ascending, with no null values.
        """
        filepath = self.data_dir / self.FILE_PATHS[self.market]
        col_map = self.COLUMN_MAPS[self.market]

        # Read CSV and rename columns
        df = pd.read_csv(filepath)
        df = df.rename(columns=col_map)

        # Parse dates: strip quotes, convert to datetime, normalize to midnight
        df['date'] = df['date'].str.strip('"')
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        df['date'] = df['date'].dt.normalize()

        # Convert OHLC and volume to float64
        for col in self.OHLC_COLS + ['volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')

        # Normalize US market OHLC prices (scaled by ~1000x in source)
        if self.market in self.US_MARKETS:
            for col in self.OHLC_COLS:
                df[col] = df[col] / 1000.0

        # Filter by date range if specified
        if start_date is not None:
            df = df[df['date'] >= pd.Timestamp(start_date)]
        if end_date is not None:
            df = df[df['date'] <= pd.Timestamp(end_date)]

        # Sort ascending by date (CSVs are newest-first)
        df = df.sort_values('date').reset_index(drop=True)

        # Drop rows with missing OHLCV values
        df = df.dropna(subset=self.OHLC_COLS + ['volume'])

        # Select output columns only
        df = df[self.OUTPUT_COLS].copy()

        # Run spot-check validation for US markets
        if self.market in self.SPOT_CHECKS:
            self.validate_spot_checks(df, self.market)

        return df

    @staticmethod
    def validate_spot_checks(df: pd.DataFrame, market: str) -> None:
        """Validate loaded data against known reference values.

        Args:
            df: Loaded and normalized DataFrame.
            market: Market identifier.

        Raises:
            ValueError: If any reference value deviates by more than 0.1%
                        from the expected value.
        """
        checks = DataLoader.SPOT_CHECKS.get(market, [])
        for ref_date, ref_close in checks:
            row = df[df['date'] == ref_date]
            if len(row) == 0:
                # Date not in data (may be filtered out) -- skip
                continue
            actual = row['close'].iloc[0]
            rel_error = abs(actual - ref_close) / ref_close
            if rel_error > 0.001:
                raise ValueError(
                    f"Spot-check failed for {market} on {ref_date}: "
                    f"expected close={ref_close}, got {actual} "
                    f"(relative error={rel_error:.6f}, threshold=0.001)"
                )
