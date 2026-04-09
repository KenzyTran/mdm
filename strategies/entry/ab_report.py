"""A/B report — raw VN100 vs CANSLIM-qualified entry streams (ENTRY-05).

Implements D-16..D-19, D-21 from
``.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md``.

Runs :class:`strategies.entry.engine.EntryEngine` twice on the same price
panel and MDM state: once with ``canslim_scores=None`` (raw universe) and
once with a supplied CANSLIM scoreboard (CANSLIM-qualified). Per-detector
D-19 metrics are collected for each run and returned as a tidy
:class:`ABReport` dataclass.

The ``__main__`` block runs the report against real VN100 2014-2025 data
loaded from Postgres and emits the Markdown + CSV audit artefacts under
``docs/audits/phase30*``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pandas as pd

from strategies.entry.config import EntryConfig
from strategies.entry.engine import EntryEngine, Fill, FillList


REQUIRED_METRICS = [
    "total_fills",
    "unique_tickers",
    "windows_with_fills",
    "mean_fills_per_window",
    "days_since_buy_histogram",
    "ab_overlap_count",
]


@dataclass
class ABReport:
    """Side-by-side raw vs canslim A/B metric tables.

    ``raw`` and ``canslim_qualified`` are DataFrames indexed by detector
    (``"A"`` / ``"C"``) with columns listed in :data:`REQUIRED_METRICS`.
    ``raw_fills`` and ``canslim_fills`` hold the per-fill detail used to
    derive the metric tables (written to CSV by :func:`run_ab_report`).
    """

    raw: pd.DataFrame
    canslim_qualified: pd.DataFrame
    raw_fills: pd.DataFrame = field(default_factory=pd.DataFrame)
    canslim_fills: pd.DataFrame = field(default_factory=pd.DataFrame)
    date_range: tuple = (None, None)
    universe_size: int = 0


# ----------------------------------------------------------------- core helpers


def _fills_to_df(fills: FillList) -> pd.DataFrame:
    """Convert a FillList to a flat DataFrame (one row per fill)."""
    if not fills:
        return pd.DataFrame(
            columns=[
                "signal_date",
                "fill_date",
                "ticker",
                "detector",
                "fill_price",
                "window_id",
                "days_since_buy",
            ]
        )
    return pd.DataFrame([asdict(f) for f in fills])


def summarize_fills(
    fills_df: pd.DataFrame,
    n_windows: int,
    detector: str,
    ab_overlap_count: int,
) -> Dict[str, Any]:
    """Compute the six D-19 metrics for a single detector stream.

    Args:
        fills_df: Per-fill DataFrame already filtered to one detector.
        n_windows: Total number of BUY windows (denominator for
            ``mean_fills_per_window``). Use total windows (not just
            windows-with-fills) per D-19 convention.
        detector: ``"A"`` or ``"C"`` — included in the output for
            table assembly.
        ab_overlap_count: Cardinality of the ticker set that appears
            in BOTH detector streams within the same window. Computed
            externally by :func:`_compute_ab_overlap` so it is
            consistent across both rows.

    Returns:
        dict of D-19 metrics.
    """
    total = int(len(fills_df))
    unique_tickers = int(fills_df["ticker"].nunique()) if total else 0
    wwf = int(fills_df["window_id"].nunique()) if total else 0
    mean_fpw = float(total / n_windows) if n_windows > 0 else 0.0
    if total and "days_since_buy" in fills_df:
        hist_series = fills_df["days_since_buy"].value_counts().sort_index()
        hist = {int(k): int(v) for k, v in hist_series.items()}
    else:
        hist = {}
    return {
        "detector": detector,
        "total_fills": total,
        "unique_tickers": unique_tickers,
        "windows_with_fills": wwf,
        "mean_fills_per_window": mean_fpw,
        "days_since_buy_histogram": hist,
        "ab_overlap_count": ab_overlap_count,
    }


def _compute_ab_overlap(fills_df: pd.DataFrame) -> int:
    """Return cardinality of (ticker, window_id) pairs filled by BOTH A and C."""
    if fills_df.empty:
        return 0
    by_pair = fills_df.groupby(["ticker", "window_id"])["detector"].agg(set)
    both = by_pair.apply(lambda s: {"A", "C"}.issubset(s))
    return int(both.sum())


def _metric_table(fills_df: pd.DataFrame, n_windows: int) -> pd.DataFrame:
    """Build a per-detector metric table indexed by ``"A"``/``"C"``."""
    overlap = _compute_ab_overlap(fills_df)
    rows = []
    for det in ("A", "C"):
        sub = fills_df[fills_df["detector"] == det] if not fills_df.empty else fills_df
        rows.append(summarize_fills(sub, n_windows, det, overlap))
    table = pd.DataFrame(rows).set_index("detector")
    return table


# --------------------------------------------------------- top-level entry point


def build_ab_report(
    prices: Mapping[str, pd.DataFrame],
    mdm_state: pd.Series,
    canslim_scores: Optional[pd.DataFrame],
    config: EntryConfig,
) -> ABReport:
    """Run EntryEngine twice (raw + canslim) and assemble the A/B tables.

    Args:
        prices: Per-ticker adjusted OHLCV frames.
        mdm_state: MDM state series indexed by trading-day timestamp.
        canslim_scores: Optional per-(date, ticker) CANSLIM scoreboard.
            When ``None``, the canslim-qualified run mirrors the raw run
            (no-op filter).
        config: :class:`EntryConfig`.

    Returns:
        :class:`ABReport` with raw + canslim metric tables and per-fill
        detail frames.
    """
    # Raw run — no CANSLIM gate.
    engine_raw = EntryEngine(mdm_state=mdm_state, config=config, canslim_scores=None)
    raw_fills = engine_raw.run(prices)
    raw_fills_df = _fills_to_df(raw_fills)

    # CANSLIM-qualified run.
    engine_cs = EntryEngine(
        mdm_state=mdm_state, config=config, canslim_scores=canslim_scores
    )
    cs_fills = engine_cs.run(prices)
    cs_fills_df = _fills_to_df(cs_fills)

    n_windows = len(engine_raw.windows)
    raw_table = _metric_table(raw_fills_df, n_windows)
    cs_table = _metric_table(cs_fills_df, n_windows)

    # Date range for the report header (D-18).
    if len(mdm_state.index):
        date_range = (mdm_state.index[0], mdm_state.index[-1])
    else:
        date_range = (None, None)

    return ABReport(
        raw=raw_table,
        canslim_qualified=cs_table,
        raw_fills=raw_fills_df,
        canslim_fills=cs_fills_df,
        date_range=date_range,
        universe_size=len(prices),
    )


# --------------------------------------------------------------- report writers


_D13_NOTE = (
    "Phase 30 assumes every next-day open is tradable. T+2 / 7% ceiling-floor "
    "lock handling is deferred to Phase 31 per D-13."
)


def _format_metric_row(row: pd.Series) -> Dict[str, str]:
    """Format a metric row for markdown rendering (histograms compacted)."""
    out = {}
    for col in REQUIRED_METRICS:
        v = row.get(col)
        if col == "days_since_buy_histogram" and isinstance(v, dict):
            if v:
                out[col] = ", ".join(f"{k}:{n}" for k, n in sorted(v.items()))
            else:
                out[col] = "(empty)"
        elif isinstance(v, float):
            out[col] = f"{v:.3f}"
        else:
            out[col] = str(v)
    return out


def _render_table_md(table: pd.DataFrame, title: str) -> str:
    """Render a metric table as a markdown table."""
    lines = [f"#### {title}", ""]
    headers = ["detector"] + REQUIRED_METRICS
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for det, row in table.iterrows():
        fmt = _format_metric_row(row)
        lines.append("| " + det + " | " + " | ".join(fmt[c] for c in REQUIRED_METRICS) + " |")
    lines.append("")
    return "\n".join(lines)


def _render_histogram_md(table: pd.DataFrame, label: str) -> str:
    """Render per-detector days_since_buy histograms as a compact block."""
    lines = [f"#### Days-since-buy histogram — {label}", ""]
    for det, row in table.iterrows():
        hist = row.get("days_since_buy_histogram", {}) or {}
        body = ", ".join(f"{k}:{v}" for k, v in sorted(hist.items())) if hist else "(empty)"
        lines.append(f"- Option {det}: {body}")
    lines.append("")
    return "\n".join(lines)


def write_report_md(report: ABReport, output_path: Path, source_commit: str = "") -> None:
    """Write the A/B markdown report to ``output_path`` (D-21)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start, end = report.date_range
    start_s = start.date().isoformat() if start is not None else "?"
    end_s = end.date().isoformat() if end is not None else "?"

    lines: List[str] = []
    lines.append("# Phase 30 — Entry A/B Audit (Option A vs Option C)")
    lines.append("")
    if source_commit:
        lines.append(f"**Source commit:** `{source_commit}`")
    lines.append(f"**MDM state coverage:** {start_s} → {end_s}  (D-18)")
    lines.append(f"**Universe size (tickers with loadable prices):** {report.universe_size}")
    lines.append("")
    lines.append(f"> {_D13_NOTE}")
    lines.append("")
    lines.append("## Side-by-side metrics")
    lines.append("")
    lines.append(_render_table_md(report.raw, "Raw VN100 (no CANSLIM gate) — Option A and Option C"))
    lines.append(_render_table_md(report.canslim_qualified, "CANSLIM-qualified — Option A and Option C"))
    lines.append("## Days-since-buy distribution")
    lines.append("")
    lines.append(_render_histogram_md(report.raw, "Raw"))
    lines.append(_render_histogram_md(report.canslim_qualified, "CANSLIM-qualified"))
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_ab_report(
    prices: Mapping[str, pd.DataFrame],
    mdm_state: pd.Series,
    canslim_scores: Optional[pd.DataFrame],
    config: EntryConfig,
    output_dir: Path,
    source_commit: str = "",
) -> ABReport:
    """Build the report, write MD + CSVs under ``output_dir``.

    Layout:
        - ``{output_dir}/phase30-entry-ab.md``
        - ``{output_dir}/phase30/entry_ab_raw_vn100.csv``
        - ``{output_dir}/phase30/entry_ab_canslim.csv``
    """
    output_dir = Path(output_dir)
    (output_dir / "phase30").mkdir(parents=True, exist_ok=True)

    report = build_ab_report(prices, mdm_state, canslim_scores, config)

    report.raw_fills.to_csv(output_dir / "phase30" / "entry_ab_raw_vn100.csv", index=False)
    report.canslim_fills.to_csv(output_dir / "phase30" / "entry_ab_canslim.csv", index=False)
    write_report_md(report, output_dir / "phase30-entry-ab.md", source_commit=source_commit)
    return report


__all__ = [
    "ABReport",
    "REQUIRED_METRICS",
    "build_ab_report",
    "run_ab_report",
    "summarize_fills",
    "write_report_md",
]


# ----------------------------------------------------------- live VN100 runner


def _live_vn100_run(
    start: str = "2014-01-01",
    end: str = "2025-12-31",
    output_dir: Path = Path("docs/audits"),
    canslim_max_dates: int | None = 80,
) -> None:
    """Run the A/B report against live VN100 2014-2025 Postgres data.

    Loads VN30 index prices via ``core.data_loader.DataLoader``, runs
    ``strategies.mdm_hybrid.HybridEngine`` once to get the state series,
    loads VN100 per-ticker adjusted OHLCV via Postgres, calls
    :class:`strategies.canslim.CanslimScorer` per unique signal-bar date
    for the CANSLIM-qualified run, and writes the MD + CSV artefacts.
    """
    import subprocess

    from core.data_loader import DataLoader
    from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
    from strategies.mdm_hybrid.config import HybridConfig
    from strategies.canslim.universe import UniverseLoader
    from connectors.postgres import get_engine, load_stock_eod
    from connectors.adjust import adjust_ohlc

    try:
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        source_commit = ""

    import sys
    # Force unbuffered stdout so background harnesses stream progress.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    print(f"[ab_report] loading VN30 index for MDM state ({start}..{end})", flush=True)
    vn30 = DataLoader("vn30").load()
    vn30 = vn30[(vn30["date"] >= start) & (vn30["date"] <= end)].reset_index(drop=True)

    print("[ab_report] running HybridEngine to derive MDM state series", flush=True)
    engine = HybridEngine(HybridConfig(filter_enabled=True))
    hybrid_out = engine.run(vn30)
    mdm_state = pd.Series(
        hybrid_out["state"].values,
        index=pd.to_datetime(hybrid_out["date"]).values,
        name="state",
    )
    mdm_state.index = pd.DatetimeIndex(mdm_state.index)

    print("[ab_report] resolving VN100 universe via UniverseLoader", flush=True)
    pg = get_engine()
    universe = sorted(
        UniverseLoader(mode="current-vn100", pg_engine=pg).get(pd.Timestamp(end).date())
    )
    print(f"[ab_report] universe size = {len(universe)}", flush=True)

    print("[ab_report] loading per-ticker OHLCV panel from stock_eod", flush=True)
    panel = load_stock_eod(universe, start, end)
    prices: Dict[str, pd.DataFrame] = {}
    if not panel.empty:
        for ticker, sub in panel.groupby("stockcode"):
            sub = sub.sort_values("tradingdate").copy()
            adj = adjust_ohlc(sub)
            adj.index = pd.DatetimeIndex(adj["tradingdate"])
            adj["totalvol"] = adj["totalvol"].astype(float)
            prices[str(ticker).upper()] = adj[
                ["adj_open", "adj_high", "adj_low", "adj_close", "totalvol"]
            ]
    print(f"[ab_report] loaded prices for {len(prices)} tickers", flush=True)

    # CANSLIM scores — build per unique raw signal-bar date for efficiency.
    # Instantiate a scorer and call .score(d) for each date the raw run touches.
    print("[ab_report] pre-running raw engine to identify signal-bar dates", flush=True)
    config = EntryConfig()
    raw_engine = EntryEngine(mdm_state=mdm_state, config=config, canslim_scores=None)
    raw_fills_pre = raw_engine.run(prices)
    signal_dates_all = sorted(
        {pd.Timestamp(f.signal_date) for f in raw_fills_pre}
        | {pd.Timestamp(u.signal_date) for u in raw_fills_pre.unfilled}
    )
    print(f"[ab_report] {len(signal_dates_all)} unique signal-bar dates (raw)", flush=True)
    # Sub-sample dates if cap supplied — per-date CANSLIM scoring is the
    # bottleneck at ~seconds/date; full coverage may take hours. Subsample
    # keeps the live audit O(minutes) while preserving signal diversity.
    if canslim_max_dates is not None and len(signal_dates_all) > canslim_max_dates:
        step = len(signal_dates_all) / canslim_max_dates
        signal_dates = [signal_dates_all[int(i * step)] for i in range(canslim_max_dates)]
        print(
            f"[ab_report] sub-sampled {len(signal_dates)}/{len(signal_dates_all)} "
            f"dates for CANSLIM scoring (cap={canslim_max_dates})",
            flush=True,
        )
    else:
        signal_dates = signal_dates_all

    canslim_scores: Optional[pd.DataFrame] = None
    if signal_dates:
        try:
            from strategies.canslim.scorer import CanslimScorer
            from strategies.canslim.config import CanslimConfig
            from strategies.canslim.sectors import SectorRouter
            from connectors.mysql import get_engine as get_mysql_engine

            ul = UniverseLoader(mode="current-vn100", pg_engine=pg)
            sr = SectorRouter.from_postgres(pg, sector_column="nhom")
            scorer = CanslimScorer(
                config=CanslimConfig(),
                universe_loader=ul,
                sector_router=sr,
                pg_engine=pg,
                mysql_engine=get_mysql_engine(),
            )
            frames = []
            for i, d in enumerate(signal_dates):
                try:
                    frame = scorer.score(d.date())
                    if frame is not None and not frame.empty:
                        frames.append(frame)
                except Exception as exc:
                    print(f"[ab_report]", flush=True); print(f"[ab_report] scorer.score({d.date()}) failed: {exc}", flush=True)
                if (i + 1) % 5 == 0:
                    print(f"[ab_report]", flush=True); print(f"[ab_report] scored {i + 1}/{len(signal_dates)} dates", flush=True)
            if frames:
                canslim_scores = pd.concat(frames, ignore_index=True)
                print(f"[ab_report]", flush=True); print(f"[ab_report] canslim_scores: {len(canslim_scores)} rows")
        except Exception as exc:
            print(f"[ab_report]", flush=True); print(f"[ab_report] CANSLIM scoring unavailable: {exc}")

    print(f"[ab_report]", flush=True); print(f"[ab_report] building A/B report -> {output_dir}")
    report = run_ab_report(
        prices=prices,
        mdm_state=mdm_state,
        canslim_scores=canslim_scores,
        config=config,
        output_dir=output_dir,
        source_commit=source_commit,
    )
    print("[ab_report] DONE")
    print("  raw table:")
    print(report.raw)
    print("  canslim-qualified table:")
    print(report.canslim_qualified)


if __name__ == "__main__":
    _live_vn100_run()
