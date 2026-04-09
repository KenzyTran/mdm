"""strategies.entry — stock-level entry confirmation (Phase 30).

Wave 0 scaffold: exposes :class:`EntryConfig` only. Detectors
(``option_a``, ``option_c``), the window tracker (``window``), and the
orchestrator (``engine.EntryEngine``) land in plans 30-02 and 30-03.
"""
from __future__ import annotations

from strategies.entry.config import EntryConfig

# EntryEngine will be re-exported by plan 30-03
__all__ = ["EntryConfig"]
