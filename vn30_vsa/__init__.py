# VN30 VSA (Volume Spike Analysis) Strategy Package
"""
Implementation of the Volume Spike Breakout Strategy for VN30 stocks.
Long-only strategy based on volume spike detection and breakout confirmation.
"""

from .data_loader import load_vn30_data, preprocess_stock_data
from .indicators import calculate_mav20, calculate_ma10, calculate_ma50, calculate_volume_ratio
from .signals import detect_volume_spike, detect_buy_signal, detect_distribution_signal
from .position_manager import PositionManager
from .stop_loss import check_fixed_stop_loss, check_spike_low_stop
from .trailing_stop import check_trailing_stop
from .vsa_engine import VSAEngine
from .performance import calculate_performance_metrics
from .kelly import calculate_rolling_kelly, get_kelly_phase

__all__ = [
    'load_vn30_data',
    'preprocess_stock_data', 
    'calculate_mav20',
    'calculate_ma10',
    'calculate_ma50',
    'calculate_volume_ratio',
    'detect_volume_spike',
    'detect_buy_signal',
    'detect_distribution_signal',
    'PositionManager',
    'check_fixed_stop_loss',
    'check_spike_low_stop',
    'check_trailing_stop',
    'VSAEngine',
    'calculate_performance_metrics',
    'calculate_rolling_kelly',
    'get_kelly_phase',
]

