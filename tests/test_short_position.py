"""
Tests for short position mechanics in V2PositionManager.

Covers requirements:
- SHORT-01: Short entry price tracking on SELL
- SHORT-04: Cover short with P&L calculation
- TRANS-01: enter_buy() guard preventing direct SELL->BUY
- SHORT-04 (engine): Engine-level cover triggers (MA50 breakout, indicator override)
- TRANS-01 (engine): NASDAQ validation -- every BUY preceded by CASH
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

from strategies.mdm_hybrid.position_manager import (
    V2PositionManager,
    V2Position,
    V2MarketState,
)
from strategies.mdm_hybrid.config import MDMV2Config, HybridConfig
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from core.data_loader import DataLoader


@pytest.fixture
def manager():
    """Create a fresh V2PositionManager with default config."""
    return V2PositionManager(MDMV2Config())


TEST_DATE = pd.Timestamp("2024-01-15")
COVER_DATE = pd.Timestamp("2024-02-01")


class TestV2PositionShortFields:
    """Tests for V2Position short entry fields (SHORT-01)."""

    def test_v2position_has_short_fields(self):
        """V2Position() has short_entry_price=0.0 and short_entry_date=None."""
        pos = V2Position()
        assert pos.short_entry_price == 0.0
        assert pos.short_entry_date is None

    def test_enter_sell_records_short_fields(self, manager):
        """After enter_sell with price, position tracks short entry."""
        manager.enter_sell(TEST_DATE, "test reason", price=1000.0)
        assert manager.position.short_entry_price == 1000.0
        assert manager.position.short_entry_date == TEST_DATE

    def test_enter_sell_without_price_defaults_zero(self, manager):
        """enter_sell without price keeps backward compatibility."""
        manager.enter_sell(TEST_DATE, "test reason")
        assert manager.position.short_entry_price == 0.0
        assert manager.position.state == V2MarketState.SELL


class TestShortModeConfig:
    """Tests for HybridConfig.short_mode (D-10)."""

    def test_short_mode_config(self):
        """HybridConfig has short_mode defaulting to 'direct'."""
        config = HybridConfig()
        assert config.short_mode == "direct"

        config2 = HybridConfig(short_mode="inverse_etf")
        assert config2.short_mode == "inverse_etf"


class TestCoverShort:
    """Tests for cover_short() method (SHORT-04)."""

    def test_cover_short_transitions_to_cash(self, manager):
        """After enter_sell then cover_short, state is CASH."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(950.0, COVER_DATE, "test cover")
        assert manager.position.state == V2MarketState.CASH

    def test_short_pnl_gain_on_market_drop(self, manager):
        """Short at 1000, cover at 950 -> P&L = +5%."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(950.0, COVER_DATE, "market drop")
        trade = manager.trades[-1]
        assert trade["pnl"] == pytest.approx(0.05)

    def test_short_pnl_loss_on_market_rise(self, manager):
        """Short at 1000, cover at 1030 -> P&L = -3%."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(1030.0, COVER_DATE, "market rise")
        trade = manager.trades[-1]
        assert trade["pnl"] == pytest.approx(-0.03)

    def test_cover_short_trade_record(self, manager):
        """cover_short appends trade with correct keys."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(960.0, COVER_DATE, "cover reason")
        trade = manager.trades[-1]
        assert trade["type"] == "SHORT_COVER"
        assert trade["entry_price"] == 1000.0
        assert "pnl" in trade
        assert trade["reason"] == "cover reason"
        assert trade["date"] == COVER_DATE
        assert trade["price"] == 960.0

    def test_cover_short_resets_short_fields(self, manager):
        """After cover_short, short fields are reset."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        manager.cover_short(960.0, COVER_DATE, "cover reason")
        assert manager.position.short_entry_price == 0.0
        assert manager.position.short_entry_date is None


class TestEnterBuyGuard:
    """Tests for enter_buy() SELL state guard (TRANS-01)."""

    def test_enter_buy_guard_raises_from_sell(self, manager):
        """enter_buy() when state==SELL raises ValueError."""
        manager.enter_sell(TEST_DATE, "test", price=1000.0)
        with pytest.raises(ValueError, match="Must cover_short"):
            manager.enter_buy(1010.0, COVER_DATE, 1005.0, "FTD")

    def test_enter_buy_works_from_cash(self, manager):
        """enter_buy() from CASH works normally."""
        manager.enter_buy(1010.0, TEST_DATE, 1005.0, "FTD")
        assert manager.position.state == V2MarketState.BUY
        assert manager.position.buy_price == 1010.0


# ---------------------------------------------------------------------------
# Integration tests: Engine-level short cover triggers (Plan 16-02)
# ---------------------------------------------------------------------------


def _make_ohlcv(n=100, start_date="2020-01-01", seed=42):
    """Create synthetic OHLCV DataFrame for testing."""
    np.random.seed(seed)
    dates = pd.bdate_range(start=start_date, periods=n)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.2
    volume = np.random.randint(1_000_000, 5_000_000, n).astype(float)

    return pd.DataFrame({
        'date': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'symbol': 'TEST',
    })


def _make_declining_then_rising(n_decline=70, n_rise=30, start=100.0):
    """Create OHLCV data: declining phase (triggers SELL via MA50) then rising phase.

    The decline is steep enough to push close below MA50 and trigger SELL.
    The rise pushes close back above MA50 to test cover trigger.
    """
    n = n_decline + n_rise
    dates = pd.bdate_range(start="2020-01-01", periods=n)

    close = np.zeros(n)
    # Decline phase: drop from start by ~0.5 per day
    for i in range(n_decline):
        close[i] = start - i * 0.5

    # Rise phase: sharp rally from bottom
    bottom = close[n_decline - 1]
    for i in range(n_rise):
        close[n_decline + i] = bottom + (i + 1) * 1.5

    high = close + 0.5
    low = close - 0.5
    open_ = close + 0.1
    volume = np.full(n, 3_000_000.0)
    # Rising volume for FTD and MA50 breakout
    volume[n_decline:] = 5_000_000.0

    return pd.DataFrame({
        'date': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'symbol': 'TEST',
    })


class TestEngineShortCoverIntegration:
    """Integration tests for engine-level short cover triggers (Plan 16-02)."""

    def test_engine_enter_sell_passes_close_price(self):
        """Engine SELL_SIGNAL trade should have price > 0 (close on that day)."""
        # Use data that triggers MA50 breakdown: declining prices cross below MA50
        df = _make_declining_then_rising(n_decline=70, n_rise=5)

        config = HybridConfig(
            v2_config=MDMV2Config(ma50_sell_enabled=True),
            filter_enabled=False,
        )
        engine = HybridEngine(config)
        engine.run(df)

        trades = engine.get_trades()
        sell_trades = [t for t in trades if t['type'] == 'SELL_SIGNAL']
        assert len(sell_trades) > 0, "Expected at least one SELL_SIGNAL trade"
        for t in sell_trades:
            assert t['price'] > 0, f"SELL_SIGNAL trade should have price > 0, got {t['price']}"

    def test_engine_ma50_breakout_covers_short(self):
        """MA50 breakout from SELL state should produce SHORT_COVER trade to CASH."""
        df = _make_declining_then_rising(n_decline=70, n_rise=30)

        config = HybridConfig(
            v2_config=MDMV2Config(ma50_sell_enabled=True),
            filter_enabled=False,
        )
        engine = HybridEngine(config)
        engine.run(df)

        trades = engine.get_trades()
        cover_trades = [t for t in trades if t['type'] == 'SHORT_COVER']
        assert len(cover_trades) > 0, "Expected SHORT_COVER trade after MA50 breakout"

        # Check that the cover trade has MA50 in reason and pnl key
        ma50_covers = [t for t in cover_trades if 'MA50' in t.get('reason', '')]
        assert len(ma50_covers) > 0, "Expected SHORT_COVER with MA50 reason"
        assert 'pnl' in ma50_covers[0], "SHORT_COVER should have pnl key"

    def test_engine_indicator_override_covers_short_with_pnl(self):
        """Indicator OVERRIDE from SELL state should produce SHORT_COVER (not STATE_DEGRADE)."""
        df = _make_declining_then_rising(n_decline=70, n_rise=30)

        config = HybridConfig(
            v2_config=MDMV2Config(ma50_sell_enabled=True),
            filter_enabled=True,
        )
        engine = HybridEngine(config)
        engine.run(df)

        trades = engine.get_trades()
        # Look for any STATE_DEGRADE trades that came from SELL state
        degrade_trades = [t for t in trades if t['type'] == 'STATE_DEGRADE'
                          and 'SELL' in t.get('reason', '').upper()]
        assert len(degrade_trades) == 0, (
            f"Found STATE_DEGRADE from SELL state -- should be SHORT_COVER instead: {degrade_trades}"
        )

        # If there are any cover trades from indicator override, verify they have pnl
        indicator_covers = [t for t in trades if t['type'] == 'SHORT_COVER'
                            and ('indicator' in t.get('reason', '').lower()
                                 or 'override' in t.get('reason', '').lower())]
        for t in indicator_covers:
            assert 'pnl' in t, f"SHORT_COVER should have pnl key: {t}"
            assert 'entry_price' in t, f"SHORT_COVER should have entry_price key: {t}"

    def test_sell_cash_buy_transition(self):
        """Engine should produce SELL_SIGNAL -> SHORT_COVER -> BUY sequence (never SELL->BUY direct)."""
        df = _make_declining_then_rising(n_decline=70, n_rise=30)

        config = HybridConfig(
            v2_config=MDMV2Config(ma50_sell_enabled=True),
            filter_enabled=False,
        )
        engine = HybridEngine(config)
        engine.run(df)

        trades = engine.get_trades()
        types = [t['type'] for t in trades]

        # Check no SELL_SIGNAL immediately followed by BUY (must have SHORT_COVER in between)
        for i in range(len(types) - 1):
            if types[i] == 'SELL_SIGNAL':
                assert types[i + 1] != 'BUY', (
                    f"Found SELL_SIGNAL directly followed by BUY at index {i}. "
                    f"Expected SHORT_COVER in between. Trade sequence: {types}"
                )


@pytest.fixture
def nasdaq_data():
    """Load full NASDAQ data from main repo."""
    loader = DataLoader('nasdaq')
    loader.data_dir = MAIN_REPO
    df = loader.load()
    if df is None or df.empty:
        pytest.skip("NASDAQ data not available")
    return df


class TestNasdaqShortValidation:
    """NASDAQ full backtest validation for TRANS-01."""

    def test_nasdaq_no_sell_to_buy(self, nasdaq_data):
        """Every BUY trade in NASDAQ backtest must be preceded by CASH state
        (either previous row state=CASH, or same-day SHORT_COVER before BUY).

        This validates TRANS-01: SELL->CASH->BUY enforcement on real data.
        Same-day cover+buy is allowed since cover_short() transitions to CASH
        before enter_buy() executes (verified via trade log sequence).
        """
        config = HybridConfig(
            v2_config=MDMV2Config(),
            filter_enabled=False,
        )
        engine = HybridEngine(config)
        result = engine.run(nasdaq_data)

        # Verify via trade log: every BUY trade must be preceded by
        # either a CASH_EXIT/STATE_DEGRADE/SHORT_COVER (not another SELL_SIGNAL)
        trades = engine.get_trades()
        trade_types = [t['type'] for t in trades]
        for i, ttype in enumerate(trade_types):
            if ttype == 'BUY' and i > 0:
                prev_type = trade_types[i - 1]
                assert prev_type in ('SHORT_COVER', 'CASH_EXIT', 'STATE_DEGRADE'), (
                    f"Trade {i}: BUY preceded by {prev_type} (expected cover/exit). "
                    f"Date: {trades[i]['date']}"
                )

        # Also verify via state column: where previous row state != current row state
        # and current = BUY, previous must be CASH (same-day SELL->BUY allowed if
        # trade log shows SHORT_COVER before BUY)
        states = result['state'].values
        sell_to_buy_dates = []
        for i in range(1, len(states)):
            if states[i] == 'BUY' and states[i - 1] == 'SELL':
                sell_to_buy_dates.append(result.iloc[i]['date'])

        # For each SELL->BUY in state column, verify trade log has SHORT_COVER on that date
        for dt in sell_to_buy_dates:
            day_trades = [t for t in trades if t['date'] == dt]
            day_types = [t['type'] for t in day_trades]
            assert 'SHORT_COVER' in day_types, (
                f"SELL->BUY on {dt} without SHORT_COVER trade on same day. "
                f"Trades: {day_types}"
            )
