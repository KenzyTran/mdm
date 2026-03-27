"""
Rally Attempt Tracker Module
Detect correction phases and count rally attempt days.
"""

import pandas as pd
from typing import Optional, Tuple
from dataclasses import dataclass

from .config import MDMConfig


@dataclass
class Day1Info:
    """Information about Day 1 of a rally attempt."""
    date: pd.Timestamp
    low: float  # Low of Day 1 - used for reset rule
    close: float


class RallyAttemptTracker:
    """
    Track rally attempts during correction phases.
    
    Rules:
    - Correction phase: Index drops >= 12% from recent peak
    - Day 1: First day with C > C_prev OR (new low but P_loc > 0.5)
    - Reset: If price breaks below Day 1 low, reset count
    """
    
    def __init__(self, config: MDMConfig = None):
        """Initialize the tracker."""
        self.config = config if config else MDMConfig()
        
        self.in_correction = False
        self.day1_info: Optional[Day1Info] = None
        self.rally_day_count = 0
        self.peak_high = 0.0
        
    def reset(self):
        """Reset rally attempt tracking."""
        self.day1_info = None
        self.rally_day_count = 0
        # Note: Keep in_correction and peak_high
    
    def full_reset(self):
        """Full reset including correction state."""
        self.in_correction = False
        self.day1_info = None
        self.rally_day_count = 0
        self.peak_high = 0.0
    
    def update_peak(self, high: float):
        """Update peak high if new high."""
        if high > self.peak_high:
            self.peak_high = high
            # Reset correction when new high is made
            self.in_correction = False
            self.reset()
    
    def check_correction(self, close: float) -> bool:
        """
        Check if market is in correction phase.
        
        Condition: Close drops >= 12% from peak
        
        Args:
            close: Current close price
            
        Returns:
            True if in correction phase
        """
        if self.peak_high == 0:
            return False
        
        drawdown = (close - self.peak_high) / self.peak_high
        
        if drawdown <= self.config.correction_threshold:
            self.in_correction = True
        
        return self.in_correction
    
    def is_day1_candidate(
        self, 
        close: float, 
        prev_close: float, 
        p_loc: float,
        low: float
    ) -> bool:
        """
        Check if current day qualifies as Day 1 of rally attempt.
        
        Conditions (one of):
        - Close > previous close
        - OR: Close at upper half (P_loc > 0.5) even if new low
        
        Args:
            close: Current close price
            prev_close: Previous close price
            p_loc: Price location
            low: Current low price
            
        Returns:
            True if qualifies as Day 1
        """
        # Condition 1: Price closes higher
        if close > prev_close:
            return True
        
        # Condition 2: Close in upper half even on down day
        if p_loc > 0.5:
            return True
        
        return False
    
    def process_day(
        self,
        date: pd.Timestamp,
        high: float,
        low: float,
        close: float,
        prev_close: float,
        p_loc: float
    ) -> Tuple[bool, int, bool]:
        """
        Process a trading day for rally tracking.
        
        Args:
            date: Current date
            high: Current high
            low: Current low
            close: Current close
            prev_close: Previous close
            p_loc: Price location
            
        Returns:
            Tuple of (in_correction, rally_day_count, is_day1)
        """
        # Update peak
        self.update_peak(high)
        
        # Check correction
        in_correction = self.check_correction(close)
        is_day1 = False
        
        if not in_correction:
            # Not in correction - no rally attempt tracking needed
            self.reset()
            return False, 0, False
        
        # In correction phase
        if self.day1_info is None:
            # Looking for Day 1
            if self.is_day1_candidate(close, prev_close, p_loc, low):
                # Found Day 1!
                self.day1_info = Day1Info(date=date, low=low, close=close)
                self.rally_day_count = 1
                is_day1 = True
        else:
            # Already have Day 1, check for reset
            if low < self.day1_info.low:
                # Price broke below Day 1 low - reset and check for new Day 1
                self.reset()
                
                # Check if today qualifies as new Day 1
                if self.is_day1_candidate(close, prev_close, p_loc, low):
                    self.day1_info = Day1Info(date=date, low=low, close=close)
                    self.rally_day_count = 1
                    is_day1 = True
            else:
                # Continue counting rally days
                self.rally_day_count += 1
        
        return in_correction, self.rally_day_count, is_day1
    
    def get_rally_day_count(self) -> int:
        """Get current rally day count."""
        return self.rally_day_count
    
    def get_day1_info(self) -> Optional[Day1Info]:
        """Get Day 1 information."""
        return self.day1_info
