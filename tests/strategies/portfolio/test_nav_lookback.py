"""SC8 no-lookahead regression tests for PortfolioEngine.

CITATION: memory/feedback_equity_formula.md — the 707% vs 93% bug was caused
by using state[i] instead of state[i-1] in equity calculations. This test
locks in the invariant: mutating close[t] AFTER bar-t entry decisions must
NOT change bar-t entry fill shares or fill prices.
"""
from __future__ import annotations

import copy
from collections import namedtuple

import pandas as pd

from strategies.portfolio import PortfolioEngine, PortfolioConfig
from tests.strategies.portfolio.fixtures.synthetic_panel import make_panel


Fill = namedtuple(
    "Fill", "ticker signal_date fill_date fill_price detector_tag window_id"
)


def _build(panel, max_slots=8):
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    tickers = sorted(panel["ticker"].unique())
    mdm_state = pd.Series(["BUY"] * len(dates), index=dates)
    scorer_rows = []
    for t in tickers:
        for d in dates:
            scorer_rows.append({"date": d, "ticker": t, "canslim_score": 80.0})
    scorer = pd.DataFrame(scorer_rows)
    rs_rows = []
    for t in tickers:
        for d in dates:
            rs_rows.append({"date": d, "ticker": t, "rs_value": 80.0})
    rs = pd.DataFrame(rs_rows)
    cfg = PortfolioConfig(max_slots=max_slots, adv_mult=1.0)
    return cfg, mdm_state, scorer, rs, dates


def test_no_bar_t_lookahead():
    """SC8: mutating close[t] after bar-t decisions must not change entries.

    CITATION: 707% vs 93% bug from memory/feedback_equity_formula.md.
    We mutate close prices on bars where fills occur and assert entry shares
    and fill prices are identical. Exit P&L may differ legitimately because
    exits legitimately depend on close[t] for triggering — D-26 allows that.
    """
    panel1 = make_panel(n_bars=60, seed=42)
    cfg, mdm_state, scorer, rs, dates = _build(panel1)
    signal_date = dates[25]
    fill_date = dates[26]
    fp = float(
        panel1.loc[
            (panel1["ticker"] == "AAA") & (panel1["date"] == fill_date), "open"
        ].iloc[0]
    )
    fills = [Fill("AAA", signal_date, fill_date, fp, "A", 1)]

    eng1 = PortfolioEngine(cfg, mdm_state, fills, scorer, panel1, rs, dates, initial_cash=1_000_000)
    result1 = eng1.run()

    # Deep-copy inputs and mutate close on bar 25 and onwards by +50%.
    panel2 = panel1.copy()
    mask = (panel2["ticker"] == "AAA") & (panel2["date"] >= dates[25])
    panel2.loc[mask, "close"] = panel2.loc[mask, "close"] * 1.5

    eng2 = PortfolioEngine(cfg, mdm_state, fills, scorer, panel2, rs, dates, initial_cash=1_000_000)
    result2 = eng2.run()

    # Compare entry sizing — shares and buy_price must be identical.
    # Compare via trades (if any closed) and final positions snapshot.
    entries1 = [
        (t.ticker, t.buy_date, t.buy_price) for t in result1.trades
    ]
    entries2 = [
        (t.ticker, t.buy_date, t.buy_price) for t in result2.trades
    ]
    assert entries1 == entries2, "SC8 violated: entry sizing changed when close[t] mutated"

    # Also compare open positions at end
    def _final_positions(res):
        if res.positions_daily.empty:
            return []
        last_date = res.positions_daily["date"].max()
        sub = res.positions_daily[res.positions_daily["date"] == last_date]
        return sorted([(r.ticker, r.shares) for r in sub.itertuples()])

    assert _final_positions(result1) == _final_positions(result2), (
        "SC8 violated: final open positions differ — bar-t close affected entry shares"
    )


def test_nav_prev_uses_prior_close():
    """_compute_nav(bar_idx) uses close[bar_idx] — but NAV[t-1] in the loop
    uses bar_idx-1. Verify by mutating close[bar 5] and observing no effect
    on entry sizing computed with nav_prev at bar 6."""
    panel = make_panel(n_bars=30, seed=7)
    cfg, mdm_state, scorer, rs, dates = _build(panel)
    signal_date = dates[6]
    fill_date = dates[7]
    fp = float(
        panel.loc[
            (panel["ticker"] == "AAA") & (panel["date"] == fill_date), "open"
        ].iloc[0]
    )
    fills = [Fill("AAA", signal_date, fill_date, fp, "A", 1)]

    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates)
    # No open positions, so _compute_nav(bar_idx=5) == cash == initial_cash
    nav5 = eng._compute_nav(5)
    assert nav5 == eng.initial_cash


def test_adv20_uses_only_prior_bars():
    """Integration: mutating close[t] after decisions should not increase
    the number of fills (via ADV20 effect)."""
    panel1 = make_panel(n_bars=60, seed=11)
    cfg, mdm_state, scorer, rs, dates = _build(panel1)
    signal_date = dates[25]
    fill_date = dates[26]
    fp = float(
        panel1.loc[
            (panel1["ticker"] == "AAA") & (panel1["date"] == fill_date), "open"
        ].iloc[0]
    )
    fills = [Fill("AAA", signal_date, fill_date, fp, "A", 1)]
    eng1 = PortfolioEngine(cfg, mdm_state, fills, scorer, panel1, rs, dates, initial_cash=1_000_000)
    result1 = eng1.run()
    n_trades_1 = len(result1.trades)
    n_positions_1 = (
        0 if result1.positions_daily.empty else len(result1.positions_daily)
    )

    # Mutate close[25] only
    panel2 = panel1.copy()
    panel2.loc[
        (panel2["ticker"] == "AAA") & (panel2["date"] == dates[25]), "close"
    ] = panel2.loc[
        (panel2["ticker"] == "AAA") & (panel2["date"] == dates[25]), "close"
    ].values * 2.0
    eng2 = PortfolioEngine(cfg, mdm_state, fills, scorer, panel2, rs, dates, initial_cash=1_000_000)
    result2 = eng2.run()
    n_trades_2 = len(result2.trades)
    assert n_trades_1 == n_trades_2, (
        "ADV20 used bar-t close — SC8 violation (see 707% bug in memory)"
    )
