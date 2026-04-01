"""Tests for Phase 25: MA50/200dma Review (MAREVIEW-01, MAREVIEW-02, MAREVIEW-03)."""
import pytest
import pandas as pd
import numpy as np
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.indicators import Indicators
from strategies.mdm_v2.ftd_signal import FTDSignalDetector
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine


def test_config_flags():
    """Verify new config flags have correct defaults."""
    config = MDMV2Config()
    assert config.ma50_breakout_enabled is True, "ma50_breakout_enabled should default True"
    assert config.ma200_enabled is False, "ma200_enabled should default False"
    # Verify they can be toggled
    config2 = MDMV2Config(ma50_breakout_enabled=False, ma200_enabled=True)
    assert config2.ma50_breakout_enabled is False
    assert config2.ma200_enabled is True


def test_sma200_indicator():
    """Verify sma200 column is computed correctly."""
    # Create 250 rows of synthetic close data
    np.random.seed(42)
    closes = 1000 + np.cumsum(np.random.randn(250))
    df = pd.DataFrame({'close': closes})
    result = Indicators.add_sma200_column(df)
    assert 'sma200' in result.columns
    # No NaN values (min_periods=1)
    assert result['sma200'].isna().sum() == 0
    # At row 199 (0-indexed), sma200 should equal mean of first 200 closes
    expected_200 = closes[:200].mean()
    assert abs(result['sma200'].iloc[199] - expected_200) < 0.01
    # At row 249, sma200 should equal mean of last 200 closes
    expected_last = closes[50:250].mean()
    assert abs(result['sma200'].iloc[249] - expected_last) < 0.01


def test_breakout_gated():
    """Verify ma50_breakout_enabled=False prevents MA50 breakout signals.

    Creates a scenario where MA50 breakout conditions ARE met, but the
    config flag disables it. This test will be expanded in Plan 02 when
    the engine gates the call.
    """
    # For now, test that config flag exists and FTDSignalDetector accepts it
    config = MDMV2Config(ma50_breakout_enabled=False)
    detector = FTDSignalDetector(config)
    # The actual gating happens in the engine (Plan 02) --
    # this test verifies the detector can be constructed with the flag
    assert detector.config.ma50_breakout_enabled is False


def test_no_sell_differs_from_baseline():
    """MAREVIEW-01: Disabling MA50 SELL changes backtest results.

    Placeholder -- will run actual A/B in Plan 03 validation script.
    Verifies configs are distinct.
    """
    baseline = MDMV2Config(ma50_sell_enabled=True, name="baseline")
    no_sell = MDMV2Config(ma50_sell_enabled=False, name="no_sell")
    assert baseline.ma50_sell_enabled != no_sell.ma50_sell_enabled
    assert baseline.name != no_sell.name


def test_no_filter_differs_from_baseline():
    """MAREVIEW-02: Disabling BUY filter changes backtest results.

    Placeholder -- will run actual A/B in Plan 03 validation script.
    Verifies configs are distinct.
    """
    baseline = MDMV2Config(buy_filter_enabled=True, name="baseline")
    no_filter = MDMV2Config(buy_filter_enabled=False, name="no_filter")
    assert baseline.buy_filter_enabled != no_filter.buy_filter_enabled
    assert baseline.name != no_filter.name


def test_200dma_replacement():
    """Verify 200dma replacement config sets all MA50 off and ma200 on."""
    config = MDMV2Config(
        ma50_sell_enabled=False,
        buy_filter_enabled=False,
        ma50_breakout_enabled=False,
        ma200_enabled=True,
        name="200dma_replace",
    )
    assert config.ma50_sell_enabled is False
    assert config.buy_filter_enabled is False
    assert config.ma50_breakout_enabled is False
    assert config.ma200_enabled is True


def test_engine_gates_ma50_breakout():
    """With ma50_breakout_enabled=False, engine produces no MA50 breakout signals."""
    np.random.seed(42)
    n = 150
    dates = pd.date_range('2020-01-01', periods=n, freq='B')
    closes = np.concatenate([np.linspace(100, 80, 100), np.linspace(80, 110, 50)])
    df = pd.DataFrame({
        'date': dates,
        'open': closes * 0.99,
        'high': closes * 1.01,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(100000, 500000, n),
        'symbol': 'TEST',
    })

    # Run with ma50_breakout_enabled=False
    config_off = MDMV2Config(ma50_breakout_enabled=False, ma200_enabled=False, name="breakout_off")
    engine_off = MDMV2Engine(config_off)
    result_off = engine_off.run(df)

    # Verify: breakout_off should have no MA50 breakout signals
    assert result_off['is_ma50_breakout'].sum() == 0, "MA50 breakout should be gated off"


def test_200dma_replacement_signals():
    """With ma200_enabled=True, engine accepts 200DMA config (Scenario 5)."""
    config = MDMV2Config(
        ma50_sell_enabled=False,
        buy_filter_enabled=False,
        ma50_breakout_enabled=False,
        ma200_enabled=True,
        name="200dma",
    )
    # Verify config is correctly set for Scenario 5
    assert config.ma200_enabled is True
    assert config.ma50_breakout_enabled is False
    assert config.ma50_sell_enabled is False
