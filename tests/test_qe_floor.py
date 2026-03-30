"""Integration tests for QE floor SELL suppression in MDM V2 engine.

Tests verify:
1. SELL signals are suppressed when qe_floor=1 and qe_floor_enabled=True
2. BUY->CASH transitions (stop loss, DD threshold) are NOT affected
3. Baseline regression: qe_floor_enabled=False produces same equity as before
4. Pre-2007 NASDAQ dates run without crash and without false suppression
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Resolve paths for worktree data access
WORKTREE_ROOT = Path(__file__).resolve().parent.parent
MAIN_REPO = WORKTREE_ROOT
if '.claude' in str(WORKTREE_ROOT) and 'worktrees' in str(WORKTREE_ROOT):
    parts = WORKTREE_ROOT.parts
    for i, part in enumerate(parts):
        if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
            MAIN_REPO = Path(*parts[:i])
            break

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from core.data_loader import DataLoader


@pytest.fixture
def vn30_data():
    """Load VN30 data from main repo."""
    loader = DataLoader('vn30')
    loader.data_dir = MAIN_REPO
    df = loader.load()
    if df is None or df.empty:
        pytest.skip("VN30 data not available")
    return df


@pytest.fixture
def nasdaq_data():
    """Load full NASDAQ data from main repo."""
    loader = DataLoader('nasdaq')
    loader.data_dir = MAIN_REPO
    df = loader.load()
    if df is None or df.empty:
        pytest.skip("NASDAQ data not available")
    return df


class TestSellSuppressedDuringQE:
    """Test 1: SELL signals suppressed when QE floor active."""

    def test_sell_suppressed_during_qe(self, vn30_data):
        """With qe_floor_enabled=True, at least one SELL is suppressed on VN30."""
        config = MDMV2Config(
            qe_floor_enabled=True,
            liquidity_csv_path=str(MAIN_REPO / "data" / "global_liquidity.csv"),
        )
        engine = MDMV2Engine(config)
        results = engine.run(vn30_data)

        suppressed = results[results['action'].str.contains('SELL suppressed', na=False)]
        assert len(suppressed) > 0, (
            "Expected at least 1 SELL suppression with QE floor enabled on VN30"
        )


class TestOtherTransitionsUnaffected:
    """Test 2: BUY->CASH transitions still occur with QE floor enabled."""

    def test_other_transitions_unaffected(self, vn30_data):
        """BUY->CASH exits (stop loss, DD threshold) still happen with qe_floor_enabled=True."""
        config = MDMV2Config(
            qe_floor_enabled=True,
            liquidity_csv_path=str(MAIN_REPO / "data" / "global_liquidity.csv"),
        )
        engine = MDMV2Engine(config)
        engine.run(vn30_data)

        trades = engine.get_trades()
        cash_exits = [t for t in trades if t['type'] == 'CASH_EXIT']
        assert len(cash_exits) > 0, (
            "Expected BUY->CASH transitions to still occur with QE floor enabled"
        )


class TestBaselineRegression:
    """Test 3: qe_floor_enabled=False produces same equity as baseline."""

    def test_baseline_regression(self, vn30_data):
        """With qe_floor_enabled=False, V2 engine produces identical results to pre-change baseline.

        Uses V2PerformanceAnalyzer with VN30-tuned params.
        The 190.8% figure in PROJECT.md refers to the hybrid engine; the pure V2
        engine with VN30 params yields ~22.6% total return (includes short returns).
        This test locks the V2 engine baseline to ensure QE floor code path
        does not alter results when disabled.
        """
        from strategies.mdm_v2.performance import V2PerformanceAnalyzer

        config = MDMV2Config(
            correction_threshold=-0.06,
            ma10_cash_consecutive=3,
            cash_deterioration_days=20,
            qe_floor_enabled=False,
            name="vn30_regression",
        )
        engine = MDMV2Engine(config)
        results = engine.run(vn30_data)

        analyzer = V2PerformanceAnalyzer(results)
        total_return_pct = analyzer.total_return() * 100

        # V2 engine (not hybrid) with VN30 params: ~22.6% total return
        # Tolerance +/- 0.5% for float arithmetic
        assert 22.1 <= total_return_pct <= 23.1, (
            f"Baseline regression failed: expected ~22.6%, got {total_return_pct:.1f}%"
        )


class TestNasdaqPre2007NoCrash:
    """Test 4: Pre-2007 NASDAQ dates run without crash and without false suppression."""

    def test_nasdaq_pre2007_no_crash(self, nasdaq_data):
        """Engine with qe_floor_enabled=True on full NASDAQ: no crash, no pre-2007 suppression."""
        config = MDMV2Config(
            qe_floor_enabled=True,
            liquidity_csv_path=str(MAIN_REPO / "data" / "global_liquidity.csv"),
        )
        engine = MDMV2Engine(config)
        results = engine.run(nasdaq_data)

        # Should have results
        assert len(results) > 0, "Engine produced no results on NASDAQ data"

        # Filter to pre-2007 period
        pre_2007 = results[results['date'] < '2007-05-01']
        assert len(pre_2007) > 0, "No pre-2007 data found in NASDAQ results"

        # No SELL suppression should occur in pre-2007 period (no liquidity data)
        pre_2007_suppressed = pre_2007[
            pre_2007['action'].str.contains('SELL suppressed', na=False)
        ]
        assert len(pre_2007_suppressed) == 0, (
            f"Found {len(pre_2007_suppressed)} false SELL suppressions in pre-2007 period"
        )
