"""Phase 31 portfolio engine CSV audit writers (D-27).

Serialize a :class:`PortfolioResult` to the canonical 4-CSV set consumed by
Phase 32 parameter sweeps and the phase audit report:

    trades.csv     — one row per completed round-trip (Trade dataclass)
    positions.csv  — daily (date, ticker) mark-to-market snapshot
    nav.csv        — daily NAV, cash, deployed %, open slot count
    unfilled.csv   — every skipped/dropped entry candidate with reason

All writers enforce column order exactly (no implicit DataFrame column
ordering) so sweeps downstream can rely on schema stability. `write_all`
creates the output directory if missing and returns a dict of written
paths. Empty results still produce header-only CSVs.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Dict

import pandas as pd

from .engine import PortfolioResult


TRADES_COLS = [
    "ticker",
    "buy_date",
    "buy_price",
    "buy_cost_vnd",
    "sell_date",
    "sell_price",
    "sell_cost_vnd",
    "pnl_vnd",
    "pnl_pct",
    "exit_reason",
]

POSITIONS_COLS = ["date", "ticker", "shares", "mark_price", "mark_value"]

NAV_COLS = ["date", "nav", "cash", "deployed_pct", "open_slots"]

UNFILLED_COLS = ["date", "ticker", "reason", "detail"]


def _trades_to_df(result: PortfolioResult) -> pd.DataFrame:
    rows = []
    for t in result.trades:
        if is_dataclass(t):
            rows.append(asdict(t))
        else:
            rows.append(dict(t))
    df = pd.DataFrame(rows, columns=TRADES_COLS)
    if not df.empty:
        df = df.sort_values("sell_date", kind="stable").reset_index(drop=True)
    return df[TRADES_COLS]


def _positions_to_df(result: PortfolioResult) -> pd.DataFrame:
    df = result.positions_daily.copy() if result.positions_daily is not None else pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame(columns=POSITIONS_COLS)
    for col in POSITIONS_COLS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    df = df[POSITIONS_COLS].sort_values(["date", "ticker"], kind="stable").reset_index(drop=True)
    return df


def _nav_to_df(result: PortfolioResult) -> pd.DataFrame:
    df = result.nav_daily.copy() if result.nav_daily is not None else pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame(columns=NAV_COLS)
    for col in NAV_COLS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    df = df[NAV_COLS].sort_values("date", kind="stable").reset_index(drop=True)
    return df


def _unfilled_to_df(result: PortfolioResult) -> pd.DataFrame:
    if not result.unfilled:
        return pd.DataFrame(columns=UNFILLED_COLS)
    rows = []
    for entry in result.unfilled:
        e = dict(entry) if not isinstance(entry, dict) else entry
        date = e.get("date")
        ticker = e.get("ticker")
        reason = e.get("reason")
        extras = {
            k: v
            for k, v in e.items()
            if k not in ("date", "ticker", "reason", "bar_idx")
        }
        detail = "" if not extras else ";".join(f"{k}={v}" for k, v in sorted(extras.items()))
        rows.append(
            {"date": date, "ticker": ticker, "reason": reason, "detail": detail}
        )
    df = pd.DataFrame(rows, columns=UNFILLED_COLS)
    return df


def write_trades_csv(result: PortfolioResult, path: Path) -> Path:
    """Write trades.csv; columns: TRADES_COLS; sorted by sell_date."""
    path = Path(path)
    df = _trades_to_df(result)
    df.to_csv(path, index=False)
    return path


def write_positions_csv(result: PortfolioResult, path: Path) -> Path:
    """Write positions.csv; columns: POSITIONS_COLS; sorted by (date,ticker)."""
    path = Path(path)
    df = _positions_to_df(result)
    df.to_csv(path, index=False)
    return path


def write_nav_csv(result: PortfolioResult, path: Path) -> Path:
    """Write nav.csv; columns: NAV_COLS; sorted by date."""
    path = Path(path)
    df = _nav_to_df(result)
    df.to_csv(path, index=False)
    return path


def write_unfilled_csv(result: PortfolioResult, path: Path) -> Path:
    """Write unfilled.csv; columns: UNFILLED_COLS.

    Extras on the raw unfilled dict (anything beyond date/ticker/reason/bar_idx)
    are serialized into the ``detail`` column as ``k=v`` pairs joined with ``;``.
    """
    path = Path(path)
    df = _unfilled_to_df(result)
    df.to_csv(path, index=False)
    return path


def write_all(result: PortfolioResult, out_dir: Path) -> Dict[str, Path]:
    """Write all 4 CSVs into ``out_dir`` (created if missing).

    Returns a dict ``{"trades": Path, "positions": Path, "nav": Path,
    "unfilled": Path}``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "trades": write_trades_csv(result, out_dir / "trades.csv"),
        "positions": write_positions_csv(result, out_dir / "positions.csv"),
        "nav": write_nav_csv(result, out_dir / "nav.csv"),
        "unfilled": write_unfilled_csv(result, out_dir / "unfilled.csv"),
    }
    return paths
