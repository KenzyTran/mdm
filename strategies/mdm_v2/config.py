"""
MDM V2 Configuration Module

Parameterized configuration for the v2 engine with Cash/Sell trigger
thresholds (per D-01, D-02, D-06) and hypothesis metadata (per D-08).
"""

from dataclasses import dataclass


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

    # Global Liquidity / QE Floor (v5.0, LIQ-03)
    qe_floor_enabled: bool = False              # Master switch, default OFF
    publication_lag_days: int = 7                # Days to offset liquidity data
    liquidity_csv_path: str = "data/global_liquidity.csv"

    # SELL Acceleration (v5.0, SELL-01)
    sell_acceleration_enabled: bool = True     # Master switch (per D-09)
    roc_threshold: float = -0.04              # ROC must be below -4% (10-day)
    roc_window: int = 10                      # 10-day lookback for ROC
    dd_cluster_count: int = 3                 # 3 DDs required for clustering
    dd_cluster_window: int = 5               # within 5 trading sessions

    # BUY Selectivity (v5.0, BUY-01, BUY-02)
    buy_filter_enabled: bool = True           # MA10 < MA50 rejection (D-12)
    buy_confirmation_enabled: bool = True     # Post-FTD confirmation (D-12)
    confirmation_window_days: int = 3         # Days to confirm (D-03, D-12)
    confirmation_max_dd: int = 1              # Max DD allowed in window (D-04, D-12)

    # Fail-Safe Mechanism (v6.0, SAFE-01, SAFE-02)
    fail_safe_enabled: bool = True        # Auto-exit SELL when close > standby-sell HIGH

    # Buy Entry Refinement (v6.0, GAP-01, RALLY-01)
    gap_filter_enabled: bool = True           # Reject FTD when gap-up broken (low < prev_close)
    rally_threshold_enabled: bool = True      # Allow early FTD in shallow pullbacks
    rally_threshold_pct: float = -0.06        # Threshold: decline < 6% = shallow

    # MA50/200dma Review (v6.0, MAREVIEW-01, MAREVIEW-02)
    ma50_breakout_enabled: bool = True    # Gate MA50 breakout buy signal (True = existing behavior)
    ma200_enabled: bool = False           # 200dma replacement mode (False = off per v5.0 convention)

    # Hypothesis metadata (per D-08)
    name: str = "default"

    def __post_init__(self):
        """Validate parameters."""
        assert self.correction_threshold < 0, "Correction threshold must be negative"
        assert self.stop_loss_pct > 0, "Stop loss percentage must be positive"
        assert self.dd_cash_threshold > 0, "DD cash threshold must be positive"
        assert self.publication_lag_days >= 0, "Publication lag must be non-negative"
        assert self.roc_threshold < 0, "ROC threshold must be negative"
        assert self.roc_window > 0, "ROC window must be positive"
        assert self.dd_cluster_count > 0, "DD cluster count must be positive"
        assert self.dd_cluster_window > 0, "DD cluster window must be positive"
        assert self.confirmation_window_days > 0, "Confirmation window must be positive"
        assert self.confirmation_max_dd >= 0, "Confirmation max DD must be non-negative"
        assert self.rally_threshold_pct < 0, "Rally threshold must be negative"


# Compatibility alias: copied modules (distribution_day, rally_attempt, ftd_signal)
# import MDMConfig from .config -- this alias lets them work unchanged.
MDMConfig = MDMV2Config
