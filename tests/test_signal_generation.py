"""
Integration tests for NASDAQ MDM signal extraction and comparison.

These tests load real NASDAQ CSV data, run the MDM classic engine,
extract model signals, and compare against published signal history.
They validate the full pipeline from data loading to comparison metrics.
"""

import pytest
import pandas as pd
from pathlib import Path

from core.data_loader import DataLoader
from core.signal_loader import load_signal_fixture
from core.signal_comparator import extract_model_signals, compare_signals
from strategies.mdm_classic import MDMEngine


# Path to project root (for data files).
# In a git worktree, data CSVs (gitignored) live in the main repo only.
# Detect main repo via git common dir for reliable data access.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MAIN_REPO = PROJECT_ROOT
if not (_MAIN_REPO / "data" / "NASDAQ.csv").exists():
    import subprocess
    _git_common = subprocess.check_output(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=str(PROJECT_ROOT), text=True
    ).strip()
    _MAIN_REPO = Path(_git_common).resolve().parent


@pytest.fixture(scope="module")
def nasdaq_df():
    """Load NASDAQ data starting from 2017-01-01."""
    loader = DataLoader("nasdaq", data_dir=str(_MAIN_REPO))
    return loader.load(start_date="2017-01-01")


@pytest.fixture(scope="module")
def engine_results(nasdaq_df):
    """Run MDM engine on NASDAQ data and return results DataFrame."""
    engine = MDMEngine()
    results = engine.run(nasdaq_df)
    return results


@pytest.fixture(scope="module")
def model_signals(engine_results):
    """Extract model signals from engine results."""
    return extract_model_signals(engine_results)


@pytest.fixture(scope="module")
def published_signals():
    """Load published NASDAQ signals."""
    return load_signal_fixture(str(_MAIN_REPO / "data" / "signals" / "nasdaq_signals.csv"))


class TestEngineRunsOnNasdaq:

    def test_engine_runs_on_nasdaq(self, engine_results):
        """MDMEngine().run() completes without error on NASDAQ data."""
        assert isinstance(engine_results, pd.DataFrame)
        assert len(engine_results) > 0

    def test_state_column_exists(self, engine_results):
        """Engine results have 'state' column."""
        assert "state" in engine_results.columns

    def test_state_values_valid(self, engine_results):
        """All state values are valid MarketState values."""
        valid_states = {"CASH", "HOLDING", "WAITING_SELL", "SHORT"}
        actual_states = set(engine_results["state"].unique())
        assert actual_states.issubset(valid_states), (
            f"Invalid states found: {actual_states - valid_states}"
        )


class TestSignalExtraction:

    def test_signal_extraction(self, model_signals):
        """extract_model_signals produces DataFrame with correct columns and >= 5 signals."""
        assert list(model_signals.columns) == ["date", "signal"]
        assert len(model_signals) >= 5, (
            f"Expected at least 5 signal transitions, got {len(model_signals)}"
        )

    def test_signal_types_valid(self, model_signals):
        """All extracted signal values are in {Buy, Sell, Cash}."""
        valid = {"Buy", "Sell", "Cash"}
        actual = set(model_signals["signal"].unique())
        assert actual.issubset(valid), (
            f"Invalid signal types: {actual - valid}"
        )

    def test_model_signals_cover_published_period(self, model_signals, published_signals):
        """Model signals span into the published signal date range (2019+)."""
        model_max = model_signals["date"].max()
        published_min = published_signals["date"].min()
        assert model_max >= published_min, (
            f"Model signals end at {model_max}, but published signals start at {published_min}"
        )


class TestComparisonProducesMetrics:

    def test_comparison_produces_metrics(self, model_signals, published_signals):
        """compare_signals returns valid metrics dict."""
        result = compare_signals(model_signals, published_signals)

        # Required keys
        assert "match_rate" in result
        assert "total_published" in result
        assert "total_matched" in result
        assert "per_type" in result

        # Type checks
        assert isinstance(result["match_rate"], float)
        assert 0.0 <= result["match_rate"] <= 100.0

        # total_published should match published signal count
        assert result["total_published"] == len(published_signals)

        # Per-type should have Buy, Sell, Cash
        for sig_type in ["Buy", "Sell", "Cash"]:
            assert sig_type in result["per_type"], (
                f"Missing '{sig_type}' in per_type breakdown"
            )
