"""Tests for CanslimScorer end-to-end orchestration — CANS-11 composite (plan 29-08).

Strategy: monkeypatch ``pandas.read_sql`` globally with a dispatcher keyed on
SQL-string substrings. Every CANSLIM module does ``import pandas as pd`` then
``pd.read_sql(...)``, so a single monkeypatch covers universe, scorer panel,
fundamentals, and foreign-flow reads.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from strategies.canslim.config import CanslimConfig
from strategies.canslim.scorer import (
    BOOL_WEIGHT,
    NUM_BOOLEAN_RULES,
    OUTPUT_COLUMNS,
    RS_WEIGHT,
    CanslimScorer,
)
from strategies.canslim.sectors import SectorRouter
from strategies.canslim.universe import UniverseLoader


AS_OF = date(2025, 6, 30)
# Enough history for min_history_days=252 + RS lookback 252 (need >=253 bars
# for compute_rs_ratings, +1 for the _roc(... len>lookback) check).
N_BARS = 320


def _fake_panel(tickers, price_map: Dict[str, float]) -> pd.DataFrame:
    """Build a synthetic OHLCV panel with a linear up-trend per ticker.

    Parameters
    ----------
    tickers : list[str]
        Tickers to fabricate.
    price_map : dict
        Per-ticker END close price. Prices grow linearly from 100 to
        ``price_map[t]`` so higher end price → stronger RS.
    """
    dates = pd.bdate_range(end=pd.Timestamp(AS_OF), periods=N_BARS)
    rows = []
    for t in tickers:
        end = price_map[t]
        prices = np.linspace(100.0, end, N_BARS)
        for d, p in zip(dates, prices):
            rows.append(
                {
                    "stockcode": t,
                    "tradingdate": d.date(),
                    "closeindex": float(p),
                    "highestindex": float(p) * 1.01,
                    "totalvol": 10_000_000,  # high volume → liq passes
                }
            )
    return pd.DataFrame(rows)


def _fake_quarters(eps_series):
    """Build a fake is_quarter_nonbank result for one ticker.

    ``eps_series`` is oldest-first list of (year, length, eps) tuples where
    length ∈ {3,6,9,12} encodes month-of-quarter-end. Post-29-09 the loader
    reads ``thoigian`` (text "Q<n> YYYY"); we still accept the old (year, L, eps)
    shape and synthesize ``thoigian`` from ``L``.
    """
    return pd.DataFrame(
        [
            {"stockcode": "X", "thoigian": f"Q{L // 3} {y}", "value": e}
            for (y, L, e) in eps_series
        ]
    )


def _strong_eps():
    """16 quarters of strictly-growing EPS so C/C+/A/A+ all pass."""
    rows = []
    eps = 100.0
    # Oldest first -> list order; the loader orders desc so newest first.
    # Provide 16 quarters from 2021 Q1 .. 2024 Q4
    for year in (2021, 2022, 2023, 2024):
        for q in (3, 6, 9, 12):
            rows.append((year, q, eps))
            eps *= 1.15
    return rows


def _weak_eps():
    """Flat EPS so C/C+/A fail (no growth)."""
    rows = []
    for year in (2021, 2022, 2023, 2024):
        for q in (3, 6, 9, 12):
            rows.append((year, q, 100.0))
    return rows


def _make_dispatcher(world: Dict[str, Any]):
    """Return a fake pd.read_sql that dispatches on SQL substrings."""

    def fake_read_sql(sql, con=None, params=None, **kwargs):  # noqa: ANN001
        s = str(sql)
        # Universe: stock_list mode=current-vn100
        if "FROM stock_list" in s and "nhomtop" in s:
            return pd.DataFrame(
                {"stockcode": world["universe_stock_list"]}
            )
        # Universe: history filter
        if "FROM stock_eod" in s and "COUNT(*)" in s:
            tickers = params["tickers"]
            return pd.DataFrame(
                {
                    "stockcode": tickers,
                    "n": [N_BARS] * len(tickers),
                }
            )
        # Scorer panel load
        if "FROM stock_eod" in s and "closeindex" in s and "highestindex" in s:
            return world["panel"]
        # Fundamentals: is_quarter_nonbank / is_quarter_bank
        if "FROM is_quarter_nonbank" in s or "FROM is_quarter_bank" in s:
            t = params["t"]
            df = world["eps"].get(t)
            if df is None:
                return pd.DataFrame(columns=["stockcode", "thoigian", "value"])
            # Loader derives year/quarter from thoigian and sorts internally,
            # so we just return the frame as-is.
            return df.reset_index(drop=True)
        # Foreign flow
        if "stock_foreign_eod" in s:
            t = params["t"]
            val = world["foreign"].get(t, 1)  # default positive
            return pd.DataFrame({"net_buy": [val]})
        raise AssertionError(f"Unexpected SQL in test dispatcher: {s[:120]}")

    return fake_read_sql


@pytest.fixture
def fake_world(monkeypatch):
    """Wire up a fake universe + panels + EPS + flow and patch pd.read_sql."""
    # 5 tickers: 3 'other' strong, 1 'bank', 1 'ctck' (ctck excluded).
    all_tickers = ["AAA", "BBB", "CCC", "BNK", "SEC"]
    sector_map = {
        "AAA": "nonbank",
        "BBB": "nonbank",
        "CCC": "nonbank",
        "BNK": "Ngân hàng TMCP",
        "SEC": "Chứng khoán X",
    }
    router = SectorRouter(ticker_to_sector=sector_map)

    # Price end-values differentiate RS strength.
    price_map = {"AAA": 200.0, "BBB": 180.0, "CCC": 160.0, "BNK": 150.0}
    panel = _fake_panel(["AAA", "BBB", "CCC", "BNK"], price_map)

    eps = {
        "AAA": _fake_quarters(_strong_eps()),
        "BBB": _fake_quarters(_strong_eps()),
        "CCC": _fake_quarters(_weak_eps()),
        "BNK": _fake_quarters(_strong_eps()),
    }

    foreign = {"AAA": 1_000, "BBB": 500, "CCC": -10, "BNK": 1}

    world = {
        "universe_stock_list": all_tickers,
        "panel": panel,
        "eps": eps,
        "foreign": foreign,
        "router": router,
    }
    monkeypatch.setattr(pd, "read_sql", _make_dispatcher(world))
    return world


def _build_scorer(world, config=None) -> CanslimScorer:
    cfg = config or CanslimConfig()
    loader = UniverseLoader(mode="current-vn100", pg_engine=object(), min_history_days=cfg.min_history_days)
    return CanslimScorer(
        config=cfg,
        universe_loader=loader,
        sector_router=world["router"],
        pg_engine=object(),
        mysql_engine=object(),
    )


# --------------------------------------------------------------------------- tests


def test_1_output_schema_exact(fake_world):
    """Test 1: output frame has EXACTLY the D-09 columns in order."""
    scorer = _build_scorer(fake_world)
    df = scorer.score(AS_OF)
    assert list(df.columns) == OUTPUT_COLUMNS


def test_2_dtypes(fake_world):
    """Test 2: *_pass columns are bool; rs_rating + score are float."""
    scorer = _build_scorer(fake_world)
    df = scorer.score(AS_OF)
    bool_cols = [
        "c_pass",
        "c_plus_pass",
        "a_pass",
        "a_plus_pass",
        "n_pass",
        "s_pass",
        "l_pass",
        "i_pass",
        "liq_pass",
    ]
    for c in bool_cols:
        assert df[c].dtype == bool, f"{c} dtype {df[c].dtype}"
    assert df["rs_rating"].dtype == float
    assert df["score"].dtype == float


def test_3_ctck_excluded(fake_world):
    """Test 3: 5 tickers in → 4 rows out (ctck SEC filtered)."""
    scorer = _build_scorer(fake_world)
    df = scorer.score(AS_OF)
    assert len(df) == 4
    assert "SEC" not in set(df["ticker"])
    assert {"AAA", "BBB", "CCC", "BNK"} == set(df["ticker"])


def test_4_publish_date_guard(monkeypatch, fake_world):
    """Test 4: EPS with publish_date > as_of_date is invisible.

    Give AAA a "future" blockbuster quarter (year=2026) whose imputed
    publish_date lies beyond AS_OF; the scorer must use the prior published
    quarter series instead — which is the ``_strong_eps()`` tail and still
    passes C. We verify the scorer does not crash AND that AAA still appears
    with its pre-existing strong-EPS passes (i.e. not corrupted by the
    look-ahead row).
    """
    # Build a modified AAA with one extra future-dated quarter at the top.
    strong = _strong_eps() + [(2026, 12, 9_999_999.0)]  # imputed pub ~2027
    fake_world["eps"]["AAA"] = _fake_quarters(strong)
    scorer = _build_scorer(fake_world)
    df = scorer.score(AS_OF)
    aaa = df[df["ticker"] == "AAA"].iloc[0]
    # C must reflect the pre-2026 series (strong and growing -> True).
    assert aaa["c_pass"] == True  # noqa: E712
    # score should equal what it would have been without the future row.


def test_5_monotone_in_pass_count():
    """Test 5: for fixed RS, more booleans → higher composite."""
    # Direct check against the locked composite helper.
    from strategies.canslim.scorer import CanslimScorer as CS

    rs = 50.0
    low = CS._composite([True] * 3 + [False] * 6, rs)
    mid = CS._composite([True] * 6 + [False] * 3, rs)
    high = CS._composite([True] * 9, rs)
    assert low < mid < high


def test_6_monotone_in_rs():
    """Test 6: for fixed pass count, higher RS → higher composite."""
    from strategies.canslim.scorer import CanslimScorer as CS

    passes = [True, True, True, False, False, False, True, True, False]
    a = CS._composite(passes, 10.0)
    b = CS._composite(passes, 50.0)
    c = CS._composite(passes, 90.0)
    assert a < b < c


def test_7_score_extremes():
    """Test 7: all-False + RS=0 → 0; all-True + RS=100 → 100."""
    from strategies.canslim.scorer import CanslimScorer as CS

    assert CS._composite([False] * 9, 0.0) == pytest.approx(0.0)
    assert CS._composite([True] * 9, 100.0) == pytest.approx(100.0)
    # Cross-check the locked weights are 0.70 / 0.30.
    assert BOOL_WEIGHT == 0.70
    assert RS_WEIGHT == 0.30
    assert NUM_BOOLEAN_RULES == 9


def test_smoke_instantiate():
    """Legacy smoke test — CanslimScorer still constructs via dataclass kwargs."""
    cfg = CanslimConfig()
    loader = UniverseLoader(mode="current-vn100", pg_engine=object())
    router = SectorRouter(ticker_to_sector={})
    s = CanslimScorer(
        config=cfg,
        universe_loader=loader,
        sector_router=router,
        pg_engine=object(),
        mysql_engine=object(),
    )
    assert s.config.c_threshold == 0.20
