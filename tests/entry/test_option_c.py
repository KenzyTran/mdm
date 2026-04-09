"""ENTRY-02 Option C (Pocket Pivot) detector tests — RED stubs (Wave 0)."""
from __future__ import annotations

from strategies.entry.config import EntryConfig
from strategies.entry.option_c import detect_option_c


def test_option_c_fires_pocket_pivot(make_ohlcv):
    df = make_ohlcv(n_bars=260)
    fires = detect_option_c(df, EntryConfig())
    # At least one day in the generated walk should plausibly be a pocket
    # pivot; if the synthetic series is too tame, the actual detector
    # implementation in 30-02 will provide a richer fixture. For the RED
    # stub we only assert the detector returned a boolean Series aligned
    # to the frame index.
    assert len(fires) == len(df)


def test_option_c_fails_closed_zero_down_days(make_ohlcv):
    """Fail-closed when there are no down days in the last 10 sessions (D-05)."""
    df = make_ohlcv(n_bars=260)
    idx = 255
    # Force the last 11 closes to be strictly increasing -> zero down days
    base = float(df["adj_close"].iloc[idx - 11])
    for k in range(11):
        df.iloc[idx - 10 + k, df.columns.get_loc("adj_close")] = base + k + 1
        df.iloc[idx - 10 + k, df.columns.get_loc("adj_open")] = base + k + 0.5
        df.iloc[idx - 10 + k, df.columns.get_loc("adj_high")] = base + k + 1.5
        df.iloc[idx - 10 + k, df.columns.get_loc("adj_low")] = base + k + 0.4
    fires = detect_option_c(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False


def test_option_c_fails_below_ma50(make_ohlcv):
    df = make_ohlcv(n_bars=260)
    idx = 255
    # Drive close well below trailing MA50 at idx
    ma50 = float(df["adj_close"].iloc[idx - 50 : idx].mean())
    df.iloc[idx, df.columns.get_loc("adj_close")] = ma50 * 0.8
    df.iloc[idx, df.columns.get_loc("adj_open")] = ma50 * 0.79
    fires = detect_option_c(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False


def test_option_c_fails_below_base_tolerance(make_ohlcv):
    """Close at 84% of 50d high is outside the 15% tolerance band."""
    df = make_ohlcv(n_bars=260)
    idx = 255
    hi_50 = float(df["adj_high"].iloc[idx - 50 : idx].max())
    df.iloc[idx, df.columns.get_loc("adj_close")] = hi_50 * 0.84
    df.iloc[idx, df.columns.get_loc("adj_open")] = hi_50 * 0.83
    fires = detect_option_c(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False


def test_option_c_fails_down_bar(make_ohlcv):
    df = make_ohlcv(n_bars=260)
    idx = 255
    close = float(df["adj_close"].iloc[idx])
    df.iloc[idx, df.columns.get_loc("adj_open")] = close + 1.0
    fires = detect_option_c(df, EntryConfig())
    assert bool(fires.iloc[idx]) is False
