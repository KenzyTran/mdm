"""MomentumScorer — v8.0 stock filter replacing CANSLIM C/A fundamental rules.

Produces scorer_frame compatible with PortfolioEngine (REQUIRED_SCORER_COLS).
Filter logic: RS >= rs_threshold AND n_prox <= n_within_high.
Pure price-based computation — no DB connectors required.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from strategies.momentum.scorer_config import MomentumScorerConfig


def apply_momentum_thresholds(
    raw: pd.DataFrame,
    config: Optional[MomentumScorerConfig] = None,
) -> pd.DataFrame:
    """v8.0 scorer: RS >= threshold AND within N% of 52-week high.

    Produces scorer_frame compatible with PortfolioEngine (columns:
    date, ticker, canslim_score). NaN = candidate dropped.

    Column name kept as 'canslim_score' for PortfolioEngine wire compat
    (REQUIRED_SCORER_COLS in portfolio/engine.py line 47).

    Args:
        raw: DataFrame with columns [date, ticker, rs_rating, n_prox].
            rs_rating: cross-sectional RS percentile rank (0-100).
            n_prox: proximity to 52-week high as fraction
                    (high_52w - close) / high_52w, so 0 = at high, 0.15 = 15% below.
        config: MomentumScorerConfig with threshold parameters.
            Defaults to MomentumScorerConfig() if None.

    Returns:
        DataFrame with columns [date, ticker, canslim_score].
        canslim_score = 100.0 iff RS >= rs_threshold AND n_prox <= n_within_high.
        canslim_score = NaN for any row that fails either filter or has missing input.
    """
    if config is None:
        config = MomentumScorerConfig()

    if raw.empty:
        return pd.DataFrame(columns=["date", "ticker", "canslim_score"])

    rs_pass = raw["rs_rating"] >= config.rs_threshold
    n_pass = raw["n_prox"] <= config.n_within_high

    # NaN comparisons return False — so any NaN in input fails the filter
    all_pass = rs_pass & n_pass

    return pd.DataFrame(
        {
            "date": raw["date"].values,
            "ticker": raw["ticker"].values,
            "canslim_score": np.where(all_pass, 100.0, np.nan),
        }
    )
