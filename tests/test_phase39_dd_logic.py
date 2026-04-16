"""
Phase 39 Plan 02 unit tests: dual-threshold DistributionDayCounter logic.

Covers:
- DD-02 (large drop path): drop <= large_drop AND vol_above_ma20 -> Type 1 DD
- DD-02 (small drop path): drop <= small_drop AND vol_top_pct -> Type 1 DD
- DD-03 feature gate: refined_dd_enabled=False uses classic v6.0 rule
- DD-04 backward-compat: classic rule unchanged when feature off
- D-01: Type 2 stalling DD remains intact regardless of refined_dd_enabled

The new dual-threshold rule replaces the hard-coded -0.2% Type 1 threshold
when refined_dd_enabled=True. Type 2 stalling DD is NOT modified (per D-01,
D-04). When refined_dd_enabled=False the classic rule must be byte-identical
to v6.0 (per DD-04).
"""
import sys
from pathlib import Path

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
from strategies.mdm_hybrid.distribution_day import DistributionDayCounter  # noqa: E402


# ── Classic v6.0 fallback (refined_dd_enabled=False) ─────────────────


def test_classic_fallback_dd_fires():
    """refined_dd_enabled=False: drop=-0.003 + volume_up=True -> Type 1 DD (classic -0.2% rule)."""
    cfg = MDMV2Config(refined_dd_enabled=False)
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(price_change_pct=-0.003, volume_up=True)
    assert is_dd is True, "classic rule: drop -0.3% with volume_up must trigger Type 1 DD"


def test_classic_fallback_dd_misses_no_volume():
    """refined_dd_enabled=False: drop=-0.003 + volume_up=False -> NOT a DD."""
    cfg = MDMV2Config(refined_dd_enabled=False)
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(price_change_pct=-0.003, volume_up=False)
    assert is_dd is False, "classic rule: volume_up=False must suppress DD"


def test_classic_fallback_dd_misses_tiny_drop():
    """refined_dd_enabled=False: drop=-0.001 (above -0.2% threshold) -> NOT a DD even with volume_up."""
    cfg = MDMV2Config(refined_dd_enabled=False)
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(price_change_pct=-0.001, volume_up=True)
    assert is_dd is False, "classic rule: drop too small to qualify"


# ── Refined dual-threshold rule (large drop path) ────────────────────


def test_refined_large_drop_hit():
    """refined: drop=-0.008 (>= large_drop -0.007) + vol_above_ma20=True -> Type 1 DD."""
    cfg = MDMV2Config(
        refined_dd_enabled=True,
        refined_dd_large_drop=-0.007,
        refined_dd_small_drop=-0.004,
    )
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(
        price_change_pct=-0.008,
        volume_up=False,           # classic volume_up irrelevant in refined mode
        vol_above_ma20=True,
        vol_top_pct=False,
    )
    assert is_dd is True, "refined: large drop with vol > MA20 must trigger DD"


def test_refined_large_drop_miss_low_vol():
    """refined: drop=-0.008 but vol_above_ma20=False AND vol_top_pct=False -> NOT a DD."""
    cfg = MDMV2Config(
        refined_dd_enabled=True,
        refined_dd_large_drop=-0.007,
        refined_dd_small_drop=-0.004,
    )
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(
        price_change_pct=-0.008,
        volume_up=True,            # classic volume_up irrelevant in refined mode
        vol_above_ma20=False,
        vol_top_pct=False,
    )
    assert is_dd is False, "refined: large drop without elevated volume must NOT trigger DD"


# ── Refined dual-threshold rule (small drop path) ────────────────────


def test_refined_small_drop_hit():
    """refined: drop=-0.005 (>= small_drop -0.004) + vol_top_pct=True -> Type 1 DD."""
    cfg = MDMV2Config(
        refined_dd_enabled=True,
        refined_dd_large_drop=-0.007,
        refined_dd_small_drop=-0.004,
    )
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(
        price_change_pct=-0.005,
        volume_up=False,
        vol_above_ma20=False,
        vol_top_pct=True,
    )
    assert is_dd is True, "refined: small drop with top-percentile volume must trigger DD"


def test_refined_small_drop_miss_no_pct():
    """refined: drop=-0.005 but vol_top_pct=False AND vol_above_ma20=False -> NOT a DD."""
    cfg = MDMV2Config(
        refined_dd_enabled=True,
        refined_dd_large_drop=-0.007,
        refined_dd_small_drop=-0.004,
    )
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(
        price_change_pct=-0.005,
        volume_up=True,
        vol_above_ma20=False,
        vol_top_pct=False,
    )
    assert is_dd is False, "refined: small drop without top-percentile volume must NOT trigger DD"


def test_refined_tiny_drop_miss():
    """refined: drop=-0.002 (above small_drop -0.004) + vol_top_pct=True -> NOT a DD (drop too small)."""
    cfg = MDMV2Config(
        refined_dd_enabled=True,
        refined_dd_large_drop=-0.007,
        refined_dd_small_drop=-0.004,
    )
    counter = DistributionDayCounter(cfg)
    is_dd = counter.is_distribution_day_type1(
        price_change_pct=-0.002,
        volume_up=True,
        vol_above_ma20=True,
        vol_top_pct=True,
    )
    assert is_dd is False, "refined: drop above small_drop threshold must NOT trigger DD"


# ── Type 2 stalling DD unaffected by refined flag (D-01) ─────────────


def test_type2_stalling_unaffected_by_refined_flag():
    """D-01: Type 2 stalling DD logic unchanged regardless of refined_dd_enabled.

    Type 2 conditions: 0 <= price_change_pct < 0.001 (stall threshold default),
    volume_up=True, p_loc <= 0.2 (low close).
    """
    # Build configs with refined flag in each state -- Type 2 must fire identically
    cfg_off = MDMV2Config(refined_dd_enabled=False)
    cfg_on = MDMV2Config(
        refined_dd_enabled=True,
        refined_dd_large_drop=-0.007,
        refined_dd_small_drop=-0.004,
    )

    counter_off = DistributionDayCounter(cfg_off)
    counter_on = DistributionDayCounter(cfg_on)

    # Stalling: small positive change (0.05%), volume up, close in lower 25%
    stall_change = 0.0005   # < dd_price_stall_threshold (0.001)
    p_loc_low = 0.15        # <= dd_stall_p_loc_threshold (0.2)

    type2_off = counter_off.is_distribution_day_type2(stall_change, True, p_loc_low)
    type2_on = counter_on.is_distribution_day_type2(stall_change, True, p_loc_low)

    assert type2_off is True, "Type 2 must fire on stalling conditions (refined off)"
    assert type2_on is True, "Type 2 must fire on stalling conditions (refined on)"
    assert type2_off == type2_on, "Type 2 result must be identical regardless of refined flag"


# ── check_distribution_day backward-compat signature ─────────────────


def test_check_distribution_day_backward_compat_signature():
    """Old caller using positional args (no vol kwargs) must still work when refined off.

    Guards Pitfall 4: adding vol_above_ma20 and vol_top_pct kwargs must default
    to False so existing call sites (regression fixtures, downstream callers)
    do not break.
    """
    cfg = MDMV2Config(refined_dd_enabled=False)
    counter = DistributionDayCounter(cfg)
    date = pd.Timestamp('2020-01-15')
    is_dd, dd_type = counter.check_distribution_day(
        date,
        high=100.0,
        price_change_pct=-0.003,
        volume_up=True,
        p_loc=0.4,
    )
    assert is_dd is True, "classic call signature must still work"
    assert dd_type == 1, "should detect Type 1 DD via classic rule"


def test_check_distribution_day_passes_refined_kwargs():
    """check_distribution_day must forward vol_above_ma20 and vol_top_pct to type1 check."""
    cfg = MDMV2Config(
        refined_dd_enabled=True,
        refined_dd_large_drop=-0.007,
        refined_dd_small_drop=-0.004,
    )
    counter = DistributionDayCounter(cfg)
    date = pd.Timestamp('2020-01-15')

    # Refined rule: small drop + top-percentile volume should fire Type 1
    is_dd, dd_type = counter.check_distribution_day(
        date,
        high=100.0,
        price_change_pct=-0.005,
        volume_up=False,           # classic volume irrelevant in refined mode
        p_loc=0.4,
        vol_above_ma20=False,
        vol_top_pct=True,
    )
    assert is_dd is True, "refined kwargs must propagate to type1 check"
    assert dd_type == 1, "should detect Type 1 DD via small-drop refined path"
