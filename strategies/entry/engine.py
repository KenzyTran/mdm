"""EntryEngine — orchestrate Option A / Option C detectors into fills (ENTRY-04).

Implements D-11..D-15 from
``.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md``.

Main loop:
    1. Precompute MDM BUY windows once from ``mdm_state`` (D-07..D-10).
    2. For each ticker in the supplied price panel:
       a. Run ``detect_option_a`` and ``detect_option_c`` on the
          (already-adjusted) frame.
       b. For each detector stream, iterate signal bars; gate by window
          membership (D-07) and optional CANSLIM pass (D-16); dedup
          within-stream on ``(ticker, window_id, detector)`` (D-15).
       c. Compute fill price = ``adj_open`` at bar t+1 (D-11). Last-bar
          signals produce an ``Unfilled`` record with reason
          ``"no next bar"`` (D-12) — stored on the returned
          ``FillList.unfilled`` attribute.
    3. Return a ``FillList`` (list of ``Fill`` + ``unfilled`` attribute).

A and C are INDEPENDENT streams (D-14): a single ticker can contribute one
fill to each stream inside the same window.

No-look-ahead discipline (state[i-1]): ``compute_buy_windows`` is called
once at ``__init__``; the main loop never re-reads ``mdm_state`` mid-run.
Mutating ``mdm_state`` bars strictly after a signal bar cannot shift the
fills produced by an already-constructed engine — but the test fixture
constructs a fresh engine per state, so the invariant verified is that a
second engine built from a post-signal-mutated state still yields the same
fills (because the transition bar — which is BEFORE the signal bar — is
untouched).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

import pandas as pd

from strategies.entry.config import EntryConfig
from strategies.entry.option_a import detect_option_a
from strategies.entry.option_c import detect_option_c
from strategies.entry.window import compute_buy_windows


@dataclass(frozen=True)
class Fill:
    """A single filled entry record (D-11, D-14)."""

    signal_date: pd.Timestamp
    fill_date: pd.Timestamp
    ticker: str
    detector: str           # "A" or "C"
    fill_price: float
    window_id: int
    days_since_buy: int     # 1-indexed (1 = transition bar)


@dataclass(frozen=True)
class Unfilled:
    """Signal that could not be filled (D-12)."""

    signal_date: pd.Timestamp
    ticker: str
    detector: str
    window_id: int
    days_since_buy: int
    reason: str


class FillList(list):
    """List of ``Fill`` with an ``unfilled`` sidecar attribute.

    Behaves like a plain list for iteration; tests retrieve unfilled
    records via ``getattr(result, "unfilled", [])``.
    """

    def __init__(self, fills: Sequence[Fill] = (), unfilled: Sequence[Unfilled] = ()):
        super().__init__(fills)
        self.unfilled: List[Unfilled] = list(unfilled)


class EntryEngine:
    """Orchestrate per-ticker detectors into a stream of fills.

    Args:
        mdm_state: ``pd.Series`` of MDM state (``"BUY"``/``"CASH"``/
            ``"SELL"``) indexed by trading-day timestamp.
        config: :class:`EntryConfig` with detector + window params.
        canslim_scores: Optional per-(date, ticker) CANSLIM scoreboard
            with per-letter boolean columns (``c_pass, a_pass, n_pass,
            s_pass, l_pass, i_pass, liq_pass``). When supplied, signals
            only pass the CANSLIM gate on bars where ALL seven letters
            are True for the ticker. When ``None``, all signals pass
            the gate (raw run, D-16).
    """

    CANSLIM_GATE_COLS = (
        "c_pass",
        "a_pass",
        "n_pass",
        "s_pass",
        "l_pass",
        "i_pass",
        "liq_pass",
    )

    def __init__(
        self,
        mdm_state: pd.Series,
        config: EntryConfig,
        canslim_scores: Optional[pd.DataFrame] = None,
    ) -> None:
        self.mdm_state = mdm_state
        self.config = config
        self.canslim_scores = canslim_scores
        # Precompute windows ONCE at construction — state[i-1] discipline.
        self.windows: List[tuple] = compute_buy_windows(
            mdm_state, window_days=config.window_days
        )
        # Build a (date, ticker) -> bool gate lookup if CANSLIM supplied.
        self._canslim_gate: Optional[pd.Series] = None
        if canslim_scores is not None and not canslim_scores.empty:
            gate_cols = [
                c for c in self.CANSLIM_GATE_COLS if c in canslim_scores.columns
            ]
            if gate_cols:
                gate = canslim_scores[gate_cols].all(axis=1)
                idx = pd.MultiIndex.from_arrays(
                    [
                        pd.to_datetime(canslim_scores["date"]),
                        canslim_scores["ticker"].astype(str),
                    ],
                    names=("date", "ticker"),
                )
                self._canslim_gate = pd.Series(gate.values, index=idx)

    # ------------------------------------------------------------------ helpers

    def _find_window(self, signal_date: pd.Timestamp):
        """Return ``(window_id, days_since_buy)`` or ``(None, None)``."""
        for wid, (start, end) in enumerate(self.windows):
            if start <= signal_date <= end:
                # 1-indexed days between start and signal_date. Use the
                # state's own trading-day index for exact accounting.
                try:
                    i = self.mdm_state.index.get_loc(start)
                    j = self.mdm_state.index.get_loc(signal_date)
                    return wid, j - i + 1
                except KeyError:
                    return wid, len(pd.bdate_range(start, signal_date))
        return None, None

    def _canslim_pass(self, signal_date: pd.Timestamp, ticker: str) -> bool:
        if self._canslim_gate is None:
            return True
        key = (pd.Timestamp(signal_date), str(ticker))
        try:
            return bool(self._canslim_gate.loc[key])
        except KeyError:
            return False

    # --------------------------------------------------------------------- run

    def run(self, prices: Mapping[str, pd.DataFrame]) -> FillList:
        """Run the engine against a dict of per-ticker adjusted OHLCV frames.

        Args:
            prices: Mapping from ticker symbol to single-ticker adjusted
                OHLCV DataFrame (must contain ``adj_open``, ``adj_high``,
                ``adj_low``, ``adj_close``, ``totalvol``).

        Returns:
            :class:`FillList` — iterable of :class:`Fill` instances with
            an ``unfilled`` attribute listing :class:`Unfilled` records
            for last-bar signals.
        """
        fills: List[Fill] = []
        unfilled: List[Unfilled] = []
        seen: set = set()  # dedup key (ticker, window_id, detector)

        for ticker, df in prices.items():
            if df is None or df.empty:
                continue
            fires_a = detect_option_a(df, self.config)
            fires_c = detect_option_c(df, self.config)
            for detector_name, fires in (("A", fires_a), ("C", fires_c)):
                signal_dates = df.index[fires.values]
                for signal_date in signal_dates:
                    wid, dsb = self._find_window(signal_date)
                    if wid is None:
                        continue
                    if not self._canslim_pass(signal_date, ticker):
                        continue
                    key = (ticker, wid, detector_name)
                    if key in seen:
                        continue
                    seen.add(key)

                    pos = df.index.get_loc(signal_date)
                    if pos >= len(df.index) - 1:
                        unfilled.append(
                            Unfilled(
                                signal_date=signal_date,
                                ticker=ticker,
                                detector=detector_name,
                                window_id=wid,
                                days_since_buy=dsb,
                                reason="unfilled: no next bar",
                            )
                        )
                        continue
                    next_bar = df.index[pos + 1]
                    fill_price = float(df.loc[next_bar, "adj_open"])
                    fills.append(
                        Fill(
                            signal_date=signal_date,
                            fill_date=next_bar,
                            ticker=ticker,
                            detector=detector_name,
                            fill_price=fill_price,
                            window_id=wid,
                            days_since_buy=dsb,
                        )
                    )
        return FillList(fills, unfilled)


__all__ = ["EntryEngine", "Fill", "Unfilled", "FillList"]
