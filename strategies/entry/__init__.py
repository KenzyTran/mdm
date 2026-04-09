"""strategies.entry — stock-level entry confirmation (Phase 30).

Exposes the Phase 30 entry building blocks:

- :class:`EntryConfig`   — threshold dataclass (Wave 0, plan 30-01)
- :func:`detect_option_a` — 52-week-high breakout detector (plan 30-02)
- :func:`detect_option_c` — pocket-pivot detector (plan 30-02)
- :func:`compute_buy_windows` / :func:`is_in_any_window` — MDM BUY window
  tracker (plan 30-02). ``find_window`` is a legacy alias for
  ``is_in_any_window``.

``EntryEngine`` will be re-exported by plan 30-03.
"""
from __future__ import annotations

from strategies.entry.config import EntryConfig
from strategies.entry.option_a import detect_option_a
from strategies.entry.option_c import detect_option_c
from strategies.entry.window import (
    compute_buy_windows,
    find_window,
    is_in_any_window,
)

__all__ = [
    "EntryConfig",
    "detect_option_a",
    "detect_option_c",
    "compute_buy_windows",
    "find_window",
    "is_in_any_window",
]
