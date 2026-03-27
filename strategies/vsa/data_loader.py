"""
Data Loader Module for VN30 Stocks
Handles loading and preprocessing of VN30_STOCKS_PRICE.csv
"""

import pandas as pd
from pathlib import Path


def load_vn30_data(filepath: str = None) -> pd.DataFrame:
    """
    Load VN30 stocks price data from CSV file.
    
    Args:
        filepath: Path to the CSV file. If None, uses default path.
        
    Returns:
        DataFrame with columns: stockcode, tradingdate, openprice, closeprice, 
                               highestprice, lowestprice, totalvol
    """
    if filepath is None:
        # Default path relative to project root
        filepath = Path(__file__).parent.parent / "VN30_STOCKS_PRICE.csv"
    
    df = pd.read_csv(filepath)
    
    # Rename columns for consistency
    df.columns = df.columns.str.lower().str.strip()
    
    # Convert tradingdate to datetime
    df['tradingdate'] = pd.to_datetime(df['tradingdate'])
    
    # Convert price and volume columns to float
    numeric_cols = ['openprice', 'closeprice', 'highestprice', 'lowestprice', 'totalvol']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sort by stock and date
    df = df.sort_values(['stockcode', 'tradingdate']).reset_index(drop=True)
    
    return df


def preprocess_stock_data(df: pd.DataFrame) -> dict:
    """
    Preprocess data and group by stock code.
    
    Args:
        df: Raw DataFrame from load_vn30_data
        
    Returns:
        Dictionary mapping stock_code -> DataFrame with calculated indicators
    """
    stock_data = {}
    
    for stock_code in df['stockcode'].unique():
        stock_df = df[df['stockcode'] == stock_code].copy()
        stock_df = stock_df.sort_values('tradingdate').reset_index(drop=True)
        stock_data[stock_code] = stock_df
    
    return stock_data


def get_all_trading_dates(df: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Get sorted unique trading dates from the data.
    
    Args:
        df: DataFrame with tradingdate column
        
    Returns:
        Sorted DatetimeIndex of all trading dates
    """
    return pd.DatetimeIndex(sorted(df['tradingdate'].unique()))


def get_stock_data_for_date(stock_data: dict, stock_code: str, date: pd.Timestamp) -> pd.Series:
    """
    Get data for a specific stock on a specific date.
    
    Args:
        stock_data: Dictionary of stock DataFrames
        stock_code: Stock symbol
        date: Trading date
        
    Returns:
        Series with stock data for that date, or None if not found
    """
    if stock_code not in stock_data:
        return None
    
    stock_df = stock_data[stock_code]
    mask = stock_df['tradingdate'] == date
    
    if mask.any():
        return stock_df[mask].iloc[0]
    return None
