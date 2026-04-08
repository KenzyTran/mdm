"""Spot-check price adjustment for a given ticker.

Usage: uv run python scripts/spot_check_adjust.py VNM 2018-01-01 2024-12-31
Prints raw vs adjusted closeprice around days where totaladjustrate changes
(split/dividend events).
"""
from __future__ import annotations

import sys

from connectors.postgres import load_stock_eod
from connectors.adjust import adjust_ohlc


def main(ticker: str, start: str, end: str) -> int:
    df = load_stock_eod([ticker], start, end)
    if df.empty:
        print(f"No rows for {ticker} in [{start}, {end}]")
        return 1
    df = adjust_ohlc(df).reset_index(drop=True)
    df["rate_change"] = df["totaladjustrate"].diff().fillna(0) != 0
    events = df[df["rate_change"]]
    print(f"=== {ticker}: {len(df)} rows, {len(events)} adjustment events ===")
    cols = ["tradingdate", "closeprice", "totaladjustrate", "adj_close"]
    if not events.empty:
        print("Around adjustment events:")
        for idx in events.index:
            lo = max(0, idx - 2)
            hi = min(len(df) - 1, idx + 2)
            window = df.loc[lo:hi, cols]
            print(window.to_string(index=False))
            print("---")
    else:
        print("No rate changes in window. Head/tail:")
        print(df[cols].head().to_string(index=False))
        print(df[cols].tail().to_string(index=False))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: spot_check_adjust.py TICKER START END")
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
