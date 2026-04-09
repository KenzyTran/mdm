"""Tests for sector routing — CANS-10 (plan 29-04)."""
import warnings

import pandas as pd
import pytest

from strategies.canslim import sectors
from strategies.canslim.sectors import SectorRouter


def test_sectors_module_imports():
    """Smoke: sectors module is importable."""
    assert hasattr(sectors, "SectorRouter")


def test_route_bank():
    assert SectorRouter({"VCB": "Ngân hàng"}).route("VCB") == "bank"


def test_route_ctck():
    assert SectorRouter({"VND": "Chứng khoán"}).route("VND") == "ctck"


def test_route_insurance():
    assert SectorRouter({"BVH": "Bảo hiểm"}).route("BVH") == "insurance"


def test_route_other():
    assert SectorRouter({"HPG": "Thép"}).route("HPG") == "other"


def test_route_unknown_ticker_warns_and_defaults_other():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = SectorRouter({}).route("XYZ")
    assert result == "other"
    assert any("XYZ" in str(wi.message) for wi in w)


def test_is_excluded():
    router = SectorRouter(
        {"VND": "Chứng khoán", "HPG": "Thép", "VCB": "Ngân hàng", "BVH": "Bảo hiểm"}
    )
    assert router.is_excluded("VND") is True
    assert router.is_excluded("BVH") is True
    assert router.is_excluded("HPG") is False
    assert router.is_excluded("VCB") is False


class _FakeEngine:
    def __init__(self, df):
        self.df = df


def test_from_postgres_builds_map(monkeypatch):
    df = pd.DataFrame(
        {
            "stockcode": ["VCB", "HPG", "VND"],
            "sector": ["Ngân hàng", "Thép", "Chứng khoán"],
        }
    )
    monkeypatch.setattr(
        "strategies.canslim.sectors.pd.read_sql",
        lambda sql, engine: df,
    )
    router = SectorRouter.from_postgres(_FakeEngine(df), sector_column="nhom")
    assert router.route("VCB") == "bank"
    assert router.route("HPG") == "other"
    assert router.route("VND") == "ctck"


def test_from_postgres_fails_loud_when_sector_mostly_missing(monkeypatch):
    df = pd.DataFrame(
        {
            "stockcode": ["A", "B", "C", "D"],
            "sector": [None, None, None, "Thép"],
        }
    )
    monkeypatch.setattr(
        "strategies.canslim.sectors.pd.read_sql",
        lambda sql, engine: df,
    )
    with pytest.raises(RuntimeError, match="schema_lock.json is stale"):
        SectorRouter.from_postgres(_FakeEngine(df), sector_column="nhom")
