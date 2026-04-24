"""Download Global Liquidity data from FRED and calculate Net Liquidity.

Components:
- WALCL: Fed total assets (balance sheet)
- WTREGEN: Treasury General Account (subtract)
- RRPONTSYD: Reverse Repo agreements (subtract)

Net Liquidity = WALCL - TGA - RRP

Additional central banks (weekly, converted to USD):
- ECBASSETSW: ECB total assets (EUR, converted)
- JPNASSETS: BOJ total assets (JPY, converted)

Output: data/global_liquidity.csv

Usage:
    uv run python scripts/download_global_liquidity.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import pandas as pd
import numpy as np
from io import StringIO

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'global_liquidity.csv')

FRED_BASE = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
START_DATE = '2007-01-01'

# FRED series: id, description, unit (millions unless noted)
SERIES = {
    # Fed components
    'WALCL': 'Fed Total Assets',
    'WTREGEN': 'Treasury General Account',
    'RRPONTSYD': 'Reverse Repo',
    # Major central banks
    'ECBASSETSW': 'ECB Total Assets (EUR)',
    'JPNASSETS': 'BOJ Total Assets (JPY)',
    # Forex rates for conversion
    'DEXUSEU': 'USD/EUR Exchange Rate',
    'DEXJPUS': 'JPY/USD Exchange Rate',
}


def download_fred(series_id: str) -> pd.DataFrame:
    """Download a single FRED series as DataFrame."""
    url = f'{FRED_BASE}?id={series_id}&cosd={START_DATE}'
    print(f'  Downloading {series_id}...', end=' ')
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    df = pd.read_csv(StringIO(resp.text))
    df.columns = ['date', series_id]
    df['date'] = pd.to_datetime(df['date'])
    df[series_id] = pd.to_numeric(df[series_id], errors='coerce')
    df = df.dropna()
    print(f'{len(df)} rows ({df["date"].min().date()} to {df["date"].max().date()})')
    return df


def main():
    print('=' * 60)
    print('GLOBAL LIQUIDITY DATA DOWNLOAD')
    print('=' * 60)

    print('\n[1/3] Downloading FRED series...')
    frames = {}
    for sid in SERIES:
        try:
            frames[sid] = download_fred(sid)
        except Exception as e:
            print(f'  WARNING: {sid} failed: {e}')

    print('\n[2/3] Merging and calculating...')

    # Start with Fed balance sheet (weekly, Wednesday)
    df = frames['WALCL'].copy()

    # Merge all series using nearest date (different frequencies)
    for sid in ['WTREGEN', 'RRPONTSYD', 'ECBASSETSW', 'JPNASSETS', 'DEXUSEU', 'DEXJPUS']:
        if sid in frames:
            df = pd.merge_asof(
                df.sort_values('date'),
                frames[sid].sort_values('date'),
                on='date',
                direction='backward',
            )

    # Fill forward missing values
    for col in df.columns:
        if col != 'date':
            df[col] = df[col].ffill()

    df = df.dropna()

    # Convert ECB (EUR millions) to USD millions
    if 'ECBASSETSW' in df.columns and 'DEXUSEU' in df.columns:
        df['ECB_USD'] = df['ECBASSETSW'] * df['DEXUSEU']
    else:
        df['ECB_USD'] = 0

    # Convert BOJ (JPY 100-millions) to USD millions
    # JPNASSETS is in 100-million JPY, DEXJPUS is JPY per USD
    if 'JPNASSETS' in df.columns and 'DEXJPUS' in df.columns:
        df['BOJ_USD'] = (df['JPNASSETS'] * 100) / df['DEXJPUS']
    else:
        df['BOJ_USD'] = 0

    # Calculate components (all in millions USD)
    df['fed_net'] = df['WALCL'] - df.get('WTREGEN', 0) - df.get('RRPONTSYD', 0)
    df['global_liquidity'] = df['fed_net'] + df['ECB_USD'] + df['BOJ_USD']

    # Slope indicator: 20-week rate of change
    df['liquidity_roc_20w'] = df['global_liquidity'].pct_change(20) * 100
    # Simple signal: positive ROC = QE floor ON
    df['qe_floor'] = (df['liquidity_roc_20w'] > 0).astype(int)

    # Select output columns
    out = df[['date', 'WALCL', 'fed_net', 'ECB_USD', 'BOJ_USD',
              'global_liquidity', 'liquidity_roc_20w', 'qe_floor']].copy()
    out = out.round(2)

    print(f'\n  Rows: {len(out)}')
    print(f'  Range: {out["date"].min().date()} to {out["date"].max().date()}')
    print(f'  Latest Global Liquidity: {out["global_liquidity"].iloc[-1]:,.0f} M USD')
    print(f'  Latest ROC 20w: {out["liquidity_roc_20w"].iloc[-1]:.2f}%')
    print(f'  Latest QE Floor: {"ON" if out["qe_floor"].iloc[-1] == 1 else "OFF"}')

    print(f'\n[3/3] Saving to {OUTPUT_PATH}...')
    out.to_csv(OUTPUT_PATH, index=False)
    print(f'  Saved {os.path.getsize(OUTPUT_PATH) // 1024} KB')

    print(f'\n{"=" * 60}')
    print('DONE')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
