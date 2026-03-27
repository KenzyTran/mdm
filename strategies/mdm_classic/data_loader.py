"""
Data Loader Module
Load and preprocess VNINDEX data from CSV file.
"""

import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    """Load and preprocess VNINDEX price data."""
    
    # Column mapping from CSV to standard names
    COLUMN_MAPPING = {
        'stockcode': 'symbol',
        'tradingdate': 'date',
        'openindex': 'open',
        'closeindex': 'close',
        'lowestindex': 'low',
        'highestindex': 'high',
        'totalvol': 'volume'
    }
    
    def __init__(self, file_path: str = 'vnindex_price.csv'):
        """
        Initialize DataLoader.
        
        Args:
            file_path: Path to the CSV file
        """
        self.file_path = Path(file_path)
        self.data: Optional[pd.DataFrame] = None
    
    def load(self, start_date: str = '2016-01-16', end_date: str = '2026-01-16') -> pd.DataFrame:
        """
        Load and preprocess data from CSV.
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            
        Returns:
            Preprocessed DataFrame with OHLCV data
        """
        # Read CSV
        df = pd.read_csv(self.file_path)
        
        # Rename columns
        df = df.rename(columns=self.COLUMN_MAPPING)
        
        # Parse date column (handles both simple 'YYYY-MM-DD' and ISO format like '2024-08-09T00:00:00.000Z')
        # Strip extra quotes if present
        df['date'] = df['date'].str.strip('"')
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        df['date'] = df['date'].dt.normalize()
        
        # Filter by date range
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        # Sort by date ascending
        df = df.sort_values('date').reset_index(drop=True)
        
        # Ensure numeric types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with missing values
        df = df.dropna(subset=numeric_cols)
        
        # Store data
        self.data = df
        
        return df
    
    def get_data(self) -> Optional[pd.DataFrame]:
        """Get loaded data."""
        return self.data
    
    def info(self) -> dict:
        """
        Get information about loaded data.
        
        Returns:
            Dictionary with data statistics
        """
        if self.data is None:
            return {'status': 'No data loaded'}
        
        return {
            'total_rows': len(self.data),
            'start_date': self.data['date'].min(),
            'end_date': self.data['date'].max(),
            'columns': list(self.data.columns),
            'price_range': {
                'min': self.data['close'].min(),
                'max': self.data['close'].max()
            }
        }
