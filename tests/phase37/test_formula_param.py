"""Phase 37 Plan 01 — Formula kwarg tests for build_momentum_raw_frame and run_v8_backtest.

Tests confirm:
1. Default formula (no arg) produces rs_rating values.
2. formula="weighted_roc" matches default output.
3. formula="roc126" produces different rs_rating values vs weighted_roc.
4. Invalid formula raises ValueError.
5. Cache filename encodes formula string.
6. run_v8_backtest accepts formula kwarg (signature check).
7. run_v8_backtest passes formula through to build_momentum_raw_frame.
"""

import inspect
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panel(n_rows: int = 350, n_tickers: int = 3, seed: int = 42) -> pd.DataFrame:
    """Synthetic panel with deterministic close prices — 3 tickers, 350 rows.

    Produces a realistic equity-like time series using random walk, so
    weighted_roc and roc126 will produce *different* rs_rating values.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n_rows, freq="B")
    rows = []
    tickers = [f"T{i:02d}" for i in range(n_tickers)]
    for tk in tickers:
        # Different seed per ticker gives different drift — ensures RS spread
        tk_seed = seed + ord(tk[1]) * 13
        rng2 = np.random.default_rng(tk_seed)
        daily_ret = 1.0 + rng2.normal(0.0005, 0.015, size=n_rows)
        close = np.cumprod(daily_ret) * 100.0
        high = close * (1.0 + np.abs(rng2.normal(0, 0.005, size=n_rows)))
        low = close * (1.0 - np.abs(rng2.normal(0, 0.005, size=n_rows)))
        open_ = close * (1.0 + rng2.normal(0, 0.003, size=n_rows))
        rows.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "ticker": tk,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": rng2.integers(100_000, 1_000_000, size=n_rows).astype(float),
                }
            )
        )
    return pd.concat(rows, ignore_index=True).sort_values(["ticker", "date"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Test 1: default formula produces rs_rating (not all NaN)
# ---------------------------------------------------------------------------

def test_build_momentum_raw_frame_default_formula(tmp_path):
    """Calling with no formula arg produces rs_rating column — not all NaN."""
    from analysis._vn100_pipeline import build_momentum_raw_frame

    panel = _make_panel()
    with patch("analysis._vn100_pipeline.CACHE_DIR", tmp_path):
        result = build_momentum_raw_frame(panel)

    assert "rs_rating" in result.columns, "rs_rating column missing from result"
    non_nan = result["rs_rating"].notna().sum()
    assert non_nan > 0, f"All rs_rating values are NaN; expected some values for 350-row panel"


# ---------------------------------------------------------------------------
# Test 2: formula="weighted_roc" output identical to default
# ---------------------------------------------------------------------------

def test_build_momentum_raw_frame_weighted_roc(tmp_path):
    """formula='weighted_roc' produces rs_rating values identical to default."""
    from analysis._vn100_pipeline import build_momentum_raw_frame

    panel = _make_panel()
    with patch("analysis._vn100_pipeline.CACHE_DIR", tmp_path):
        result_default = build_momentum_raw_frame(panel)
    with patch("analysis._vn100_pipeline.CACHE_DIR", tmp_path):
        result_explicit = build_momentum_raw_frame(panel, formula="weighted_roc")

    # Both should produce the same rs_rating (same formula)
    merged = result_default.merge(
        result_explicit, on=["date", "ticker"], suffixes=("_def", "_wroc")
    )
    diff = (merged["rs_rating_def"] - merged["rs_rating_wroc"]).abs().max()
    assert diff < 1e-9, f"Default and weighted_roc rs_rating differ by {diff} — should be identical"


# ---------------------------------------------------------------------------
# Test 3: formula="roc126" produces different rs_rating values vs weighted_roc
# ---------------------------------------------------------------------------

def test_build_momentum_raw_frame_roc126(tmp_path):
    """formula='roc126' produces rs_rating values that differ from weighted_roc."""
    from analysis._vn100_pipeline import build_momentum_raw_frame

    panel = _make_panel()
    with patch("analysis._vn100_pipeline.CACHE_DIR", tmp_path):
        result_wroc = build_momentum_raw_frame(panel, formula="weighted_roc")
    # Use a different tmp subdir so cache miss forces recompute for roc126
    tmp2 = tmp_path / "roc126_cache"
    tmp2.mkdir()
    with patch("analysis._vn100_pipeline.CACHE_DIR", tmp2):
        result_roc126 = build_momentum_raw_frame(panel, formula="roc126")

    assert "rs_rating" in result_roc126.columns, "rs_rating column missing for roc126 formula"

    # Spot-check T00: at least some rows differ between formulas
    merged = result_wroc.merge(
        result_roc126, on=["date", "ticker"], suffixes=("_wroc", "_roc126")
    )
    t00 = merged[merged["ticker"] == "T00"].dropna(subset=["rs_rating_wroc", "rs_rating_roc126"])
    assert len(t00) > 0, "No overlapping rows for spot-check ticker T00"
    diffs = (t00["rs_rating_wroc"] - t00["rs_rating_roc126"]).abs()
    assert diffs.max() > 0.1, (
        f"weighted_roc and roc126 produced identical rs_rating for T00 — "
        f"formula branch may not be wired correctly (max diff = {diffs.max():.6f})"
    )


# ---------------------------------------------------------------------------
# Test 4: invalid formula raises ValueError
# ---------------------------------------------------------------------------

def test_invalid_formula_raises(tmp_path):
    """formula='bad_formula' raises ValueError with message referencing valid options."""
    from analysis._vn100_pipeline import build_momentum_raw_frame

    panel = _make_panel(n_rows=100)  # small panel — error should fire before computation
    with patch("analysis._vn100_pipeline.CACHE_DIR", tmp_path):
        with pytest.raises(ValueError, match="weighted_roc|roc126"):
            build_momentum_raw_frame(panel, formula="bad_formula")


# ---------------------------------------------------------------------------
# Test 5: cache filename includes formula
# ---------------------------------------------------------------------------

def test_cache_filename_includes_formula(tmp_path):
    """formula='roc126' writes cache file with 'roc126' in the filename."""
    from analysis._vn100_pipeline import build_momentum_raw_frame

    panel = _make_panel()
    with patch("analysis._vn100_pipeline.CACHE_DIR", tmp_path):
        build_momentum_raw_frame(panel, formula="roc126")

    parquet_files = list(tmp_path.glob("*.parquet"))
    names = [f.name for f in parquet_files]
    roc126_files = [n for n in names if "roc126" in n]
    weighted_files = [n for n in names if "weighted_roc" in n]
    assert len(roc126_files) >= 1, (
        f"Expected a cache file with 'roc126' in name, got: {names}"
    )
    assert len(weighted_files) == 0, (
        f"Did NOT expect a 'weighted_roc' cache file when formula='roc126', got: {names}"
    )


# ---------------------------------------------------------------------------
# Test 6: run_v8_backtest accepts formula kwarg (signature introspection)
# ---------------------------------------------------------------------------

def test_run_v8_backtest_formula_kwarg_accepted():
    """run_v8_backtest signature must include 'formula' parameter."""
    from analysis._vn100_pipeline import run_v8_backtest

    sig = inspect.signature(run_v8_backtest)
    assert "formula" in sig.parameters, (
        f"'formula' kwarg missing from run_v8_backtest signature; "
        f"found parameters: {list(sig.parameters.keys())}"
    )
    # Default must be 'weighted_roc'
    default = sig.parameters["formula"].default
    assert default == "weighted_roc", (
        f"Expected default formula='weighted_roc', got default={default!r}"
    )


# ---------------------------------------------------------------------------
# Test 7: formula pass-through — run_v8_backtest calls build_momentum_raw_frame
#         with the formula it received
# ---------------------------------------------------------------------------

def test_formula_passthrough():
    """Mock build_momentum_raw_frame; confirm run_v8_backtest passes formula kwarg through."""
    from analysis._vn100_pipeline import run_v8_backtest

    panel = _make_panel()

    # Minimal fake precomputed dict to satisfy v8 validation
    dates = sorted(panel["date"].unique())
    gate = pd.Series("BUY", index=pd.DatetimeIndex(dates), name="mdm_state")
    fake_precomputed = {
        "universe": None,
        "ohlc": _make_ohlc_from_panel(panel),
        "mdm_gate": gate,
        "momentum_raw": None,  # set to None so code falls through to build_momentum_raw_frame
    }
    # Remove momentum_raw so the code path calls build_momentum_raw_frame
    del fake_precomputed["momentum_raw"]

    mock_raw = pd.DataFrame({
        "date": pd.to_datetime(["2019-01-02"]),
        "ticker": ["T00"],
        "n_prox": [0.05],
        "rs_rating": [80.0],
    })

    with patch("analysis._vn100_pipeline.build_momentum_raw_frame", return_value=mock_raw) as mock_bmrf:
        # We expect an error later (portfolio engine will fail without real data),
        # but we only need to verify the call was made with formula="roc126"
        try:
            run_v8_backtest(
                momentum_cfg=_make_momentum_cfg(),
                portfolio_cfg=_make_portfolio_cfg(),
                entry_option="A",
                period=("2019-01-01", "2019-12-31"),
                precomputed=fake_precomputed,
                formula="roc126",
            )
        except Exception:
            pass  # Expected — fake data will fail portfolio engine

    mock_bmrf.assert_called_once()
    call_kwargs = mock_bmrf.call_args
    # formula="roc126" should have been passed as keyword arg
    passed_formula = call_kwargs.kwargs.get("formula") or (
        call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
    )
    assert passed_formula == "roc126", (
        f"Expected build_momentum_raw_frame to be called with formula='roc126', "
        f"got: {call_kwargs}"
    )


# ---------------------------------------------------------------------------
# Helpers for test 7
# ---------------------------------------------------------------------------

def _make_ohlc_from_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Convert synthetic panel to the raw DB column format expected by run_v8_backtest."""
    return pd.DataFrame({
        "tradingdate": panel["date"],
        "stockcode": panel["ticker"],
        "openprice": panel["open"],
        "highestprice": panel["high"],
        "lowestprice": panel["low"],
        "closeprice": panel["close"],
        "totalvol": panel["volume"],
    })


def _make_momentum_cfg():
    from strategies.momentum.scorer_config import MomentumScorerConfig
    return MomentumScorerConfig()


def _make_portfolio_cfg():
    from strategies.portfolio.config import PortfolioConfig
    return PortfolioConfig()
