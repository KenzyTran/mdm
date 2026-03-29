"""
Core Indicator Computation Module

Compute EMA 9/21/55, MA 200, MACD (12,26,9), Heikin Ashi, and
Heikin Ashi Smoothed candles on OHLCV DataFrames.

All EMA calculations use adjust=False to match standard charting
platform behavior (TradingView, StockCharts).

All SMA calculations use min_periods=window to avoid partial-window
averages that produce misleading early values.
"""

import pandas as pd


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    """Compute Exponential Moving Average using standard recursive formula.

    Uses adjust=False to match TradingView/StockCharts EMA behavior.
    The first value equals the first input value (no weighted average).

    Args:
        series: Price series (typically close prices).
        span: EMA period (e.g., 9, 21, 55).

    Returns:
        EMA series with same index as input.
    """
    return series.ewm(span=span, adjust=False).mean()


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    """Compute Simple Moving Average with strict min_periods.

    Uses min_periods=window so early rows are NaN rather than
    misleading partial-window averages.

    Args:
        series: Price series (typically close prices).
        window: SMA period (e.g., 200).

    Returns:
        SMA series. First (window-1) values will be NaN.
    """
    return series.rolling(window=window, min_periods=window).mean()


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Compute MACD line, signal line, and histogram.

    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(signal) of MACD
    Histogram = MACD - Signal

    All internal EMAs use adjust=False.

    Args:
        close: Close price series.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        DataFrame with columns [macd, macd_signal, macd_histogram].
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({
        "macd": macd_line,
        "macd_signal": signal_line,
        "macd_histogram": histogram,
    })


def compute_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Heikin Ashi OHLC from standard OHLC.

    HA Close = (O + H + L + C) / 4
    HA Open[0] = (O[0] + C[0]) / 2
    HA Open[i] = (HA Open[i-1] + HA Close[i-1]) / 2  (recursive)
    HA High = max(H, HA Open, HA Close) per row
    HA Low = min(L, HA Open, HA Close) per row

    Args:
        df: DataFrame with columns [open, high, low, close].

    Returns:
        DataFrame with columns [ha_open, ha_high, ha_low, ha_close].
    """
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

    ha_open = pd.Series(index=df.index, dtype="float64")
    ha_open.iloc[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2

    ha_high = pd.concat([df["high"], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df["low"], ha_open, ha_close], axis=1).min(axis=1)

    return pd.DataFrame({
        "ha_open": ha_open,
        "ha_high": ha_high,
        "ha_low": ha_low,
        "ha_close": ha_close,
    })


def compute_heikin_ashi_smoothed(
    df: pd.DataFrame, period: int = 55
) -> pd.DataFrame:
    """Compute Heikin Ashi Smoothed candles.

    Two-stage process:
    1. Smooth each of open/high/low/close with EMA(period) using adjust=False
    2. Compute Heikin Ashi candles from the smoothed OHLC

    Args:
        df: DataFrame with columns [open, high, low, close].
        period: EMA smoothing period (default 55, matching Dr. K's setup).

    Returns:
        DataFrame with columns [ha_open, ha_high, ha_low, ha_close].
    """
    smoothed = pd.DataFrame({
        "open": df["open"].ewm(span=period, adjust=False).mean(),
        "high": df["high"].ewm(span=period, adjust=False).mean(),
        "low": df["low"].ewm(span=period, adjust=False).mean(),
        "close": df["close"].ewm(span=period, adjust=False).mean(),
    })
    return compute_heikin_ashi(smoothed)


def build_indicator_dataframe(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Add all Phase 8 indicators to an OHLCV DataFrame.

    Adds: ema9, ema21, ema55, ma200, macd, macd_signal, macd_histogram,
    ha_smooth_open, ha_smooth_high, ha_smooth_low, ha_smooth_close.

    Args:
        ohlcv: DataFrame with columns [date, open, high, low, close, volume].

    Returns:
        Copy of input DataFrame with all indicator columns appended.
        Original columns are preserved unchanged.
    """
    df = ohlcv.copy()

    # IND-01: EMAs on close
    df["ema9"] = compute_ema(df["close"], span=9)
    df["ema21"] = compute_ema(df["close"], span=21)
    df["ema55"] = compute_ema(df["close"], span=55)

    # IND-02: MA 200
    df["ma200"] = compute_sma(df["close"], window=200)

    # IND-03: MACD (12, 26, 9)
    macd_df = compute_macd(df["close"])
    df["macd"] = macd_df["macd"]
    df["macd_signal"] = macd_df["macd_signal"]
    df["macd_histogram"] = macd_df["macd_histogram"]

    # IND-04: Heikin Ashi Smoothed (period=55)
    ha_smoothed = compute_heikin_ashi_smoothed(df, period=55)
    df["ha_smooth_open"] = ha_smoothed["ha_open"].values
    df["ha_smooth_high"] = ha_smoothed["ha_high"].values
    df["ha_smooth_low"] = ha_smoothed["ha_low"].values
    df["ha_smooth_close"] = ha_smoothed["ha_close"].values

    return df
