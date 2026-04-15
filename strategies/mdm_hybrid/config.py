"""
MDM Hybrid Configuration Module

Parameterized configuration for the hybrid engine composing v2 state machine
config with two-phase commit flags and indicator filter configuration.

Phase 11: two_phase_enabled + filter_enabled only.
Phase 12: Added FilterConfig composition for indicator filter layer.
"""

from dataclasses import dataclass, field

from .indicator_filter import FilterConfig


@dataclass
class MDMV2Config:
    """Configuration parameters for MDM v2 strategy.

    Extends classic MDMConfig with Cash and Sell trigger parameters
    for the 3-state machine (BUY/CASH/SELL).
    """

    # Rally / FTD parameters (from classic)
    correction_threshold: float = -0.10
    ftd_min_rally_day: int = 3
    ftd_max_rally_day: int = 12
    ftd_min_price_gain: float = 0.01
    ma50_breakout_correction: float = -0.06

    # Distribution Day parameters
    dd_window_size: int = 20
    dd_price_drop_threshold: float = -0.002
    dd_price_stall_threshold: float = 0.001
    dd_stall_p_loc_threshold: float = 0.2

    # Cash trigger parameters (NEW in v2, per D-01)
    dd_cash_threshold: int = 5          # DD count triggers Buy->Cash
    ma10_cash_enabled: bool = True      # close<MA10 as Cash trigger
    ma10_cash_consecutive: int = 2      # Consecutive days below MA10

    # Sell trigger parameters (NEW in v2, per D-02)
    ma50_sell_enabled: bool = True      # MA50 breakdown triggers Cash->Sell
    cash_deterioration_days: int = 10   # Days in Cash before auto-Sell

    # Stop Loss
    stop_loss_pct: float = 0.015

    # Short stop loss (Phase 17, RISK-03/SHORT-03)
    short_stop_pct_above_dd5: float = 0.01  # Cover short when close > DD5 high * (1 + pct)

    # ATR / Volatility-adaptive stop loss (Phase 17, RISK-02)
    atr_period: int = 14
    atr_baseline_period: int = 50
    volatility_adaptive: bool = True
    stop_loss_min_multiplier: float = 0.5
    stop_loss_max_multiplier: float = 2.5

    # Fail-Safe Mechanism (SAFE-01, SAFE-02)
    fail_safe_enabled: bool = True        # Auto-exit SELL when close > standby-sell HIGH

    # ATR Buffer Zone (Phase 38, ATR-01/ATR-03)
    atr_buffer_enabled: bool = False          # Feature gate: off = v6.0 behavior (ATR-04)
    atr_buffer_k: float = 0.5                 # Multiplier: violation_threshold = MA50 - k * ATR_N
    atr_buffer_period: int = 14               # ATR lookback period (separate from atr_period for stop-loss)
    atr_buffer_consecutive_days: int = 2      # m-day consecutive close < violation_threshold required

    # Hypothesis metadata (per D-08)
    name: str = "default"

    def __post_init__(self):
        """Validate parameters."""
        assert self.correction_threshold < 0, "Correction threshold must be negative"
        assert self.stop_loss_pct > 0, "Stop loss percentage must be positive"
        assert self.dd_cash_threshold > 0, "DD cash threshold must be positive"
        assert self.atr_buffer_k > 0, "atr_buffer_k must be positive"
        assert self.atr_buffer_period > 0, "atr_buffer_period must be positive"
        assert self.atr_buffer_consecutive_days >= 1, "atr_buffer_consecutive_days must be >= 1"


# Compatibility alias: copied modules (distribution_day, rally_attempt, ftd_signal)
# import MDMConfig from .config -- this alias lets them work unchanged.
MDMConfig = MDMV2Config


@dataclass
class HybridConfig:
    """Hybrid MDM engine configuration.

    Composes v2 state machine config with hybrid control flags and
    indicator filter configuration.

    Phase 11: two_phase_enabled + filter_enabled only.
    Phase 12: Added filter_config for indicator filter layer.
    """
    v2_config: MDMV2Config = field(default_factory=MDMV2Config)
    two_phase_enabled: bool = True   # per D-05: defaults True
    filter_enabled: bool = False     # per D-07: Phase 11 has no filter
    filter_config: FilterConfig = field(default_factory=FilterConfig)
    short_mode: str = 'direct'  # 'direct' (VN30) or 'inverse_etf' (NASDAQ) per D-10

    def __post_init__(self):
        if isinstance(self.v2_config, dict):
            self.v2_config = MDMV2Config(**self.v2_config)
        if isinstance(self.filter_config, dict):
            self.filter_config = FilterConfig(**self.filter_config)


# ── Market-specific presets ──────────────────────────────────────────

VN30_PRESET = MDMV2Config(
    correction_threshold=-0.06,
    ftd_min_rally_day=3,
    ftd_max_rally_day=12,
    ftd_min_price_gain=0.01,
    ma50_breakout_correction=-0.06,
    dd_window_size=20,
    dd_price_drop_threshold=-0.002,
    dd_price_stall_threshold=0.001,
    dd_stall_p_loc_threshold=0.2,
    dd_cash_threshold=5,
    ma10_cash_enabled=True,
    ma10_cash_consecutive=3,
    ma50_sell_enabled=True,
    cash_deterioration_days=20,
    stop_loss_pct=0.015,
    short_stop_pct_above_dd5=0.01,
    atr_period=14,
    atr_baseline_period=50,
    volatility_adaptive=True,
    stop_loss_min_multiplier=0.5,
    stop_loss_max_multiplier=2.5,
    fail_safe_enabled=True,
    atr_buffer_enabled=False,
    atr_buffer_k=0.5,
    atr_buffer_period=14,
    atr_buffer_consecutive_days=2,
    name="vn30",
)

NASDAQ_PRESET = MDMV2Config(
    correction_threshold=-0.10,
    ftd_min_rally_day=3,
    ftd_max_rally_day=12,
    ftd_min_price_gain=0.01,
    ma50_breakout_correction=-0.06,
    dd_window_size=20,
    dd_price_drop_threshold=-0.002,
    dd_price_stall_threshold=0.001,
    dd_stall_p_loc_threshold=0.2,
    dd_cash_threshold=5,
    ma10_cash_enabled=True,
    ma10_cash_consecutive=2,
    ma50_sell_enabled=True,
    cash_deterioration_days=10,
    stop_loss_pct=0.015,
    short_stop_pct_above_dd5=0.01,
    atr_period=14,
    atr_baseline_period=50,
    volatility_adaptive=True,
    stop_loss_min_multiplier=0.5,
    stop_loss_max_multiplier=2.5,
    fail_safe_enabled=True,
    atr_buffer_enabled=False,
    atr_buffer_k=0.5,
    atr_buffer_period=14,
    atr_buffer_consecutive_days=2,
    name="nasdaq",
)
