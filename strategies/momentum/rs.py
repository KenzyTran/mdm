"""Vectorized Relative Strength computation (Phase 35, MOM-01/MOM-02/MOM-03).

Computes cross-sectional RS percentile ranks for all (date, ticker) pairs
using pivot + pct_change + rank — no per-ticker loops.

Exports:
    compute_rs_panel: Core RS computation (no I/O).
    get_rs_rankings: High-level entry point with parquet caching + DB loading.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from strategies.momentum.config import RSConfig

CACHE_DIR = Path("docs/audits/phase32/cache")


def _cache_path(formula: str, mode: str, start: str, end: str) -> Path:
    """Return cache file path: rs_{formula}_{mode}_{start}_{end}.parquet"""
    return CACHE_DIR / f"rs_{formula}_{mode}_{start}_{end}.parquet"


def get_rs_rankings(
    formula: str,
    period: tuple[str, str],
    mode: str = "current-vn100",
    config: RSConfig | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Load or compute RS rankings, caching to parquet.

    Args:
        formula: "weighted_roc" or "roc126".
        period: (start_date, end_date) as strings "YYYY-MM-DD".
        mode: Universe mode — "current-vn100", "liquidity-reconstructed", or "vn30-only".
        config: RSConfig (defaults to RSConfig() if None).
        force: If True, recompute even if cache exists.

    Returns:
        DataFrame with columns [date, ticker, rs_raw, rs_rank].
    """
    if config is None:
        config = RSConfig()
    start, end = period
    path = _cache_path(formula, mode, start, end)

    if path.exists() and not force:
        return pd.read_parquet(path)

    # Load OHLC data from Postgres (lazy imports to avoid DB dep at import time)
    from connectors import postgres
    from connectors.adjust import adjust_ohlc
    from strategies.canslim.universe import UniverseLoader

    pg = postgres.get_engine()
    loader = UniverseLoader(mode=mode, pg_engine=pg, min_history_days=config.min_history_days)

    # Get universe tickers at end of period
    from datetime import date as dt_date
    from datetime import timedelta

    end_date = dt_date.fromisoformat(end)
    tickers = sorted(loader.get(end_date))

    # Need extra history before start for longest lookback (252 days ~ 1 year)
    # Load from ~400 calendar days before start to ensure enough trading days
    pre_start = (dt_date.fromisoformat(start) - timedelta(days=400)).isoformat()
    raw = postgres.load_stock_eod(tickers, pre_start, end)
    ohlc = adjust_ohlc(raw)

    # Compute RS panel
    result = compute_rs_panel(ohlc, formula, config)

    # Filter to requested period only (exclude pre-start warm-up rows)
    result = result[result["date"] >= pd.Timestamp(start)].reset_index(drop=True)

    # Cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(path, index=False)
    return result


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
