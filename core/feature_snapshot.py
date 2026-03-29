"""Feature Snapshot Extraction Module

Joins indicator-enriched NASDAQ data with signal dates to produce a single
DataFrame containing all indicator values and derived boolean features at
each signal date. This snapshot is the direct input to Phase 9 rule discovery.

Weekend signal dates are snapped to the nearest prior trading day (Friday)
since markets are closed on weekends.
"""

import pandas as pd


def snap_to_trading_day(
    signal_date: pd.Timestamp,
    trading_dates: pd.DatetimeIndex,
    max_lookback: int = 5,
) -> pd.Timestamp:
    """Snap a signal date to the nearest prior trading day.

    If the signal date already falls on a trading day, return it unchanged.
    Otherwise, search backward day by day up to max_lookback days for a
    matching trading day. This handles the 10 known weekend signal dates
    in Dr. K's published history by snapping to Friday.

    Args:
        signal_date: The date of the published signal.
        trading_dates: DatetimeIndex of known trading days from OHLCV data.
        max_lookback: Maximum number of days to search backward (default 5).

    Returns:
        The matched trading day as pd.Timestamp, or pd.NaT if no match found
        within max_lookback.
    """
    # Normalize to midnight for consistent comparison
    signal_date = pd.Timestamp(signal_date).normalize()
    trading_set = set(trading_dates.normalize())

    if signal_date in trading_set:
        return signal_date

    for i in range(1, max_lookback + 1):
        candidate = signal_date - pd.Timedelta(days=i)
        if candidate in trading_set:
            return candidate

    return pd.NaT


def extract_feature_snapshot(
    indicators_df: pd.DataFrame,
    signals_df: pd.DataFrame,
) -> pd.DataFrame:
    """Extract a feature snapshot by joining indicators with signal dates.

    For each signal date, looks up the indicator values on that trading day
    (snapping weekend dates to the prior Friday). Adds 8 derived boolean
    features capturing EMA crossover states and price-vs-MA relationships.

    Args:
        indicators_df: DataFrame from build_indicator_dataframe() with columns
            including date, close, ema9, ema21, ema55, ma200, macd,
            macd_signal, macd_histogram, ha_smooth_*.
        signals_df: DataFrame from load_signal_fixture() with columns
            date, signal, gain_loss_pct.

    Returns:
        DataFrame with one row per signal date, containing all indicator
        columns plus 8 derived boolean features, sorted by date.
    """
    # Step 1: Normalize date columns to datetime64
    ind = indicators_df.copy()
    ind["date"] = pd.to_datetime(ind["date"]).dt.normalize()

    sig = signals_df.copy()
    sig["date"] = pd.to_datetime(sig["date"]).dt.normalize()

    # Step 2: Get trading dates
    trading_dates = pd.DatetimeIndex(ind["date"])

    # Step 3: Snap each signal date to a trading day
    sig["lookup_date"] = sig["date"].apply(
        lambda d: snap_to_trading_day(d, trading_dates)
    )

    # Step 4: Build mapping with original date + lookup date + signal info
    mapping = sig[["date", "lookup_date", "signal"]].copy()
    mapping = mapping.rename(columns={"date": "original_date"})
    if "gain_loss_pct" in sig.columns:
        mapping["gain_loss_pct"] = sig["gain_loss_pct"].values

    # Step 5: Merge mapping with indicators on lookup_date == date
    result = mapping.merge(
        ind,
        left_on="lookup_date",
        right_on="date",
        how="left",
    )

    # Step 6: Replace date with original signal date
    result["date"] = result["original_date"]
    result = result.drop(columns=["original_date", "lookup_date"])

    # Step 7: Add 8 derived boolean features
    # Use .fillna(False) before bool cast to handle NaN from warmup period
    result["ema9_above_ema21"] = (result["ema9"] > result["ema21"]).fillna(False).astype(bool)
    result["ema21_above_ema55"] = (result["ema21"] > result["ema55"]).fillna(False).astype(bool)
    result["close_above_ma200"] = (result["close"] > result["ma200"]).fillna(False).astype(bool)
    result["close_above_ema9"] = (result["close"] > result["ema9"]).fillna(False).astype(bool)
    result["close_above_ema21"] = (result["close"] > result["ema21"]).fillna(False).astype(bool)
    result["close_above_ema55"] = (result["close"] > result["ema55"]).fillna(False).astype(bool)
    result["macd_histogram_positive"] = (result["macd_histogram"] > 0).fillna(False).astype(bool)
    result["macd_above_signal"] = (result["macd"] > result["macd_signal"]).fillna(False).astype(bool)

    # Step 8: Sort by date and return
    result = result.sort_values("date").reset_index(drop=True)

    return result
