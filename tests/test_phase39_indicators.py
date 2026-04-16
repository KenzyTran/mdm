"""
Phase 39 unit tests: refined DD config fields and volume indicator columns.

Covers:
- DD-01/DD-03: MDMV2Config refined_dd_* fields with correct defaults
- DD-02 data layer: Indicators.add_volume_ma_column produces vol_ma20
- DD-02 data layer: Indicators.add_volume_percentile_column produces vol_top_pct
- Pitfall 5: validation only fires when refined_dd_enabled=True
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
# Handle git worktree paths
if '.claude' in str(ROOT) and 'worktrees' in str(ROOT):
    parts = ROOT.parts
    for i, part in enumerate(parts):
        if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
            ROOT = Path(*parts[:i])
            break
sys.path.insert(0, str(ROOT))

from strategies.mdm_hybrid.config import MDMV2Config  # noqa: E402
from strategies.mdm_hybrid.indicators import Indicators  # noqa: E402


# ── Indicator: add_volume_ma_column ──────────────────────────────────


def test_add_volume_ma_column_basic():
    """vol_ma20 column exists, no NaN, row 20 value matches manual rolling(20).mean()."""
    np.random.seed(42)
    df = pd.DataFrame({
        'volume': np.random.randint(1_000_000, 5_000_000, size=25).astype(float)
    })
    out = Indicators.add_volume_ma_column(df, period=20)
    assert 'vol_ma20' in out.columns, "vol_ma20 column missing"
    assert out['vol_ma20'].isna().sum() == 0, "vol_ma20 has NaN values (min_periods=1 violation)"
    expected_row20 = df['volume'].iloc[1:21].mean()
    assert out['vol_ma20'].iloc[20] == pytest.approx(expected_row20, rel=1e-9), \
        "row 20 vol_ma20 must equal manual rolling(20).mean()"


def test_add_volume_ma_column_min_periods():
    """First row vol_ma20 equals volume[0] (min_periods=1)."""
    df = pd.DataFrame({'volume': [1_000_000.0, 2_000_000.0, 3_000_000.0]})
    out = Indicators.add_volume_ma_column(df, period=20)
    assert out['vol_ma20'].iloc[0] == pytest.approx(1_000_000.0)
    # Row 1 = mean of first 2 = 1.5M
    assert out['vol_ma20'].iloc[1] == pytest.approx(1_500_000.0)
    # Row 2 = mean of first 3 = 2M
    assert out['vol_ma20'].iloc[2] == pytest.approx(2_000_000.0)


def test_add_volume_ma_column_does_not_mutate_input():
    """Input DataFrame must not be mutated (df.copy() pattern)."""
    df = pd.DataFrame({'volume': [1.0, 2.0, 3.0]})
    cols_before = list(df.columns)
    Indicators.add_volume_ma_column(df)
    assert list(df.columns) == cols_before, "input df was mutated"


# ── Indicator: add_volume_percentile_column ──────────────────────────


def test_add_volume_percentile_column_basic():
    """vol_top_pct column exists with boolean dtype on 60 rows of data."""
    np.random.seed(42)
    df = pd.DataFrame({
        'volume': np.random.randint(1_000_000, 5_000_000, size=60).astype(float)
    })
    out = Indicators.add_volume_percentile_column(df, lookback=50, percentile=5)
    assert 'vol_top_pct' in out.columns, "vol_top_pct column missing"
    assert out['vol_top_pct'].dtype == bool, \
        f"vol_top_pct dtype must be bool, got {out['vol_top_pct'].dtype}"


def test_add_volume_percentile_column_top_hit():
    """Row with maximum volume in window must be flagged True."""
    # Construct a deterministic series where row 50 is by far the highest
    volumes = [1_000_000.0] * 50 + [10_000_000.0]  # row 50 = 10x the rest
    df = pd.DataFrame({'volume': volumes})
    out = Indicators.add_volume_percentile_column(df, lookback=50, percentile=5)
    # Row 50 has volume 10M, max in 50-day window. Top 5% threshold = 95th pctile.
    # Row 50 must be True since it dominates the window.
    assert out['vol_top_pct'].iloc[50] == True, \
        "row with max volume in window must be flagged True"


def test_add_volume_percentile_column_mid_miss():
    """Row with median volume must NOT be flagged True for top-5% threshold."""
    # Linear ramp 1..100 — median is around 50
    volumes = list(range(1, 101))
    df = pd.DataFrame({'volume': [float(v) for v in volumes]})
    out = Indicators.add_volume_percentile_column(df, lookback=50, percentile=5)
    # Row at value=50 (mid-range) within a top-5% window — should be False
    # Row index 49 has volume=50, in window [0..49] which contains volumes 1..50
    # 95th percentile of [1..50] is ~47.55, so 50 is above it (True).
    # Pick a clearer mid-window row: with 50-day lookback at row 75, window is [26..75]
    # values range 27..76, 95th percentile ~73.55, so volume 50 (which is NOT in window)
    # Test instead at row 60: window [11..60], values 12..61, 95th pct ~58.55
    # row 60 has value 61 → True. Need a row whose own value is below 95th pctile of its window.
    # Construct fresh: rows where value is near min of window → False.
    df2 = pd.DataFrame({'volume': [float(v) for v in range(1, 101)]})
    out2 = Indicators.add_volume_percentile_column(df2, lookback=50, percentile=5)
    # Row 60: window [11..60], values 12..61, 95th pctile = 12 + 0.95*(61-12) = 12 + 46.55 = 58.55
    # row 60 value=61 >= 58.55 → True
    # Row 30: window [0..30] (min_periods used), values 1..31, 95th pctile ~ 29.5, value 31 → True (it is the max)
    # Pick a row where value is LOW in its window: there's no such row in monotonically increasing series.
    # Switch tactic: use a series with a clear low-mid value
    volumes3 = [10_000_000.0] * 49 + [3_000_000.0] + [10_000_000.0] * 10
    # At row 49, value=3M, window=[0..49]=49 values of 10M + the 3M. 95th pctile = 10M.
    # 3M < 10M → False
    df3 = pd.DataFrame({'volume': volumes3})
    out3 = Indicators.add_volume_percentile_column(df3, lookback=50, percentile=5)
    assert out3['vol_top_pct'].iloc[49] == False, \
        "low-volume row in high-volume window must be False"


def test_add_volume_percentile_column_short_data():
    """Edge case: lookback=50 but only 10 rows — no NaN, column is boolean."""
    df = pd.DataFrame({'volume': [float(v) for v in range(1, 11)]})
    out = Indicators.add_volume_percentile_column(df, lookback=50, percentile=5)
    assert 'vol_top_pct' in out.columns
    assert out['vol_top_pct'].isna().sum() == 0, \
        "vol_top_pct has NaN with min_periods=1 violation on short data"
    assert out['vol_top_pct'].dtype == bool


def test_add_volume_percentile_column_does_not_mutate_input():
    """Input DataFrame must not be mutated."""
    df = pd.DataFrame({'volume': [1.0, 2.0, 3.0]})
    cols_before = list(df.columns)
    Indicators.add_volume_percentile_column(df)
    assert list(df.columns) == cols_before


# ── Config: refined_dd defaults and validation gating ─────────────────


def test_config_refined_dd_defaults():
    """MDMV2Config() ships D-06 defaults for all refined_dd_* fields."""
    c = MDMV2Config()
    assert c.refined_dd_enabled is False
    assert c.refined_dd_large_drop == -0.007
    assert c.refined_dd_small_drop == -0.004
    assert c.refined_dd_large_vol_rule == 'vol_ma20'
    assert c.refined_dd_small_vol_percentile == 5
    assert c.refined_dd_small_vol_lookback == 50


def test_config_validation_fires_when_enabled():
    """Enabled + invalid params raises AssertionError."""
    # Positive large_drop is invalid
    with pytest.raises(AssertionError, match="large_drop must be negative"):
        MDMV2Config(refined_dd_enabled=True, refined_dd_large_drop=0.01)


def test_config_validation_skipped_when_disabled():
    """Disabled + invalid params does NOT raise (Pitfall 5 protection)."""
    # Should not raise even though large_drop is positive
    c = MDMV2Config(refined_dd_enabled=False, refined_dd_large_drop=0.01)
    assert c.refined_dd_large_drop == 0.01


def test_config_validation_order_constraint():
    """Enabled + large_drop > small_drop (less negative) raises."""
    with pytest.raises(AssertionError, match="large_drop must be <= small_drop"):
        MDMV2Config(
            refined_dd_enabled=True,
            refined_dd_large_drop=-0.001,
            refined_dd_small_drop=-0.005,
        )


def test_config_validation_percentile_range():
    """Enabled + invalid percentile (out of 1-100) raises."""
    with pytest.raises(AssertionError, match="percentile must be 1-100"):
        MDMV2Config(refined_dd_enabled=True, refined_dd_small_vol_percentile=0)
    with pytest.raises(AssertionError, match="percentile must be 1-100"):
        MDMV2Config(refined_dd_enabled=True, refined_dd_small_vol_percentile=101)


def test_config_validation_lookback_positive():
    """Enabled + non-positive lookback raises."""
    with pytest.raises(AssertionError, match="lookback must be positive"):
        MDMV2Config(refined_dd_enabled=True, refined_dd_small_vol_lookback=0)
