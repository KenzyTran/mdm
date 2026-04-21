"""Download 5 liquidity proxies via yfinance and merge into daily panel for VN30 macro-regime research."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


TICKERS = {
    'usdvnd_close': 'VND=X',
    'dxy_close':    'DX-Y.NYB',
    'tnx_close':    '^TNX',
    'vnm_close':    'VNM',
    'eem_close':    'EEM',
}
START = '2015-01-01'
END = '2026-01-01'
OUTPUT = Path('data/vn_liquidity_proxy.csv')


def fetch_ticker(symbol: str, start: str, end: str, col_name: str) -> pd.Series:
    """Download a single yfinance ticker and return its Close series named ``col_name``.

    Args:
        symbol: yfinance ticker string (e.g. ``'VND=X'``).
        start: Start date (inclusive), ``'YYYY-MM-DD'``.
        end: End date (exclusive), ``'YYYY-MM-DD'``.
        col_name: Target column name to assign to the returned Series.

    Returns:
        pandas Series indexed by date with the ticker's daily close.
    """
    df = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        close = df.xs('Close', axis=1, level=0).iloc[:, 0]
    else:
        close = df['Close']
    close.name = col_name
    return close


def build_panel() -> pd.DataFrame:
    """Fetch all tickers and outer-join into a single daily panel keyed on date.

    Returns:
        DataFrame with columns ``[date, usdvnd_close, dxy_close, tnx_close, vnm_close, eem_close]``.
        NaNs are preserved on days where a given market was closed.
    """
    series_dict = {
        col_name: fetch_ticker(symbol, START, END, col_name)
        for col_name, symbol in TICKERS.items()
    }
    panel = pd.concat(series_dict, axis=1)
    panel = panel.sort_index()
    panel.index.name = 'date'
    panel = panel.reset_index()
    panel['date'] = pd.to_datetime(panel['date']).dt.strftime('%Y-%m-%d')
    return panel


def main() -> None:
    """Build the liquidity proxy panel and write it to disk."""
    panel = build_panel()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(panel)} rows to {OUTPUT}")
    print(f"Date range: {panel['date'].min()} -> {panel['date'].max()}")


if __name__ == '__main__':
    main()
