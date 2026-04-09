"""Tests for CanslimScorer orchestrator — CANS-11 composite."""
import pytest

from strategies.canslim.scorer import CanslimScorer
from strategies.canslim.config import CanslimConfig


def test_scorer_imports_and_instantiates():
    """Smoke: scorer can be constructed."""
    s = CanslimScorer(config=CanslimConfig())
    assert s.config.c_threshold == 0.20


@pytest.mark.skip(reason="implemented in plan 29-08")
def test_scorer_score_returns_dataframe_with_expected_schema():
    """CANS-11: composite score output schema per D-09."""
    pass
