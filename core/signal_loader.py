"""Signal fixture loader for published MDM signal histories.

Loads CSV files containing Dr. K's published Buy/Sell/Cash signals
into validated DataFrames for use as ground truth in signal comparison.
"""

import warnings

import pandas as pd


VALID_SIGNALS = {"Buy", "Sell", "Cash"}


def load_signal_fixture(filepath: str) -> pd.DataFrame:
    """Load a published signal history CSV into a structured DataFrame.

    Args:
        filepath: Path to signal CSV. Supports both 3-column
                  (date, signal, gain_loss_pct) and 4-column
                  (+ dollar_becomes) formats.

    Returns:
        DataFrame with parsed dates, validated signal types, numeric
        gain_loss_pct, and optional dollar_becomes column.

    Raises:
        ValueError: If any signal type is not in {Buy, Sell, Cash}
    """
    df = pd.read_csv(filepath)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"])

    # Strip whitespace from signal values (pitfall: extra spaces in manual entry)
    df["signal"] = df["signal"].str.strip()

    # Validate signal types
    invalid = set(df["signal"].unique()) - VALID_SIGNALS
    if invalid:
        raise ValueError(f"Invalid signal types found: {invalid}")

    # Convert gain_loss_pct to numeric (NaN for empty/missing)
    df["gain_loss_pct"] = pd.to_numeric(df["gain_loss_pct"], errors="coerce")

    # Parse dollar_becomes if present (backward compatible per D-01)
    if "dollar_becomes" in df.columns:
        df["dollar_becomes"] = pd.to_numeric(
            df["dollar_becomes"], errors="coerce"
        )

    # Sort by date ascending and reset index
    df = df.sort_values("date").reset_index(drop=True)

    return df


def check_signal_date_alignment(
    signals: pd.DataFrame, ohlcv: pd.DataFrame
) -> pd.DataFrame:
    """Check which signal dates have no matching OHLCV trading day.

    Per D-05: warns and reports but does not fail when signal dates
    have no matching OHLCV row.

    Args:
        signals: Signal DataFrame with 'date' column (datetime64).
        ohlcv: OHLCV DataFrame with 'date' column (datetime64).

    Returns:
        DataFrame with columns [date, signal, day_of_week] for unmatched
        signal dates. Empty DataFrame if all dates align.
    """
    ohlcv_dates = set(ohlcv["date"].dt.normalize())
    sig_dates_norm = signals["date"].dt.normalize()
    mask = ~sig_dates_norm.isin(ohlcv_dates)

    if mask.sum() == 0:
        return pd.DataFrame(columns=["date", "signal", "day_of_week"])

    gaps = signals.loc[mask, ["date", "signal"]].copy()
    gaps["day_of_week"] = gaps["date"].dt.day_name()

    # Warn about gaps per D-05
    warnings.warn(
        f"{len(gaps)} signal date(s) have no matching OHLCV row: "
        f"{gaps['date'].dt.strftime('%Y-%m-%d').tolist()}",
        UserWarning,
        stacklevel=2,
    )

    return gaps.reset_index(drop=True)
