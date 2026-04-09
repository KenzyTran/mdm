"""Tests for UniverseLoader — UNIV-01, UNIV-02, UNIV-03."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from strategies.canslim import universe as universe_mod
from strategies.canslim.universe import UniverseLoader


def test_universe_module_imports():
    """Smoke: universe module exposes UniverseLoader."""
    assert hasattr(universe_mod, "UniverseLoader")


def _install_fake_read_sql(monkeypatch, router):
    """Patch pandas.read_sql so UniverseLoader's queries are routed via `router`.

    router(sql, params) -> DataFrame
    """
    def fake_read_sql(sql, con, params=None, **kwargs):
        return router(sql, params or {})

    monkeypatch.setattr(universe_mod.pd, "read_sql", fake_read_sql)


def _long_history(tickers, min_days=300):
    return pd.DataFrame([{"stockcode": t, "n": min_days} for t in tickers])


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        UniverseLoader(mode="bogus", pg_engine=object())


def test_last_rebalance_date_midyear():
    loader = UniverseLoader(mode="vn30-only", pg_engine=object())
    assert loader._last_rebalance_date(date(2025, 3, 15)) == date(2025, 1, 1)
    assert loader._last_rebalance_date(date(2025, 8, 2)) == date(2025, 7, 1)
    assert loader._last_rebalance_date(date(2025, 1, 1)) == date(2025, 1, 1)
    assert loader._last_rebalance_date(date(2025, 7, 1)) == date(2025, 7, 1)


def test_current_vn100_mode_returns_vn30_and_vn100(monkeypatch):
    captured = {}

    def router(sql, params):
        if "nhomtop IN" in sql:
            captured["list_sql"] = sql
            return pd.DataFrame(
                {"stockcode": ["AAA", "BBB", "CCC", "DDD"]}
            )
        # history filter
        return _long_history(["AAA", "BBB", "CCC", "DDD"])

    _install_fake_read_sql(monkeypatch, router)
    loader = UniverseLoader(mode="current-vn100", pg_engine=object())
    result = loader.get(date(2025, 6, 1))
    assert result == {"AAA", "BBB", "CCC", "DDD"}
    assert "nhomtop IN ('VN30','VN100')" in captured["list_sql"]


def test_vn30_only_mode(monkeypatch):
    def router(sql, params):
        if "nhomtop = 'VN30'" in sql:
            return pd.DataFrame({"stockcode": ["AAA", "BBB"]})
        return _long_history(["AAA", "BBB"])

    _install_fake_read_sql(monkeypatch, router)
    loader = UniverseLoader(mode="vn30-only", pg_engine=object())
    assert loader.get(date(2025, 6, 1)) == {"AAA", "BBB"}


def test_liquidity_reconstructed_uses_rebalance_date(monkeypatch):
    calls = []

    def router(sql, params):
        if "AVG(closeindex * totalvol)" in sql:
            calls.append(params)
            return pd.DataFrame(
                {"stockcode": [f"T{i:03d}" for i in range(100)]}
            )
        return _long_history([f"T{i:03d}" for i in range(100)])

    _install_fake_read_sql(monkeypatch, router)
    loader = UniverseLoader(
        mode="liquidity-reconstructed", pg_engine=object()
    )

    # Mar 15 and May 10 both fall between Jan 1 and Jul 1 → same rebalance
    res_a = loader.get(date(2025, 3, 15))
    res_b = loader.get(date(2025, 5, 10))
    assert len(res_a) == 100
    assert res_a == res_b  # no intra-period churn
    assert calls[0]["end"] == date(2025, 1, 1)
    assert calls[1]["end"] == date(2025, 1, 1)

    # Aug 2 crosses Jul 1 rebalance
    loader.get(date(2025, 8, 2))
    assert calls[-1]["end"] == date(2025, 7, 1)


def test_history_filter_drops_short_history(monkeypatch):
    def router(sql, params):
        if "nhomtop IN" in sql:
            return pd.DataFrame({"stockcode": ["AAA", "BBB", "CCC"]})
        # AAA has 300 days, BBB has only 100, CCC has exactly 252
        return pd.DataFrame(
            [
                {"stockcode": "AAA", "n": 300},
                {"stockcode": "BBB", "n": 100},
                {"stockcode": "CCC", "n": 252},
            ]
        )

    _install_fake_read_sql(monkeypatch, router)
    loader = UniverseLoader(mode="current-vn100", pg_engine=object())
    result = loader.get(date(2025, 6, 1))
    assert result == {"AAA", "CCC"}
    assert "BBB" not in result
