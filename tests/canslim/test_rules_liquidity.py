"""Tests for liquidity gate — CANS-11."""
import pytest

from strategies.canslim.rules import liquidity  # noqa: F401


def test_liquidity_module_imports():
    """Smoke."""
    assert hasattr(liquidity, "check_liquidity_turnover")


@pytest.mark.skip(reason="implemented in plan 29-07")
def test_cans11_liquidity_turnover():
    """CANS-11."""
    pass
