"""ENTRY-03 MDM BUY-window tracker tests — RED stubs (Wave 0).

Pins D-07..D-09 semantics plus the locked decision in 30-01-NOTES.md §3
(series-starts-in-BUY -> no initial window).
"""
from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip(
    "strategies.entry.window",
    reason="30-02 Task 3 not yet implemented",
)

from strategies.entry.window import compute_buy_windows, is_in_any_window  # noqa: E402


def _dates(n: int, start: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def test_window_day_1_inclusive(make_mdm_state):
    dates = _dates(30)
    state = make_mdm_state(dates, [(dates[5], "BUY")], initial="CASH")
    windows = compute_buy_windows(state, window_days=20)
    assert len(windows) == 1
    # Signal on transition bar itself must be in-window (day 1)
    ok, day = is_in_any_window(dates[5], windows)
    assert ok is True
    assert day == 1


def test_window_day_20_inclusive(make_mdm_state):
    dates = _dates(50)
    state = make_mdm_state(dates, [(dates[5], "BUY")], initial="CASH")
    windows = compute_buy_windows(state, window_days=20)
    ok, day = is_in_any_window(dates[5 + 19], windows)  # day 20
    assert ok is True
    assert day == 20


def test_window_day_21_rejected(make_mdm_state):
    dates = _dates(50)
    state = make_mdm_state(dates, [(dates[5], "BUY")], initial="CASH")
    windows = compute_buy_windows(state, window_days=20)
    ok, _ = is_in_any_window(dates[5 + 20], windows)  # day 21
    assert ok is False


def test_window_no_extension_on_continuous_buy(make_mdm_state):
    dates = _dates(60)
    state = make_mdm_state(dates, [(dates[0], "BUY")], initial="BUY")
    # Series starts in BUY with no observable prior CASH/SELL -> no window
    # (locked decision, 30-01-NOTES.md §3). So this test also covers
    # "continuous BUY does not extend" implicitly: there is no window to
    # extend. We verify that continuing to be BUY does not magically open
    # a window at bar 50.
    windows = compute_buy_windows(state, window_days=20)
    assert windows == []


def test_window_reset_on_cash_to_buy_transition(make_mdm_state):
    dates = _dates(80)
    state = make_mdm_state(
        dates,
        [
            (dates[5], "BUY"),
            (dates[30], "CASH"),
            (dates[40], "BUY"),
        ],
        initial="CASH",
    )
    windows = compute_buy_windows(state, window_days=20)
    assert len(windows) == 2
    # Second window starts fresh at dates[40]
    ok, day = is_in_any_window(dates[40], windows)
    assert ok is True
    assert day == 1


def test_window_sell_to_buy_is_transition(make_mdm_state):
    """SELL -> BUY counts same as CASH -> BUY (D-07)."""
    dates = _dates(50)
    state = make_mdm_state(
        dates,
        [
            (dates[5], "SELL"),
            (dates[10], "BUY"),
        ],
        initial="CASH",
    )
    windows = compute_buy_windows(state, window_days=20)
    assert len(windows) == 1
    ok, day = is_in_any_window(dates[10], windows)
    assert ok is True
    assert day == 1


def test_window_series_starts_in_buy_no_initial_window(make_mdm_state):
    """Locked decision per 30-01-NOTES.md §3: no initial window."""
    dates = _dates(30)
    state = make_mdm_state(dates, [], initial="BUY")
    windows = compute_buy_windows(state, window_days=20)
    assert windows == []
