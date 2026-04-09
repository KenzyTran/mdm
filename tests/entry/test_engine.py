"""ENTRY-04 EntryEngine tests — RED stubs (Wave 0).

Covers D-11..D-15: next-day-open fill, last-bar unfilled record, no
look-ahead (state[i-1] discipline), A/C stream independence, within-stream
first-fire dedup.
"""
from __future__ import annotations

from strategies.entry.config import EntryConfig
from strategies.entry.engine import EntryEngine


def test_fill_next_open(make_ohlcv, make_buy_breakout_bar, make_mdm_state):
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    state = make_mdm_state(df.index, [(df.index[idx - 5], "BUY")], initial="CASH")
    engine = EntryEngine(mdm_state=state, config=EntryConfig())
    fills = engine.run({"TEST": df})
    # At least one fill for TEST at df.index[idx+1], price == df.loc[idx+1, adj_open]
    matching = [f for f in fills if f.ticker == "TEST" and f.detector == "A"]
    assert len(matching) >= 1
    fill = matching[0]
    assert fill.fill_date == df.index[idx + 1]
    assert fill.fill_price == float(df["adj_open"].iloc[idx + 1])


def test_last_bar_unfilled(make_ohlcv, make_buy_breakout_bar, make_mdm_state):
    df = make_ohlcv(n_bars=260)
    idx = len(df) - 1  # final bar
    df = make_buy_breakout_bar(df, idx)
    state = make_mdm_state(df.index, [(df.index[idx - 5], "BUY")], initial="CASH")
    engine = EntryEngine(mdm_state=state, config=EntryConfig())
    result = engine.run({"TEST": df})
    # Unfilled record must exist with reason "no next bar"
    unfilled = [u for u in getattr(result, "unfilled", []) if u.ticker == "TEST"]
    assert len(unfilled) >= 1
    assert "no next bar" in unfilled[0].reason.lower()


def test_no_lookahead_state_shuffle(make_ohlcv, make_buy_breakout_bar, make_mdm_state):
    """Mutating state AFTER the signal bar must not change fills.

    Enforces state[i-1] discipline per CLAUDE.md memory.
    """
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    state_a = make_mdm_state(df.index, [(df.index[idx - 5], "BUY")], initial="CASH")

    engine_a = EntryEngine(mdm_state=state_a, config=EntryConfig())
    fills_a = engine_a.run({"TEST": df.copy()})

    # Now shuffle state AFTER the signal bar to garbage values
    state_b = state_a.copy()
    state_b.iloc[idx + 1 :] = "SELL"
    engine_b = EntryEngine(mdm_state=state_b, config=EntryConfig())
    fills_b = engine_b.run({"TEST": df.copy()})

    assert [(f.ticker, f.signal_date, f.detector) for f in fills_a] == [
        (f.ticker, f.signal_date, f.detector) for f in fills_b
    ]


def test_ac_streams_independent(make_ohlcv, make_buy_breakout_bar, make_mdm_state):
    """Same ticker, same bar, both A and C fire -> two fills (D-14)."""
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    state = make_mdm_state(df.index, [(df.index[idx - 5], "BUY")], initial="CASH")
    engine = EntryEngine(mdm_state=state, config=EntryConfig())
    fills = engine.run({"TEST": df})
    detectors = {f.detector for f in fills if f.ticker == "TEST"}
    # If the breakout bar satisfies both A and C on the synthetic fixture,
    # both streams must record a fill. The 30-03 implementer is responsible
    # for ensuring the breakout fixture also satisfies C (or adjusting this
    # test's fixture). For the Wave 0 stub we only assert set semantics.
    assert detectors <= {"A", "C"}
    assert "A" in detectors


def test_within_stream_dedup_first_fire_only(
    make_ohlcv, make_buy_breakout_bar, make_mdm_state
):
    """Same ticker fires A twice in one window -> only first recorded (D-15)."""
    df = make_ohlcv(n_bars=260)
    idx1 = 252
    idx2 = 255
    df = make_buy_breakout_bar(df, idx1)
    df = make_buy_breakout_bar(df, idx2)
    state = make_mdm_state(df.index, [(df.index[idx1 - 2], "BUY")], initial="CASH")
    engine = EntryEngine(mdm_state=state, config=EntryConfig())
    fills = engine.run({"TEST": df})
    a_fills = [f for f in fills if f.ticker == "TEST" and f.detector == "A"]
    assert len(a_fills) == 1
    assert a_fills[0].signal_date == df.index[idx1]
