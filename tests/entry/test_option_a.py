"""ENTRY-01 Option A detector tests — RED stubs (Wave 0).

Uses ``pytest.importorskip`` so this module SKIPS cleanly until
30-02 Task 1 creates ``strategies.entry.option_a``. At that point every
test below becomes a real RED/GREEN gate.
"""
from __future__ import annotations

from strategies.entry.config import EntryConfig
from strategies.entry.option_a import detect_option_a


def test_option_a_fires_on_full_breakout(make_ohlcv, make_buy_breakout_bar):
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    fires = detect_option_a(df, EntryConfig())
    assert bool(fires.iloc[idx]) is True


def test_option_a_fails_not_new_high(make_ohlcv, make_buy_breakout_bar):
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    # Set close to equal prior-252 max (strict > required, so must fail)
    prior_max = float(df["adj_close"].iloc[idx - 252 : idx].max())
    df.iloc[idx, df.columns.get_loc("adj_close")] = prior_max
    fires = detect_option_a(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False


def test_option_a_fails_volume_below_1_5x(make_ohlcv, make_buy_breakout_bar):
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    avg_vol = float(df["totalvol"].iloc[idx - 50 : idx].mean())
    df.iloc[idx, df.columns.get_loc("totalvol")] = avg_vol * 1.49
    fires = detect_option_a(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False


def test_option_a_fails_down_bar(make_ohlcv, make_buy_breakout_bar):
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    close = float(df["adj_close"].iloc[idx])
    df.iloc[idx, df.columns.get_loc("adj_open")] = close + 1.0
    fires = detect_option_a(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False


def test_option_a_fails_lower_half_close(make_ohlcv, make_buy_breakout_bar):
    df = make_ohlcv(n_bars=260)
    idx = 255
    df = make_buy_breakout_bar(df, idx)
    high = float(df["adj_high"].iloc[idx])
    low = float(df["adj_low"].iloc[idx])
    mid = (high + low) / 2.0
    # Close just below midpoint (still > prior-max in setup? no — must adjust)
    df.iloc[idx, df.columns.get_loc("adj_close")] = mid - 0.01
    df.iloc[idx, df.columns.get_loc("adj_high")] = mid + 10.0  # stretch high up
    fires = detect_option_a(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False


def test_option_a_excludes_today_from_52wk_max(make_ohlcv):
    """Off-by-one guard: 52-wk window MUST exclude today.

    Construct a frame where today's close equals yesterday's prior-252 max.
    Without ``shift(1)`` the detector would include today in the max and
    the ``>`` comparison would fail. With shift(1) it fires.
    """
    df = make_ohlcv(n_bars=260)
    idx = 255
    # Make yesterday the running 252 max by inflating it
    df.iloc[idx - 1, df.columns.get_loc("adj_close")] = 200.0
    # Today: close strictly greater, full Option A satisfaction
    avg_vol = float(df["totalvol"].iloc[idx - 50 : idx].mean())
    df.iloc[idx, df.columns.get_loc("adj_close")] = 201.0
    df.iloc[idx, df.columns.get_loc("adj_open")] = 199.5
    df.iloc[idx, df.columns.get_loc("adj_low")] = 199.0
    df.iloc[idx, df.columns.get_loc("adj_high")] = 201.2
    df.iloc[idx, df.columns.get_loc("totalvol")] = avg_vol * 2.0
    fires = detect_option_a(df, EntryConfig())
    assert bool(fires.iloc[idx]) is True
