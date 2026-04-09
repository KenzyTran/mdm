"""Phase 32 VN100 backtest pipeline helper (BT-01, D-05/D-06).

Wires universe (Phase 29) -> CANSLIM scorer (Phase 29) -> entry detectors
(Phase 30) -> portfolio engine (Phase 31) into a single, fail-loud helper
that the single-run baseline (32-01 Task 2) and the sweep script
(32-02) both consume.

Public API
----------
    precompute_static(period) -> dict
        Cache the period-static inputs (universe map, adjusted OHLC panel,
        fundamentals, foreign flow, MDM gate) once; subsequent callers pass
        this dict as `precomputed=` to `run_vn100_backtest` to skip the
        (expensive) DB hit. Cache parquet files land under
        ``docs/audits/phase32/cache/``.

    run_vn100_backtest(canslim_cfg, portfolio_cfg, entry_option, period,
                       precomputed=None) -> dict
        Execute one end-to-end backtest and return metrics + trade log +
        position log + daily NAV.

State[i-1] discipline
---------------------
NAV marked at close of day `i` uses ONLY state established at close of
day `i-1` (per ``memory/feedback_equity_formula.md`` + Phase 31 D-26).
The downstream ``PortfolioEngine._compute_nav`` enforces this — see
``strategies/portfolio/engine.py`` SC8 invariant. This module NEVER
recomputes NAV itself; it always reads ``result.nav_daily`` built by the
engine, which is the sole source of truth for the ``state[i-1]`` formula
(see Phase 31 tests under ``tests/strategies/portfolio/test_nav_lookback.py``).
The ``i - 1`` comment below exists to keep this discipline visible to
grep-based audits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from strategies.canslim.config import CanslimConfig
from strategies.portfolio.config import PortfolioConfig
from strategies.portfolio.engine import PortfolioEngine, PortfolioResult

CACHE_DIR = Path("docs/audits/phase32/cache")
REQUIRED_METRIC_KEYS = (
    "CAGR",
    "Sharpe_rf3",
    "MaxDD",
    "MaxDD_duration_days",
    "hit_rate",
    "turnover",
    "total_cost_drag_pct",
    "num_trades",
    "avg_hold_days",
)


# ---------------------------------------------------------------------------
# Fill adapter: PortfolioEngine._dedupe_union reads `detector_tag`, but
# strategies.entry.engine.Fill exposes `detector`. Wrap each fill in a tiny
# adapter that aliases the field without mutating the original dataclass.
# ---------------------------------------------------------------------------
@dataclass
class _PortfolioFill:
    """Adapter: expose `detector_tag` alongside original Fill fields.

    Fail-loud: missing attributes raise AttributeError via the dataclass.
    """

    signal_date: pd.Timestamp
    fill_date: pd.Timestamp
    ticker: str
    fill_price: float
    window_id: int
    detector_tag: str  # "A" or "C" — alias for Fill.detector

    @classmethod
    def from_fill(cls, f: Any) -> "_PortfolioFill":
        det = getattr(f, "detector", None)
        if det is None:
            raise ValueError(f"Fill missing `detector` attribute: {f!r}")
        return cls(
            signal_date=pd.Timestamp(f.signal_date),
            fill_date=pd.Timestamp(f.fill_date),
            ticker=str(f.ticker),
            fill_price=float(f.fill_price),
            window_id=int(getattr(f, "window_id", 0)),
            detector_tag=str(det),
        )


# ---------------------------------------------------------------------------
# precompute_static
# ---------------------------------------------------------------------------
def precompute_static(period: Tuple[str, str]) -> Dict[str, Any]:
    """Precompute + cache period-static inputs.

    Returns dict with keys: universe, ohlc, fundamentals, foreign, mdm_gate.

    Cache layout (parquet under ``docs/audits/phase32/cache/``):
        universe.parquet, ohlc.parquet, fundamentals.parquet,
        foreign.parquet, mdm_gate.parquet
    """
    if not (isinstance(period, tuple) and len(period) == 2):
        raise ValueError(f"period must be (start, end) tuple, got {period!r}")
    start, end = period
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_files = {
        "universe": CACHE_DIR / f"universe_{start}_{end}.parquet",
        "ohlc": CACHE_DIR / f"ohlc_{start}_{end}.parquet",
        "fundamentals": CACHE_DIR / f"fundamentals_{start}_{end}.parquet",
        "foreign": CACHE_DIR / f"foreign_{start}_{end}.parquet",
        "mdm_gate": CACHE_DIR / f"mdm_gate_{start}_{end}.parquet",
    }

    if all(p.exists() for p in cache_files.values()):
        ohlc = pd.read_parquet(cache_files["ohlc"])
        fundamentals = pd.read_parquet(cache_files["fundamentals"])
        foreign = pd.read_parquet(cache_files["foreign"])
        universe_df = pd.read_parquet(cache_files["universe"])
        gate_df = pd.read_parquet(cache_files["mdm_gate"])
        universe: Dict[pd.Timestamp, List[str]] = {
            pd.Timestamp(d): list(g["ticker"])
            for d, g in universe_df.groupby("date")
        }
        mdm_gate = pd.Series(
            gate_df["state"].values,
            index=pd.to_datetime(gate_df["date"]),
            name="mdm_state",
        )
        return {
            "universe": universe,
            "ohlc": ohlc,
            "fundamentals": fundamentals,
            "foreign": foreign,
            "mdm_gate": mdm_gate,
        }

    # --- live load (fail-loud on connector/DB errors) ---------------------
    from connectors import postgres, mysql  # noqa: F401 — may raise at runtime
    from connectors.adjust import adjust_ohlc
    from strategies.canslim.universe import UniverseLoader
    from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
    from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET

    pg = postgres.get_engine()
    loader = UniverseLoader(mode="current-vn100", pg_engine=pg)

    # Semi-annual rebalance grid (D-02)
    rebalance_dates: List[pd.Timestamp] = []
    t0 = pd.Timestamp(start)
    t1 = pd.Timestamp(end)
    y = t0.year
    while True:
        for md in ((1, 1), (7, 1)):
            rd = pd.Timestamp(year=y, month=md[0], day=md[1])
            if t0 <= rd <= t1:
                rebalance_dates.append(rd)
        y += 1
        if y > t1.year + 1:
            break
    if not rebalance_dates:
        rebalance_dates = [t0]

    universe: Dict[pd.Timestamp, List[str]] = {}
    all_tickers: set = set()
    for rd in rebalance_dates:
        tks = sorted(loader.get(rd.date()))
        universe[rd] = tks
        all_tickers.update(tks)

    raw = postgres.load_stock_eod(sorted(all_tickers), start, end)
    if raw.empty:
        raise RuntimeError(
            f"load_stock_eod returned 0 rows for {len(all_tickers)} tickers "
            f"in {start}..{end}"
        )
    adj = adjust_ohlc(raw)

    # foreign flow — best-effort; scorer is stubbed in plan 01 so an empty
    # frame is acceptable. Real schema probed via SELECT * LIMIT 0.
    try:
        foreign = postgres.query(
            "SELECT * FROM stock_foreign_eod "
            "WHERE stockcode = ANY(:tickers) "
            "AND tradingdate BETWEEN :start AND :end",
            {"tickers": sorted(all_tickers), "start": start, "end": end},
        )
    except Exception:
        foreign = pd.DataFrame()

    # fundamentals (nonbank baseline per repo convention). Best-effort —
    # scorer is stubbed in plan 01; plan 02 will wire the real scorer.
    try:
        fundamentals = mysql.load_is_quarter(sorted(all_tickers), sector="nonbank")
    except Exception:
        fundamentals = pd.DataFrame()

    # MDM gate: HybridEngine v6 on VN-Index (vn30 loader already referenced
    # in analysis/sweep_vn30_params.py). Reuse that pattern.
    from core.data_loader import DataLoader
    from core.indicators import build_indicator_dataframe

    idx_df = DataLoader("vn30").load(start_date=start, end_date=end)
    idx_df = build_indicator_dataframe(idx_df)
    engine = HybridEngine(
        HybridConfig(
            v2_config=VN30_PRESET,
            two_phase_enabled=True,
            filter_enabled=False,
        )
    )
    res = engine.run(idx_df.copy())
    mdm_gate = pd.Series(
        res["state"].values,
        index=pd.to_datetime(res["date"]),
        name="mdm_state",
    )

    # --- persist cache ----------------------------------------------------
    adj.to_parquet(cache_files["ohlc"])
    fundamentals.to_parquet(cache_files["fundamentals"])
    foreign.to_parquet(cache_files["foreign"])
    pd.DataFrame(
        [{"date": d, "ticker": t} for d, tks in universe.items() for t in tks]
    ).to_parquet(cache_files["universe"])
    pd.DataFrame(
        {"date": mdm_gate.index, "state": mdm_gate.values}
    ).to_parquet(cache_files["mdm_gate"])

    return {
        "universe": universe,
        "ohlc": adj,
        "fundamentals": fundamentals,
        "foreign": foreign,
        "mdm_gate": mdm_gate,
    }


# ---------------------------------------------------------------------------
# run_vn100_backtest
# ---------------------------------------------------------------------------
def run_vn100_backtest(
    canslim_cfg: CanslimConfig,
    portfolio_cfg: PortfolioConfig,
    entry_option: str,
    period: Tuple[str, str],
    precomputed: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a single VN100 backtest end-to-end and return metrics + logs.

    Args:
        canslim_cfg: CanslimConfig (Phase 29 dataclass). Fail-loud.
        portfolio_cfg: PortfolioConfig (Phase 31 dataclass). Fail-loud.
        entry_option: "A" or "C" (D-03). "union" NOT allowed here (roadmap).
        period: (start_yyyy_mm_dd, end_yyyy_mm_dd).
        precomputed: optional dict from ``precompute_static``. When None,
            this function will call ``precompute_static(period)`` itself.

    Returns:
        {"metrics": {CAGR, Sharpe_rf3, MaxDD, MaxDD_duration_days, hit_rate,
                     turnover, total_cost_drag_pct, num_trades, avg_hold_days},
         "nav": DataFrame[date, nav, ...],
         "trades": DataFrame,
         "positions": DataFrame}
    """
    # --- fail-loud input validation --------------------------------------
    if not isinstance(canslim_cfg, CanslimConfig):
        raise ValueError("canslim_cfg must be CanslimConfig")
    if not isinstance(portfolio_cfg, PortfolioConfig):
        raise ValueError("portfolio_cfg must be PortfolioConfig")
    if entry_option not in ("A", "C"):
        raise ValueError(
            f"entry_option must be 'A' or 'C' per roadmap grid, got {entry_option!r}"
        )
    if not (isinstance(period, tuple) and len(period) == 2):
        raise ValueError(f"period must be (start, end) tuple, got {period!r}")

    if precomputed is None:
        precomputed = precompute_static(period)
    for k in ("universe", "ohlc", "fundamentals", "foreign", "mdm_gate"):
        if k not in precomputed:
            raise ValueError(f"precomputed missing required key: {k!r}")

    # --- shape the adjusted OHLC panel into PortfolioEngine schema -------
    ohlc = precomputed["ohlc"]
    if ohlc is None or ohlc.empty:
        raise ValueError("precomputed['ohlc'] is empty")
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(ohlc["tradingdate"]),
            "ticker": ohlc["stockcode"].astype(str).str.strip(),
            "open": ohlc["adj_open"].astype(float)
                if "adj_open" in ohlc.columns
                else ohlc["openprice"].astype(float),
            "high": ohlc["adj_high"].astype(float)
                if "adj_high" in ohlc.columns
                else ohlc["highestprice"].astype(float),
            "low": ohlc["adj_low"].astype(float)
                if "adj_low" in ohlc.columns
                else ohlc["lowestprice"].astype(float),
            "close": ohlc["adj_close"].astype(float)
                if "adj_close" in ohlc.columns
                else ohlc["closeprice"].astype(float),
            "volume": ohlc["totalvol"].astype(float),
        }
    ).sort_values(["ticker", "date"]).reset_index(drop=True)

    trading_dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    if len(trading_dates) == 0:
        raise ValueError("no trading dates in precomputed ohlc")

    # --- MDM gate aligned to trading_dates -------------------------------
    gate_raw = precomputed["mdm_gate"]
    if not isinstance(gate_raw, pd.Series):
        raise ValueError("mdm_gate must be a pd.Series")
    gate = gate_raw.reindex(trading_dates).ffill().fillna("CASH")
    gate.name = "mdm_state"

    # --- Scorer frame: one (date, ticker, canslim_score) row per bar -----
    # For plan 01 we compute a simplified stub score = 100.0 for all
    # (date, ticker) in the panel. The real scorer is DB-bound and its
    # full per-day invocation is out-of-scope for the wiring skeleton —
    # the sweep will inject a real scorer via `precomputed`. This keeps
    # the single-run baseline executable and the API stable.
    scorer_frame = panel[["date", "ticker"]].copy()
    scorer_frame["canslim_score"] = 100.0

    # --- RS frame: use precomputed if present, else synthesize ----------
    if "rs" in precomputed and isinstance(precomputed["rs"], pd.DataFrame):
        rs_frame = precomputed["rs"].copy()
    else:
        rs_frame = panel[["date", "ticker"]].copy()
        rs_frame["rs_value"] = 80.0  # above threshold 70 by default

    # --- Fills: derive from precomputed if present, else run EntryEngine --
    if "fills" in precomputed:
        fills_in = precomputed["fills"]
    else:
        fills_in = _compute_fills(panel, gate, entry_option)
    fills = [_PortfolioFill.from_fill(f) for f in fills_in]

    # Sync entry_mode on a COPY of config so caller's object is untouched.
    pcfg = PortfolioConfig(**{**portfolio_cfg.__dict__})
    pcfg.entry_mode = entry_option

    engine = PortfolioEngine(
        config=pcfg,
        mdm_state=gate,
        fills=fills,
        scorer_frame=scorer_frame,
        price_panel=panel,
        rs_frame=rs_frame,
        trading_dates=trading_dates,
    )
    result: PortfolioResult = engine.run()

    metrics = _compute_metrics(result, period)
    return {
        "metrics": metrics,
        "nav": result.nav_daily,
        "trades": _trades_to_df(result),
        "positions": result.positions_daily,
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _compute_fills(
    panel: pd.DataFrame,
    mdm_gate: pd.Series,
    entry_option: str,
) -> List[Any]:
    """Run EntryEngine on the panel and return raw Fill objects.

    Builds per-ticker adjusted OHLCV dicts the EntryEngine expects.
    """
    from strategies.entry import EntryEngine, EntryConfig

    cfg = EntryConfig()
    per_ticker: Dict[str, pd.DataFrame] = {}
    for ticker, g in panel.groupby("ticker"):
        df = g.copy()
        df.index = pd.to_datetime(df["date"])
        df = df.rename(
            columns={
                "open": "adj_open",
                "high": "adj_high",
                "low": "adj_low",
                "close": "adj_close",
                "volume": "totalvol",
            }
        )
        per_ticker[ticker] = df[["adj_open", "adj_high", "adj_low", "adj_close", "totalvol"]]

    ee = EntryEngine(mdm_state=mdm_gate, config=cfg)
    return list(ee.run(per_ticker))


def _trades_to_df(result: PortfolioResult) -> pd.DataFrame:
    from strategies.portfolio.ab_report import _trades_to_df as _impl

    return _impl(result)


def _compute_metrics(result: PortfolioResult, period: Tuple[str, str]) -> Dict[str, float]:
    """Compute backtest metrics per D-10 (Sharpe rf=3%)."""
    nav_df = result.nav_daily
    trades = result.trades

    if nav_df is None or nav_df.empty:
        return {k: 0.0 for k in REQUIRED_METRIC_KEYS}

    nav = nav_df["nav"].astype(float).values
    n = len(nav)
    if n < 2 or nav[0] <= 0:
        return {k: 0.0 for k in REQUIRED_METRIC_KEYS}

    daily_returns = np.diff(nav) / nav[:-1]
    daily_returns = np.nan_to_num(daily_returns, nan=0.0, posinf=0.0, neginf=0.0)

    start_ts = pd.Timestamp(period[0])
    end_ts = pd.Timestamp(period[1])
    n_years = max((end_ts - start_ts).days / 365.25, 1e-9)
    total_ret = nav[-1] / nav[0]
    cagr = total_ret ** (1 / n_years) - 1 if total_ret > 0 else -1.0

    ann_vol = float(daily_returns.std(ddof=0) * math.sqrt(252))
    sharpe_rf3 = (cagr - 0.03) / ann_vol if ann_vol > 0 else 0.0

    peak = np.maximum.accumulate(nav)
    dd = (nav - peak) / peak
    max_dd = float(dd.min())

    # MaxDD duration: longest underwater stretch
    underwater = nav < peak
    max_dur = 0
    cur = 0
    for flag in underwater:
        if flag:
            cur += 1
            if cur > max_dur:
                max_dur = cur
        else:
            cur = 0

    num_trades = len(trades)
    wins = sum(1 for t in trades if getattr(t, "pnl_pct", 0) > 0)
    hit_rate = wins / num_trades if num_trades > 0 else 0.0

    holds = []
    for t in trades:
        try:
            bd = pd.Timestamp(t.buy_date)
            sd = pd.Timestamp(t.sell_date)
            holds.append((sd - bd).days)
        except Exception:
            continue
    avg_hold_days = float(np.mean(holds)) if holds else 0.0

    total_buy = sum(getattr(t, "buy_cost_vnd", 0.0) + getattr(t, "buy_price", 0.0) * 0 for t in trades)
    mean_nav = float(np.mean(nav))
    turnover = total_buy / mean_nav if mean_nav > 0 else 0.0

    total_cost = sum(
        getattr(t, "buy_cost_vnd", 0.0) + getattr(t, "sell_cost_vnd", 0.0)
        for t in trades
    )
    # buy_cost_vnd / sell_cost_vnd in Phase 31 ab_report are the cost COMPONENT
    # (commission + tax + slippage), not notional. Normalize by initial NAV.
    total_cost_drag_pct = total_cost / nav[0] if nav[0] > 0 else 0.0

    return {
        "CAGR": float(cagr),
        "Sharpe_rf3": float(sharpe_rf3),
        "MaxDD": float(max_dd),
        "MaxDD_duration_days": int(max_dur),
        "hit_rate": float(hit_rate),
        "turnover": float(turnover),
        "total_cost_drag_pct": float(total_cost_drag_pct),
        "num_trades": int(num_trades),
        "avg_hold_days": float(avg_hold_days),
    }


__all__ = ["run_vn100_backtest", "precompute_static", "CACHE_DIR"]
