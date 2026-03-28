"""
Unit tests for core/signal_comparator.py

Tests signal extraction, alignment, comparison, and divergence classification
using synthetic DataFrames.
"""

import pandas as pd
import numpy as np
import pytest

from core.signal_comparator import (
    STATE_TO_SIGNAL,
    extract_model_signals,
    align_signals,
    compare_signals,
    classify_divergences,
    generate_divergence_context,
)
from strategies.mdm_classic.config import MDMConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_results_df(states, start="2020-01-01"):
    """Create a minimal engine results DataFrame with a state column."""
    dates = pd.date_range(start, periods=len(states), freq="B")
    return pd.DataFrame({
        "date": dates,
        "close": [100.0] * len(states),
        "state": states,
        "dd_count": [0] * len(states),
        "drawdown_pct": [0.0] * len(states),
        "price_change_pct": [0.0] * len(states),
    })


def _make_signals_df(rows):
    """Create a signal DataFrame from list of (date_str, signal)."""
    return pd.DataFrame(rows, columns=["date", "signal"]).assign(
        date=lambda d: pd.to_datetime(d["date"])
    )


# ---------------------------------------------------------------------------
# extract_model_signals
# ---------------------------------------------------------------------------

class TestExtractModelSignals:

    def test_extract_transitions(self):
        """Alternating states produce all transition points."""
        states = ["CASH", "HOLDING", "HOLDING", "CASH", "SHORT"]
        df = _make_results_df(states)
        signals = extract_model_signals(df)
        assert list(signals.columns) == ["date", "signal"]
        # Transitions: CASH(initial), CASH->HOLDING=Buy, HOLDING->CASH=Cash, CASH->SHORT=Sell
        # First row is initial state: Cash
        assert len(signals) == 4
        assert list(signals["signal"]) == ["Cash", "Buy", "Cash", "Sell"]

    def test_extract_constant_state(self):
        """Constant state returns single row (initial state only)."""
        states = ["HOLDING", "HOLDING", "HOLDING"]
        df = _make_results_df(states)
        signals = extract_model_signals(df)
        assert len(signals) == 1
        assert signals.iloc[0]["signal"] == "Buy"

    def test_extract_waiting_sell_maps_to_cash(self):
        """WAITING_SELL maps to Cash per D-01."""
        states = ["HOLDING", "WAITING_SELL", "WAITING_SELL", "SHORT"]
        df = _make_results_df(states)
        signals = extract_model_signals(df)
        # HOLDING(initial=Buy), HOLDING->WAITING_SELL=Cash, WAITING_SELL->SHORT=Sell
        assert len(signals) == 3
        assert list(signals["signal"]) == ["Buy", "Cash", "Sell"]

    def test_extract_all_signal_types_valid(self):
        """All extracted signals are in {Buy, Sell, Cash}."""
        states = ["CASH", "HOLDING", "WAITING_SELL", "SHORT", "CASH"]
        df = _make_results_df(states)
        signals = extract_model_signals(df)
        assert set(signals["signal"].unique()).issubset({"Buy", "Sell", "Cash"})


# ---------------------------------------------------------------------------
# align_signals
# ---------------------------------------------------------------------------

class TestAlignSignals:

    def test_align_identical_dates(self):
        """Identical dates produce fully populated rows."""
        model = _make_signals_df([("2020-01-01", "Buy"), ("2020-02-01", "Sell")])
        published = _make_signals_df([("2020-01-01", "Buy"), ("2020-02-01", "Sell")])
        aligned = align_signals(model, published)
        assert list(aligned.columns) == ["date", "published", "model"]
        assert aligned["published"].notna().all()
        assert aligned["model"].notna().all()
        assert len(aligned) == 2

    def test_align_no_overlap(self):
        """No overlapping dates produce all NaN in opposite column."""
        model = _make_signals_df([("2020-01-01", "Buy")])
        published = _make_signals_df([("2020-06-01", "Sell")])
        aligned = align_signals(model, published)
        assert len(aligned) == 2
        # First row: model present, published NaN
        row0 = aligned.iloc[0]
        assert pd.notna(row0["model"])
        assert pd.isna(row0["published"])
        # Second row: published present, model NaN
        row1 = aligned.iloc[1]
        assert pd.notna(row1["published"])
        assert pd.isna(row1["model"])

    def test_align_sorted_by_date(self):
        """Result is sorted by date."""
        model = _make_signals_df([("2020-03-01", "Sell")])
        published = _make_signals_df([("2020-01-01", "Buy")])
        aligned = align_signals(model, published)
        assert aligned["date"].is_monotonic_increasing


# ---------------------------------------------------------------------------
# compare_signals
# ---------------------------------------------------------------------------

class TestCompareSignals:

    def test_compare_perfect_match(self):
        """Perfect match returns match_rate=100.0."""
        model = _make_signals_df([("2020-01-01", "Buy"), ("2020-02-01", "Sell")])
        published = _make_signals_df([("2020-01-01", "Buy"), ("2020-02-01", "Sell")])
        result = compare_signals(model, published)
        assert result["match_rate"] == 100.0
        assert result["total_published"] == 2
        assert result["total_matched"] == 2

    def test_compare_zero_overlap(self):
        """Zero overlap returns match_rate=0.0."""
        model = _make_signals_df([("2020-01-01", "Buy")])
        published = _make_signals_df([("2020-06-01", "Sell")])
        result = compare_signals(model, published)
        assert result["match_rate"] == 0.0
        assert result["total_matched"] == 0
        assert result["total_published"] == 1

    def test_compare_per_type_breakdown(self):
        """Per-type breakdown has entries for Buy, Sell, Cash per D-03."""
        model = _make_signals_df([
            ("2020-01-01", "Buy"),
            ("2020-02-01", "Sell"),
            ("2020-03-01", "Cash"),
        ])
        published = _make_signals_df([
            ("2020-01-01", "Buy"),
            ("2020-02-01", "Sell"),
            ("2020-03-01", "Cash"),
        ])
        result = compare_signals(model, published)
        assert "per_type" in result
        for sig_type in ["Buy", "Sell", "Cash"]:
            assert sig_type in result["per_type"]
            assert result["per_type"][sig_type]["rate"] == 100.0

    def test_compare_exact_date_only(self):
        """Model signal one day off does NOT match (per D-02)."""
        model = _make_signals_df([("2020-01-02", "Buy")])  # one day late
        published = _make_signals_df([("2020-01-01", "Buy")])
        result = compare_signals(model, published)
        assert result["match_rate"] == 0.0

    def test_compare_signal_type_must_match(self):
        """Same date but different signal type does NOT match."""
        model = _make_signals_df([("2020-01-01", "Sell")])
        published = _make_signals_df([("2020-01-01", "Buy")])
        result = compare_signals(model, published)
        assert result["match_rate"] == 0.0


# ---------------------------------------------------------------------------
# classify_divergences
# ---------------------------------------------------------------------------

class TestClassifyDivergences:

    def _make_aligned(self, rows):
        """rows: list of (date_str, published, model)"""
        data = []
        for date_str, pub, mod in rows:
            data.append({
                "date": pd.Timestamp(date_str),
                "published": pub,
                "model": mod,
            })
        return pd.DataFrame(data)

    def test_classify_timing_same_type_nearby(self):
        """TIMING: same signal type within +/-5 days -> TIMING per D-06."""
        aligned = self._make_aligned([
            ("2020-01-10", "Buy", "Cash"),  # divergence
        ])
        # Model has a Buy signal 2 days later
        model_signals = _make_signals_df([("2020-01-12", "Buy")])
        engine_results = _make_results_df(["CASH"] * 20)
        config = MDMConfig()

        result = classify_divergences(aligned, model_signals, engine_results, config)
        assert result.loc[0, "divergence_type"] == "TIMING"

    def test_classify_structural_no_cash_nearby(self):
        """STRUCTURAL: published Cash and no model Cash within +/-5 days -> STRUCTURAL."""
        aligned = self._make_aligned([
            ("2020-01-10", "Cash", "Buy"),  # divergence: published Cash, model Buy
        ])
        # Model has NO Cash signal anywhere nearby
        model_signals = _make_signals_df([("2020-01-10", "Buy"), ("2020-02-01", "Cash")])
        engine_results = _make_results_df(["HOLDING"] * 30)
        config = MDMConfig()

        result = classify_divergences(aligned, model_signals, engine_results, config)
        assert result.loc[0, "divergence_type"] == "STRUCTURAL"

    def test_classify_timing_before_structural(self):
        """TIMING checked before STRUCTURAL: Cash divergence with nearby Cash -> TIMING, not STRUCTURAL."""
        aligned = self._make_aligned([
            ("2020-01-10", "Cash", "Buy"),  # divergence: published Cash, model Buy
        ])
        # Model HAS a Cash signal 3 days later -> TIMING, not STRUCTURAL
        model_signals = _make_signals_df([("2020-01-10", "Buy"), ("2020-01-13", "Cash")])
        engine_results = _make_results_df(["HOLDING"] * 20)
        config = MDMConfig()

        result = classify_divergences(aligned, model_signals, engine_results, config)
        assert result.loc[0, "divergence_type"] == "TIMING"

    def test_classify_threshold(self):
        """THRESHOLD: dd_count within 1 of dd_window_size -> THRESHOLD."""
        aligned = self._make_aligned([
            ("2020-01-10", "Sell", "Buy"),  # divergence
        ])
        # No same-type signal nearby for TIMING
        model_signals = _make_signals_df([("2020-02-01", "Sell")])

        # Engine results with dd_count = 19 (within 1 of 20)
        engine_df = _make_results_df(["HOLDING"] * 20)
        engine_df.loc[engine_df["date"] == pd.Timestamp("2020-01-10"), "dd_count"] = 19
        config = MDMConfig()  # dd_window_size=20

        result = classify_divergences(aligned, model_signals, engine_df, config)
        assert result.loc[0, "divergence_type"] == "THRESHOLD"

    def test_classify_irreproducible(self):
        """IRREPRODUCIBLE: none of the above criteria match."""
        aligned = self._make_aligned([
            ("2020-01-10", "Sell", "Buy"),  # divergence
        ])
        # No nearby same-type signal
        model_signals = _make_signals_df([("2020-03-01", "Sell")])
        # dd_count = 0 (not near threshold)
        engine_df = _make_results_df(["HOLDING"] * 30)
        config = MDMConfig()

        result = classify_divergences(aligned, model_signals, engine_df, config)
        assert result.loc[0, "divergence_type"] == "IRREPRODUCIBLE"

    def test_classify_match_rows_get_nan(self):
        """Matching rows get NaN divergence_type."""
        aligned = self._make_aligned([
            ("2020-01-10", "Buy", "Buy"),  # match
        ])
        model_signals = _make_signals_df([("2020-01-10", "Buy")])
        engine_df = _make_results_df(["HOLDING"] * 20)
        config = MDMConfig()

        result = classify_divergences(aligned, model_signals, engine_df, config)
        assert pd.isna(result.loc[0, "divergence_type"])

    def test_timing_must_match_signal_type(self):
        """TIMING requires same signal type -- Buy only matches nearby Buy, not Sell (Pitfall 5)."""
        aligned = self._make_aligned([
            ("2020-01-10", "Buy", "Sell"),  # divergence
        ])
        # Model has a Sell nearby (wrong type) but no Buy nearby
        model_signals = _make_signals_df([
            ("2020-01-10", "Sell"),
            ("2020-01-12", "Sell"),
            ("2020-03-01", "Buy"),  # too far away
        ])
        engine_df = _make_results_df(["CASH"] * 50)
        config = MDMConfig()

        result = classify_divergences(aligned, model_signals, engine_df, config)
        # Should NOT be TIMING since no nearby Buy
        assert result.loc[0, "divergence_type"] != "TIMING"


# ---------------------------------------------------------------------------
# generate_divergence_context
# ---------------------------------------------------------------------------

class TestGenerateDivergenceContext:

    def test_timing_context(self):
        """TIMING context includes 'TIMING' and mentions nearby date."""
        row = pd.Series({
            "date": pd.Timestamp("2020-01-10"),
            "published": "Buy",
            "model": "Cash",
            "divergence_type": "TIMING",
        })
        model_signals = _make_signals_df([("2020-01-12", "Buy")])
        engine_df = _make_results_df(["CASH"] * 20)
        config = MDMConfig()
        ctx = generate_divergence_context(row, model_signals, engine_df, config)
        assert "TIMING" in ctx

    def test_structural_context(self):
        """STRUCTURAL context includes 'STRUCTURAL'."""
        row = pd.Series({
            "date": pd.Timestamp("2020-01-10"),
            "published": "Cash",
            "model": "Buy",
            "divergence_type": "STRUCTURAL",
        })
        model_signals = _make_signals_df([("2020-01-10", "Buy")])
        engine_df = _make_results_df(["HOLDING"] * 20)
        config = MDMConfig()
        ctx = generate_divergence_context(row, model_signals, engine_df, config)
        assert "STRUCTURAL" in ctx
