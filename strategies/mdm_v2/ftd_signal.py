"""
Follow-Through Day (FTD) Signal Detector Module
Detect buy signals based on FTD rules.
"""

import pandas as pd
from typing import Optional, Tuple
from dataclasses import dataclass

from .config import MDMConfig


@dataclass
class FTDSignal:
    """Information about a Follow-Through Day signal."""
    date: pd.Timestamp
    price: float  # Buy price (close of FTD)
    rally_day: int  # Which day of the rally
    signal_type: str = "FTD"  # Type of signal: FTD, MA50, 52WEEK


class FTDSignalDetector:
    """
    Detect Follow-Through Day (FTD) buy signals.
    
    Rules:
    - Occurs between Day 4 and Day 11 of rally attempt
    - Price up >= 1%: C >= C_prev * 1.01
    - Volume up: V > V_prev
    """
    
    def __init__(self, config: MDMConfig = None):
        """Initialize the detector."""
        self.config = config if config else MDMConfig()
        self.last_signal: Optional[FTDSignal] = None
    
    def check_ftd(
        self,
        rally_day_count: int,
        price_change_pct: float,
        volume_up: bool,
        date: pd.Timestamp,
        close: float
    ) -> Tuple[bool, Optional[FTDSignal]]:
        """
        Check if current day is a Follow-Through Day.
        
        Args:
            rally_day_count: Current day number in rally attempt
            price_change_pct: Price change percentage
            volume_up: Whether volume increased
            date: Current date
            close: Close price
            
        Returns:
            Tuple of (is_ftd, signal)
        """
        # Check rally day range
        if not (self.config.ftd_min_rally_day <= rally_day_count <= self.config.ftd_max_rally_day):
            return False, None
        
        # Check price gain
        if price_change_pct < self.config.ftd_min_price_gain:
            return False, None
        
        # Check volume
        if not volume_up:
            return False, None
        
        # All conditions met - FTD detected!
        signal = FTDSignal(
            date=date,
            price=close,
            rally_day=rally_day_count,
            signal_type="FTD"
        )
        self.last_signal = signal
        
        return True, signal
    
    def get_last_signal(self) -> Optional[FTDSignal]:
        """Get the last FTD signal."""
        return self.last_signal
    
    def reset(self):
        """Reset the detector."""
        self.last_signal = None
    
    def check_ma50_breakout(
        self,
        close: float,
        prev_close: float,
        ma50: float,
        prev_ma50: float,
        volume_up: bool,
        drawdown_pct: float,
        date: pd.Timestamp
    ) -> Tuple[bool, Optional[FTDSignal]]:
        """
        Check if price breaks above MA50 after a correction.
        
        Rules:
        - Correction >= 6% from peak
        - Close above MA50 (C > MA50)
        - Previous close was below or at MA50 (cross above)
        - Volume higher than previous session
        
        Args:
            close: Current close price
            prev_close: Previous close price
            ma50: Current 50-day MA
            prev_ma50: Previous 50-day MA
            volume_up: Whether volume increased
            drawdown_pct: Current drawdown from peak (negative value)
            date: Current date
            
        Returns:
            Tuple of (is_breakout, signal)
        """
        # Check correction depth
        if drawdown_pct > self.config.ma50_breakout_correction:
            return False, None
        
        # Check if crossing above MA50 (prev below or at, now above)
        if not (prev_close <= prev_ma50 and close > ma50):
            return False, None
        
        # Check volume
        if not volume_up:
            return False, None
        
        # All conditions met - MA50 breakout signal!
        signal = FTDSignal(
            date=date,
            price=close,
            rally_day=0,  # Not from rally attempt
            signal_type="MA50"
        )
        self.last_signal = signal
        
        return True, signal

    def check_200dma_breakout(
        self,
        close: float,
        prev_close: float,
        sma200: float,
        prev_sma200: float,
        volume_up: bool,
        drawdown_pct: float,
        date: pd.Timestamp
    ) -> Tuple[bool, Optional[FTDSignal]]:
        """Check if price breaks above 200dma after a correction.

        Per D-03: 200dma crossover replaces MA50 breakout in Scenario 5.
        Same conditions as MA50 breakout but using 200-day SMA.

        Args:
            close: Current close price
            prev_close: Previous close price
            sma200: Current 200-day SMA
            prev_sma200: Previous 200-day SMA
            volume_up: Whether volume increased
            drawdown_pct: Current drawdown from peak (negative value)
            date: Current date

        Returns:
            Tuple of (is_breakout, signal)
        """
        # Check correction depth (reuse ma50_breakout_correction threshold)
        if drawdown_pct > self.config.ma50_breakout_correction:
            return False, None

        # Check if crossing above 200dma (prev below or at, now above)
        if not (prev_close <= prev_sma200 and close > sma200):
            return False, None

        # Check volume
        if not volume_up:
            return False, None

        # All conditions met - 200dma breakout signal
        signal = FTDSignal(
            date=date,
            price=close,
            rally_day=0,
            signal_type="200DMA"
        )
        self.last_signal = signal
        return True, signal

    def check_52week_breakout(
        self,
        close: float,
        high_52w: float,
        date: pd.Timestamp
    ) -> Tuple[bool, Optional[FTDSignal]]:
        """
        Check if price breaks out 52-week high.
        
        Rules:
        - Close > 52-week high
        
        Args:
            close: Current close price
            high_52w: Previous 52-week high
            date: Current date
            
        Returns:
            Tuple of (is_breakout, signal)
        """
        if high_52w is None or pd.isna(high_52w):
            return False, None
            
        if close > high_52w:
            signal = FTDSignal(
                date=date,
                price=close,
                rally_day=0,
                signal_type="52WEEK"
            )
            self.last_signal = signal
            return True, signal
            
        return False, None
