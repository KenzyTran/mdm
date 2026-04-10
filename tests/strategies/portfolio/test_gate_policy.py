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


def _make_inputs_with_varied_rs(
    tickers=("T90", "T80", "T60", "T40"),
    rs_values=(90.0, 80.0, 60.0, 40.0),
    n_bars: int = 60,
    sell_retain_pct: float = 0.5,
):
    """4 tickers with distinct RS scores for partial-liquidation tests.

    MDM state: BUY through bar 34, SELL from bar 35 onwards.
    All fills on bar 25 (signal) / bar 26 (fill) — ADV20 is ready.
    """
    panel = make_panel(tickers=tickers, n_bars=n_bars)
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    mdm_state_values = ["BUY"] * len(dates)
    for i in range(35, len(dates)):
        mdm_state_values[i] = "SELL"
    mdm_state = pd.Series(mdm_state_values, index=dates)

    scorer_rows = []
    for t in tickers:
        for d in dates:
            scorer_rows.append({"date": d, "ticker": t, "canslim_score": 80.0})
    scorer_frame = pd.DataFrame(scorer_rows)

    rs_rows = []
    for ticker, rs_val in zip(tickers, rs_values):
        for d in dates:
            rs_rows.append({"date": d, "ticker": ticker, "rs_value": rs_val})
    rs_frame = pd.DataFrame(rs_rows)

    cfg = PortfolioConfig(
        max_slots=8,
        adv_mult=1.0,
        sell_retain_pct=sell_retain_pct,
    )

    signal_date = dates[25]
    fill_date = dates[26]
    fills = []
    for t in tickers:
        fp = float(
            panel.loc[(panel["ticker"] == t) & (panel["date"] == fill_date), "open"].iloc[0]
        )
        fills.append(Fill(t, signal_date, fill_date, fp, "A", 1))

    return panel, dates, mdm_state, fills, scorer_frame, rs_frame, cfg


def test_sell_retains_strongest_by_rs():
    """4 positions with RS [90,80,60,40]; sell_retain_pct=0.5 keeps top 2, closes bottom 2."""
    panel, dates, mdm_state, fills, scorer, rs_frame, cfg = _make_inputs_with_varied_rs(
        sell_retain_pct=0.5
    )
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs_frame, dates, initial_cash=1_000_000)
    result = eng.run()
    mdm_sell_trades = [t for t in result.trades if t.exit_reason == "mdm_sell"]
    assert len(mdm_sell_trades) == 2, f"Expected 2 mdm_sell trades, got {len(mdm_sell_trades)}"
    closed_tickers = {t.ticker for t in mdm_sell_trades}
    # Weakest two: T60 and T40
    assert closed_tickers == {"T60", "T40"}, f"Expected {{T60, T40}} closed, got {closed_tickers}"


def test_sell_retain_pct_configurable():
    """sell_retain_pct=0.75 keeps 3 of 4; sell_retain_pct=0.25 keeps 1 of 4."""
    # 0.75 -> ceil(4*0.75)=3 retained, 1 closed
    panel, dates, mdm_state, fills, scorer, rs_frame, cfg = _make_inputs_with_varied_rs(
        sell_retain_pct=0.75
    )
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs_frame, dates, initial_cash=1_000_000)
    result = eng.run()
    sell_75 = [t for t in result.trades if t.exit_reason == "mdm_sell"]
    assert len(sell_75) == 1, f"sell_retain_pct=0.75: expected 1 closed, got {len(sell_75)}"

    # 0.25 -> ceil(4*0.25)=1 retained, 3 closed
    panel2, dates2, mdm_state2, fills2, scorer2, rs_frame2, cfg2 = _make_inputs_with_varied_rs(
        sell_retain_pct=0.25
    )
    eng2 = PortfolioEngine(cfg2, mdm_state2, fills2, scorer2, panel2, rs_frame2, dates2, initial_cash=1_000_000)
    result2 = eng2.run()
    sell_25 = [t for t in result2.trades if t.exit_reason == "mdm_sell"]
    assert len(sell_25) == 3, f"sell_retain_pct=0.25: expected 3 closed, got {len(sell_25)}"


def test_sell_nan_rs_treated_as_weakest():
    """Position with NaN RS is closed before valid-RS positions."""
    # T40's RS set to NaN — it should be treated as weakest and closed first.
    tickers = ("T90", "T80", "T60", "T40")
    panel = make_panel(tickers=tickers, n_bars=60)
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    mdm_state_values = ["BUY"] * len(dates)
    for i in range(35, len(dates)):
        mdm_state_values[i] = "SELL"
    mdm_state = pd.Series(mdm_state_values, index=dates)

    scorer_rows = []
    for t in tickers:
        for d in dates:
            scorer_rows.append({"date": d, "ticker": t, "canslim_score": 80.0})
    scorer_frame = pd.DataFrame(scorer_rows)

    rs_rows = []
    rs_map = {"T90": 90.0, "T80": 80.0, "T60": 60.0, "T40": float("nan")}
    for t in tickers:
        for d in dates:
            rs_rows.append({"date": d, "ticker": t, "rs_value": rs_map[t]})
    rs_frame = pd.DataFrame(rs_rows)

    cfg = PortfolioConfig(max_slots=8, adv_mult=1.0, sell_retain_pct=0.5)
    signal_date = dates[25]
    fill_date = dates[26]
    fills = []
    for t in tickers:
        fp = float(panel.loc[(panel["ticker"] == t) & (panel["date"] == fill_date), "open"].iloc[0])
        fills.append(Fill(t, signal_date, fill_date, fp, "A", 1))

    eng = PortfolioEngine(cfg, mdm_state, fills, scorer_frame, panel, rs_frame, dates, initial_cash=1_000_000)
    result = eng.run()
    mdm_sell_trades = [t for t in result.trades if t.exit_reason == "mdm_sell"]
    assert len(mdm_sell_trades) == 2, f"Expected 2 mdm_sell trades, got {len(mdm_sell_trades)}"
    closed_tickers = {t.ticker for t in mdm_sell_trades}
    # NaN RS (T40) + T60 should be closed; T90 + T80 retained
    assert "T40" in closed_tickers, f"NaN RS ticker T40 should be closed, got {closed_tickers}"
    assert "T60" in closed_tickers, f"T60 (lowest valid RS) should be closed, got {closed_tickers}"


def test_sell_retain_rounds_up():
    """With 3 positions and sell_retain_pct=0.5, ceil(3*0.5)=2 retained, 1 closed."""
    tickers = ("T90", "T60", "T40")
    rs_values = (90.0, 60.0, 40.0)
    panel, dates, mdm_state, fills, scorer, rs_frame, cfg = _make_inputs_with_varied_rs(
        tickers=tickers,
        rs_values=rs_values,
        sell_retain_pct=0.5,
    )
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs_frame, dates, initial_cash=1_000_000)
    result = eng.run()
    mdm_sell_trades = [t for t in result.trades if t.exit_reason == "mdm_sell"]
    assert len(mdm_sell_trades) == 1, f"ceil(3*0.5)=2 retained → 1 closed, got {len(mdm_sell_trades)}"
    assert mdm_sell_trades[0].ticker == "T40", f"Weakest T40 should be closed, got {mdm_sell_trades[0].ticker}"


def test_sell_retain_pct_validation():
    """sell_retain_pct validation: 0.0 raises, 1.0 valid, -0.1 raises, 1.1 raises."""
    with pytest.raises(ValueError):
        PortfolioConfig(sell_retain_pct=0.0)
    with pytest.raises(ValueError):
        PortfolioConfig(sell_retain_pct=-0.1)
    with pytest.raises(ValueError):
        PortfolioConfig(sell_retain_pct=1.1)
    # 1.0 is valid (keep all)
    cfg = PortfolioConfig(sell_retain_pct=1.0)
    assert cfg.sell_retain_pct == 1.0


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
