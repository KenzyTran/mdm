"""Unit tests for MomentumScorer (36-01, MSCO-01/MSCO-02/MSCO-04).

Tests cover:
- RS threshold filtering (MSCO-01)
- N rule filtering (MSCO-02)
- Combined filter logic
- NaN propagation
- Empty DataFrame handling
- Output schema compliance with REQUIRED_SCORER_COLS
- Custom threshold configuration
- Config validation
- No MySQL/fundamentals dependency (MSCO-04)
"""
from __future__ import annotations

import math
import pathlib

import numpy as np
import pandas as pd
import pytest

from strategies.momentum.scorer import apply_momentum_thresholds
from strategies.momentum.scorer_config import MomentumScorerConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw(rs_ratings: list[float], n_proxs: list[float]) -> pd.DataFrame:
    """Build a minimal raw DataFrame with [date, ticker, rs_rating, n_prox]."""
    n = len(rs_ratings)
    assert len(n_proxs) == n
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "ticker": [f"TICK{i:02d}" for i in range(n)],
            "rs_rating": rs_ratings,
            "n_prox": n_proxs,
        }
    )


# ---------------------------------------------------------------------------
# RS threshold tests (MSCO-01)
# ---------------------------------------------------------------------------

def test_rs_threshold_filter():
    """RS >= 70 passes, RS < 70 fails (default rs_threshold=70)."""
    raw = _make_raw(
        rs_ratings=[80.0, 60.0, 70.0, 50.0],
        n_proxs=[0.05, 0.05, 0.05, 0.05],
    )
    cfg = MomentumScorerConfig()
    result = apply_momentum_thresholds(raw, cfg)

    scores = result["canslim_score"].tolist()
    assert scores[0] == 100.0,  "rs=80 should pass"
    assert math.isnan(scores[1]), "rs=60 should fail (< 70)"
    assert scores[2] == 100.0,  "rs=70 should pass (== threshold)"
    assert math.isnan(scores[3]), "rs=50 should fail"


# ---------------------------------------------------------------------------
# N rule tests (MSCO-02)
# ---------------------------------------------------------------------------

def test_n_rule_filter():
    """n_prox <= 0.15 passes, > 0.15 fails (default n_within_high=0.15)."""
    raw = _make_raw(
        rs_ratings=[80.0, 80.0, 80.0],
        n_proxs=[0.10, 0.20, 0.15],
    )
    cfg = MomentumScorerConfig()
    result = apply_momentum_thresholds(raw, cfg)

    scores = result["canslim_score"].tolist()
    assert scores[0] == 100.0,  "n_prox=0.10 should pass (<= 0.15)"
    assert math.isnan(scores[1]), "n_prox=0.20 should fail (> 0.15)"
    assert scores[2] == 100.0,  "n_prox=0.15 should pass (== threshold)"


# ---------------------------------------------------------------------------
# Combined filter tests
# ---------------------------------------------------------------------------

def test_combined_filter():
    """Both conditions must pass for score=100; either failing => NaN."""
    raw = _make_raw(
        rs_ratings=[60.0, 80.0, 80.0, 60.0],
        n_proxs=[0.20, 0.05, 0.20, 0.05],
    )
    result = apply_momentum_thresholds(raw)  # default config

    scores = result["canslim_score"].tolist()
    assert math.isnan(scores[0]), "rs fail + n fail => NaN"
    assert scores[1] == 100.0,   "rs pass + n pass => 100"
    assert math.isnan(scores[2]), "rs pass + n fail => NaN"
    assert math.isnan(scores[3]), "rs fail + n pass => NaN"


# ---------------------------------------------------------------------------
# NaN propagation
# ---------------------------------------------------------------------------

def test_nan_input_propagates_rs():
    """NaN rs_rating => score NaN (missing data dropped)."""
    raw = _make_raw(rs_ratings=[float("nan")], n_proxs=[0.05])
    result = apply_momentum_thresholds(raw)
    assert math.isnan(result["canslim_score"].iloc[0])


def test_nan_input_propagates_n_prox():
    """NaN n_prox => score NaN (missing data dropped)."""
    raw = _make_raw(rs_ratings=[80.0], n_proxs=[float("nan")])
    result = apply_momentum_thresholds(raw)
    assert math.isnan(result["canslim_score"].iloc[0])


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_empty_input():
    """Empty DataFrame => empty DataFrame with correct columns."""
    raw = pd.DataFrame(columns=["date", "ticker", "rs_rating", "n_prox"])
    result = apply_momentum_thresholds(raw)

    assert result.empty
    assert set(result.columns) == {"date", "ticker", "canslim_score"}


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

def test_output_schema():
    """Output always has exactly columns [date, ticker, canslim_score]."""
    raw = _make_raw(rs_ratings=[80.0, 60.0], n_proxs=[0.05, 0.10])
    result = apply_momentum_thresholds(raw)

    assert set(result.columns) == {"date", "ticker", "canslim_score"}
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------

def test_custom_thresholds():
    """Custom MomentumScorerConfig(rs_threshold=80, n_within_high=0.10) changes behavior."""
    raw = _make_raw(
        rs_ratings=[75.0, 85.0, 75.0, 85.0],
        n_proxs=[0.08, 0.08, 0.12, 0.12],
    )
    cfg = MomentumScorerConfig(rs_threshold=80.0, n_within_high=0.10)
    result = apply_momentum_thresholds(raw, cfg)

    scores = result["canslim_score"].tolist()
    assert math.isnan(scores[0]), "rs=75 fails rs_threshold=80"
    assert scores[1] == 100.0,   "rs=85, n=0.08 passes both"
    assert math.isnan(scores[2]), "rs=75 fails rs_threshold=80"
    assert math.isnan(scores[3]), "n=0.12 fails n_within_high=0.10"


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def test_config_validation_rs_threshold_negative():
    """rs_threshold=-1 raises ValueError."""
    with pytest.raises(ValueError, match="rs_threshold"):
        MomentumScorerConfig(rs_threshold=-1.0)


def test_config_validation_rs_threshold_over_100():
    """rs_threshold=101 raises ValueError."""
    with pytest.raises(ValueError, match="rs_threshold"):
        MomentumScorerConfig(rs_threshold=101.0)


def test_config_validation_n_within_high_zero():
    """n_within_high=0 raises ValueError."""
    with pytest.raises(ValueError, match="n_within_high"):
        MomentumScorerConfig(n_within_high=0.0)


def test_config_validation_n_within_high_over_one():
    """n_within_high=1.5 raises ValueError."""
    with pytest.raises(ValueError, match="n_within_high"):
        MomentumScorerConfig(n_within_high=1.5)


# ---------------------------------------------------------------------------
# No MySQL / fundamentals dependency (MSCO-04)
# ---------------------------------------------------------------------------

def test_no_mysql_dependency():
    """scorer.py and scorer_config.py must not import mysql or fundamentals."""
    base = pathlib.Path(__file__).parents[3]  # project root
    scorer_py = base / "strategies" / "momentum" / "scorer.py"
    scorer_config_py = base / "strategies" / "momentum" / "scorer_config.py"

    for path in (scorer_py, scorer_config_py):
        content = path.read_text(encoding="utf-8").lower()
        assert "mysql" not in content, f"Found 'mysql' in {path.name}"
        assert "fundamentals" not in content, f"Found 'fundamentals' in {path.name}"
