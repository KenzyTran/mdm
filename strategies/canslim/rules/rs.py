"""RS rating rule L (CANS-07).

Formula (locked by plan 29-02/29-06):

    raw_rs = 0.4*ROC(63) + 0.2*ROC(126) + 0.2*ROC(189) + 0.2*ROC(252)

Raw scores are percentile-ranked **within the active universe** at
``as_of_date`` and scaled to ``[0, 100]`` (higher = stronger). Tickers with
fewer than ``config.min_history_days`` bars return NaN and therefore fail
the L rule. Weights / lookbacks are taken from :class:`CanslimConfig` so
sweep scripts can tune them without editing source.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd

from strategies.canslim.config import CanslimConfig


def _roc(prices: pd.Series, lookback: int) -> float:
    if len(prices) <= lookback:
        return float("nan")
    past = float(prices.iloc[-lookback - 1])
    now = float(prices.iloc[-1])
    if past <= 0:
        return float("nan")
    return (now / past) - 1.0


def _raw_rs(prices: pd.Series, config: CanslimConfig) -> float:
    if len(prices) < config.min_history_days:
        return float("nan")
    total = 0.0
    for w, lb in zip(config.rs_weights, config.rs_roc_days):
        r = _roc(prices, lb)
        if np.isnan(r):
            return float("nan")
        total += w * r
    return total


def compute_rs_ratings(
    panel: pd.DataFrame,
    as_of_date: date,
    universe: Iterable[str],
    config: CanslimConfig,
) -> pd.Series:
    """Compute RS ratings percentile-ranked within ``universe``.

    Args:
        panel: Long-format DataFrame with columns
            ``['stockcode', 'tradingdate', 'closeindex']``.
        as_of_date: Cutoff date — only bars ``<= as_of_date`` are used.
        universe: Tickers to score (others in the panel are ignored).
        config: :class:`CanslimConfig` — supplies ``rs_roc_days``,
            ``rs_weights``, and ``min_history_days``.

    Returns:
        ``pd.Series`` indexed by ticker in ``[0, 100]`` (NaN for insufficient
        history). Series name is ``'rs_rating'``.
    """
    uset = {u.upper() for u in universe}
    df = panel[
        (panel["tradingdate"] <= as_of_date)
        & (panel["stockcode"].str.upper().isin(uset))
    ].copy()
    df["stockcode"] = df["stockcode"].str.upper()
    df = df.sort_values(["stockcode", "tradingdate"])

    raws: dict[str, float] = {}
    for t, g in df.groupby("stockcode"):
        raws[t] = _raw_rs(g["closeindex"].reset_index(drop=True), config)

    # Ensure every requested ticker shows up even with no data.
    for t in uset:
        raws.setdefault(t, float("nan"))

    raw = pd.Series(raws, name="rs_raw").sort_index()
    ranked = raw.rank(pct=True, na_option="keep") * 100.0
    return ranked.rename("rs_rating")


# --- Legacy stub signatures (kept for plan-01 compatibility) ---------------


def check_l_rs_rank(ticker: str, as_of_date, config) -> bool:
    """Legacy stub — use ``compute_rs_ratings`` + threshold compare."""
    raise NotImplementedError("Use compute_rs_ratings(panel, date, universe, config)")


def check_l_industry_leader(ticker: str, as_of_date, config) -> bool:
    """Industry-group leadership — handled in a later plan."""
    raise NotImplementedError("Industry-leader check implemented in a later plan")
