"""
Global Liquidity Loader Module

Loads weekly global liquidity CSV (Fed+ECB+BOJ balance sheets),
applies publication lag offset to prevent look-ahead bias,
and merges to daily trading dates via merge_asof.

Used by MDM V2 engine for QE floor SELL suppression (v5.0, LIQ-01/LIQ-03).
"""

from enum import Enum

import pandas as pd


class LiquidityRegime(Enum):
    """Liquidity regime classification.

    EXPANDING: Global liquidity growth positive (suppress SELL signals).
    NEUTRAL: Insufficient data or flat liquidity.
    CONTRACTING: Global liquidity declining.
    """

    EXPANDING = "EXPANDING"
    NEUTRAL = "NEUTRAL"
    CONTRACTING = "CONTRACTING"


class LiquidityLoader:
    """Loads weekly global liquidity data and merges to daily trading dates.

    The CSV contains weekly observations (Wednesdays) with columns:
    date, WALCL, fed_net, ECB_USD, BOJ_USD, global_liquidity,
    liquidity_roc_20w, qe_floor.

    Publication lag offset shifts liquidity dates forward by a configurable
    number of days to prevent look-ahead bias: weekly data released with delay,
    so a Monday trader would only know last week's (or older) observation.

    Args:
        csv_path: Path to global_liquidity.csv file.
    """

    def __init__(self, csv_path: str = "data/global_liquidity.csv"):
        self.csv_path = csv_path

    def load_and_merge(
        self, daily_df: pd.DataFrame, publication_lag_days: int = 7
    ) -> pd.DataFrame:
        """Load liquidity CSV and merge to daily trading dates.

        Uses pd.merge_asof with backward direction so each daily date
        gets the most recent liquidity observation that was available
        (after accounting for publication lag).

        Args:
            daily_df: DataFrame with 'date' column (daily trading dates).
                Must contain at least a 'date' column. Other columns are preserved.
            publication_lag_days: Number of days to shift liquidity dates forward
                to prevent look-ahead bias. Default 7 (one week).

        Returns:
            DataFrame with same rows as daily_df plus added columns:
            global_liquidity, liquidity_roc_20w, qe_floor.
            Pre-data dates get qe_floor=0 and NaN for other liquidity columns.
        """
        # Read weekly liquidity data
        liq = pd.read_csv(self.csv_path, parse_dates=["date"])

        # Select only needed columns
        liq = liq[["date", "global_liquidity", "liquidity_roc_20w", "qe_floor"]].copy()

        # Apply publication lag: shift dates forward so merge_asof
        # only matches observations that would have been available
        liq["date"] = liq["date"] + pd.Timedelta(days=publication_lag_days)

        # Sort both DataFrames by date (required for merge_asof)
        liq = liq.sort_values("date").reset_index(drop=True)
        daily_sorted = daily_df.sort_values("date").reset_index(drop=True)

        # Merge: each daily date gets the most recent available liquidity observation
        merged = pd.merge_asof(
            daily_sorted, liq, on="date", direction="backward"
        )

        # Fill NaN in qe_floor with 0 (pre-2007 dates have no liquidity data)
        merged["qe_floor"] = merged["qe_floor"].fillna(0).astype(int)

        return merged
