"""Vectorized Relative Strength computation (Phase 35, MOM-01/MOM-02).

Computes cross-sectional RS percentile ranks for all (date, ticker) pairs
using pivot + pct_change + rank — no per-ticker loops.

Exports:
    compute_rs_panel: Main entry point for RS computation.
"""
from __future__ import annotations

import pandas as pd

from strategies.momentum.config import RSConfig


def compute_rs_panel(
    ohlc: pd.DataFrame,
    formula: str,
    config: RSConfig | None = None,
) -> pd.DataFrame:
    """Compute RS percentile ranks for all (date, ticker) pairs.

    Args:
        ohlc: Long-format DataFrame with columns [stockcode, tradingdate, adj_close].
        formula: "weighted_roc" (MOM-01) or "roc126" (MOM-02).
        config: RSConfig with lookback/weight parameters. Uses defaults if None.

    Returns:
        DataFrame with columns [date, ticker, rs_raw, rs_rank].
        rs_rank is cross-sectional percentile in [0, 100].
        Rows with insufficient history (NaN rs_raw) are excluded.
    """
    if config is None:
        config = RSConfig()

    # Pivot to wide: rows=dates, cols=tickers, values=adj_close
    wide = ohlc.pivot(index="tradingdate", columns="stockcode", values="adj_close")

    if formula == "roc126":
        raw = wide.pct_change(126, fill_method=None)
    elif formula == "weighted_roc":
        rocs = [wide.pct_change(lb, fill_method=None) for lb in config.roc_days]
        raw = sum(w * r for w, r in zip(config.roc_weights, rocs))
    else:
        raise ValueError(f"Unknown formula: {formula!r}")

    # Cross-sectional percentile rank per date (axis=1 = across tickers)
    ranked = raw.rank(axis=1, pct=True, na_option="keep") * 100.0

    # Melt raw scores to long format
    raw_long = raw.reset_index().melt(
        id_vars="tradingdate",
        var_name="ticker",
        value_name="rs_raw",
    )
    # Melt ranks to long format
    rank_long = ranked.reset_index().melt(
        id_vars="tradingdate",
        var_name="ticker",
        value_name="rs_rank",
    )

    # Merge raw + rank
    result = raw_long.merge(rank_long, on=["tradingdate", "ticker"])
    result = result.rename(columns={"tradingdate": "date"})
    result = result.dropna(subset=["rs_rank"])
    return (
        result[["date", "ticker", "rs_raw", "rs_rank"]]
        .sort_values(["date", "ticker"])
        .reset_index(drop=True)
    )
