"""
Signal Comparator Module

Compares model-generated signals against published signal history.
Provides extraction, alignment, comparison, and divergence classification
for MDM signal analysis.

Key functions:
    - extract_model_signals: Convert engine state column to Buy/Sell/Cash transitions
    - align_signals: Outer-merge model and published signals on date
    - compare_signals: Compute match rate and per-type breakdown
    - classify_divergences: Assign TIMING/STRUCTURAL/THRESHOLD/IRREPRODUCIBLE
    - generate_divergence_context: Produce human-readable context strings
"""

import pandas as pd
import numpy as np
from typing import Optional

from strategies.mdm_classic.config import MDMConfig


# State-to-signal mapping per D-01
STATE_TO_SIGNAL = {
    "HOLDING": "Buy",
    "SHORT": "Sell",
    "CASH": "Cash",
    "WAITING_SELL": "Cash",
}

# Window size for TIMING divergence detection (trading days)
TIMING_WINDOW = 5


def extract_model_signals(results_df: pd.DataFrame) -> pd.DataFrame:
    """Extract Buy/Sell/Cash signal transitions from engine results.

    Maps the 'state' column via STATE_TO_SIGNAL, then detects rows where
    the mapped signal differs from the previous row's mapped signal.
    The first row is always included as the initial state.

    Args:
        results_df: Engine results DataFrame with 'date' and 'state' columns.

    Returns:
        DataFrame with columns [date, signal] containing only transition rows,
        index reset.
    """
    df = results_df[["date", "state"]].copy()
    df["signal"] = df["state"].map(STATE_TO_SIGNAL)

    # Detect transitions: signal differs from previous row
    df["prev_signal"] = df["signal"].shift(1)
    # First row is always a transition (initial state)
    transitions = df[(df["signal"] != df["prev_signal"]) | df["prev_signal"].isna()]

    return transitions[["date", "signal"]].reset_index(drop=True)


def align_signals(
    model_signals: pd.DataFrame,
    published_signals: pd.DataFrame,
) -> pd.DataFrame:
    """Outer-merge model and published signals on date.

    Args:
        model_signals: DataFrame with columns [date, signal] from model.
        published_signals: DataFrame with columns [date, signal] from published source.

    Returns:
        DataFrame with columns [date, published, model], sorted by date.
    """
    model = model_signals[["date", "signal"]].rename(columns={"signal": "model"})
    published = published_signals[["date", "signal"]].rename(columns={"signal": "published"})

    merged = pd.merge(published, model, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    return merged[["date", "published", "model"]]


def compare_signals(
    model_signals: pd.DataFrame,
    published_signals: pd.DataFrame,
) -> dict:
    """Compute match rate between model and published signals.

    A match requires the same signal type on the exact same date (per D-02).

    Args:
        model_signals: DataFrame with columns [date, signal].
        published_signals: DataFrame with columns [date, signal].

    Returns:
        dict with keys:
            - match_rate: float 0-100
            - total_published: int
            - total_matched: int
            - per_type: dict of signal_type -> {published, matched, rate}
    """
    aligned = align_signals(model_signals, published_signals)

    total_published = int(published_signals["signal"].notna().sum())
    total_matched = 0

    # Per-type tracking
    per_type = {}
    for sig_type in ["Buy", "Sell", "Cash"]:
        per_type[sig_type] = {"published": 0, "matched": 0, "rate": 0.0}

    # Count matches: published signal present AND model signal matches exactly
    for _, row in aligned.iterrows():
        pub = row["published"]
        mod = row["model"]

        if pd.isna(pub):
            continue  # No published signal on this date

        if pub in per_type:
            per_type[pub]["published"] += 1

        if pd.notna(mod) and pub == mod:
            total_matched += 1
            if pub in per_type:
                per_type[pub]["matched"] += 1

    # Compute rates
    match_rate = (total_matched / total_published * 100.0) if total_published > 0 else 0.0

    for sig_type in per_type:
        p = per_type[sig_type]["published"]
        m = per_type[sig_type]["matched"]
        per_type[sig_type]["rate"] = (m / p * 100.0) if p > 0 else 0.0

    return {
        "match_rate": match_rate,
        "total_published": total_published,
        "total_matched": total_matched,
        "per_type": per_type,
    }


def _find_nearby_same_type(
    target_date: pd.Timestamp,
    target_signal: str,
    model_signals_df: pd.DataFrame,
    window: int = TIMING_WINDOW,
) -> Optional[pd.Timestamp]:
    """Find nearest model signal of same type within +/- window trading days.

    Args:
        target_date: Date to search around.
        target_signal: Signal type to match (Buy, Sell, Cash).
        model_signals_df: Model signals DataFrame with [date, signal].
        window: Number of trading days tolerance.

    Returns:
        Date of nearest matching signal, or None if not found.
    """
    same_type = model_signals_df[model_signals_df["signal"] == target_signal].copy()
    if same_type.empty:
        return None

    same_type = same_type.copy()
    same_type["day_diff"] = (same_type["date"] - target_date).dt.days.abs()
    within_window = same_type[same_type["day_diff"] <= (window * 2)]  # calendar days ~ 2x trading days

    if within_window.empty:
        return None

    # More precise: filter by actual trading day count using business days
    # For simplicity, use calendar day threshold of window * 1.5 (accounts for weekends)
    # A 5 trading day window is roughly 7 calendar days
    calendar_threshold = window * 1.5
    within_window = same_type[same_type["day_diff"] <= calendar_threshold]

    if within_window.empty:
        return None

    nearest_idx = within_window["day_diff"].idxmin()
    return within_window.loc[nearest_idx, "date"]


def classify_divergences(
    aligned_df: pd.DataFrame,
    model_signals_df: pd.DataFrame,
    engine_results_df: pd.DataFrame,
    config: MDMConfig,
) -> pd.DataFrame:
    """Classify each divergence as TIMING, STRUCTURAL, THRESHOLD, or IRREPRODUCIBLE.

    Processing order per D-06:
    1. TIMING (checked FIRST): Same signal type within +/-5 trading days
    2. STRUCTURAL: Published Cash with no model Cash transition within +/-5 days
    3. THRESHOLD: Engine metrics near decision boundaries
    4. IRREPRODUCIBLE: None of the above

    Args:
        aligned_df: Aligned signals DataFrame with [date, published, model].
        model_signals_df: All model signal transitions with [date, signal].
        engine_results_df: Full engine results with indicator columns.
        config: MDMConfig with threshold parameters.

    Returns:
        aligned_df with added 'divergence_type' column (NaN for matches).
    """
    result = aligned_df.copy()
    result["divergence_type"] = pd.array([pd.NA] * len(result), dtype="object")

    for idx, row in result.iterrows():
        pub = row["published"]
        mod = row["model"]

        # Skip matches and rows without published signal
        if pd.isna(pub) or (pd.notna(mod) and pub == mod):
            continue

        target_date = row["date"]

        # 1. TIMING: Same signal type within +/-5 trading days
        nearby_date = _find_nearby_same_type(target_date, pub, model_signals_df)
        if nearby_date is not None:
            result.at[idx, "divergence_type"] = "TIMING"
            continue

        # 2. STRUCTURAL: Published Cash and no model Cash transition nearby
        if pub == "Cash":
            nearby_cash = _find_nearby_same_type(target_date, "Cash", model_signals_df)
            if nearby_cash is None:
                result.at[idx, "divergence_type"] = "STRUCTURAL"
                continue

        # 3. THRESHOLD: Check engine metrics near decision boundaries
        engine_row = engine_results_df[engine_results_df["date"] == target_date]
        if not engine_row.empty:
            er = engine_row.iloc[0]

            # dd_count within 1 of dd_window_size
            dd_count = er.get("dd_count", 0)
            if dd_count >= config.dd_window_size - 1:
                result.at[idx, "divergence_type"] = "THRESHOLD"
                continue

            # price_change_pct within 10% of ftd_min_price_gain
            price_change = abs(er.get("price_change_pct", 0))
            if price_change >= config.ftd_min_price_gain * 0.9:
                result.at[idx, "divergence_type"] = "THRESHOLD"
                continue

            # drawdown_pct within 10% of correction_threshold
            drawdown = er.get("drawdown_pct", 0)
            if drawdown != 0 and abs(drawdown) >= abs(config.correction_threshold) * 0.9:
                result.at[idx, "divergence_type"] = "THRESHOLD"
                continue

        # 4. IRREPRODUCIBLE
        result.at[idx, "divergence_type"] = "IRREPRODUCIBLE"

    return result


def generate_divergence_context(
    row: pd.Series,
    model_signals_df: pd.DataFrame,
    engine_results_df: pd.DataFrame,
    config: MDMConfig,
) -> str:
    """Produce a human-readable context string for a divergence.

    Args:
        row: A single row from the classified aligned DataFrame.
        model_signals_df: All model signal transitions.
        engine_results_df: Full engine results.
        config: MDMConfig with threshold parameters.

    Returns:
        Short string explaining the divergence classification.
    """
    div_type = row.get("divergence_type")
    pub = row.get("published", "?")
    mod = row.get("model", "?")
    target_date = row["date"]

    if pd.isna(div_type):
        return f"MATCH: both {pub} on {target_date.strftime('%Y-%m-%d')}"

    if div_type == "TIMING":
        nearby = _find_nearby_same_type(target_date, pub, model_signals_df)
        if nearby is not None:
            day_diff = (nearby - target_date).days
            direction = "late" if day_diff > 0 else "early"
            return (
                f"TIMING: model {pub} on {nearby.strftime('%Y-%m-%d')} "
                f"({abs(day_diff)} days {direction})"
            )
        return f"TIMING: published {pub}, model {mod}"

    if div_type == "STRUCTURAL":
        return (
            f"STRUCTURAL: published {pub}, "
            f"model has no deliberate {pub} signal within {TIMING_WINDOW} trading days"
        )

    if div_type == "THRESHOLD":
        engine_row = engine_results_df[engine_results_df["date"] == target_date]
        details = []
        if not engine_row.empty:
            er = engine_row.iloc[0]
            dd = er.get("dd_count", 0)
            if dd >= config.dd_window_size - 1:
                details.append(f"dd_count={dd} near threshold {config.dd_window_size}")
            pcp = abs(er.get("price_change_pct", 0))
            if pcp >= config.ftd_min_price_gain * 0.9:
                details.append(f"price_change={pcp:.4f} near {config.ftd_min_price_gain}")
        detail_str = "; ".join(details) if details else "near decision boundary"
        return f"THRESHOLD: published {pub} vs model {mod} ({detail_str})"

    return f"IRREPRODUCIBLE: published {pub} vs model {mod}, no pattern match"
