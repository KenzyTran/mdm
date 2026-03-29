"""
VN30 Microstructure Filter Module

Annotates DataFrames with VN30-specific columns for market microstructure
adjustments. Functions are stateless DataFrame transformers that add columns
without modifying existing data.

Columns added:
- is_limit_day: Boolean flag for days where index moved >= 6.5% from prev close
- is_expiry_day: Boolean flag for derivative expiry (3rd Thursday of each month)

Per D-01: is_limit_day is informational only -- signals are NOT suppressed.
Per D-02: FTD signals on limit-up days remain valid.
Per D-04: T+2.5 settlement is ignored (signal model, not execution).
Per D-05: DD counting is suppressed on expiry days via volume_up override.
Per D-06: Expiry dates computed algorithmically, no external CSV needed.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta


def add_limit_day_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add is_limit_day boolean column based on intraday range vs prev_close.

    For VN30 index: flags days where high or low approaches the 7%
    theoretical maximum (threshold: >= 6.5% from previous close).
    Index rarely hits exactly 7% since not all 30 stocks hit limit
    simultaneously.

    Args:
        df: DataFrame with 'close', 'high', 'low' columns.

    Returns:
        DataFrame copy with 'is_limit_day' column added.
        First row is always False (no previous close available).
    """
    df = df.copy()
    prev_close = df['close'].shift(1)
    high_pct = (df['high'] - prev_close) / prev_close
    low_pct = (df['low'] - prev_close) / prev_close
    df['is_limit_day'] = (high_pct >= 0.065) | (low_pct <= -0.065)
    # First row has NaN prev_close -> NaN comparison -> False
    df['is_limit_day'] = df['is_limit_day'].fillna(False)
    return df


def _compute_third_thursday(year: int, month: int) -> date:
    """Compute the 3rd Thursday of a given month.

    The 3rd Thursday falls on a day between 15 and 21 inclusive.

    Args:
        year: Calendar year.
        month: Calendar month (1-12).

    Returns:
        date object for the 3rd Thursday of the month.
    """
    # Find the first day of the month
    first_day = date(year, month, 1)
    # Thursday is weekday 3
    # Find first Thursday: offset from day 1
    days_until_thursday = (3 - first_day.weekday()) % 7
    first_thursday = first_day + timedelta(days=days_until_thursday)
    # 3rd Thursday is 2 weeks after the first
    third_thursday = first_thursday + timedelta(weeks=2)
    assert 15 <= third_thursday.day <= 21, (
        f"3rd Thursday {third_thursday} not in expected range 15-21"
    )
    return third_thursday


def add_expiry_day_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add is_expiry_day boolean column for 3rd Thursday of each month.

    Per D-06: Derivative expiry dates computed algorithmically.
    Per Pitfall 1: If the computed 3rd Thursday is NOT a trading day
    in the DataFrame, the preceding trading day gets the flag.

    Args:
        df: DataFrame with 'date' column (datetime or date).

    Returns:
        DataFrame copy with 'is_expiry_day' column added.
    """
    df = df.copy()
    df['is_expiry_day'] = False

    # Build set of trading dates for fast lookup
    trading_dates = set(pd.to_datetime(df['date']).dt.date)

    # For each unique (year, month) in the data, compute expiry
    dates_series = pd.to_datetime(df['date'])
    year_months = dates_series.dt.to_period('M').unique()

    expiry_dates = set()
    for period in year_months:
        year = period.year
        month = period.month
        third_thu = _compute_third_thursday(year, month)

        if third_thu in trading_dates:
            expiry_dates.add(third_thu)
        else:
            # Holiday fallback: find the latest trading day before the 3rd Thursday
            # in the same month
            candidates = [d for d in trading_dates
                          if d.year == year and d.month == month and d < third_thu]
            if candidates:
                expiry_dates.add(max(candidates))

    # Set is_expiry_day for matching rows
    df_dates_as_date = pd.to_datetime(df['date']).dt.date
    df['is_expiry_day'] = df_dates_as_date.isin(expiry_dates)

    return df


def suppress_dd_on_expiry(df: pd.DataFrame) -> pd.DataFrame:
    """Set volume_up to False on expiry days to suppress DD counting.

    Per D-05: Elevated volume on derivative expiry is structural,
    not distribution. This prevents the DD counter from firing on
    these days without modifying the engine's core logic.

    Guard: Only applies if 'is_expiry_day' column exists.
    NASDAQ runs without this column, so no suppression occurs
    (per Pitfall 5).

    Args:
        df: DataFrame with 'volume_up' column and optionally 'is_expiry_day'.

    Returns:
        DataFrame copy with volume_up overridden on expiry days.
    """
    df = df.copy()
    if 'is_expiry_day' in df.columns:
        df.loc[df['is_expiry_day'] == True, 'volume_up'] = False
    return df


def apply_vn30_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all VN30 microstructure filters as a single pipeline.

    Adds is_limit_day and is_expiry_day columns. Does NOT call
    suppress_dd_on_expiry -- that runs after the engine's indicator
    computation creates the volume_up column.

    Args:
        df: DataFrame with OHLCV data (date, open, high, low, close, volume).

    Returns:
        DataFrame with both annotation columns added.
    """
    df = add_limit_day_column(df)
    df = add_expiry_day_column(df)
    return df
