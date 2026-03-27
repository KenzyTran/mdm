# Configuration for VSA Strategy

# Volume Spike Configuration
VOLUME_SPIKE_MULTIPLIER = 4.0  # V >= 4x MAV20
LOOKBACK_DAYS = 5  # Lookback window for spike detection

# Portfolio Configuration
MAX_POSITIONS = 5  # Maximum number of stocks to hold
POSITION_WEIGHT = 0.12  # 15% NAV per position (default for first 20 trades)
INITIAL_NAV = 1_000_000_000  # 1 billion VND

# Kelly Criterion Configuration (Rolling Kelly)
KELLY_MIN_TRADES_PHASE1 = 20    # Fixed 15% for first 20 trades
KELLY_MIN_TRADES_PHASE2 = 50    # Use 20-trade window for trades 21-50
KELLY_WINDOW_SMALL = 20         # Rolling window for phase 2
KELLY_WINDOW_LARGE = 50         # Rolling window for phase 3 (51+)
KELLY_FRACTION = 1            # Half Kelly for safety
KELLY_MIN_WEIGHT = 0.05         # 5% minimum position weight
KELLY_MAX_WEIGHT = 0.25         # 25% maximum position weight

# Stop Loss Configuration
FIXED_STOP_LOSS_PCT = 0.07  # 7% stop loss
TAKE_PROFIT_PCT = 0.23  # 20% take profit (sell 50%)

# Trailing Stop Configuration
MA10_WEEKS_THRESHOLD = 7  # Weeks to use MA10 before switching to MA50
MA10_WEEKS_IN_DAYS = 35  # 7 weeks * 5 trading days

# Order Type
ORDER_TYPE = "CLOSE"  # Market on Close

