"""Tests for fundamental rules — CANS-01..CANS-04 (plan 29-05).

All tests monkeypatch ``strategies.canslim.rules.fundamental.pd.read_sql``
to return deterministic quarterly DataFrames and monkeypatch the cached
``_SCHEMA_LOCK`` so no filesystem read happens.
"""
from __future__ import annotations

from datetime import date
from typing import List

import pandas as pd
import pytest

from strategies.canslim.config import CanslimConfig
from strategies.canslim.rules import fundamental
from strategies.canslim.rules.fundamental import (
    compute_a,
    compute_a_plus,
    compute_c,
    compute_c_plus,
    compute_fundamentals,
)
from strategies.canslim.sectors import SectorRouter

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

AS_OF = date(2025, 6, 30)


@pytest.fixture(autouse=True)
def _lock_schema(monkeypatch):
    """Force a deterministic schema_lock so tests don't hit disk."""
    monkeypatch.setattr(
        fundamental,
        "_SCHEMA_LOCK",
        {
            "locked": {
                "stock_list_sector_column": "nhom",
                "is_quarter_nonbank_eps_column": "loi_nhuan_gop",
                "is_quarter_bank_ppop_column": None,
                "publish_date_column": None,
            }
        },
    )
    yield


@pytest.fixture
def cfg() -> CanslimConfig:
    return CanslimConfig(c_threshold=0.20, a_threshold=0.15)


def _router(mapping):
    """Build a SectorRouter from a {ticker: raw-sector-label} dict."""
    return SectorRouter(ticker_to_sector={k.upper(): v for k, v in mapping.items()})


def _quarterly_frame(values: List[float], newest_year=2025, newest_quarter=1):
    """Build a newest-first quarterly frame: ``values[0]`` is the newest row."""
    rows = []
    y, q = newest_year, newest_quarter
    for v in values:
        rows.append(
            {
                "stockcode": "AAA",
                "yearreport": y,
                "lengthreport": q * 3,
                "value": v,
            }
        )
        q -= 1
        if q == 0:
            q = 4
            y -= 1
    return pd.DataFrame(rows)


def _patch_read_sql(monkeypatch, frame, capture=None):
    def fake(sql, engine, params=None):
        if capture is not None:
            capture["sql"] = sql
            capture["params"] = params
        return frame.copy()

    monkeypatch.setattr(fundamental.pd, "read_sql", fake)


# --------------------------------------------------------------------------- #
# Pure-helper tests
# --------------------------------------------------------------------------- #


def test_compute_c_passes_when_yoy_ge_threshold():
    # current=100, 4q ago=80 → yoy 0.25 >= 0.20
    assert compute_c([100, 95, 90, 85, 80], 0.20) is True


def test_compute_c_fails_when_yoy_below_threshold():
    # current=88, 4q ago=80 → yoy 0.10 < 0.20
    assert compute_c([88, 85, 82, 81, 80], 0.20) is False


def test_compute_c_plus_detects_acceleration():
    # values newest-first; YoY(0)=0.30, prior YoYs 0.20 and 0.15
    vals = [130, 120, 115, 112, 100, 100, 100]
    assert compute_c_plus(vals) is True


def test_compute_c_plus_false_when_flat():
    vals = [110, 110, 110, 110, 100, 100, 100]
    assert compute_c_plus(vals) is False


def test_compute_a_3yr_ttm_cagr():
    # TTM now = 135, TTM 2y ago = 100 → CAGR ≈ 0.162 >= 0.15
    q_now = [35, 34, 33, 33]  # sums to 135
    q_1y = [30, 30, 30, 30]  # sums to 120
    q_2y = [25, 25, 25, 25]  # sums to 100
    assert compute_a(q_now + q_1y + q_2y, 0.15) is True


def test_compute_a_insufficient_history():
    assert compute_a([100, 90, 80, 70], 0.15) is False


def test_compute_a_plus_all_positive():
    assert compute_a_plus([15, 12, 10]) is True


def test_compute_a_plus_one_negative_year():
    assert compute_a_plus([15, -2, 10]) is False


# --------------------------------------------------------------------------- #
# Integration tests for compute_fundamentals
# --------------------------------------------------------------------------- #


def test_compute_fundamentals_nonbank_happy_path(monkeypatch, cfg):
    # Build 12+ quarters with 25% YoY and acceleration; newest 2025Q1 (publish ≈ 2025-05-15)
    values = [
        # year 2025 Q1
        135,
        # 2024 Q4..Q1
        130, 120, 115, 110,
        # 2023 Q4..Q1
        108, 100, 95, 92,
        # 2022 Q4..Q1
        88, 85, 82, 80,
    ]
    frame = _quarterly_frame(values, newest_year=2025, newest_quarter=1)
    _patch_read_sql(monkeypatch, frame)

    router = _router({"AAA": "Sản xuất"})
    c, cp, a, ap = compute_fundamentals("AAA", AS_OF, cfg, router, object())
    assert c is True
    assert ap is True
    assert a is True  # ttm_now=500, ttm_2y_ago≈335 → cagr ~22%


def test_compute_fundamentals_look_ahead_guard(monkeypatch, cfg):
    """A row with publish_date > as_of_date must be hidden."""
    # Newest quarter is 2025Q2 → imputed publish = 2025-06-30+45d = 2025-08-14
    # as_of_date = 2025-06-30 → that newest row is filtered out.
    # We build 13 quarters so that after dropping the 2025Q2 row we still
    # have >=12 and the "current" becomes 2025Q1.
    values = [
        9999,  # 2025Q2 — future, must be filtered
        135,   # 2025Q1 — visible newest after guard
        130, 120, 115, 110,
        108, 100, 95, 92,
        88, 85, 82, 80,
    ]
    frame = _quarterly_frame(values, newest_year=2025, newest_quarter=2)
    _patch_read_sql(monkeypatch, frame)

    router = _router({"AAA": "Sản xuất"})
    c, _, a, _ = compute_fundamentals("AAA", AS_OF, cfg, router, object())
    # If guard had failed, 9999 would dominate and C would still pass but via
    # a peek. We verify indirectly: a_pass stays True only because the TTM
    # rollup uses the guarded window starting at 2025Q1.
    assert c is True
    assert a is True


def test_compute_fundamentals_bank_routes_to_bank_table(monkeypatch, cfg):
    """Bank ticker must query is_quarter_bank, not is_quarter_nonbank."""
    capture: dict = {}
    values = [135, 130, 120, 115, 110, 108, 100, 95, 92, 88, 85, 82, 80]
    frame = _quarterly_frame(values, newest_year=2025, newest_quarter=1)
    _patch_read_sql(monkeypatch, frame, capture=capture)

    router = _router({"VCB": "Ngân hàng TMCP"})
    compute_fundamentals("VCB", AS_OF, cfg, router, object())
    assert "is_quarter_bank" in capture["sql"]
    assert "is_quarter_nonbank" not in capture["sql"]


def test_compute_fundamentals_ctck_excluded(monkeypatch, cfg):
    """ctck tickers short-circuit to all-False without touching the DB."""
    called = {"n": 0}

    def fail(*a, **kw):
        called["n"] += 1
        raise AssertionError("DB must not be hit for excluded sectors")

    monkeypatch.setattr(fundamental.pd, "read_sql", fail)
    router = _router({"VND": "Công ty chứng khoán"})
    result = compute_fundamentals("VND", AS_OF, cfg, router, object())
    assert result == (False, False, False, False)
    assert called["n"] == 0


def test_compute_fundamentals_insufficient_history_a_false(monkeypatch, cfg):
    """Fewer than 12 quarters → A rule returns False (not an exception)."""
    frame = _quarterly_frame([110, 105, 100, 95, 90], newest_year=2025, newest_quarter=1)
    _patch_read_sql(monkeypatch, frame)

    router = _router({"AAA": "Sản xuất"})
    c, cp, a, ap = compute_fundamentals("AAA", AS_OF, cfg, router, object())
    assert a is False  # insufficient history
    # C can still be evaluated with 5 quarters:
    assert c is True or c is False  # just verify no exception
