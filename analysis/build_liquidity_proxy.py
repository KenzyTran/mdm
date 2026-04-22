"""Download 5 liquidity proxies via yfinance and merge into daily panel for VN30 macro-regime research.

Hardened builder per Phase 43 plan 43-01:
- CLI args (argparse) per D-03
- yfinance retry loop with exponential backoff per D-04 (HTTP 401/403/429,
  ConnectionError, Timeout, empty-DataFrame)
- Missing-'Close'-column guard raises RuntimeError per D-05 (fail loud on schema drift)

Usage:
    uv run python analysis/build_liquidity_proxy.py
    uv run python analysis/build_liquidity_proxy.py --start 2020-01-01 --end 2021-01-01 --output /tmp/proxy.csv
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yfinance as yf


TICKERS = {
    'usdvnd_close': 'VND=X',
    'dxy_close':    'DX-Y.NYB',
    'tnx_close':    '^TNX',
    'vnm_close':    'VNM',
    'eem_close':    'EEM',
}
OUTPUT = Path('data/vn_liquidity_proxy.csv')

DEFAULT_START = '2015-01-01'
DEFAULT_END = '2026-01-01'
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SEC = 5.0
TRANSIENT_HTTP_CODES = frozenset({401, 403, 429})


def fetch_ticker(
    symbol: str,
    start: str,
    end: str,
    col_name: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_sec: float = DEFAULT_RETRY_BACKOFF_SEC,
) -> pd.Series:
    """Download a single yfinance ticker's Close series with retry + schema guard.

    Transient errors (HTTP 401/403/429, ConnectionError, Timeout, empty DataFrame)
    trigger exponential backoff retry up to ``max_retries`` attempts. Non-transient
    errors (missing ``'Close'`` column) surface immediately per D-05 — silent
    missing-column failures would produce all-NaN columns and Phase 44 would
    inherit them as silent "no signal" days.

    Args:
        symbol: yfinance ticker (e.g., ``'VND=X'``).
        start: Inclusive start date ``'YYYY-MM-DD'``.
        end: Exclusive end date ``'YYYY-MM-DD'``.
        col_name: Output column name for the returned Series.
        max_retries: Max retry attempts on transient errors.
        retry_backoff_sec: Base backoff in seconds; sleep = base * 2**attempt.

    Returns:
        pandas Series indexed by date, named ``col_name``.

    Raises:
        RuntimeError: When yfinance returns a DataFrame without a ``'Close'``
            column (schema change — fail loud, do not silence), or when all
            retries are exhausted for transient errors.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        try:
            df = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)

            # Missing-column guard (D-05 — MUST raise, not silence).
            if isinstance(df.columns, pd.MultiIndex):
                if 'Close' not in df.columns.get_level_values(0):
                    raise RuntimeError(
                        f"ticker {symbol}: 'Close' not in MultiIndex level 0 — "
                        f"yfinance schema changed"
                    )
                close = df.xs('Close', axis=1, level=0).iloc[:, 0]
            else:
                if 'Close' not in df.columns:
                    raise RuntimeError(
                        f"ticker {symbol}: 'Close' column missing — "
                        f"yfinance schema changed"
                    )
                close = df['Close']

            # Empty-DataFrame is a silent yfinance rate-limit failure — treat as transient.
            if len(close) == 0:
                raise ValueError(
                    f"ticker {symbol}: empty DataFrame returned (likely rate-limited)"
                )

            close.name = col_name
            return close

        except RuntimeError:
            # Missing-column — re-raise immediately, do NOT retry
            # (D-05: fail loud on schema break).
            raise

        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                ValueError) as exc:
            # Transient classification:
            # - HTTPError: only retry on codes in TRANSIENT_HTTP_CODES; other HTTP
            #   status codes re-raise immediately (e.g., 500 is a real outage, not
            #   a rate-limit).
            # - ValueError from empty-DataFrame check: retry (treated as rate-limit).
            # - ConnectionError / Timeout: retry.
            if isinstance(exc, requests.exceptions.HTTPError):
                status = getattr(exc.response, 'status_code', None)
                if status not in TRANSIENT_HTTP_CODES:
                    raise
            last_exc = exc
            if attempt < max_retries:
                sleep_sec = retry_backoff_sec * (2 ** attempt)
                print(
                    f"[fetch_ticker] transient error on {symbol} "
                    f"(attempt {attempt + 1}/{max_retries + 1}): "
                    f"{type(exc).__name__}: {exc}. "
                    f"Sleeping {sleep_sec:.1f}s before retry."
                )
                time.sleep(sleep_sec)
                continue
            # Exhausted retries — re-raise last transient exception with context.
            raise RuntimeError(
                f"ticker {symbol}: all {max_retries + 1} attempts failed. "
                f"Last error: {type(last_exc).__name__}: {last_exc}"
            ) from last_exc

    # Defensive: the for-loop always returns or raises; this is unreachable.
    raise RuntimeError(f"ticker {symbol}: fetch_ticker exited retry loop without result")


def build_panel(
    start: str,
    end: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_sec: float = DEFAULT_RETRY_BACKOFF_SEC,
) -> pd.DataFrame:
    """Fetch all tickers in :data:`TICKERS` and outer-join into a daily panel.

    Preserves the quick-task schema: column order matches ``TICKERS`` dict order,
    the ``date`` column is first and ISO-formatted (``YYYY-MM-DD`` string). NaNs
    are preserved on days where a given market was closed — no forward-fill in
    the builder (Phase 44 handles fill policy).

    Args:
        start: Inclusive start date ``'YYYY-MM-DD'``.
        end: Exclusive end date ``'YYYY-MM-DD'``.
        max_retries: Max retry attempts per ticker on transient errors.
        retry_backoff_sec: Base backoff in seconds; sleep = base * 2**attempt.

    Returns:
        DataFrame with columns
        ``[date, usdvnd_close, dxy_close, tnx_close, vnm_close, eem_close]``.
    """
    series_dict = {
        col_name: fetch_ticker(
            symbol,
            start,
            end,
            col_name,
            max_retries=max_retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        for col_name, symbol in TICKERS.items()
    }
    panel = pd.concat(series_dict, axis=1)
    panel = panel.sort_index()
    panel.index.name = 'date'
    panel = panel.reset_index()
    panel['date'] = pd.to_datetime(panel['date']).dt.strftime('%Y-%m-%d')
    return panel


def _build_arg_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser with the 5 CLI flags locked by D-03."""
    parser = argparse.ArgumentParser(
        description=(
            "Download VN30 liquidity proxies via yfinance and write canonical "
            "daily panel CSV."
        ),
    )
    parser.add_argument(
        '--start',
        default=DEFAULT_START,
        help=f'inclusive start date YYYY-MM-DD (default: {DEFAULT_START})',
    )
    parser.add_argument(
        '--end',
        default=DEFAULT_END,
        help=f'exclusive end date YYYY-MM-DD (default: {DEFAULT_END})',
    )
    parser.add_argument(
        '--output',
        default=str(OUTPUT),
        type=Path,
        help=f'output CSV path (default: {OUTPUT})',
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=DEFAULT_MAX_RETRIES,
        dest='max_retries',
        help=(
            f'max retry attempts on transient yfinance errors '
            f'(default: {DEFAULT_MAX_RETRIES})'
        ),
    )
    parser.add_argument(
        '--retry-backoff-sec',
        type=float,
        default=DEFAULT_RETRY_BACKOFF_SEC,
        dest='retry_backoff_sec',
        help=(
            f'base backoff seconds; sleep = base * 2**attempt '
            f'(default: {DEFAULT_RETRY_BACKOFF_SEC})'
        ),
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry: parse args, build panel, write CSV, print summary.

    Args:
        argv: Optional argv override for programmatic invocation / tests.
    """
    args = _build_arg_parser().parse_args(argv)
    panel = build_panel(
        start=args.start,
        end=args.end,
        max_retries=args.max_retries,
        retry_backoff_sec=args.retry_backoff_sec,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)
    print(f"Wrote {len(panel)} rows to {args.output}")
    print(f"Date range: {panel['date'].min()} -> {panel['date'].max()}")


if __name__ == '__main__':
    main()
