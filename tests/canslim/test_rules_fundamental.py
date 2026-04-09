"""Tests for fundamental rules — CANS-01..CANS-04."""
import pytest

from strategies.canslim.rules import fundamental  # noqa: F401


def test_fundamental_module_imports():
    """Smoke."""
    assert hasattr(fundamental, "check_c_quarterly_eps_yoy")


@pytest.mark.skip(reason="implemented in plan 29-05")
def test_cans01_c_rule_quarterly_eps_yoy():
    """CANS-01."""
    pass


@pytest.mark.skip(reason="implemented in plan 29-05")
def test_cans02_c_plus_eps_acceleration():
    """CANS-02."""
    pass


@pytest.mark.skip(reason="implemented in plan 29-05")
def test_cans03_a_annual_eps_growth():
    """CANS-03."""
    pass


@pytest.mark.skip(reason="implemented in plan 29-05")
def test_cans04_a_plus_roe():
    """CANS-04."""
    pass
