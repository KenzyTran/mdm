"""Tests for technical rule (N) — CANS-05, CANS-06."""
import pytest

from strategies.canslim.rules import technical  # noqa: F401


def test_technical_module_imports():
    """Smoke."""
    assert hasattr(technical, "check_n_new_high")


@pytest.mark.skip(reason="implemented in plan 29-06")
def test_cans05_n_new_high():
    """CANS-05."""
    pass


@pytest.mark.skip(reason="implemented in plan 29-06")
def test_cans06_n_pivot_breakout():
    """CANS-06."""
    pass
