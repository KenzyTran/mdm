"""
MacroFilter Module for MDM Hybrid Engine

Stateless macro-policy filter that overlays DXY/EEM z-score signals and
SBV regime classification on the v6.0 state-machine decisions. Per
Phase 44 CONTEXT.md D-04, the filter combines signals via the
most-restrictive rule and produces a MacroVerdict with three orthogonal
policy levers (veto sell, lower DD threshold, tighten stop-loss).

Phase 44: MacroVerdict dataclass + add_macro_columns precompute helper +
path constants. The MacroFilter class lives in this module too but is
instantiated/wired in Plan 03 (this plan provides the dataclass + helper
foundation; Plan 03 adds the .apply() integration).

Design decisions referenced (44-CONTEXT.md):
  D-04: Most-restrictive combiner — multiple tightening policies stack
  D-07: New file, parallel to indicator_filter.py
  D-08: Hook AFTER IndicatorFilter in HybridEngine.run() (Plan 03 wires)
  D-09: Hard short-circuit when macro_filter_enabled=False
  D-10: Precompute enrichment via add_macro_columns(df, ...)
  D-11..D-15: 10 config fields on MDMV2Config (Plan 02 Task 1 lands them)
  D-16: CSV paths hardcoded (LIQUIDITY_PROXY_PATH, SBV_EVENTS_PATH)

Code-Docs Sync (CLAUDE.md):
  docs/rules_mdm_hybrid.md update is Phase 47 DOC-01 scope per CONTEXT.md
  memory anchors. Phase 44 commits without touching the rules doc.

  docs/liquidity_proxy_spec.md is the LOAD-BEARING contract for
  add_macro_columns (§5 merge_asof recipe, §6 look-ahead traps). This
  module implements the spec verbatim — no spec deviation, no spec edit
  needed (per RESEARCH.md Open Q5 recommendation).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


# ── Path constants (D-16 — hardcoded per Phase 43 frozen contract) ──────
LIQUIDITY_PROXY_PATH = Path('data/vn_liquidity_proxy.csv')
SBV_EVENTS_PATH = Path('data/sbv_policy_events.csv')


@dataclass(frozen=True)
class MacroVerdict:
    """Per-day macro policy decision.

    Three independent flags + two scalar overrides. Multiple flags can be
    True simultaneously per D-04 most-restrictive combiner — e.g., DXY
    tightening + SBV tightening sets BOTH effective_dd_threshold AND
    effective_stop_loss_max_multiplier in the same verdict.

    Why dataclass not enum: a single-value enum cannot express stacking.
    Per RESEARCH.md Pattern 1, stacking requires orthogonal fields.

    Attributes:
        veto_sell: If True, the engine MUST NOT transition to SELL today
            (regardless of state machine proposal). D-01.
        effective_dd_threshold: Override for V2PositionManager's
            dd_cash_threshold today. None = use config default. D-02 sets
            this to dxy_tightening_dd_threshold (default 3) when DXY or
            EEM tightening active.
        effective_stop_loss_max_multiplier: Override for StopLossChecker's
            stop_loss_max_multiplier today. None = use config default.
            D-03 sets this to sbv_tightening_stop_loss_max_multiplier
            (default 1.5) when SBV tightening active.
    """
    veto_sell: bool = False
    effective_dd_threshold: Optional[int] = None
    effective_stop_loss_max_multiplier: Optional[float] = None

    @classmethod
    def pass_through(cls) -> "MacroVerdict":
        """Sentinel returned when filter is disabled or no signal active.

        All defaults — equivalent to PASS in the original D-08 enum
        phrasing. Use this in MacroFilter.apply()'s D-09 short-circuit.
        """
        return cls()

    def is_pass(self) -> bool:
        """True iff this verdict imposes no policy changes."""
        return (
            not self.veto_sell
            and self.effective_dd_threshold is None
            and self.effective_stop_loss_max_multiplier is None
        )


def add_macro_columns(
    df: pd.DataFrame,
    liquidity_proxy_path: Path = LIQUIDITY_PROXY_PATH,
    sbv_events_path: Path = SBV_EVENTS_PATH,
    dxy_window_days: int = 20,
    eem_window_days: int = 20,
    sbv_decay_days: int = 90,
) -> pd.DataFrame:
    """Enrich VN30 DataFrame with dxy_z, eem_z, sbv_regime columns.

    Three-step pipeline per docs/liquidity_proxy_spec.md (frozen contract):
        1. Merge proxy CSV onto VN30 dates via merge_asof(backward) — §5.1
        2. Compute rolling z-scores AFTER the merge (VN30-indexed) — §5.3
        3. Merge SBV events on shifted effective_date and apply N-day decay
           — §4.4 / §5.2

    Order of operations is LOAD-BEARING. Computing z-score before merge
    leaks future US closes into VN dates (spec §6 trap #4). Using SBV date
    directly without +1 BusinessDay shift uses same-session info (trap #2).
    Using direction='nearest' or 'forward' reintroduces look-ahead (traps
    #1 and #5).

    Args:
        df: VN30 DataFrame, MUST have a sorted 'date' column (datetime64).
        liquidity_proxy_path: Path to canonical 6-column proxy CSV
            (Phase 43 LIQ-01 output).
        sbv_events_path: Path to canonical 5-column SBV events CSV
            (Phase 43 LIQ-02 output).
        dxy_window_days: Rolling window for DXY z-score (default 20 from
            quick-task 260421-lb4 evidence; corr -0.19 with VN30 forward).
        eem_window_days: Rolling window for EEM z-score (default 20).
        sbv_decay_days: Days after event before regime decays to 'neutral'
            (default 90 = SBV rate-action transmission lag estimate).

    Returns:
        Copy of input DataFrame with appended columns:
            dxy_z (float, NaN during warm-up)
            eem_z (float, NaN during warm-up)
            sbv_regime (str, one of 'easing' | 'neutral' | 'tightening')
            sbv_days_since_event (int/NaN, diagnostic — Claude's Discretion
                                   per RESEARCH.md Open Q3 YES recommendation)
    """
    df = df.copy()
    df = df.sort_values('date').reset_index(drop=True)

    # ── Step 1: merge proxy onto VN30 dates (no look-ahead) ─────────────
    proxy = pd.read_csv(liquidity_proxy_path, parse_dates=['date'])
    proxy = proxy.sort_values('date').reset_index(drop=True)

    merged = pd.merge_asof(
        df,
        proxy[['date', 'dxy_close', 'eem_close']],
        on='date',
        direction='backward',
        allow_exact_matches=True,
    )

    # ── Step 2: rolling z-scores on the merged (VN30-indexed) DataFrame ─
    # CRITICAL: z-score AFTER merge per spec §5.3. Computing on raw proxy
    # would leak future US closes into VN dates (spec §6 trap #4).
    dxy_mean = merged['dxy_close'].rolling(dxy_window_days, min_periods=dxy_window_days).mean()
    dxy_std = merged['dxy_close'].rolling(dxy_window_days, min_periods=dxy_window_days).std()
    merged['dxy_z'] = (merged['dxy_close'] - dxy_mean) / dxy_std

    eem_mean = merged['eem_close'].rolling(eem_window_days, min_periods=eem_window_days).mean()
    eem_std = merged['eem_close'].rolling(eem_window_days, min_periods=eem_window_days).std()
    merged['eem_z'] = (merged['eem_close'] - eem_mean) / eem_std

    # Drop intermediate close columns to keep the schema lean
    merged = merged.drop(columns=['dxy_close', 'eem_close'])

    # ── Step 3: SBV regime via shifted-date merge_asof + N-day decay ────
    sbv = pd.read_csv(sbv_events_path, parse_dates=['date'])
    sbv = sbv.sort_values('date').reset_index(drop=True)

    # Edge case: empty SBV file (e.g., test fixture with no events before
    # the series start). pd.read_csv on an empty file yields object dtypes
    # and BusinessDay(1) on an empty datetime Series collapses to float64,
    # which breaks merge_asof's dtype alignment. Short-circuit to an
    # all-'neutral' regime when there are zero events.
    if len(sbv) == 0:
        sbv_merged = merged.copy()
        sbv_merged['sbv_days_since_event'] = pd.Series(
            pd.NA, index=sbv_merged.index, dtype='Int64'
        )
        sbv_merged['sbv_regime'] = 'neutral'
        return sbv_merged

    # CRITICAL: shift first, then merge. Spec §6 trap #2 forbids same-day use.
    sbv['effective_date'] = sbv['date'] + pd.tseries.offsets.BusinessDay(1)

    sbv_merged = pd.merge_asof(
        merged,
        sbv[['effective_date', 'direction']].rename(columns={'direction': 'sbv_raw_direction'}),
        left_on='date',
        right_on='effective_date',
        direction='backward',
        allow_exact_matches=True,
    )

    # Compute decay: days since most-recent SBV effective_date
    sbv_merged['sbv_days_since_event'] = (
        sbv_merged['date'] - sbv_merged['effective_date']
    ).dt.days

    # Apply N-day decay: regime → 'neutral' when no event within sbv_decay_days
    # NaN days_since means we're before the first SBV event — also 'neutral'.
    sbv_merged['sbv_regime'] = sbv_merged['sbv_raw_direction'].where(
        sbv_merged['sbv_days_since_event'].notna()
        & (sbv_merged['sbv_days_since_event'] <= sbv_decay_days),
        other='neutral',
    )

    # Cleanup intermediate columns
    sbv_merged = sbv_merged.drop(columns=['effective_date', 'sbv_raw_direction'])

    return sbv_merged
