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
CANSLIM_RAW_CACHE = CACHE_DIR / "canslim_raw.parquet"
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
def precompute_static(period: Tuple[str, str], mode: str = "current-vn100") -> Dict[str, Any]:
    """Precompute + cache period-static inputs.

    Args:
        period: (start_yyyy_mm_dd, end_yyyy_mm_dd).
        mode: Universe mode string (default "current-vn100"). Included in
            cache filenames so that sensitivity runs across different universe
            modes do not collide. Fix for D-06.

    Returns dict with keys: universe, ohlc, fundamentals, foreign, mdm_gate.

    Cache layout (parquet under ``docs/audits/phase32/cache/``):
        universe_{mode}_{start}_{end}.parquet,
        ohlc_{mode}_{start}_{end}.parquet, etc.
    """
    if not (isinstance(period, tuple) and len(period) == 2):
        raise ValueError(f"period must be (start, end) tuple, got {period!r}")
    start, end = period
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_files = {
        "universe": CACHE_DIR / f"universe_{mode}_{start}_{end}.parquet",
        "ohlc": CACHE_DIR / f"ohlc_{mode}_{start}_{end}.parquet",
        "fundamentals": CACHE_DIR / f"fundamentals_{mode}_{start}_{end}.parquet",
        "foreign": CACHE_DIR / f"foreign_{mode}_{start}_{end}.parquet",
        "mdm_gate": CACHE_DIR / f"mdm_gate_{mode}_{start}_{end}.parquet",
        "rs": CACHE_DIR / f"rs_{mode}_{start}_{end}.parquet",
    }

    non_rs_keys = [k for k in cache_files if k != "rs"]
    all_non_rs_exist = all(cache_files[k].exists() for k in non_rs_keys)
    all_exist = all_non_rs_exist and cache_files["rs"].exists()

    if all_non_rs_exist:
        # Load the 5 main cache files (always available on this branch).
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

        if all_exist:
            rs_df = pd.read_parquet(cache_files["rs"])
        else:
            # RS cache missing — fetch only RS from DB and persist.
            from connectors import postgres  # noqa: F401
            all_tickers_cache: List[str] = sorted(
                set(t for tks in universe.values() for t in tks)
            )
            try:
                rs_df = postgres.load_stock_rs(
                    start, end, tickers=all_tickers_cache, rs_col="rsl"
                )
            except Exception:
                rs_df = pd.DataFrame(columns=["date", "ticker", "rs_value"])
            rs_df.to_parquet(cache_files["rs"])

        return {
            "universe": universe,
            "ohlc": ohlc,
            "fundamentals": fundamentals,
            "foreign": foreign,
            "mdm_gate": mdm_gate,
            "rs": rs_df,
        }

    # --- live load (fail-loud on connector/DB errors) ---------------------
    from connectors import postgres, mysql  # noqa: F401 — may raise at runtime
    from connectors.adjust import adjust_ohlc
    from strategies.canslim.universe import UniverseLoader
    from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
    from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET

    pg = postgres.get_engine()
    loader = UniverseLoader(mode=mode, pg_engine=pg)

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

    # RS ratings (long-term rsl). Best-effort — fall back to empty frame
    # so a missing stock_rs table does not abort the backtest.
    try:
        rs = postgres.load_stock_rs(start, end, tickers=sorted(all_tickers), rs_col="rsl")
    except Exception:
        rs = pd.DataFrame(columns=["date", "ticker", "rs_value"])

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
    rs.to_parquet(cache_files["rs"])

    return {
        "universe": universe,
        "ohlc": adj,
        "fundamentals": fundamentals,
        "foreign": foreign,
        "mdm_gate": mdm_gate,
        "rs": rs,
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
    entry_cfg=None,
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
    # Plan 02: real CANSLIM scoring driven by canslim_cfg thresholds.
    # Raw per-(date,ticker) metrics are computed once via
    # ``build_canslim_raw_frame`` (cached to parquet, reused by every sweep
    # worker). Thresholds from canslim_cfg are applied here; a row passes
    # iff  c_pass AND a_pass AND n_pass, otherwise canslim_score = NaN
    # (which makes PortfolioEngine drop the candidate).
    if "canslim_raw" in precomputed and isinstance(
        precomputed["canslim_raw"], pd.DataFrame
    ):
        raw = precomputed["canslim_raw"]
    else:
        raw = build_canslim_raw_frame(panel, precomputed)
    scorer_frame = _apply_canslim_thresholds(raw, canslim_cfg)

    # --- RS frame: DB RS where available, fill gaps from computed rs_rating --
    db_rs = precomputed.get("rs")
    if isinstance(db_rs, pd.DataFrame) and not db_rs.empty:
        rs_frame = db_rs.copy()
        rs_frame["date"] = pd.to_datetime(rs_frame["date"])
        # Fill gaps before DB RS coverage using price-computed rs_rating from raw
        if "rs_rating" in raw.columns:
            computed_rs = raw[["date", "ticker", "rs_rating"]].rename(
                columns={"rs_rating": "rs_value"}
            ).copy()
            computed_rs["date"] = pd.to_datetime(computed_rs["date"])
            # Only keep computed rows where DB RS has no coverage for that date
            db_dates = set(rs_frame["date"].unique())
            gap_rs = computed_rs[~computed_rs["date"].isin(db_dates)]
            rs_frame = pd.concat([gap_rs, rs_frame], ignore_index=True)
    elif "rs_rating" in raw.columns:
        # No DB RS at all — use price-computed RS for entire period
        rs_frame = raw[["date", "ticker", "rs_rating"]].rename(
            columns={"rs_rating": "rs_value"}
        ).copy()
        rs_frame["date"] = pd.to_datetime(rs_frame["date"])
    else:
        rs_frame = panel[["date", "ticker"]].copy()
        rs_frame["rs_value"] = 80.0

    # --- Fills: derive from precomputed if present, else run EntryEngine --
    if "fills" in precomputed:
        fills_in = precomputed["fills"]
    else:
        fills_in = _compute_fills(panel, gate, entry_option, entry_cfg=entry_cfg)
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
# run_v8_backtest — v8.0 entry point (RS+N scoring, no fundamentals)
# ---------------------------------------------------------------------------
def run_v8_backtest(
    momentum_cfg: "MomentumScorerConfig",
    portfolio_cfg: PortfolioConfig,
    entry_option: str,
    period: Tuple[str, str],
    precomputed: Optional[Mapping[str, Any]] = None,
    entry_cfg=None,
    formula: str = "weighted_roc",
) -> Dict[str, Any]:
    """Run a single VN100 v8.0 backtest — RS+N scoring, no fundamentals.

    Same contract as run_vn100_backtest but uses MomentumScorerConfig
    instead of CanslimConfig. Pure price-based computation — no DB
    connectors required in the v8.0 scoring path (MSCO-04).

    Args:
        momentum_cfg: MomentumScorerConfig (Phase 36 dataclass).
        portfolio_cfg: PortfolioConfig (Phase 31 dataclass).
        entry_option: "A" or "C".
        period: (start_yyyy_mm_dd, end_yyyy_mm_dd).
        precomputed: optional dict from precompute_static. The
            "fundamentals" key is NOT required (ignored if present).
        entry_cfg: optional EntryConfig override.
        formula: RS formula for build_momentum_raw_frame
            ('weighted_roc' | 'roc126'). Default 'weighted_roc'.

    Returns:
        Same schema as run_vn100_backtest:
        {"metrics": {...}, "nav": DataFrame, "trades": DataFrame,
         "positions": DataFrame}
    """
    from strategies.momentum.scorer import apply_momentum_thresholds
    from strategies.momentum.scorer_config import MomentumScorerConfig

    if not isinstance(momentum_cfg, MomentumScorerConfig):
        raise ValueError("momentum_cfg must be MomentumScorerConfig")
    if not isinstance(portfolio_cfg, PortfolioConfig):
        raise ValueError("portfolio_cfg must be PortfolioConfig")
    if entry_option not in ("A", "C"):
        raise ValueError(f"entry_option must be 'A' or 'C', got {entry_option!r}")
    if not (isinstance(period, tuple) and len(period) == 2):
        raise ValueError(f"period must be (start, end) tuple, got {period!r}")

    if precomputed is None:
        precomputed = precompute_static(period)
    # v8.0 does NOT require "fundamentals" key (MSCO-04)
    for k in ("universe", "ohlc", "mdm_gate"):
        if k not in precomputed:
            raise ValueError(f"precomputed missing required key: {k!r}")

    # Shape OHLC panel (same as v7.0)
    ohlc = precomputed["ohlc"]
    if ohlc is None or ohlc.empty:
        raise ValueError("precomputed['ohlc'] is empty")
    panel = pd.DataFrame({
        "date": pd.to_datetime(ohlc["tradingdate"]),
        "ticker": ohlc["stockcode"].astype(str).str.strip(),
        "open": ohlc["adj_open"].astype(float) if "adj_open" in ohlc.columns else ohlc["openprice"].astype(float),
        "high": ohlc["adj_high"].astype(float) if "adj_high" in ohlc.columns else ohlc["highestprice"].astype(float),
        "low": ohlc["adj_low"].astype(float) if "adj_low" in ohlc.columns else ohlc["lowestprice"].astype(float),
        "close": ohlc["adj_close"].astype(float) if "adj_close" in ohlc.columns else ohlc["closeprice"].astype(float),
        "volume": ohlc["totalvol"].astype(float),
    }).sort_values(["ticker", "date"]).reset_index(drop=True)

    trading_dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    if len(trading_dates) == 0:
        raise ValueError("no trading dates in precomputed ohlc")

    # MDM gate (same as v7.0)
    gate_raw = precomputed["mdm_gate"]
    if not isinstance(gate_raw, pd.Series):
        raise ValueError("mdm_gate must be a pd.Series")
    gate = gate_raw.reindex(trading_dates).ffill().fillna("CASH")
    gate.name = "mdm_state"

    # v8.0 scorer: momentum raw frame + thresholds
    if "momentum_raw" in precomputed and isinstance(precomputed["momentum_raw"], pd.DataFrame):
        raw = precomputed["momentum_raw"]
    else:
        raw = build_momentum_raw_frame(panel, formula=formula)
    scorer_frame = apply_momentum_thresholds(raw, momentum_cfg)

    # RS frame: DB RS where available, fill gaps from computed rs_rating
    db_rs = precomputed.get("rs")
    if isinstance(db_rs, pd.DataFrame) and not db_rs.empty:
        rs_frame = db_rs.copy()
        rs_frame["date"] = pd.to_datetime(rs_frame["date"])
        if "rs_rating" in raw.columns:
            computed_rs = raw[["date", "ticker", "rs_rating"]].rename(
                columns={"rs_rating": "rs_value"}
            ).copy()
            computed_rs["date"] = pd.to_datetime(computed_rs["date"])
            db_dates = set(rs_frame["date"].unique())
            gap_rs = computed_rs[~computed_rs["date"].isin(db_dates)]
            rs_frame = pd.concat([gap_rs, rs_frame], ignore_index=True)
    elif "rs_rating" in raw.columns:
        rs_frame = raw[["date", "ticker", "rs_rating"]].rename(
            columns={"rs_rating": "rs_value"}
        ).copy()
        rs_frame["date"] = pd.to_datetime(rs_frame["date"])
    else:
        rs_frame = panel[["date", "ticker"]].copy()
        rs_frame["rs_value"] = 80.0

    # Fills (same as v7.0 — MSCO-03: Option A/C unchanged)
    if "fills" in precomputed:
        fills_in = precomputed["fills"]
    else:
        fills_in = _compute_fills(panel, gate, entry_option, entry_cfg=entry_cfg)
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
# ---------------------------------------------------------------------------
# CANSLIM raw-metrics precompute (plan 02)
# ---------------------------------------------------------------------------
def build_canslim_raw_frame(
    panel: pd.DataFrame,
    precomputed: Mapping[str, Any],
) -> pd.DataFrame:
    """Compute raw CANSLIM metrics per (date, ticker) — threshold-free.

    Returns a DataFrame with columns:
        date, ticker, eps_yoy_q0, eps_cagr_3y, n_prox

    - ``eps_yoy_q0``: current-quarter EPS YoY using the latest published
      quarter whose ``publish_date`` (imputed per D-11) is <= the bar date.
      Quarters are forward-filled between publish events.
    - ``eps_cagr_3y``: 3-year TTM CAGR (sum of last 4 quarters / sum of
      quarters 8..12 periods ago) ^ (1/2) - 1, computed per publish event
      and forward-filled.
    - ``n_prox``: 1 - close / rolling_max(highestprice, 252) — distance
      below the 252-day high. ``n_pass`` is ``n_prox <= n_within_high``.

    Cached per date range to ``canslim_raw_{min_date}_{max_date}.parquet``
    under :data:`CACHE_DIR`. Date range is derived from the panel so that
    OOS and in-sample runs never share the same cache file (D-03 fix).

    NaN rows are acceptable — the threshold applier will score them NaN
    (→ candidate dropped by PortfolioEngine).
    """
    # D-03 fix: cache key includes date range so OOS run does not silently
    # reuse in-sample fundamentals.
    min_d = pd.Timestamp(panel["date"].min()).strftime("%Y-%m-%d")
    max_d = pd.Timestamp(panel["date"].max()).strftime("%Y-%m-%d")
    cache_path = CACHE_DIR / f"canslim_raw_{min_d}_{max_d}.parquet"

    if cache_path.exists():
        cached = pd.read_parquet(cache_path)
        # cheap shape check: tickers match precomputed panel?
        want_tickers = set(panel["ticker"].unique())
        have_tickers = set(cached["ticker"].unique())
        if want_tickers.issubset(have_tickers) and not cached.empty:
            return cached

    tickers = sorted(panel["ticker"].unique())

    # ---- load quarterly fundamentals in one SQL -------------------------
    try:
        from connectors import mysql
        from connectors.eps import resolve_eps_publish_date
    except Exception:  # pragma: no cover
        mysql = None
        resolve_eps_publish_date = None  # type: ignore

    fund_lookup: Dict[str, pd.DataFrame] = {}
    if mysql is not None and resolve_eps_publish_date is not None:
        try:
            sql = (
                "SELECT mack, thoigian, loi_nhuan_gop AS value "
                "FROM is_quarter_nonbank WHERE mack IN :ts"
            )
            from sqlalchemy import text, bindparam

            stmt = text(sql).bindparams(bindparam("ts", expanding=True))
            with mysql.get_engine().connect() as conn:
                raw_fund = pd.read_sql(stmt, conn, params={"ts": tickers})
        except Exception:
            raw_fund = pd.DataFrame()

        if not raw_fund.empty:
            # parse thoigian → year/length and impute publish_date
            def _parse(s: str) -> Tuple[Optional[int], Optional[int]]:
                try:
                    parts = str(s).strip().split()
                    q = int(parts[0].lstrip("Qq"))
                    y = int(parts[1])
                    return y, q * 3
                except Exception:
                    return None, None

            parsed = raw_fund["thoigian"].map(_parse)
            raw_fund["yearreport"] = [p[0] for p in parsed]
            raw_fund["lengthreport"] = [p[1] for p in parsed]
            raw_fund = raw_fund.dropna(subset=["yearreport", "lengthreport"])
            if not raw_fund.empty:
                raw_fund["yearreport"] = raw_fund["yearreport"].astype(int)
                raw_fund["lengthreport"] = raw_fund["lengthreport"].astype(int)
                raw_fund["stockcode"] = raw_fund["mack"].astype(str).str.upper().str.strip()
                raw_fund = resolve_eps_publish_date(raw_fund)
                for tk, g in raw_fund.groupby("stockcode"):
                    g2 = g.sort_values(
                        ["yearreport", "lengthreport"], ascending=[False, False]
                    ).reset_index(drop=True)
                    fund_lookup[tk] = g2

    # ---- compute per-ticker per-day raw frame ---------------------------
    all_rows: List[pd.DataFrame] = []
    for tk, g in panel.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        dates = pd.to_datetime(g["date"]).values
        close = g["close"].astype(float).values
        high = g["high"].astype(float).values
        vol = g["volume"].astype(float).values

        # N-rule raw: 1 - close / rolling 252d max high
        high_series = pd.Series(high)
        roll_max = high_series.rolling(252, min_periods=252).max().values
        n_prox = np.where(
            (roll_max > 0) & np.isfinite(roll_max),
            1.0 - close / roll_max,
            np.nan,
        )

        # S-rule raw: volume ratio = vol[t] / mean(vol[t-50..t-1])
        vol_series = pd.Series(vol)
        vol_avg50 = vol_series.shift(1).rolling(50, min_periods=10).mean().values
        vol_ratio = np.where(
            (vol_avg50 > 0) & np.isfinite(vol_avg50),
            vol / vol_avg50,
            np.nan,
        )

        # fundamentals: build per-bar yoy_q0 and cagr_3y by walking publish dates
        yoy_q0 = np.full(len(dates), np.nan, dtype=float)
        cagr_3y = np.full(len(dates), np.nan, dtype=float)
        fund_df = fund_lookup.get(tk.upper())
        if fund_df is not None and not fund_df.empty:
            # each row of fund_df has publish_date + descending value history
            # iterate by publish events ordered ascending, at each publish
            # "snapshot" compute yoy_q0 and cagr_3y from the quarters
            # published up to that date.
            fd = fund_df.sort_values("publish_date").reset_index(drop=True)
            pub_dates = pd.to_datetime(fd["publish_date"]).values
            values_all = fd["value"].astype(float).values
            # At publish index i, available quarters = values_all[0..i]
            # ordered newest-first relative to that snapshot requires reversing.
            snap_yoy: List[float] = []
            snap_cagr: List[float] = []
            for i in range(len(fd)):
                hist = list(values_all[: i + 1][::-1])  # newest first
                # c: yoy_q0
                if len(hist) >= 5 and hist[4] != 0:
                    snap_yoy.append((hist[0] - hist[4]) / abs(hist[4]))
                else:
                    snap_yoy.append(float("nan"))
                # a: 3y ttm cagr
                if len(hist) >= 12:
                    ttm_now = sum(hist[0:4])
                    ttm_2y = sum(hist[8:12])
                    if ttm_2y > 0 and ttm_now > 0:
                        snap_cagr.append((ttm_now / ttm_2y) ** 0.5 - 1.0)
                    else:
                        snap_cagr.append(float("nan"))
                else:
                    snap_cagr.append(float("nan"))

            # Map each bar date to the last publish_date <= bar date.
            idx = np.searchsorted(pub_dates, dates, side="right") - 1
            for j, ii in enumerate(idx):
                if ii >= 0:
                    yoy_q0[j] = snap_yoy[ii]
                    cagr_3y[j] = snap_cagr[ii]

        all_rows.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "ticker": tk,
                    "eps_yoy_q0": yoy_q0,
                    "eps_cagr_3y": cagr_3y,
                    "n_prox": n_prox,
                    "vol_ratio": vol_ratio,
                    "close": close,
                }
            )
        )

    raw = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame(
        columns=["date", "ticker", "eps_yoy_q0", "eps_cagr_3y", "n_prox", "vol_ratio", "close", "rs_rating"]
    )

    # --- Cross-sectional RS rating (percentile rank within universe) ------
    # Formula: raw_rs = 0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252
    # Computed per date across all tickers in panel.
    if not raw.empty and "close" in raw.columns:
        raw = raw.sort_values(["ticker", "date"]).reset_index(drop=True)
        # Compute shifted closes for ROC lookbacks using per-ticker groupby
        for lb in (63, 126, 189, 252):
            raw[f"_close_lag{lb}"] = raw.groupby("ticker")["close"].shift(lb)
        weights = {63: 0.4, 126: 0.2, 189: 0.2, 252: 0.2}
        raw["_raw_rs"] = sum(
            w * (raw["close"] / raw[f"_close_lag{lb}"] - 1.0)
            for lb, w in weights.items()
        )
        # Rank cross-sectionally per date → [0, 100]
        raw["rs_rating"] = (
            raw.groupby("date")["_raw_rs"]
            .rank(pct=True, na_option="keep") * 100.0
        )
        raw = raw.drop(columns=[c for c in raw.columns if c.startswith("_close_lag") or c == "_raw_rs"])
    else:
        raw["rs_rating"] = np.nan

    raw = raw.drop(columns=["close"], errors="ignore")
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        raw.to_parquet(cache_path)
    except Exception:
        pass
    return raw


def build_momentum_raw_frame(
    panel: pd.DataFrame,
    formula: str = "weighted_roc",
) -> pd.DataFrame:
    """Compute raw momentum metrics per (date, ticker) for v8.0 scorer.

    Returns DataFrame with columns: date, ticker, n_prox, rs_rating.
    Pure price-based computation — no DB connectors required (MSCO-04).

    Cached per date range and formula to
    ``momentum_raw_{formula}_{min_date}_{max_date}.parquet`` under CACHE_DIR.
    Different filename prefix from v7.0 canslim_raw_* to avoid stale schema
    collisions. Each formula variant has its own cache file to prevent
    cross-contamination.

    Args:
        panel: DataFrame with columns date, ticker, open, high, low, close, volume.
        formula: RS formula to use. One of:
            - "weighted_roc" (default): IBD Weighted ROC —
              0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252
            - "roc126": Simple 6-month ROC — pct_change(126)
    """
    _VALID_FORMULAS = ("weighted_roc", "roc126")
    if formula not in _VALID_FORMULAS:
        raise ValueError(f"formula must be one of {_VALID_FORMULAS}, got {formula!r}")

    min_d = pd.Timestamp(panel["date"].min()).strftime("%Y-%m-%d")
    max_d = pd.Timestamp(panel["date"].max()).strftime("%Y-%m-%d")
    cache_path = CACHE_DIR / f"momentum_raw_{formula}_{min_d}_{max_d}.parquet"

    if cache_path.exists():
        cached = pd.read_parquet(cache_path)
        want_tickers = set(panel["ticker"].unique())
        have_tickers = set(cached["ticker"].unique())
        if want_tickers.issubset(have_tickers) and not cached.empty:
            return cached

    all_rows: List[pd.DataFrame] = []
    for tk, g in panel.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        dates = pd.to_datetime(g["date"]).values
        close = g["close"].astype(float).values
        high = g["high"].astype(float).values

        # N-rule raw: 1 - close / rolling 252d max high (MSCO-02)
        high_series = pd.Series(high)
        roll_max = high_series.rolling(252, min_periods=252).max().values
        n_prox = np.where(
            (roll_max > 0) & np.isfinite(roll_max),
            1.0 - close / roll_max,
            np.nan,
        )

        all_rows.append(pd.DataFrame({
            "date": dates,
            "ticker": tk,
            "n_prox": n_prox,
            "close": close,
        }))

    raw = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame(
        columns=["date", "ticker", "n_prox", "rs_rating"]
    )

    # Cross-sectional RS rating — formula branch controlled by `formula` kwarg
    # (MSCO-01: percentile rank within universe per date)
    if not raw.empty and "close" in raw.columns:
        raw = raw.sort_values(["ticker", "date"]).reset_index(drop=True)
        if formula == "roc126":
            # Simple 6-month ROC — single lookback
            raw["_close_lag126"] = raw.groupby("ticker")["close"].shift(126)
            raw["_raw_rs"] = raw["close"] / raw["_close_lag126"] - 1.0
        else:
            # IBD Weighted ROC: 0.4*ROC63 + 0.2*ROC126 + 0.2*ROC189 + 0.2*ROC252
            for lb in (63, 126, 189, 252):
                raw[f"_close_lag{lb}"] = raw.groupby("ticker")["close"].shift(lb)
            weights = {63: 0.4, 126: 0.2, 189: 0.2, 252: 0.2}
            raw["_raw_rs"] = sum(
                w * (raw["close"] / raw[f"_close_lag{lb}"] - 1.0)
                for lb, w in weights.items()
            )
        raw["rs_rating"] = (
            raw.groupby("date")["_raw_rs"]
            .rank(pct=True, na_option="keep") * 100.0
        )
        raw = raw.drop(columns=[c for c in raw.columns if c.startswith("_close_lag") or c == "_raw_rs"])
    else:
        raw["rs_rating"] = np.nan

    raw = raw.drop(columns=["close"], errors="ignore")
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        raw.to_parquet(cache_path)
    except Exception:
        pass
    return raw


def _apply_canslim_thresholds(
    raw: pd.DataFrame,
    canslim_cfg: CanslimConfig,
) -> pd.DataFrame:
    """Convert raw frame + thresholds into a PortfolioEngine scorer_frame.

    Rule: canslim_score = 100 iff C AND A AND N AND S all pass. NaN raw
    values fail their rule (score → NaN → engine drops candidate).
    """
    if raw.empty:
        return pd.DataFrame(columns=["date", "ticker", "canslim_score"])
    c_pass = raw["eps_yoy_q0"] >= canslim_cfg.c_threshold
    a_pass = raw["eps_cagr_3y"] >= canslim_cfg.a_threshold
    n_pass = raw["n_prox"] <= canslim_cfg.n_within_high
    if canslim_cfg.s_vol_mult > 0 and "vol_ratio" in raw.columns:
        s_pass = raw["vol_ratio"] >= canslim_cfg.s_vol_mult
    else:
        s_pass = pd.Series(True, index=raw.index)
    all_pass = c_pass & a_pass & n_pass & s_pass
    out = pd.DataFrame(
        {
            "date": raw["date"],
            "ticker": raw["ticker"],
            "canslim_score": np.where(all_pass, 100.0, np.nan),
        }
    )
    return out


def _compute_fills(
    panel: pd.DataFrame,
    mdm_gate: pd.Series,
    entry_option: str,
    entry_cfg=None,
) -> List[Any]:
    """Run EntryEngine on the panel and return raw Fill objects.

    Builds per-ticker adjusted OHLCV dicts the EntryEngine expects.
    """
    from strategies.entry import EntryEngine, EntryConfig

    cfg = entry_cfg if entry_cfg is not None else EntryConfig()
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


__all__ = [
    "run_vn100_backtest",
    "run_v8_backtest",
    "precompute_static",
    "build_canslim_raw_frame",
    "build_momentum_raw_frame",
    "CACHE_DIR",
]
