---
phase: 31-multi-stock-portfolio-engine
plan: 04
type: execute
wave: 4
depends_on: [31-01, 31-02, 31-03]
files_modified:
  - strategies/portfolio/engine.py
  - strategies/portfolio/__init__.py
  - tests/strategies/portfolio/test_gate_policy.py
  - tests/strategies/portfolio/test_nav_lookback.py
  - tests/strategies/portfolio/test_engine_integration.py
autonomous: true
requirements: [GATE-01, GATE-02, GATE-03, GATE-04, PORT-01, PORT-02, PORT-03, PORT-04, PORT-06, PORT-07, PORT-09, PORT-10]
must_haves:
  truths:
    - "PortfolioEngine consumes injected HybridEngine state series, Phase 30 fills, Phase 29 scorer frame, adjusted price panel, and load_stock_rs output — no re-running upstream"
    - "Bar loop computes NAV[t-1] BEFORE any bar-t sizing decision (SC8)"
    - "Policy A BUY/CASH/SELL dispatch routes correctly: BUY admits new fills, CASH drops candidates, SELL schedules all-position liquidation"
    - "Exit decisions fill at open[t+1], subject to floor-lock deferral"
    - "Ceiling-locked next-open blocks entry fill with unfilled log"
    - "T+2 override prevents any exit before buy_bar+3"
    - "SC8 test proves mutating close[t] after NAV[t-1] computation does not change bar-t fills"
  artifacts:
    - path: strategies/portfolio/engine.py
      provides: "PortfolioEngine with .run() returning PortfolioResult"
      contains: "class PortfolioEngine"
    - path: tests/strategies/portfolio/test_nav_lookback.py
      provides: "SC8 state[i-1] no-lookahead regression test"
      contains: "def test_no_bar_t_lookahead"
  key_links:
    - from: strategies/portfolio/engine.py
      to: strategies/portfolio/exits.py
      via: import
      pattern: "from .exits import evaluate_exits"
    - from: strategies/portfolio/engine.py
      to: strategies/portfolio/sizing.py
      via: import
      pattern: "from .sizing import"
    - from: strategies/portfolio/engine.py
      to: strategies/portfolio/state.py
      via: import
      pattern: "from .state import PositionBook"
---

<objective>
Build `PortfolioEngine` — the bar-by-bar orchestrator that composes config + state + exits + sizing + microstructure + costs into a single `.run()` loop. Enforces MDM gate Policy A (D-08), the SC8 `state[i-1]` discipline, and produces trades/positions/NAV/unfilled logs in-memory for the audit plan (Plan 05) to serialize.

Purpose: This is where all the primitives integrate. The non-negotiable invariant is SC8 — a dedicated regression test that mutates `close[t]` after bar-`t` decisions and asserts fills are unchanged.

Output: Importable `PortfolioEngine(config, mdm_state, fills, scorer_frame, price_panel, rs_frame, trading_dates).run() → PortfolioResult(trades, positions_daily, nav_daily, unfilled)`. Engine is fully unit-testable with synthetic inputs.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md
@.planning/phases/31-multi-stock-portfolio-engine/31-RESEARCH.md
@strategies/portfolio/config.py
@strategies/portfolio/state.py
@strategies/portfolio/exits.py
@strategies/portfolio/sizing.py
@strategies/portfolio/microstructure.py
@strategies/portfolio/costs.py
@strategies/entry/engine.py
</context>

<interfaces>
From Plans 01-03:
- PortfolioConfig (Plan 01)
- PositionBook, SlotState, CooldownRegistry, Position, Trade (Plan 01)
- is_ceiling_locked, is_floor_locked, t2_earliest_sell_bar (Plan 02)
- apply_entry_cost, apply_exit_cost, entry_cost_basis (Plan 02)
- evaluate_exits, ExitDecision, rs_streak_hit (Plan 03)
- target_notional, lot_round_shares, adv20, liquidity_gate_passes, sort_by_canslim (Plan 03)

Expected upstream input shapes (inject at __init__):
- mdm_state: pd.Series indexed by date with values in {"BUY","CASH","SELL"}
- fills: list of Phase 30 Fill records (attrs: ticker, signal_date, fill_date, fill_price, detector_tag in {"A","C"}, window_id)
- scorer_frame: DataFrame with columns (date, ticker, canslim_score) — wide or long, engine accepts long
- price_panel: long DataFrame (date, ticker, open, high, low, close, volume) already adjusted via connectors/adjust.py
- rs_frame: long DataFrame (date, ticker, rs_value) from load_stock_rs
- trading_dates: pd.DatetimeIndex of bar dates (intersection of all sources)
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: PortfolioEngine bar-loop orchestrator</name>
  <files>strategies/portfolio/engine.py, strategies/portfolio/__init__.py</files>
  <read_first>.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-04 through D-28, all decisions), 31-RESEARCH.md "Bar Loop Skeleton" section, strategies/entry/engine.py (inject-all-upstream pattern)</read_first>
  <behavior>
    - PortfolioResult dataclass: trades:list[Trade], nav_daily:pd.DataFrame (date, nav, cash, deployed_pct, open_slots), positions_daily:pd.DataFrame (date, ticker, shares, mark_price, mark_value), unfilled:list[dict]
    - PortfolioEngine.__init__(config, mdm_state, fills, scorer_frame, price_panel, rs_frame, trading_dates, initial_cash=1_000_000_000)
      Validates inputs (raise ValueError on missing required columns). Builds fast-lookup indexes: fills_by_signal_date (dict), panel_by_ticker_date (multi-indexed), rs_by_ticker_date, scorer_by_ticker_date, ma50_by_ticker_date (precomputed via rolling(50).mean() on close, groupby ticker — done ONCE at init, not per-bar), vol20_avg_by_ticker_date (rolling(20).mean() on volume).
    - .run() -> PortfolioResult. Bar loop per 31-RESEARCH.md skeleton:
        For each t in trading_dates (using integer bar_idx):
          1. nav_prev = self._compute_nav(t_prev_idx) if t_prev_idx >= 0 else initial_cash
             (Uses close[t_prev] only — NEVER close[t].)
          2. Materialize any fills/exits SCHEDULED on previous bar for today's open (update positions, debit/credit cash via apply_entry_cost / apply_exit_cost). Register cooldowns for stop-out exits but NOT for mdm_sell (D-20).
          3. Read gate = mdm_state.loc[t]. If SELL: schedule liquidation fills at open[t+1] for all open positions (exit_reason="mdm_sell"), subject to floor-lock deferral (re-check next bar).
          4. For each open position, build bar_ctx dict (include rs_streak_count maintained per-position in a dict) and call evaluate_exits(pos, bar_idx, bar_ctx, cfg). If ExitDecision returned:
             - If deferred=True (limit-down) → keep pending, re-evaluate next bar.
             - Else schedule exit at fill_bar = bar_idx+1, but check floor-lock on next bar's open; if floor-locked, defer.
          5. If gate == BUY and free_slots > 0:
             - Select entry candidates = fills with signal_date == t, filtered by cfg.entry_mode (A/C/union). Dedupe per D-04 (earlier fill_date wins, tie A before C).
             - Sort by CANSLIM score desc via sort_by_canslim (log dropped as unfilled/canslim_score_missing).
             - For each candidate up to free_slots:
                * Skip + log unfilled/cooldown if CooldownRegistry.is_cooling
                * Skip + log unfilled/no_free_slot if slots full
                * Compute target_notional(nav_prev). Compute adv20(ticker, bar_idx). If liquidity_gate_passes False → log unfilled/liquidity_gate.
                * Look up next_bar (t+1) row in panel for that ticker. Check is_ceiling_locked(next_open, next_high, next_low, ceiling=next_prev_close*1.07). If locked → log unfilled/ceiling_lock.
                * Compute shares = lot_round_shares(target_notional, candidate.fill_price, cfg.lot_size). If 0 → log unfilled/shares_zero.
                * Schedule entry fill at fill_date = t+1 (using candidate.fill_price from Phase 30 Fill, which is already the next-day open).
          6. Update rs_streak_count for each open position from rs_frame at date t (D-16 NaN reset).
          7. Record nav_daily row (mark to close[t]) and per-position positions_daily rows.
        After loop, return PortfolioResult.
    - Critical SC8 invariant documented in docstring: "NAV[t-1] is computed using only close[t-1] and earlier; mutating close[t] AFTER _compute_nav returns MUST NOT change bar-t fill shares/prices."
  </behavior>
  <action>
    Create `strategies/portfolio/engine.py`. Imports: pandas, numpy, dataclasses, typing.Optional/Iterable/List/Dict, logging; from `.config import PortfolioConfig`; from `.state import PositionBook, Position, Trade, CooldownRegistry`; from `.exits import evaluate_exits, ExitDecision, rs_streak_hit`; from `.sizing import target_notional, lot_round_shares, adv20, liquidity_gate_passes, sort_by_canslim`; from `.microstructure import is_ceiling_locked, is_floor_locked, t2_earliest_sell_bar`; from `.costs import apply_entry_cost, apply_exit_cost, entry_cost_basis`.

    Implement `PortfolioResult` dataclass and `PortfolioEngine` class with __init__ + .run() + private helpers: `_compute_nav(bar_idx)`, `_build_bar_ctx(position, bar_idx)`, `_dedupe_union(fills)`, `_log_unfilled(cand, reason, bar_idx, **extra)`, `_materialize_scheduled_fills(bar_idx)`, `_precompute_indicators()`.

    Precompute indicators ONCE in __init__:
    - MA50: `price_panel.groupby("ticker")["close"].rolling(50).mean()` → join back
    - Vol20 avg: `price_panel.groupby("ticker")["volume"].rolling(20).mean()` → join back
    - Ceiling / floor: per bar, `prev_close * 1.07` and `* 0.93` via groupby shift.
    - ADV20 series: `(close*volume)` rolling 20 mean per ticker, shifted by 1 so ADV20[t] only uses data up to t-1 (SC8!).

    Dedupe union fills (D-04): group by (ticker, window_id), pick earliest fill_date; tiebreak detector_tag lexicographic ("A" < "C").

    RS streak tracking: maintain a per-ticker-in-position counter; each bar update = if rs_value &lt; threshold increment else reset (NaN also resets per D-16).

    Update `strategies/portfolio/__init__.py` to export PortfolioEngine, PortfolioResult, PortfolioConfig.

    Fail-loud on missing columns or empty inputs. No silent defaults.
  </action>
  <verify>
    <automated>uv run python -c "from strategies.portfolio import PortfolioEngine, PortfolioConfig, PortfolioResult; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - grep "class PortfolioEngine" strategies/portfolio/engine.py matches
    - grep "def _compute_nav" strategies/portfolio/engine.py matches
    - grep "nav_prev" strategies/portfolio/engine.py matches (appears ≥2 times)
    - grep "entry_mode" strategies/portfolio/engine.py matches (Policy A dispatch)
    - grep "mdm_sell" strategies/portfolio/engine.py matches
    - grep "ceiling_lock" strategies/portfolio/engine.py matches
    - grep "liquidity_gate" strategies/portfolio/engine.py matches
    - grep "PortfolioEngine" strategies/portfolio/__init__.py matches
    - Import smoke passes: `uv run python -c "from strategies.portfolio import PortfolioEngine"` exit 0
  </acceptance_criteria>
  <done>PortfolioEngine importable and precomputes all indicators at __init__; bar loop honors full D-04..D-28 contract.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Gate policy + SC8 no-lookahead regression + end-to-end integration tests</name>
  <files>tests/strategies/portfolio/test_gate_policy.py, tests/strategies/portfolio/test_nav_lookback.py, tests/strategies/portfolio/test_engine_integration.py</files>
  <read_first>strategies/portfolio/engine.py, tests/strategies/portfolio/fixtures/synthetic_panel.py, memory feedback_equity_formula.md (707% bug), .planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-26 SC8 mandatory test)</read_first>
  <behavior>
    - test_gate_policy.py:
      - test_state_source_injection: PortfolioEngine accepts mdm_state at ctor; reading engine.mdm_state returns the same series
      - test_policy_a_buy_admits_new: synthetic panel, mdm_state all BUY, 3 fills on bar 5 → after run, 3 positions opened (or ≤ max_slots)
      - test_policy_a_cash_drops_candidates: mdm_state CASH on bar 5, fill on bar 5 → 0 new positions, unfilled log entry (NOT cooldown, just dropped). Per D-08: candidates dropped, not queued.
      - test_policy_a_sell_liquidates_all: open 2 positions on bar 5 with BUY, transition to SELL on bar 15 (after T+2 cleared) → both positions exited at open[16], exit_reason="mdm_sell", cooldown NOT registered (D-20).
    - test_nav_lookback.py (SC8 MANDATORY):
      - test_no_bar_t_lookahead: build synthetic panel; run engine once, capture fills list. Build a DEEP COPY of inputs, MUTATE close[t] values by +50% for bars with fills, run engine again. Assert fills list (ticker, fill_date, shares, fill_price) is IDENTICAL between runs. This proves no bar-t close was used in bar-t sizing decisions. Cite memory feedback_equity_formula.md in a comment.
      - test_nav_prev_uses_prior_close: instrument engine via monkey-patch or direct call to _compute_nav(bar_idx=5); assert the computed NAV uses close.iloc[5] only from positions that already existed (not new mark-to-market on bar 5 entries).
      - test_adv20_uses_only_prior_bars: direct call to sizing.adv20 already tested, but this integration check asserts engine.run() does not increase fill count when close[t] is spiked (redundant with first test, but explicitly parameterized by ADV20).
    - test_engine_integration.py:
      - test_end_to_end_synthetic: 3-ticker 60-bar synthetic panel, 2 fake BUY fills, mdm_state BUY throughout, run engine → PortfolioResult has ≥1 trade OR ≥1 open position in positions_daily; nav_daily has 60 rows; unfilled is empty or contains only expected reasons.
      - test_t2_blocks_early_exit: force hard-stop trigger on bar 2 after buy on bar 0 → exit is deferred to bar 3 (buy_bar+3). Assert trade.sell_date equals trading_dates[3].
      - test_ceiling_lock_blocks_entry: force lock_days={"AAA": [(6, "ceiling")]} on synthetic panel, feed a BUY fill for AAA with fill_date=bar6 → unfilled entry with reason="ceiling_lock" and NO new position opened.
      - test_canslim_tiebreak_selects_top: 4 BUY fills on bar 5 with scorer values giving AAA=90, BBB=80, CCC=70, DDD=60; max_slots reduced to 2 via config override → the 2 opened positions are AAA and BBB.
      - test_cooldown_blocks_reentry: force a hard-stop exit on ticker AAA at bar 10; feed another AAA fill at bar 13 → unfilled reason="cooldown" (D+6 earliest is bar 16).
  </behavior>
  <action>
    Create `tests/strategies/portfolio/test_gate_policy.py` with the 4 tests. Each test constructs: synthetic_panel fixture, a 3-ticker × N-bar price panel; a tiny mdm_state series; a list of Fill-like namedtuples (`Fill = namedtuple("Fill","ticker signal_date fill_date fill_price detector_tag window_id")`); a scorer_frame DataFrame with canslim_score filled in; an rs_frame with rs_value=75 (above threshold, no trigger); calls PortfolioEngine(...).run(); asserts on the result.

    Create `tests/strategies/portfolio/test_nav_lookback.py` with the 3 SC8 tests. test_no_bar_t_lookahead MUST:
      1. Build inputs, call engine.run(), extract `trades1 = result.trades` + open positions snapshot
      2. import copy; deep-copy `price_panel`, mutate `close` column on specific bar indices (e.g., multiply by 1.5 on every bar where a fill occurs)
      3. Build a SECOND engine with the mutated panel, call run(), extract trades2 + positions snapshot
      4. Assert trades1 == trades2 (ticker/buy_date/sell_date/buy_price/shares identical; allow P&L to differ because exit close IS legitimately different)
      Actually — since exit prices depend on close[t], compare only the BUY side and SHARE COUNT. Document with inline comment: "SC8: bar-t close must not influence bar-t ENTRY sizing. Exit P&L differs legitimately because exits use close[t] for trigger — that's allowed by D-26."

    Create `tests/strategies/portfolio/test_engine_integration.py` with the 5 end-to-end tests. Use the `synthetic_panel` fixture. For tests that require specific bar prices (hard stop, ceiling lock), override fixture output with explicit price adjustments after calling make_panel.

    All tests use `initial_cash=1_000_000_000` unless the test needs sizing quirks.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_gate_policy.py tests/strategies/portfolio/test_nav_lookback.py tests/strategies/portfolio/test_engine_integration.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def test_no_bar_t_lookahead" tests/strategies/portfolio/test_nav_lookback.py matches
    - grep "707" tests/strategies/portfolio/test_nav_lookback.py matches (citing the bug in a comment)
    - grep "def test_policy_a_sell_liquidates_all" tests/strategies/portfolio/test_gate_policy.py matches
    - grep "def test_ceiling_lock_blocks_entry" tests/strategies/portfolio/test_engine_integration.py matches
    - grep "def test_canslim_tiebreak_selects_top" tests/strategies/portfolio/test_engine_integration.py matches
    - grep "def test_t2_blocks_early_exit" tests/strategies/portfolio/test_engine_integration.py matches
    - grep "def test_cooldown_blocks_reentry" tests/strategies/portfolio/test_engine_integration.py matches
    - pytest command exits 0 with ≥12 tests passed (4 gate + 3 nav + 5 integration)
  </acceptance_criteria>
  <done>Gate policy + SC8 + end-to-end integration green. SC8 proves no bar-t look-ahead in entry sizing.</done>
</task>

</tasks>

<verification>
uv run pytest tests/strategies/portfolio/ -x -q
</verification>

<success_criteria>
- PortfolioEngine.run() produces coherent PortfolioResult
- Policy A dispatch correct
- T+2 override enforced end-to-end
- Ceiling lock, cooldown, CANSLIM tie-break all exercised in integration tests
- SC8 state[i-1] regression test passes — bar-t close mutation does not change bar-t entry shares
</success_criteria>

<output>
After completion, create `.planning/phases/31-multi-stock-portfolio-engine/31-04-SUMMARY.md`
</output>
