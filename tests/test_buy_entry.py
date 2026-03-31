"""
Tests for Buy Entry Filter (GAP-01, RALLY-01, RALLY-02).

GAP-01: Reject FTD when intraday low < previous close (gap-up broken).
RALLY-01: Allow early FTD in shallow pullbacks (< 6% decline).
RALLY-02: Deep corrections (>= 6%) require classic rally_day >= 4.
"""

import pytest

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.buy_entry import BuyEntryFilter


class TestGapFilter:
    """Unit tests for gap-up invalidation filter."""

    def _make_filter(self, gap_filter_enabled: bool = True) -> BuyEntryFilter:
        """Create a BuyEntryFilter with specified gap filter config."""
        config = MDMV2Config(gap_filter_enabled=gap_filter_enabled)
        return BuyEntryFilter(config)

    def test_gap_broken_rejects_ftd(self):
        """FTD rejected when intraday low < previous close (gap-up broken)."""
        f = self._make_filter()
        assert f.check_gap("FTD", low=99.0, prev_close=100.0) is False

    def test_gap_intact_allows_ftd(self):
        """FTD allowed when intraday low > previous close (gap intact)."""
        f = self._make_filter()
        assert f.check_gap("FTD", low=100.5, prev_close=100.0) is True

    def test_gap_equal_allows_ftd(self):
        """FTD allowed when intraday low == previous close (low >= prev_close)."""
        f = self._make_filter()
        assert f.check_gap("FTD", low=100.0, prev_close=100.0) is True

    def test_bypass_ma50(self):
        """MA50 breakout bypasses gap filter even if gap is broken."""
        f = self._make_filter()
        assert f.check_gap("MA50", low=99.0, prev_close=100.0) is True

    def test_bypass_52week(self):
        """52-week breakout bypasses gap filter even if gap is broken."""
        f = self._make_filter()
        assert f.check_gap("52WEEK", low=99.0, prev_close=100.0) is True

    def test_disabled_allows_all(self):
        """gap_filter_enabled=False allows all signals through."""
        f = self._make_filter(gap_filter_enabled=False)
        assert f.check_gap("FTD", low=99.0, prev_close=100.0) is True


class TestRallyThreshold:
    """Unit tests for rally threshold (early FTD in shallow pullbacks)."""

    def _make_filter(self, rally_threshold_enabled: bool = True,
                     rally_threshold_pct: float = -0.06) -> BuyEntryFilter:
        """Create a BuyEntryFilter with specified rally threshold config."""
        config = MDMV2Config(
            rally_threshold_enabled=rally_threshold_enabled,
            rally_threshold_pct=rally_threshold_pct,
        )
        return BuyEntryFilter(config)

    def test_shallow_pullback_allows_early(self):
        """Shallow pullback (4% < 6%) allows early FTD."""
        f = self._make_filter()
        assert f.should_allow_early_ftd(drawdown_pct=-0.04) is True

    def test_deep_correction_requires_classic(self):
        """Deep correction (8% > 6%) requires classic day-3+ FTD."""
        f = self._make_filter()
        assert f.should_allow_early_ftd(drawdown_pct=-0.08) is False

    def test_exactly_at_threshold(self):
        """Exactly at 6% threshold is NOT shallow (requires classic)."""
        f = self._make_filter()
        assert f.should_allow_early_ftd(drawdown_pct=-0.06) is False

    def test_disabled_returns_false(self):
        """rally_threshold_enabled=False always returns False (classic only)."""
        f = self._make_filter(rally_threshold_enabled=False)
        assert f.should_allow_early_ftd(drawdown_pct=-0.04) is False

    def test_no_drawdown(self):
        """No drawdown (0%) is considered shallow, allows early FTD."""
        f = self._make_filter()
        assert f.should_allow_early_ftd(drawdown_pct=0.0) is True
