"""Signal fixture loader for published MDM signal histories.

Loads CSV files containing Dr. K's published Buy/Sell/Cash signals
into validated DataFrames for use as ground truth in signal comparison.
"""

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
