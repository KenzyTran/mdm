---
phase: 31-multi-stock-portfolio-engine
plan: 03
type: execute
wave: 3
depends_on: [31-01, 31-02]
files_modified:
  - strategies/portfolio/exits.py
  - strategies/portfolio/sizing.py
  - tests/strategies/portfolio/test_exit_chain.py
  - tests/strategies/portfolio/test_sizing.py
  - tests/strategies/portfolio/test_liquidity_gate.py
autonomous: true
requirements: [GATE-02, PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-09]
must_haves:
  truths:
    - "Exit priority chain fires in exact order MDM SELL > 8% hard stop > MA50 break+vol > RS<70 5-streak"
    - "T+2 override defers any exit trigger on D+1/D+2 until D+3"
    - "Limit-down day defers hard stop exit to next non-floor-locked bar"
    - "Slot sizing uses NAV[t-1] * 0.125 and floors shares to 100-lot"
    - "Liquidity gate refuses entry when ADV20[t] < 10 * target_notional"
    - "RS streak resets on missing data (fail-closed)"
  artifacts:
    - path: strategies/portfolio/exits.py
      provides: "evaluate_exits, ExitDecision, rs_streak_hit"
      contains: "def evaluate_exits"
    - path: strategies/portfolio/sizing.py
      provides: "target_notional, lot_round_shares, liquidity_gate_passes, select_candidates"
      contains: "def lot_round_shares"
  key_links:
    - from: strategies/portfolio/exits.py
      to: strategies/portfolio/microstructure.py
      via: import
      pattern: "from .microstructure import"
    - from: strategies/portfolio/sizing.py
      to: strategies/portfolio/config.py
      via: import
      pattern: "from .config import PortfolioConfig"
---

<objective>
Build the exit priority chain (D-13, D-14) and the sizing / liquidity-gate primitives. All decisions on bar `t` use data ≤ `t-1` for sizing, but `close[t]` is allowed for exit triggers (which fill at `open[t+1]`).

Purpose: The exit chain is the single most error-prone component (707% bug lives here). Isolating it as a pure function with exhaustive tests is the highest-leverage correctness investment.

Output: Exit chain + sizing module with ~20 tests covering GATE-02 SELL dispatch, PORT-01..06, PORT-09.
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
@strategies/portfolio/microstructure.py
@strategies/portfolio/costs.py
</context>

<interfaces>
From strategies/portfolio/state.py (Plan 01):
- Position(ticker, buy_bar, buy_date, buy_price, shares, cost_basis, earliest_sell_bar)

From strategies/portfolio/microstructure.py (Plan 02):
- is_floor_locked(open_, high, low, floor) -> bool
- t2_earliest_sell_bar(buy_bar_idx, t_plus=2) -> int

From strategies/portfolio/config.py (Plan 01):
- PortfolioConfig with hard_stop_pct, ma50_vol_mult, rs_threshold, rs_streak_days, adv_mult, slot_weight, lot_size
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Exit priority chain (exits.py) + comprehensive tests</name>
  <files>strategies/portfolio/exits.py, tests/strategies/portfolio/test_exit_chain.py</files>
  <read_first>.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-13, D-14, D-16, D-19), strategies/portfolio/microstructure.py, strategies/portfolio/state.py</read_first>
  <behavior>
    - ExitReason enum or str-constants: "mdm_sell", "hard_stop", "ma50_break", "rs_deterioration"
    - ExitDecision dataclass: reason:str, fill_bar_idx:int, deferred:bool, original_trigger_bar:int
    - evaluate_exits(position:Position, bar_idx:int, bar_ctx:dict, cfg:PortfolioConfig) -> Optional[ExitDecision]
      bar_ctx is a plain dict with keys: mdm_state (BUY/CASH/SELL), low, high, open, close, ma50, vol, vol20_avg, rs_streak_count (int), next_open, next_high, next_low, next_floor, next_close
      Logic:
        1. If bar_idx &lt; position.earliest_sell_bar → return None (T+2 hard block per D-14). All triggers deferred silently.
        2. Check MDM SELL first: if mdm_state=="SELL" → schedule exit at bar_idx+1, reason="mdm_sell"
        3. Hard stop: if low ≤ position.buy_price * (1 - cfg.hard_stop_pct) → reason="hard_stop". Limit-down exception: if low==high==open AND equals the floor → mark deferred=True (caller must re-check next bar).
        4. MA50 break: if close < ma50 AND vol ≥ cfg.ma50_vol_mult * vol20_avg → reason="ma50_break"
        5. RS deterioration: if rs_streak_count ≥ cfg.rs_streak_days → reason="rs_deterioration"
        First match wins. Return ExitDecision(reason, fill_bar_idx=bar_idx+1, deferred=False_or_True, original_trigger_bar=bar_idx).
    - rs_streak_hit(rs_series:pd.Series, threshold:int, min_streak:int) -> bool helper. Missing (NaN) data resets streak (D-16 fail-closed).
    - Tests (≥12):
      - test_t2_blocks_all: position.earliest_sell_bar=13, bar_idx=11, any trigger set → returns None
      - test_priority_order: all 4 triggers fire simultaneously → returns "mdm_sell" (first match)
      - test_hard_stop: low=92, buy=100, hard_stop_pct=0.08 → "hard_stop", fill_bar=bar+1
      - test_hard_stop_limit_down: low=high=open=floor=92, buy=100 → deferred=True, reason="hard_stop"
      - test_ma50_break: close&lt;ma50 AND vol &gt;=1.25*vol20 → "ma50_break"
      - test_ma50_break_vol_insufficient: vol &lt; 1.25 * vol20 → no trigger (returns None, assuming other triggers also absent)
      - test_rs_streak_hit: rs_streak_count=5 → "rs_deterioration"
      - test_rs_streak_not_yet: rs_streak_count=4 → no trigger
      - test_rs_streak_resets_on_nan: rs_streak_hit helper with [60,60,NaN,60,60,60] threshold=70 min_streak=5 → False
      - test_rs_streak_continuous: [60,60,60,60,60] threshold=70 min_streak=5 → True
      - test_mdm_sell_beats_hard_stop: both trigger → "mdm_sell"
      - test_hard_stop_beats_ma50: both trigger → "hard_stop"
  </behavior>
  <action>
    Create `strategies/portfolio/exits.py` implementing the `ExitDecision` dataclass, `EXIT_REASONS` constants, `evaluate_exits()` function, and `rs_streak_hit()` helper. Use first-match-wins ordering explicitly (if/elif/elif/elif). For the limit-down branch, check `bar_ctx["low"] == bar_ctx["high"] == bar_ctx["open"]` AND equals `bar_ctx["floor"]`. Set `deferred=True` — do NOT attempt to compute the actual deferred fill bar here (engine does that by re-calling evaluate_exits next bar).
    Create `tests/strategies/portfolio/test_exit_chain.py` with the 12 tests listed above. Build a helper `make_bar(**overrides)` inside the test file to construct default bar_ctx dicts (mdm_state="BUY", low=100, high=100, open=100, close=100, ma50=90, vol=1000, vol20_avg=1000, rs_streak_count=0, floor=92). Build a helper `make_position(earliest_sell_bar=0, buy_price=100.0)` to yield a Position.
    Per D-13 and D-14, T+2 is checked FIRST — document with an inline comment.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_exit_chain.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def evaluate_exits" strategies/portfolio/exits.py matches
    - grep "earliest_sell_bar" strategies/portfolio/exits.py matches
    - grep "mdm_sell" strategies/portfolio/exits.py matches
    - grep "rs_streak_hit" strategies/portfolio/exits.py matches
    - grep "def test_priority_order" tests/strategies/portfolio/test_exit_chain.py matches
    - grep "def test_t2_blocks_all" tests/strategies/portfolio/test_exit_chain.py matches
    - pytest exits 0 with ≥12 tests passed
  </acceptance_criteria>
  <done>Exit chain matches D-13/D-14 exactly; all ordering and edge cases covered by tests.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Sizing + liquidity gate (sizing.py) + tests</name>
  <files>strategies/portfolio/sizing.py, tests/strategies/portfolio/test_sizing.py, tests/strategies/portfolio/test_liquidity_gate.py</files>
  <read_first>.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-09, D-10, D-11, D-24), strategies/portfolio/config.py</read_first>
  <behavior>
    - target_notional(nav_prev:float, cfg:PortfolioConfig) -> float: nav_prev * cfg.slot_weight
    - lot_round_shares(target_notional:float, fill_price:float, lot_size:int=100) -> int: floor(target/fill_price/lot_size)*lot_size. Never returns negative.
    - adv20(close_series, vol_series, bar_idx:int) -> float: mean of close[t-20..t-1] * vol[t-20..t-1]. Uses STRICTLY t-1 and earlier (no look-ahead). Returns NaN if fewer than 20 prior bars.
    - liquidity_gate_passes(adv20_value:float, target_notional:float, adv_mult:float) -> bool: adv20_value ≥ adv_mult * target_notional. NaN → False (fail-closed).
    - sort_by_canslim(candidates:list, score_lookup:callable) -> (sorted_list, dropped_missing_list). Candidates with missing score land in dropped list (for engine to log as unfilled/canslim_score_missing per D-10).
    - Tests sizing (test_sizing.py):
      - test_target_notional: nav=1e9, cfg default → 125_000_000
      - test_lot_round_exact: target=125M, fill=25000 → 5000 shares
      - test_lot_round_floors_down: target=125M, fill=25100 → 4900 shares (not 5000). Residual stays in cash (D-11). Test via assertion that deployed=122,990,000 leaving 2,010,000 residual.
      - test_lot_round_zero_when_price_too_high: target=1000, fill=50000 → 0 shares
      - test_canslim_sort_desc: 3 candidates with scores {AAA:80, BBB:90, CCC:70} → order [BBB, AAA, CCC]
      - test_canslim_sort_missing_score: candidate "DDD" with None score → lands in dropped list (D-10)
    - Tests liquidity (test_liquidity_gate.py):
      - test_adv20_formula: synthetic close=[100]*25, vol=[1000]*25 → adv20 at bar 24 = 100_000
      - test_adv20_insufficient_history: bar_idx=10 with only 10 prior bars → NaN
      - test_liquidity_gate_passes: adv20=1.5e9, target=125M, adv_mult=10 → True (1.5e9 ≥ 1.25e9)
      - test_liquidity_gate_blocks: adv20=1.0e9, target=125M, adv_mult=10 → False (1.0e9 &lt; 1.25e9)
      - test_liquidity_gate_nan: adv20=NaN → False
      - test_adv20_no_lookahead: compute adv20 at bar 25; mutate close[25] AFTER computation → result unchanged (because only t-1 and earlier consumed)
  </behavior>
  <action>
    Create `strategies/portfolio/sizing.py` with the 5 functions listed. `adv20` accepts pandas Series (or np arrays) and takes `bar_idx`. Implementation: `slice = close_series.iloc[bar_idx-20:bar_idx]; vol_slice = vol_series.iloc[bar_idx-20:bar_idx]; if len(slice) &lt; 20: return float("nan"); return float((slice * vol_slice).mean())`. Explicit slicing (no rolling) to make the `state[i-1]` discipline audit-obvious.
    `sort_by_canslim` takes candidates as list of objects with attribute `ticker` (use duck typing), and `score_lookup` as a callable `score_lookup(ticker) -> Optional[float]`. Returns `(kept_sorted_desc, dropped_missing)`.
    Create `tests/strategies/portfolio/test_sizing.py` with the 6 sizing tests. Use `pytest.approx` where appropriate. For canslim tests, define a tiny local `Cand = namedtuple("Cand","ticker")`.
    Create `tests/strategies/portfolio/test_liquidity_gate.py` with the 6 liquidity tests, using pandas Series synthetic data. test_adv20_no_lookahead is critical for SC8 — document with inline comment citing memory feedback_equity_formula.md.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_sizing.py tests/strategies/portfolio/test_liquidity_gate.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def lot_round_shares" strategies/portfolio/sizing.py matches
    - grep "def adv20" strategies/portfolio/sizing.py matches
    - grep "def liquidity_gate_passes" strategies/portfolio/sizing.py matches
    - grep "def sort_by_canslim" strategies/portfolio/sizing.py matches
    - grep "def test_lot_round_floors_down" tests/strategies/portfolio/test_sizing.py matches
    - grep "def test_adv20_no_lookahead" tests/strategies/portfolio/test_liquidity_gate.py matches
    - pytest exits 0 with ≥12 sizing+liquidity tests passed
  </acceptance_criteria>
  <done>Sizing, ADV20, liquidity gate, and canslim tie-break tests all green; residual-cash semantics locked in.</done>
</task>

</tasks>

<verification>
uv run pytest tests/strategies/portfolio/test_exit_chain.py tests/strategies/portfolio/test_sizing.py tests/strategies/portfolio/test_liquidity_gate.py -x -q
</verification>

<success_criteria>
- Exit chain honors D-13 first-match-wins + D-14 T+2 override
- Hard-stop limit-down deferral flagged (D-19)
- RS streak resets on NaN (D-16)
- 100-lot floor leaves residual in cash (D-11)
- ADV20 no-lookahead (SC8 precursor)
- CANSLIM tie-break sorts desc, drops missing scores (D-10)
</success_criteria>

<output>
After completion, create `.planning/phases/31-multi-stock-portfolio-engine/31-03-SUMMARY.md`
</output>
