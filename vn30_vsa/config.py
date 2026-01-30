# Configuration for VSA Strategy

# Volume Spike Configuration
VOLUME_SPIKE_MULTIPLIER = 4.0  # V >= 4x MAV20
LOOKBACK_DAYS = 5  # Lookback window for spike detection

# Portfolio Configuration
MAX_POSITIONS = 5  # Maximum number of stocks to hold
POSITION_WEIGHT = 0.20  # 20% NAV per position
INITIAL_NAV = 1_000_000_000  # 1 billion VND

# Stop Loss Configuration
FIXED_STOP_LOSS_PCT = 0.07  # 7% stop loss
TAKE_PROFIT_PCT = 0.20  # 20% take profit (sell 50%)

# Trailing Stop Configuration
MA10_WEEKS_THRESHOLD = 7  # Weeks to use MA10 before switching to MA50
MA10_WEEKS_IN_DAYS = 35  # 7 weeks * 5 trading days

# Order Type
ORDER_TYPE = "CLOSE"  # Market on Close
