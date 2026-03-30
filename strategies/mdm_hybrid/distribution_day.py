"""
Distribution Day Module
Detect and count distribution days.
"""

import pandas as pd
from typing import Tuple

from .config import MDMConfig


class DistributionDayCounter:
    """
    Count Distribution Days within a rolling window.
    
    Distribution Day Types:
    - Type 1 (Heavy Selling): Price down >= 0.2% with higher volume
    - Type 2 (Stalling): Price up < 0.1% with higher volume, close in lower 25%
    """
    
    def __init__(self, config: MDMConfig = None):
        """Initialize the counter."""
        self.config = config if config else MDMConfig()
        self.dd_history = []  # List of (date, high) tuples for distribution days
        self.dd5_high = 0.0  # High of the day when DD count reaches 5

    def reset(self):
        """Reset the distribution day counter (called after FTD signal)."""
        self.dd_history = []
        self.dd5_high = 0.0
    
    def is_distribution_day_type1(
        self, 
        price_change_pct: float, 
        volume_up: bool
    ) -> bool:
        """
        Check if it's a Type 1 Distribution Day (Heavy Selling).
        
        Args:
            price_change_pct: Price change percentage
            volume_up: Whether volume increased
            
        Returns:
            True if Type 1 DD
        """
        return (price_change_pct <= self.config.dd_price_drop_threshold) and volume_up
    
    def is_distribution_day_type2(
        self, 
        price_change_pct: float, 
        volume_up: bool,
        p_loc: float
    ) -> bool:
        """
        Check if it's a Type 2 Distribution Day (Stalling).
        
        Args:
            price_change_pct: Price change percentage
            volume_up: Whether volume increased
            p_loc: Price location
            
        Returns:
            True if Type 2 DD
        """
        # Price stall: 0 <= change < threshold
        price_stall = 0 <= price_change_pct < self.config.dd_price_stall_threshold
        low_close = p_loc <= self.config.dd_stall_p_loc_threshold
        return price_stall and volume_up and low_close
    
    def check_distribution_day(
        self,
        date,
        high: float,
        price_change_pct: float,
        volume_up: bool,
        p_loc: float
    ) -> Tuple[bool, int]:
        """
        Check if current day is a distribution day and update count.

        Args:
            date: Current date
            high: Current day's high price (for DD5 tracking)
            price_change_pct: Price change percentage
            volume_up: Whether volume increased
            p_loc: Price location

        Returns:
            Tuple of (is_dd, dd_type) where dd_type is 0, 1, or 2
        """
        is_type1 = self.is_distribution_day_type1(price_change_pct, volume_up)
        is_type2 = self.is_distribution_day_type2(price_change_pct, volume_up, p_loc)

        if is_type1 or is_type2:
            self.dd_history.append((date, high))
            dd_type = 1 if is_type1 else 2
            return True, dd_type

        return False, 0
    
    def get_dd_count_in_window(self, current_date, all_dates: list) -> int:
        """
        Get count of distribution days in the last 20 trading sessions.
        
        Args:
            current_date: Current date
            all_dates: List of all trading dates
            
        Returns:
            Count of distribution days in window
        """
        # Find position of current date
        try:
            current_idx = all_dates.index(current_date)
        except ValueError:
            return 0
        
        # Get dates in window
        window_start_idx = max(0, current_idx - self.config.dd_window_size + 1)
        window_dates = set(all_dates[window_start_idx:current_idx + 1])
        
        # Count DD in window (dd_history stores (date, high) tuples)
        count = sum(1 for d, h in self.dd_history if d in window_dates)
        return count

    def get_dd5_high(self, current_date, all_dates: list) -> float:
        """Get the high of the day when DD count reached 5 in the rolling window.

        Per rules_mdm_classic.md section IV.4: "Gia cao nhat ngay DD5"
        This is the HIGH of the specific day when dd_count == 5,
        NOT the maximum high across all 5 DD days.

        Args:
            current_date: Current trading date.
            all_dates: List of all trading dates.

        Returns:
            High price of the 5th DD day, or 0.0 if fewer than 5 DDs in window.
        """
        try:
            current_idx = all_dates.index(current_date)
        except ValueError:
            return 0.0
        window_start_idx = max(0, current_idx - self.config.dd_window_size + 1)
        window_dates = set(all_dates[window_start_idx:current_idx + 1])
        dd_in_window = [(d, h) for d, h in self.dd_history if d in window_dates]
        if len(dd_in_window) >= 5:
            self.dd5_high = dd_in_window[4][1]  # High of the 5th DD
            return self.dd5_high
        return 0.0
    
    def add_dd_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add distribution day columns to DataFrame.
        
        Args:
            df: DataFrame with required columns
            
        Returns:
            DataFrame with DD columns added
        """
        df = df.copy()
        
        dd_results = []
        dd_counts = []
        all_dates = df['date'].tolist()
        
        for idx, row in df.iterrows():
            is_dd, dd_type = self.check_distribution_day(
                row['date'],
                row.get('high', 0.0),  # Pass high for DD5 tracking
                row.get('price_change_pct', 0),
                row.get('volume_up', False),
                row.get('p_loc', 0.5)
            )
            dd_results.append(dd_type)
            dd_counts.append(self.get_dd_count_in_window(row['date'], all_dates))
        
        df['dd_type'] = dd_results
        df['is_dd'] = df['dd_type'] > 0
        df['dd_count_20d'] = dd_counts
        
        return df
