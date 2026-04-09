"""Tests for RS rule (L) — CANS-07, CANS-08."""
import pytest

from strategies.canslim.rules import rs  # noqa: F401


def test_rs_module_imports():
    """Smoke."""
    assert hasattr(rs, "check_l_rs_rank")


@pytest.mark.skip(reason="implemented in plan 29-06")
def test_cans07_l_rs_rank():
    """CANS-07."""
    pass


@pytest.mark.skip(reason="implemented in plan 29-06")
def test_cans08_l_industry_leader():
    """CANS-08."""
    pass
