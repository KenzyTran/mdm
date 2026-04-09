"""PortfolioEngine — Phase 31 bar-by-bar orchestrator.

Composes PortfolioConfig + state + exits + sizing + microstructure + costs
into a single `.run()` loop.

Non-negotiable invariant (SC8, per memory/feedback_equity_formula.md — the
707% vs 93% equity-formula bug): NAV[t-1] is computed using ONLY close[t-1]
and earlier data. Mutating close[t] AFTER _compute_nav returns MUST NOT
change bar-t entry fill shares or fill prices.

Contract per Phase 31 CONTEXT decisions D-04 .. D-28.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import math
import numpy as np
import pandas as pd

from .config import PortfolioConfig
from .state import Position, Trade, PositionBook, CooldownRegistry
from .exits import evaluate_exits, ExitDecision, rs_streak_hit
from .sizing import (
    target_notional,
    lot_round_shares,
    adv20,
    liquidity_gate_passes,
    sort_by_canslim,
)
from .microstructure import (
    is_ceiling_locked,
    is_floor_locked,
    t2_earliest_sell_bar,
)
from .costs import apply_entry_cost, apply_exit_cost, entry_cost_basis


logger = logging.getLogger(__name__)


REQUIRED_PANEL_COLS = {"date", "ticker", "open", "high", "low", "close", "volume"}
REQUIRED_RS_COLS = {"date", "ticker", "rs_value"}
REQUIRED_SCORER_COLS = {"date", "ticker", "canslim_score"}


@dataclass
class PortfolioResult:
    trades: List[Trade] = field(default_factory=list)
    nav_daily: pd.DataFrame = field(default_factory=pd.DataFrame)
    positions_daily: pd.DataFrame = field(default_factory=pd.DataFrame)
    unfilled: List[dict] = field(default_factory=list)


@dataclass
class _ScheduledEntry:
    candidate: object  # Fill-like
    fill_bar_idx: int
    shares: int
    fill_price: float


@dataclass
class _ScheduledExit:
    position: Position
    fill_bar_idx: int
    reason: str


class PortfolioEngine:
    """Bar-by-bar multi-stock portfolio engine.

    SC8 INVARIANT: `_compute_nav(bar_idx)` uses ONLY close prices at or
    before `bar_idx`. The main loop computes `nav_prev = _compute_nav(t-1)`
    BEFORE any bar-`t` sizing decision. Mutating `close[t]` in the input
    panel after this computation must not change bar-`t` entry fill shares
    or fill prices. A dedicated regression test in
    `tests/strategies/portfolio/test_nav_lookback.py` proves this.
    """

    def __init__(
        self,
        config: PortfolioConfig,
        mdm_state: pd.Series,
        fills: List,
        scorer_frame: pd.DataFrame,
        price_panel: pd.DataFrame,
        rs_frame: pd.DataFrame,
        trading_dates: pd.DatetimeIndex,
        initial_cash: float = 1_000_000_000,
    ):
        # --- validate inputs (fail-loud) ---
        if not isinstance(config, PortfolioConfig):
            raise ValueError("config must be a PortfolioConfig instance")
        if not isinstance(mdm_state, pd.Series):
            raise ValueError("mdm_state must be a pd.Series indexed by date")
        if not isinstance(price_panel, pd.DataFrame) or price_panel.empty:
            raise ValueError("price_panel must be a non-empty DataFrame")
        missing = REQUIRED_PANEL_COLS - set(price_panel.columns)
        if missing:
            raise ValueError(f"price_panel missing required columns: {missing}")
        if not isinstance(rs_frame, pd.DataFrame):
            raise ValueError("rs_frame must be a DataFrame")
        missing = REQUIRED_RS_COLS - set(rs_frame.columns)
        if missing:
            raise ValueError(f"rs_frame missing required columns: {missing}")
        if not isinstance(scorer_frame, pd.DataFrame):
            raise ValueError("scorer_frame must be a DataFrame")
        missing = REQUIRED_SCORER_COLS - set(scorer_frame.columns)
        if missing:
            raise ValueError(f"scorer_frame missing required columns: {missing}")
        if not isinstance(trading_dates, pd.DatetimeIndex) or len(trading_dates) == 0:
            raise ValueError("trading_dates must be a non-empty DatetimeIndex")
        if initial_cash <= 0:
            raise ValueError(f"initial_cash must be > 0, got {initial_cash}")

        self.config = config
        self.cfg = config  # shorthand
        self.mdm_state = mdm_state
        self.fills = list(fills)
        self.scorer_frame = scorer_frame
        self.price_panel = price_panel
        self.rs_frame = rs_frame
        self.trading_dates = trading_dates
        self.initial_cash = float(initial_cash)

        # --- internal state ---
        self.cash: float = float(initial_cash)
        self.book = PositionBook(max_slots=config.max_slots)
        self._scheduled_entries: List[_ScheduledEntry] = []
        self._scheduled_exits: List[_ScheduledExit] = []
        self._rs_streak_counts: Dict[str, int] = {}
        self._nav_rows: List[dict] = []
        self._positions_rows: List[dict] = []

        # --- precompute indicators ONCE ---
        self._precompute_indicators()

        # --- build fast lookups ---
        self._build_lookups()

    # ---------- precompute ----------

    def _precompute_indicators(self) -> None:
        """Precompute MA50, vol20_avg, and ADV20 series per ticker.

        SC8 discipline: ADV20 is shifted by 1 bar so ADV20 at bar t uses
        only bars strictly before t.
        """
        panel = self.price_panel.copy()
        panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)

        panel["ma50"] = (
            panel.groupby("ticker")["close"].transform(
                lambda s: s.rolling(50, min_periods=50).mean()
            )
        )
        panel["vol20_avg"] = (
            panel.groupby("ticker")["volume"].transform(
                lambda s: s.rolling(20, min_periods=20).mean()
            )
        )
        # prev_close for ceiling/floor
        panel["prev_close"] = panel.groupby("ticker")["close"].shift(1)
        panel["ceiling_px"] = panel["prev_close"] * (1.0 + self.cfg.ceiling_pct)
        panel["floor_px"] = panel["prev_close"] * (1.0 - self.cfg.floor_pct)

        # ADV20 pre-shift: rolling mean of (close*volume) over 20 bars, then
        # shift(1) so bar-t sees only bars [t-20..t-1].
        cv = panel["close"] * panel["volume"]
        panel["adv20"] = (
            cv.groupby(panel["ticker"]).transform(
                lambda s: s.rolling(20, min_periods=20).mean()
            )
        )
        panel["adv20"] = panel.groupby("ticker")["adv20"].shift(1)

        self._panel = panel

    def _build_lookups(self) -> None:
        # (ticker, date) -> row dict
        self._panel_lookup: Dict[tuple, dict] = {}
        for row in self._panel.itertuples(index=False):
            self._panel_lookup[(row.ticker, pd.Timestamp(row.date))] = {
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
                "ma50": float(row.ma50) if not pd.isna(row.ma50) else float("nan"),
                "vol20_avg": float(row.vol20_avg) if not pd.isna(row.vol20_avg) else float("nan"),
                "ceiling_px": float(row.ceiling_px) if not pd.isna(row.ceiling_px) else float("nan"),
                "floor_px": float(row.floor_px) if not pd.isna(row.floor_px) else float("nan"),
                "adv20": float(row.adv20) if not pd.isna(row.adv20) else float("nan"),
            }

        # fills_by_signal_date
        self._fills_by_signal_date: Dict[pd.Timestamp, List] = {}
        for f in self.fills:
            key = pd.Timestamp(f.signal_date)
            self._fills_by_signal_date.setdefault(key, []).append(f)

        # scorer: (ticker, date) -> score
        self._scorer_lookup: Dict[tuple, float] = {}
        for row in self.scorer_frame.itertuples(index=False):
            self._scorer_lookup[(row.ticker, pd.Timestamp(row.date))] = float(row.canslim_score) if not pd.isna(row.canslim_score) else float("nan")

        # rs: (ticker, date) -> value
        self._rs_lookup: Dict[tuple, float] = {}
        for row in self.rs_frame.itertuples(index=False):
            val = row.rs_value
            self._rs_lookup[(row.ticker, pd.Timestamp(row.date))] = float(val) if not pd.isna(val) else float("nan")

        # bar_idx lookup
        self._bar_idx: Dict[pd.Timestamp, int] = {
            pd.Timestamp(d): i for i, d in enumerate(self.trading_dates)
        }

    # ---------- helpers ----------

    def _panel_row(self, ticker: str, date: pd.Timestamp) -> Optional[dict]:
        return self._panel_lookup.get((ticker, pd.Timestamp(date)))

    def _compute_nav(self, bar_idx: int) -> float:
        """NAV marked-to-close at bar_idx. Uses ONLY close[bar_idx] and earlier.

        When bar_idx < 0, returns initial_cash (pre-history).
        """
        if bar_idx < 0:
            return self.initial_cash
        nav = self.cash
        date = pd.Timestamp(self.trading_dates[bar_idx])
        for pos in self.book.slots.open_positions:
            row = self._panel_row(pos.ticker, date)
            if row is None:
                # Fallback: last known close up to bar_idx
                mark_px = pos.buy_price
            else:
                mark_px = row["close"]
            nav += pos.shares * mark_px
        return nav

    def _log_unfilled(self, candidate, reason: str, bar_idx: int, **extra) -> None:
        entry = {
            "bar_idx": bar_idx,
            "date": pd.Timestamp(self.trading_dates[bar_idx]),
            "ticker": getattr(candidate, "ticker", None),
            "reason": reason,
            **extra,
        }
        self.book.unfilled.append(entry)

    def _dedupe_union(self, fills_today: List) -> List:
        """D-04: per (ticker, window_id), keep earliest fill_date; tiebreak A<C."""
        mode = self.cfg.entry_mode
        if mode == "A":
            fills_today = [f for f in fills_today if f.detector_tag == "A"]
        elif mode == "C":
            fills_today = [f for f in fills_today if f.detector_tag == "C"]
        # union → dedupe
        bucket: Dict[tuple, object] = {}
        for f in fills_today:
            key = (f.ticker, getattr(f, "window_id", None))
            cur = bucket.get(key)
            if cur is None:
                bucket[key] = f
                continue
            cur_date = pd.Timestamp(cur.fill_date)
            f_date = pd.Timestamp(f.fill_date)
            if f_date < cur_date:
                bucket[key] = f
            elif f_date == cur_date and f.detector_tag < cur.detector_tag:
                bucket[key] = f
        return list(bucket.values())

    def _materialize_scheduled_fills(self, bar_idx: int) -> None:
        """Execute entries and exits scheduled for today's open.

        Handles floor-lock deferral for exits. Registers cooldowns for
        stop-outs but NOT for mdm_sell (D-20).
        """
        date = pd.Timestamp(self.trading_dates[bar_idx])

        # --- exits first (free slots before entries) ---
        still_pending: List[_ScheduledExit] = []
        for sx in self._scheduled_exits:
            if sx.fill_bar_idx != bar_idx:
                if sx.fill_bar_idx > bar_idx:
                    still_pending.append(sx)
                continue
            row = self._panel_row(sx.position.ticker, date)
            if row is None:
                # No data — defer to next bar
                sx.fill_bar_idx = bar_idx + 1
                still_pending.append(sx)
                continue
            # floor-lock deferral: if open is floor-locked, cannot exit
            floor_px = row.get("floor_px", float("nan"))
            if not math.isnan(floor_px) and is_floor_locked(
                row["open"], row["high"], row["low"], floor_px
            ):
                sx.fill_bar_idx = bar_idx + 1
                still_pending.append(sx)
                continue

            sell_price = row["open"]
            gross = sx.position.shares * sell_price
            net = apply_exit_cost(gross, self.cfg)
            self.cash += net
            pnl_vnd = net - sx.position.cost_basis * sx.position.shares
            pnl_pct = (
                (sell_price - sx.position.buy_price) / sx.position.buy_price
                if sx.position.buy_price > 0
                else 0.0
            )
            trade = Trade(
                ticker=sx.position.ticker,
                buy_date=sx.position.buy_date,
                buy_price=sx.position.buy_price,
                buy_cost_vnd=sx.position.cost_basis * sx.position.shares,
                sell_date=date,
                sell_price=sell_price,
                sell_cost_vnd=gross - net,
                pnl_vnd=pnl_vnd,
                pnl_pct=pnl_pct,
                exit_reason=sx.reason,
            )
            self.book.completed_trades.append(trade)
            # remove from slot
            self.book.slots.open_positions = [
                p for p in self.book.slots.open_positions if p is not sx.position
            ]
            # cooldown — skip for mdm_sell (D-20)
            if sx.reason != "mdm_sell":
                self.book.cooldowns.register(sx.position.ticker, bar_idx)
            # clear rs streak
            self._rs_streak_counts.pop(sx.position.ticker, None)
        self._scheduled_exits = still_pending

        # --- entries ---
        still_pending_entries: List[_ScheduledEntry] = []
        for se in self._scheduled_entries:
            if se.fill_bar_idx != bar_idx:
                if se.fill_bar_idx > bar_idx:
                    still_pending_entries.append(se)
                continue
            # ceiling lock re-check on the actual fill bar
            row = self._panel_row(se.candidate.ticker, date)
            if row is not None:
                ceil = row.get("ceiling_px", float("nan"))
                if not math.isnan(ceil) and is_ceiling_locked(
                    row["open"], row["high"], row["low"], ceil
                ):
                    self._log_unfilled(
                        se.candidate, "ceiling_lock", bar_idx
                    )
                    continue
            # slot check (in case slots changed)
            if self.book.slots.free_slots() <= 0:
                self._log_unfilled(se.candidate, "no_free_slot", bar_idx)
                continue
            notional = se.shares * se.fill_price
            debit = apply_entry_cost(notional, self.cfg)
            if debit > self.cash:
                self._log_unfilled(se.candidate, "insufficient_cash", bar_idx)
                continue
            self.cash -= debit
            cost_basis = entry_cost_basis(se.fill_price, self.cfg)
            pos = Position(
                ticker=se.candidate.ticker,
                buy_bar=bar_idx,
                buy_date=date,
                buy_price=se.fill_price,
                shares=se.shares,
                cost_basis=cost_basis,
                earliest_sell_bar=t2_earliest_sell_bar(bar_idx, self.cfg.t_plus),
            )
            self.book.slots.open_positions.append(pos)
            self._rs_streak_counts[pos.ticker] = 0
        self._scheduled_entries = still_pending_entries

    def _update_rs_streaks(self, bar_idx: int) -> None:
        """Update RS streak counter per open position (D-16 NaN resets)."""
        date = pd.Timestamp(self.trading_dates[bar_idx])
        for pos in self.book.slots.open_positions:
            rs_val = self._rs_lookup.get((pos.ticker, date))
            if rs_val is None or (isinstance(rs_val, float) and math.isnan(rs_val)):
                self._rs_streak_counts[pos.ticker] = 0
                continue
            if rs_val < self.cfg.rs_threshold:
                self._rs_streak_counts[pos.ticker] = (
                    self._rs_streak_counts.get(pos.ticker, 0) + 1
                )
            else:
                self._rs_streak_counts[pos.ticker] = 0

    def _build_bar_ctx(self, position: Position, bar_idx: int) -> dict:
        date = pd.Timestamp(self.trading_dates[bar_idx])
        row = self._panel_row(position.ticker, date)
        if row is None:
            return {
                "open": position.buy_price,
                "high": position.buy_price,
                "low": position.buy_price,
                "close": position.buy_price,
                "vol": 0.0,
                "vol20_avg": float("nan"),
                "ma50": float("nan"),
                "floor": float("nan"),
                "mdm_state": self.mdm_state.get(date),
                "rs_streak_count": self._rs_streak_counts.get(position.ticker, 0),
            }
        return {
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "vol": row["volume"],
            "vol20_avg": row["vol20_avg"],
            "ma50": row["ma50"],
            "floor": row["floor_px"],
            "mdm_state": self.mdm_state.get(date),
            "rs_streak_count": self._rs_streak_counts.get(position.ticker, 0),
        }

    # ---------- main loop ----------

    def run(self) -> PortfolioResult:
        """Execute bar-by-bar loop and return PortfolioResult."""
        for bar_idx in range(len(self.trading_dates)):
            date = pd.Timestamp(self.trading_dates[bar_idx])

            # (1) NAV[t-1] computed BEFORE any bar-t decision. SC8.
            nav_prev = self._compute_nav(bar_idx - 1)

            # (2) Materialize scheduled fills/exits for today's open.
            self._materialize_scheduled_fills(bar_idx)

            # (3) MDM gate dispatch.
            gate = self.mdm_state.get(date)
            if gate == "SELL":
                # Schedule liquidation for every open position at next open.
                existing = {
                    id(sx.position)
                    for sx in self._scheduled_exits
                    if sx.reason == "mdm_sell"
                }
                for pos in self.book.slots.open_positions:
                    if id(pos) in existing:
                        continue
                    # T+2 override still applies (D-14 via evaluate_exits path).
                    # MDM SELL bypasses T+2? Per D-13 MDM SELL is first in chain
                    # but D-14 is checked FIRST in evaluate_exits. We honor D-14.
                    if bar_idx < pos.earliest_sell_bar:
                        continue
                    self._scheduled_exits.append(
                        _ScheduledExit(
                            position=pos,
                            fill_bar_idx=bar_idx + 1,
                            reason="mdm_sell",
                        )
                    )

            # (4) Per-position exit evaluation (non-SELL path triggers too).
            for pos in list(self.book.slots.open_positions):
                # skip if already has a scheduled exit
                if any(sx.position is pos for sx in self._scheduled_exits):
                    continue
                bar_ctx = self._build_bar_ctx(pos, bar_idx)
                decision = evaluate_exits(pos, bar_idx, bar_ctx, self.cfg)
                if decision is None:
                    continue
                if decision.deferred:
                    # limit-down on hard stop: re-evaluate next bar
                    continue
                self._scheduled_exits.append(
                    _ScheduledExit(
                        position=pos,
                        fill_bar_idx=decision.fill_bar_idx,
                        reason=decision.reason,
                    )
                )

            # (5) Entry candidate processing (only when gate == BUY).
            if gate == "BUY" and self.book.slots.free_slots() > 0:
                fills_today = self._fills_by_signal_date.get(date, [])
                candidates = self._dedupe_union(fills_today)
                # CANSLIM sort
                def _score(tk: str) -> Optional[float]:
                    return self._scorer_lookup.get((tk, date))

                kept, dropped = sort_by_canslim(candidates, _score)
                for d in dropped:
                    self._log_unfilled(d, "canslim_score_missing", bar_idx)

                for cand in kept:
                    if self.book.slots.free_slots() <= 0:
                        self._log_unfilled(cand, "no_free_slot", bar_idx)
                        continue
                    if self.book.slots.has_open(cand.ticker):
                        self._log_unfilled(cand, "already_open", bar_idx)
                        continue
                    if self.book.cooldowns.is_cooling(
                        cand.ticker, bar_idx, self.cfg.cooldown_days
                    ):
                        self._log_unfilled(cand, "cooldown", bar_idx)
                        continue

                    tgt = target_notional(nav_prev, self.cfg)

                    # ADV20 from precomputed panel (already shifted = no lookahead)
                    row_today = self._panel_row(cand.ticker, date)
                    if row_today is None:
                        self._log_unfilled(cand, "no_price_data", bar_idx)
                        continue
                    adv = row_today.get("adv20", float("nan"))
                    if not liquidity_gate_passes(adv, tgt, self.cfg.adv_mult):
                        self._log_unfilled(
                            cand, "liquidity_gate", bar_idx, adv20=adv
                        )
                        continue

                    # Check ceiling lock on next bar (fill bar)
                    if bar_idx + 1 < len(self.trading_dates):
                        next_date = pd.Timestamp(self.trading_dates[bar_idx + 1])
                        next_row = self._panel_row(cand.ticker, next_date)
                        if next_row is not None:
                            ceil = next_row.get("ceiling_px", float("nan"))
                            if not math.isnan(ceil) and is_ceiling_locked(
                                next_row["open"],
                                next_row["high"],
                                next_row["low"],
                                ceil,
                            ):
                                self._log_unfilled(cand, "ceiling_lock", bar_idx)
                                continue
                    else:
                        self._log_unfilled(cand, "no_next_bar", bar_idx)
                        continue

                    fill_price = float(cand.fill_price)
                    shares = lot_round_shares(tgt, fill_price, self.cfg.lot_size)
                    if shares <= 0:
                        self._log_unfilled(cand, "shares_zero", bar_idx)
                        continue
                    # schedule
                    self._scheduled_entries.append(
                        _ScheduledEntry(
                            candidate=cand,
                            fill_bar_idx=bar_idx + 1,
                            shares=shares,
                            fill_price=fill_price,
                        )
                    )
            elif gate == "CASH":
                # D-08 Policy A: CASH drops candidates (not queued).
                fills_today = self._fills_by_signal_date.get(date, [])
                for cand in self._dedupe_union(fills_today):
                    self._log_unfilled(cand, "gate_cash", bar_idx)

            # (6) update RS streaks for next-bar exit evaluation
            self._update_rs_streaks(bar_idx)

            # (7) record NAV + positions snapshot
            nav_t = self._compute_nav(bar_idx)
            deployed = nav_t - self.cash
            deployed_pct = deployed / nav_t if nav_t > 0 else 0.0
            self._nav_rows.append(
                {
                    "date": date,
                    "nav": nav_t,
                    "cash": self.cash,
                    "deployed_pct": deployed_pct,
                    "open_slots": len(self.book.slots.open_positions),
                }
            )
            for pos in self.book.slots.open_positions:
                row = self._panel_row(pos.ticker, date)
                mark_px = row["close"] if row is not None else pos.buy_price
                self._positions_rows.append(
                    {
                        "date": date,
                        "ticker": pos.ticker,
                        "shares": pos.shares,
                        "mark_price": mark_px,
                        "mark_value": pos.shares * mark_px,
                    }
                )

        nav_df = pd.DataFrame(self._nav_rows)
        pos_df = pd.DataFrame(self._positions_rows)
        return PortfolioResult(
            trades=self.book.completed_trades,
            nav_daily=nav_df,
            positions_daily=pos_df,
            unfilled=self.book.unfilled,
        )
