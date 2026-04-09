"""ENTRY-05 A/B report tests — RED stubs (Wave 0).

Pins D-16..D-19 metric columns: total_fills, unique_tickers, windows_with_fills,
mean_fills_per_window, days_since_buy_histogram, ab_overlap_count.
"""
from __future__ import annotations

import pytest

pytest.importorskip(
    "strategies.entry.ab_report",
    reason="30-03 not yet implemented",
)

from strategies.entry.ab_report import build_ab_report  # noqa: E402
from strategies.entry.config import EntryConfig  # noqa: E402


REQUIRED_METRICS = {
    "total_fills",
    "unique_tickers",
    "windows_with_fills",
    "mean_fills_per_window",
    "days_since_buy_histogram",
    "ab_overlap_count",
}


def test_ab_report_runs_twice_and_produces_required_columns(
    make_ohlcv, make_buy_breakout_bar, make_mdm_state
):
    df_a = make_ohlcv(n_bars=260, seed=1)
    df_b = make_ohlcv(n_bars=260, seed=2)
    df_a = make_buy_breakout_bar(df_a, 255)
    df_b = make_buy_breakout_bar(df_b, 250)

    state = make_mdm_state(df_a.index, [(df_a.index[240], "BUY")], initial="CASH")

    # canslim_scores=None -> raw; scores=something -> qualified
    report = build_ab_report(
        prices={"AAA": df_a, "BBB": df_b},
        mdm_state=state,
        canslim_scores=None,  # report helper runs twice internally per D-16
        config=EntryConfig(),
    )

    # Two tables present
    assert hasattr(report, "raw")
    assert hasattr(report, "canslim_qualified")

    for table in (report.raw, report.canslim_qualified):
        # Per-detector rows (A, C) with all required metrics as columns
        assert set(table.columns) >= REQUIRED_METRICS
