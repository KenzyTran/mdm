"""
MDM Configuration Module
"""

from dataclasses import dataclass

@dataclass
class MDMConfig:
    """Configuration parameters for MDM strategy."""
    
    # Rally Attempt Parameters
    correction_threshold: float = -0.10  # -10% from recent peak
    
    # FTD Parameters
    ftd_min_rally_day: int = 3
    ftd_max_rally_day: int = 12  # Slightly wider window than strict 4-11
    ftd_min_price_gain: float = 0.01  # 1%
    ma50_breakout_correction: float = -0.06  # 6%
    
    # Stop Loss Parameters
    stop_loss_pct: float = 0.025  # 2.5%
    
    # Distribution Day Parameters
    dd_window_size: int = 20
    dd_price_drop_threshold: float = -0.002  # -0.2%
    dd_price_stall_threshold: float = 0.001  # 0.1%
    dd_stall_p_loc_threshold: float = 0.2
    
    def __post_init__(self):
        """Validate parameters."""
        assert self.correction_threshold < 0, "Correction threshold must be negative"
        assert self.stop_loss_pct > 0, "Stop loss percentage must be positive"
