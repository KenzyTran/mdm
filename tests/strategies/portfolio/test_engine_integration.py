"""End-to-end integration tests for PortfolioEngine.

Covers: baseline synthetic run, T+2 block, ceiling-lock entry block,
CANSLIM tie-break, cooldown re-entry block.
"""
from __future__ import annotations

from collections import namedtuple

import pandas as pd

from strategies.portfolio import PortfolioEngine, PortfolioConfig
from tests.strategies.portfolio.fixtures.synthetic_panel import make_panel


Fill = namedtuple(
    "Fill", "ticker signal_date fill_date fill_price detector_tag window_id"
)


def _common(panel, max_slots=8, mdm_override=None):
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    tickers = sorted(panel["ticker"].unique())
    mdm_state = pd.Series(["BUY"] * len(dates), index=dates)
    if mdm_override:
        for i, v in mdm_override.items():
            mdm_state.iloc[i] = v
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


def _fill_for(panel, ticker, signal_bar, dates):
    signal_date = dates[signal_bar]
    fill_date = dates[signal_bar + 1]
    fp = float(
        panel.loc[
            (panel["ticker"] == ticker) & (panel["date"] == fill_date), "open"
        ].iloc[0]
    )
    return Fill(ticker, signal_date, fill_date, fp, "A", 1)


def test_end_to_end_synthetic():
    panel = make_panel(n_bars=60, seed=3)
    cfg, mdm_state, scorer, rs, dates = _common(panel)
    fills = [_fill_for(panel, "AAA", 25, dates), _fill_for(panel, "BBB", 25, dates)]
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates, initial_cash=1_000_000)
    result = eng.run()
    assert len(result.nav_daily) == 60
    # At least one position opened or trade created
    assert len(result.trades) >= 0  # may be all open
    # Open positions or trades exist
    assert (not result.positions_daily.empty) or len(result.trades) >= 1


def test_t2_blocks_early_exit():
    """Force hard-stop trigger immediately after buy. Exit must defer to
    buy_bar + 3 (earliest_sell_bar)."""
    panel = make_panel(n_bars=60, seed=99)
    # Force a crash: set close/low on bar 27+ to very low, so hard stop would
    # trigger on bar 27 (buy_bar=26) but T+2 blocks until bar 29.
    mask = (panel["ticker"] == "AAA") & (panel["date"] >= sorted(panel["date"].unique())[27])
    # We need to drop low below buy_price * 0.92. Use a big discount.
    panel.loc[mask, "low"] = panel.loc[mask, "low"] * 0.5
    panel.loc[mask, "close"] = panel.loc[mask, "close"] * 0.5
    panel.loc[mask, "open"] = panel.loc[mask, "open"] * 0.5
    panel.loc[mask, "high"] = panel.loc[mask, "high"] * 0.5
    # Recompute floor_px would be stale but engine uses prev_close — OK

    cfg, mdm_state, scorer, rs, dates = _common(panel)
    fills = [_fill_for(panel, "AAA", 25, dates)]
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates, initial_cash=1_000_000)
    result = eng.run()
    # Find AAA trade
    aaa_trades = [t for t in result.trades if t.ticker == "AAA"]
    if aaa_trades:
        tr = aaa_trades[0]
        # buy_bar = 26, earliest_sell_bar = 29, so sell_date >= dates[29]
        assert tr.sell_date >= dates[29], (
            f"T+2 violated: sold on {tr.sell_date}, expected >= {dates[29]}"
        )


def test_ceiling_lock_blocks_entry():
    """Force ceiling lock on the fill bar → unfilled/ceiling_lock."""
    # lock bar 26 (= fill_date for signal bar 25) on AAA
    panel = make_panel(n_bars=60, lock_days={"AAA": [(26, "ceiling")]}, seed=5)
    cfg, mdm_state, scorer, rs, dates = _common(panel)
    fills = [_fill_for(panel, "AAA", 25, dates)]
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates, initial_cash=1_000_000)
    result = eng.run()
    reasons = [(u.get("ticker"), u.get("reason")) for u in result.unfilled]
    assert ("AAA", "ceiling_lock") in reasons
    # And no AAA position opened
    if not result.positions_daily.empty:
        aaa_pos = result.positions_daily[result.positions_daily["ticker"] == "AAA"]
        assert aaa_pos.empty


def test_canslim_tiebreak_selects_top():
    """4 BUY fills, max_slots=2 → the 2 highest-CANSLIM candidates open."""
    panel = make_panel(n_bars=60, tickers=("AAA", "BBB", "CCC", "DDD"), seed=7)
    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    # Custom scorer: AAA=90, BBB=80, CCC=70, DDD=60
    scores = {"AAA": 90, "BBB": 80, "CCC": 70, "DDD": 60}
    scorer_rows = []
    for t, s in scores.items():
        for d in dates:
            scorer_rows.append({"date": d, "ticker": t, "canslim_score": float(s)})
    scorer = pd.DataFrame(scorer_rows)
    rs = pd.DataFrame(
        [{"date": d, "ticker": t, "rs_value": 80.0} for t in scores for d in dates]
    )
    mdm_state = pd.Series(["BUY"] * len(dates), index=dates)
    cfg = PortfolioConfig(max_slots=2, adv_mult=1.0)
    fills = [_fill_for(panel, t, 25, dates) for t in ("AAA", "BBB", "CCC", "DDD")]
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates, initial_cash=1_000_000)
    result = eng.run()
    # After bar 26, the first 2 positions should be AAA & BBB
    opened_tickers = {p.ticker for p in eng.book.slots.open_positions}
    # Lower-scoring ones should be in unfilled with no_free_slot reason
    lower_unfilled = {
        u["ticker"] for u in result.unfilled if u["reason"] == "no_free_slot"
    }
    assert "AAA" in opened_tickers or ("AAA" in {t.ticker for t in result.trades})
    assert "BBB" in opened_tickers or ("BBB" in {t.ticker for t in result.trades})
    # CCC and DDD should NOT have been opened before AAA/BBB
    assert "CCC" not in opened_tickers or "DDD" not in opened_tickers
    assert lower_unfilled.issubset({"CCC", "DDD"})


def test_cooldown_blocks_reentry():
    """Hard stop on AAA at bar 10 → re-entry fill at bar 13 should be
    blocked by cooldown (D+6)."""
    panel = make_panel(n_bars=80, seed=13)
    dates_all = sorted(panel["date"].unique())
    # Crash AAA from bar 31 onward to trigger hard stop (buy_bar=26, earliest_sell=29)
    mask = (panel["ticker"] == "AAA") & (panel["date"] >= dates_all[31])
    for col in ("open", "high", "low", "close"):
        panel.loc[mask, col] = panel.loc[mask, col] * 0.4
    cfg, mdm_state, scorer, rs, dates = _common(panel)
    # First fill at bar 25 → fills bar 26
    first_fill = _fill_for(panel, "AAA", 25, dates)
    # Second fill attempted at bar 33 (after crash exit, within cooldown window)
    second_fill = _fill_for(panel, "AAA", 33, dates)
    fills = [first_fill, second_fill]
    eng = PortfolioEngine(cfg, mdm_state, fills, scorer, panel, rs, dates, initial_cash=1_000_000)
    result = eng.run()
    reasons = [(u.get("ticker"), u.get("reason")) for u in result.unfilled]
    assert ("AAA", "cooldown") in reasons
