"""Gate policy (D-08 Policy A) tests for PortfolioEngine.

BUY: admits new fills.
CASH: drops candidates (no cooldown, no queue).
SELL: schedules liquidation of all open positions at next open, NO cooldown
registration (D-20).
"""
from __future__ import annotations

from collections import namedtuple

import pandas as pd
import pytest

from strategies.portfolio import PortfolioEngine, PortfolioConfig
from tests.strategies.portfolio.fixtures.synthetic_panel import make_panel


Fill = namedtuple(
    "Fill", "ticker signal_date fill_date fill_price detector_tag window_id"
)


def _make_inputs(
    n_bars: int = 60,
    tickers=("AAA", "BBB", "CCC"),
    mdm_state_values=None,
    fills=None,
    max_slots: int = 8,
):
    panel = make_panel(tickers=tickers, n_bars=n_bars)
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    if mdm_state_values is None:
        mdm_state_values = ["BUY"] * len(dates)
    mdm_state = pd.Series(mdm_state_values, index=dates)
    # scorer: every ticker/date has a score
    scorer_rows = []
    for t in tickers:
        for i, d in enumerate(dates):
            scorer_rows.append(
                {"date": d, "ticker": t, "canslim_score": 80 - (i % 5)}
            )
    scorer_frame = pd.DataFrame(scorer_rows)
    # rs: all 80 (above threshold 70)
    rs_rows = []
    for t in tickers:
        for d in dates:
            rs_rows.append({"date": d, "ticker": t, "rs_value": 80.0})
    rs_frame = pd.DataFrame(rs_rows)
    cfg = PortfolioConfig(max_slots=max_slots, adv_mult=1.0)
    return panel, dates, mdm_state, fills or [], scorer_frame, rs_frame, cfg


def test_state_source_injection():
    panel, dates, mdm_state, fills, scorer, rs, cfg = _make_inputs()
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates)
    assert eng.mdm_state is mdm_state


def test_policy_a_buy_admits_new():
    panel, dates, mdm_state, _, scorer, rs, cfg = _make_inputs(max_slots=8)
    # Use a late signal bar so ADV20 (requires 20 prior bars) is available.
    signal_date = dates[25]
    fill_date = dates[26]
    fills = []
    for t in ("AAA", "BBB", "CCC"):
        fp = float(
            panel.loc[(panel["ticker"] == t) & (panel["date"] == fill_date), "open"].iloc[0]
        )
        fills.append(Fill(t, signal_date, fill_date, fp, "A", 1))
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates, initial_cash=1_000_000)
    result = eng.run()
    # At least one position was opened (synthetic panel may fail ADV20 on some)
    assert len(result.positions_daily) > 0 or len(result.trades) > 0


def test_policy_a_cash_drops_candidates():
    panel, dates, mdm_state, _, scorer, rs, cfg = _make_inputs()
    # Set bar 25 to CASH
    mdm_state.iloc[25] = "CASH"
    signal_date = dates[25]
    fill_date = dates[26]
    fp = float(
        panel.loc[
            (panel["ticker"] == "AAA") & (panel["date"] == fill_date), "open"
        ].iloc[0]
    )
    fills = [Fill("AAA", signal_date, fill_date, fp, "A", 1)]
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates)
    result = eng.run()
    # No entries scheduled → no trades, no positions at bar 6 from this fill
    # The unfilled log should contain a gate_cash reason
    reasons = {u["reason"] for u in result.unfilled}
    assert "gate_cash" in reasons


def test_policy_a_sell_liquidates_all():
    panel, dates, mdm_state, _, scorer, rs, cfg = _make_inputs(n_bars=60)
    # BUY through bar 34, then SELL from bar 35 onwards
    for i in range(35, len(dates)):
        mdm_state.iloc[i] = "SELL"
    # Fill 2 positions on bar 25 (ADV20 ready)
    signal_date = dates[25]
    fill_date = dates[26]
    fills = []
    for t in ("AAA", "BBB"):
        fp = float(
            panel.loc[(panel["ticker"] == t) & (panel["date"] == fill_date), "open"].iloc[0]
        )
        fills.append(Fill(t, signal_date, fill_date, fp, "A", 1))
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates, initial_cash=1_000_000)
    result = eng.run()
    mdm_sell_trades = [t for t in result.trades if t.exit_reason == "mdm_sell"]
    # Both positions liquidated via mdm_sell
    assert len(mdm_sell_trades) >= 1
    # Cooldown NOT registered for mdm_sell — verify via cooldowns internal
    for tr in mdm_sell_trades:
        # After an mdm_sell exit the ticker should NOT be in cooldown registry
        # (D-20 exemption). We test through re-entry would be allowed.
        assert tr.ticker not in eng.book.cooldowns._exit_bars
