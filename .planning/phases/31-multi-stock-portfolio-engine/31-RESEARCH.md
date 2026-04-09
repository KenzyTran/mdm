# Phase 31: Multi-Stock Portfolio Engine - Research

**Researched:** 2026-04-09
**Domain:** Long-only multi-stock portfolio state machine (Vietnam VN100, daily bars, MDM-gated)
**Confidence:** HIGH

## Summary

Phase 31 is almost entirely design-locked by `31-CONTEXT.md` (D-01..D-28). Research scope reduces to: (1) verify upstream integration surfaces (Phase 30 `Fill`, Phase 29 scorer, HybridEngine state, `connectors/adjust.py`), (2) design the `stock_rs` postgres reader, (3) map each GATE/PORT requirement to a concrete test, and (4) enumerate the `state[i-1]` look-ahead test that SC8 demands. No library research is needed — stack is pandas/numpy/dataclasses, identical to Phase 28-30.

**Primary recommendation:** Mirror `strategies/entry/` package layout exactly. Build a bar-by-bar loop (correctness over vectorization) keyed off a shared trading-date index. All upstream inputs are injected at `PortfolioEngine.__init__` (mdm_state, fills, scorer_frame, price_panel, rs_frame) — zero re-running of upstream components. Enforce `state[i-1]` by never passing bar-`t` NAV/cash into decisions that fire fills on bar `t`; enforce with a dedicated unit test (SC8) that monkey-patches bar-`t` state and asserts fill outputs are unchanged.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Package Layout**
- D-01: New package `strategies/portfolio/` parallel to `strategies/entry/` and `strategies/canslim/`. Files: `config.py` (PortfolioConfig), `engine.py` (PortfolioEngine), `state.py` (PositionBook / SlotState / CooldownRegistry), `exits.py` (exit priority chain), `costs.py`, `microstructure.py` (T+2, ceiling/floor locks), `ab_report.py` (trade/position/NAV writers).
- D-02: All price/volume reads via `connectors/adjust.py::adjust_ohlc()`.
- D-03: `PortfolioConfig` = dataclass, fail-loud `__post_init__`, no YAML.

**Entry Source**
- D-04: Entry feed = `A ∪ C` union of Phase 30 Fill streams, deduped per (ticker, window). Same ticker both A & C inside one window → earlier fill_date wins; ties broken A before C.
- D-05: `entry_mode ∈ {"A","C","union"}`, default `"union"`.
- D-06: Consume Phase 30 `EntryEngine` Fill records directly — no re-running detectors.

**MDM Gate**
- D-07: Gate = HybridEngine VN30 state series (v6 config). Passed in at construction.
- D-08: Policy A strict. BUY → new entries up to 8 slots. CASH → hold, no new fills (candidates dropped, not queued). SELL → liquidate all at next-day open, subject to floor-lock deferral.

**Slot Allocation & Tie-Breaker**
- D-09: Target notional per slot = `NAV[t-1] * 0.125`. Shares = `floor(target / fill_price / 100) * 100`. NAV from `state[i-1]`.
- D-10: Tie-break on over-subscribed bars = CANSLIM total score (Phase 29) descending. Missing score → drop candidate with fail-loud log warning.
- D-11: Lot-rounding residual stays in cash. No redistribution.
- D-12: Slot freed by exit on bar `t` is available for a signal-bar-`t` candidate that fills at `open[t+1]`. Not intraday reuse.

**Exit Priority Chain (per-position, first-match wins)**
- D-13:
  1. MDM SELL → `open[t+1]`, deferred on floor-lock
  2. 8% hard stop → `low[t] ≤ buy_price*0.92` → `open[t+1]`. Limit-down exception: if `low[t]==floor[t]==high[t]`, defer to next non-floor-locked open
  3. MA50 trailing break → `close[t] < MA50[t]` AND `vol[t] ≥ 1.25 * mean(vol[t-20..t-1])`, same-bar trigger → `open[t+1]`. MA50 = SMA on adjusted close.
  4. RS deterioration → `stock_rs < 70` for 5 consecutive sessions → `open[t+1]` where t is the 5th day
- D-14: T+2 constraint (GATE-04) overrides ALL exit triggers. Position bought bar D cannot exit before D+3. Triggers firing on D+1 or D+2 deferred to D+3 (or next non-floor-locked bar).

**RS Source**
- D-15: RS from postgres table `stock_rs`. Add reader in `connectors/postgres.py` (e.g. `load_stock_rs(start, end, tickers)`) returning `(date, ticker) → rs_value`. Validate against ≥2 known historical rows before use.
- D-16: Trigger = 5 consecutive trading days with `rs_value < 70`. Missing data is fail-closed (does not break streak by counting, but does not advance either — treat as "not < 70", i.e. streak reset).

**Vietnam Microstructure**
- D-17: T+2: `earliest_sell_bar = buy_bar + 3`.
- D-18: Ceiling lock on entry: skip fill if `open[t+1]==ceiling[t+1] AND high[t+1]==low[t+1]`. Ceiling = `prev_close * 1.07` (raw, with TODO if no tick helper). Skipped → log `unfilled: ceiling_lock`, no retry.
- D-19: Floor lock on exit: if `open[t+1]==floor[t+1] AND high[t+1]==low[t+1]`, defer to next non-locked bar. Deferred exit keeps original trigger reason.

**Cooldown**
- D-20: 5-day re-entry cooldown after stop-out (8% / MA50 / RS). MDM SELL liquidations do NOT trigger cooldown.
- D-21: Clock: 5 trading days from D+1 where D = exit fill bar. Earliest re-entry bar = D+6.

**Costs**
- D-22: Entry = 0.25% comm + 0.10% slippage. Exit = 0.25% comm + 0.10% sell tax + 0.10% slippage. Costs debited from cash at fill time. P&L cost basis = `fill_price * (1 + entry_cost_pct)`.
- D-23: All cost components PortfolioConfig-overridable.

**Liquidity Gate**
- D-24: Refuse entry if `ADV20[t] < 10 * target_notional` where `ADV20[t] = mean(close[t-20..t-1] * vol[t-20..t-1])`. Refused → log `unfilled: liquidity_gate` with value + threshold.

**NAV & Equity Curve**
- D-25: `NAV[t] = cash[t] + Σ shares_i * close[t]_i`. Mark to `close[t]`.
- D-26: `state[i-1]` discipline. Sizing/gate reads on bar `t` use data ≤ `t-1`. Exit checks needing `close[t]`/MA50[t] are allowed but fire at `open[t+1]`. **SC8 mandatory test:** assert no NAV or fill-sizing path reads `state[t]` to decide bar `t` actions.

**Output**
- D-27: Report `docs/audits/phase31-portfolio-engine.md` + CSVs under `docs/audits/phase31/`: `trades.csv`, `positions.csv`, `nav.csv`, `unfilled.csv`.
- D-28: No notebooks. Markdown + CSV only.

### Claude's Discretion
- `PositionBook` internal data structure (dict vs dataclass list vs frame)
- Test fixture layout under `tests/strategies/portfolio/`
- Vectorized vs loop (correctness first)
- Materialize full daily state frame vs stream bar-by-bar
- Ceiling/floor tick rounding helper (raw `* 1.07` + TODO acceptable)
- Logging format for unfilled/deferred events
- Whether `stock_rs` reader lives in `connectors/postgres.py` or new `connectors/rs.py`

### Deferred Ideas (OUT OF SCOPE)
- VN100 end-to-end backtest + sweep → Phase 32
- OOS 2019-2025 + sensitivity → Phase 33
- Dashboard + `docs/rules_canslim_mdm.md` finalization → Phase 34
- Alternative gate policies (B/C, partial exposure)
- Short positions
- Sector concentration limits
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-01 | MDM signal source = HybridEngine + fail-safe on VNINDEX | Inject HybridEngine state series at engine ctor (D-07). HybridEngine already wired in Phase 30 — reuse that call site. |
| GATE-02 | Policy A strict (BUY/CASH/SELL semantics) | Encoded in D-08; implement as 3-branch dispatch in bar loop before per-position exit evaluation. |
| GATE-03 | Ceiling/floor lock handling | Helpers in `strategies/portfolio/microstructure.py`. Unit test with synthetic bar where `open==high==low==prev_close*1.07`. |
| GATE-04 | T+2 settlement | `earliest_sell_bar = buy_bar + 3` in `state.SlotState`. Unit test: exit trigger on D+1 is deferred to D+3. |
| PORT-01 | Max 8 concurrent positions, long-only | `PositionBook` with fixed `max_slots=8` from config. Reject when full unless an exit on same bar frees a slot (D-12). |
| PORT-02 | Equal-weight 12.5%, 100-lot round-down | D-09 formula. Test: NAV=1e9, fill_price=25000 → target=125M → shares=floor(125M/25000/100)*100 = 5000. |
| PORT-03 | 8% hard stop | D-13 item 2. Test limit-down exception (PORT-05). |
| PORT-04 | MA50 trailing stop + vol confirm 1.25× 20d avg | D-13 item 3. Use `models/indicators.py` MA50 helper only if it operates on adjusted close — otherwise implement locally. |
| PORT-05 | Limit-down exit deferral | Merged into D-13 item 2 + D-19. |
| PORT-06 | Exit priority chain + RS<70 5 sessions | D-13 ordering + D-16 RS streak. RS source = new `load_stock_rs()` reader. |
| PORT-07 | 5-day cooldown after stop-out | `CooldownRegistry` in `state.py`. D-20/D-21. MDM SELL exempt. |
| PORT-08 | Costs 0.25% comm both sides + 0.10% tax + 0.10% slippage | `costs.py` pure functions. D-22/D-23. |
| PORT-09 | 20d ADV > 10× position size | D-24 ADV20 formula. Computed on signal bar `t` from `t-20..t-1`. |
| PORT-10 | Trade/position/NAV logs + `state[i-1]` discipline | D-25/D-26 + mandatory look-ahead unit test (SC8). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.10+**, pandas ≥2.0, numpy ≥1.24, matplotlib ≥3.7, uv package manager.
- **Naming:** snake_case functions, PascalCase classes, UPPERCASE enums, dataclasses PascalCase. Dataframe columns: `date, close, high, low, open, volume, symbol` (the project uses `ticker` in strategies/ — keep consistent with `strategies/entry/`).
- **`state[i-1]` discipline** is the #1 enforced invariant (memory: 707% equity bug). SC8 unit test is non-negotiable.
- **No try/except as control flow.** Fail-loud via assertions / `ValueError` in `__post_init__`.
- **Adjusted OHLC only** via `connectors/adjust.py::adjust_ohlc()`. Zero raw-price reads in strategy code.
- **Code-Docs Sync Rule:** portfolio-engine section in `docs/rules_canslim_mdm.md` must ship in the same commit as engine code (even though file is finalized in Phase 34).
- **GSD workflow:** all edits through GSD commands.

## Standard Stack

### Core
| Library | Version (verified) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | ≥2.0 (project locked) | Time series frames, groupby on ticker, rolling windows for ADV20/MA50 | Already project stack |
| numpy | ≥1.24 | Vectorized math (only where it doesn't obscure bar-by-bar determinism) | Already project stack |
| sqlalchemy + psycopg2 | as in `connectors/postgres.py` | `load_stock_rs` reader | Existing connector pattern |
| dataclasses (stdlib) | 3.10+ | `PortfolioConfig`, `SlotState`, `Trade`, `Position` | Phase 29/30 precedent |

### Supporting
| Library | Purpose |
|---------|---------|
| `python-dotenv` | Postgres creds for `stock_rs` reader — already loaded in `connectors/postgres.py` |

### Alternatives Considered
| Instead of | Alternative | Tradeoff |
|------------|-------------|----------|
| Bar-by-bar Python loop | Vectorized state simulation | Vectorized obscures T+2/cooldown/exit-priority branching. Correctness-first mandates loop. |
| Pandas rolling for ADV20 | Manual slice `close[t-20..t-1]` inside loop | Rolling on `close * vol` precomputed once outside loop is fine and preserves `state[i-1]` (value at `t-1` used on bar `t`). Use rolling precompute. |

**Installation:** All dependencies already present. No new packages.

## Architecture Patterns

### Recommended Package Structure (matches D-01)

```
strategies/portfolio/
├── __init__.py
├── config.py           # PortfolioConfig dataclass (fail-loud __post_init__)
├── engine.py           # PortfolioEngine — orchestrator, bar loop
├── state.py            # PositionBook, SlotState, CooldownRegistry, Trade, Position
├── exits.py            # Exit priority chain: evaluate_exits(position, bar_ctx) -> ExitDecision | None
├── costs.py            # apply_entry_cost(notional, cfg), apply_exit_cost(notional, cfg)
├── microstructure.py   # compute_ceiling(prev_close), compute_floor(prev_close),
│                       #   is_ceiling_locked(bar), is_floor_locked(bar),
│                       #   t2_earliest_sell_bar(buy_bar)
└── ab_report.py        # write_trades_csv, write_positions_csv, write_nav_csv, write_unfilled_csv

tests/strategies/portfolio/
├── conftest.py
├── test_config.py              # fail-loud validation
├── test_microstructure.py      # ceiling, floor, T+2
├── test_costs.py
├── test_cooldown.py
├── test_exit_chain.py          # priority ordering, T+2 override
├── test_sizing.py              # lot rounding, 100-share
├── test_rs_reader.py           # stock_rs historical validation (≥2 rows)
├── test_gate_policy.py         # BUY/CASH/SELL Policy A
├── test_liquidity_gate.py
├── test_nav_lookback.py        # SC8 — state[i-1] discipline
├── test_engine_integration.py  # end-to-end synthetic 3-ticker scenario
└── fixtures/
    └── synthetic_panel.py
```

### Pattern 1: Inject-All-Upstream Constructor
`PortfolioEngine.__init__(config, mdm_state, fills, scorer_frame, price_panel, rs_frame, trading_dates)` — same "nothing is recomputed mid-run" pattern as `strategies/entry/engine.py` (see D-07 invariant there).

### Pattern 2: First-Match-Wins Exit Chain
`exits.evaluate_exits(position, bar_ctx) -> Optional[ExitDecision]` iterates 4 triggers in D-13 order and returns the first match, OR `None` if T+2 not yet satisfied (D-14 override).

### Pattern 3: Bar Loop Skeleton
```
for t in trading_dates:
    nav_prev = compute_nav(t_prev)           # state[i-1]
    # 1. MDM gate read
    gate = mdm_state[t]
    # 2. Evaluate exits for all open positions (uses close[t], MA50[t], rs[t] — allowed)
    #    Apply T+2 override, floor-lock deferral
    #    Fills scheduled for open[t+1]
    # 3. If gate == SELL -> schedule liquidation for all positions at open[t+1]
    # 4. If gate == BUY -> select entry candidates signal_bar == t from fills feed,
    #    dedupe A∪C (D-04), sort by canslim score desc (D-10),
    #    check free slots (after scheduled exits free them), liquidity gate, cooldown,
    #    ceiling-lock on open[t+1]. Schedule fills for open[t+1].
    # 5. Materialize any fills/exits scheduled for open[t] from previous bar.
    # 6. Record NAV[t] = cash[t] + Σ shares_i * close[t]_i
```

### Anti-Patterns to Avoid
- **Reading `mdm_state[t+1]` or `close[t+1]` to decide bar `t` action.** 707% bug pattern.
- **Mutating `NAV[t]` via bar-`t` entry then using it for same-bar sizing.** Sizing must use `NAV[t-1]`.
- **Hidden retries on `unfilled: ceiling_lock`.** D-18 is explicit: opportunity gone.
- **Same-bar slot reuse.** D-12 requires next-bar fill.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OHLC adjustment | Your own split/dividend logic | `connectors/adjust.py::adjust_ohlc()` | Already validated in Phases 28-30 |
| MDM state | Re-run HybridEngine | Inject state series at ctor (D-07) | Phase 30 precedent, single source of truth |
| CANSLIM score | Recompute for tie-break | Import Phase 29 scorer output frame | D-10 explicit |
| Postgres engine | New connection | `connectors/postgres.py::get_engine()` | Pool reuse |
| Entry detection | Re-run A/C detectors | Consume Phase 30 Fill records (D-06) | Avoid drift |

## Runtime State Inventory

Not applicable — Phase 31 is greenfield module creation. No rename/refactor. No existing stored state to migrate. Build artifacts are pure Python (no egg-info). Only new side effect: `load_stock_rs` reader hitting existing postgres table (read-only, no schema change).

## Common Pitfalls

### Pitfall 1: Look-ahead via `NAV[t]` in bar-`t` sizing
**What goes wrong:** Sizing uses current-bar NAV which already includes open positions marked to `close[t]` — the 707% bug.
**Prevention:** Strict ordering — compute `nav_prev` first, use only that for sizing. Unit test (SC8): given a panel where `close[t]` is mutated drastically, bar-`t` entry fills must be identical.

### Pitfall 2: T+2 vs exit-trigger interaction
**What goes wrong:** 8% stop on D+1 silently exits, violating T+2.
**Prevention:** `exits.evaluate_exits` returns `None` if `t < earliest_sell_bar`, AND the deferred trigger must re-check each subsequent bar (not silently discarded). Test: synthetic bar where stop fires on D+1, exit actually lands on D+3.

### Pitfall 3: Missing CANSLIM score on tie-break day
**What goes wrong:** Silent drop → fewer fills than expected, hard to debug.
**Prevention:** D-10 mandates fail-loud log and `unfilled: canslim_score_missing` row.

### Pitfall 4: RS streak counting with missing data
**What goes wrong:** Streak counts straight through NaN days and fires spurious exit.
**Prevention:** D-16 — missing data resets streak. Test: `[65, 65, NaN, 65, 65]` should NOT trigger.

### Pitfall 5: Ceiling/floor reference price
**What goes wrong:** Using adjusted prev_close for ceiling computation when Vietnamese exchange rule uses raw prev_close.
**Prevention:** Acceptable per D-18 to use raw `prev_close * 1.07` with TODO. Document clearly.

### Pitfall 6: Multiple exits triggering on same day against SELL liquidation
**What goes wrong:** 8% stop and MDM SELL both fire, double-counted trade.
**Prevention:** First-match-wins — MDM SELL is priority 1 per D-13. Single exit record.

### Pitfall 7: Lot-rounding residual bookkeeping
**What goes wrong:** Residual VND silently disappears, NAV drifts.
**Prevention:** D-11: residual stays in cash. Test: notional 125M, price 25100 → shares=4900, deployed=122.99M, residual=2.01M must appear in `cash[t]`.

## Code Examples

### Bar-loop entry selection skeleton
```python
# strategies/portfolio/engine.py — illustrative
def _select_entries(self, t: pd.Timestamp, nav_prev: float,
                    free_slots: int) -> list[EntryPlan]:
    if free_slots <= 0 or self.mdm_state.loc[t] != "BUY":
        return []
    # Candidates = Phase 30 fills with signal_date == t, filtered by entry_mode
    cands = self._candidates_on(t)
    # Dedup A∪C (D-04): earlier fill_date wins, tie A before C
    cands = self._dedupe_union(cands)
    # Tie-break: CANSLIM total score descending (D-10)
    cands = self._sort_by_canslim(cands, t)  # drops missing-score with log
    plans = []
    target = nav_prev * self.config.slot_weight  # 0.125
    for c in cands[:free_slots]:
        if self._in_cooldown(c.ticker, t):
            self._log_unfilled(c, "cooldown"); continue
        if self._adv20(c.ticker, t) < self.config.adv_mult * target:
            self._log_unfilled(c, "liquidity_gate"); continue
        if self._is_ceiling_locked(c.ticker, t_plus_1=c.fill_date):
            self._log_unfilled(c, "ceiling_lock"); continue
        shares = int((target / c.fill_price) // 100) * 100
        if shares == 0:
            self._log_unfilled(c, "no_free_slot"); continue
        plans.append(EntryPlan(ticker=c.ticker, fill_date=c.fill_date,
                               fill_price=c.fill_price, shares=shares))
    return plans
```

### `stock_rs` reader (D-15)
```python
# connectors/postgres.py — new function
def load_stock_rs(start: str, end: str,
                  tickers: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Load stock_rs values for RS<70 streak exit trigger (Phase 31 PORT-06).

    Returns a long frame with columns ['date', 'ticker', 'rs_value'].
    Validate against ≥2 known historical rows before first production use.
    """
    eng = get_engine()
    q = """
        SELECT tradingdate AS date, stockcode AS ticker, rs AS rs_value
        FROM stock_rs
        WHERE tradingdate BETWEEN :start AND :end
    """
    params = {"start": start, "end": end}
    if tickers:
        q += " AND stockcode = ANY(:tickers)"
        params["tickers"] = list(tickers)
    df = pd.read_sql(text(q), eng, params=params)
    df["date"] = pd.to_datetime(df["date"])
    return df
```
**IMPORTANT:** Actual column names in `stock_rs` must be confirmed by the implementer (`SELECT * FROM stock_rs LIMIT 1`) before writing this query — the above is a template, not verified schema. D-15 requires ≥2 known historical rows validated in a test.

## Open Questions

1. **`stock_rs` exact schema**
   - What we know: user confirmed table exists with data (`SELECT * FROM stock_rs LIMIT 10`).
   - What's unclear: exact column names (`stockcode`/`ticker`, `tradingdate`/`date`, `rs`/`rs_value`).
   - Recommendation: First task of Wave 0 is a spike — run `\d stock_rs` in psql and write the reader against real schema. Validation test reads ≥2 known rows.

2. **MA50 helper reuse**
   - What we know: `models/indicators.py` has MA50.
   - What's unclear: whether it's configured for adjusted close or raw.
   - Recommendation: Implementer inspects `models/indicators.py`. If adjusted-close compatible, reuse; otherwise compute locally `close.rolling(50).mean()` on adjusted series.

3. **VN tick rounding helper existence**
   - What we know: D-18 explicitly permits raw `* 1.07` with TODO.
   - Recommendation: Use raw, log TODO. No blocker.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.10+ | All | ✓ | project locked | — |
| pandas ≥2.0 | All | ✓ | project locked | — |
| numpy ≥1.24 | All | ✓ | project locked | — |
| postgres (`stock_rs` table) | PORT-06 RS reader | ✓ (user confirmed) | — | None — hard dependency |
| HybridEngine VN30 state | GATE-01 | ✓ | v6 current best | — |
| Phase 30 `strategies/entry/` | D-06 | ✓ | shipped | — |
| Phase 29 `strategies/canslim/` | D-10 tie-break | ✓ | shipped | — |
| `connectors/adjust.py::adjust_ohlc` | D-02 | ✓ | shipped | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (inferred from `tests/` layout, existing `test_*.py` files) |
| Config file | None detected at repo root (no `pytest.ini`/`pyproject.toml [tool.pytest]` specified for portfolio scope); existing tests run via `pytest tests/...` — Wave 0 task: verify and add `[tool.pytest.ini_options]` if missing |
| Quick run command | `uv run pytest tests/strategies/portfolio/ -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| GATE-01 | HybridEngine state injection | unit | `uv run pytest tests/strategies/portfolio/test_gate_policy.py::test_state_source -x` | ❌ Wave 0 |
| GATE-02 | Policy A BUY/CASH/SELL dispatch | unit | `uv run pytest tests/strategies/portfolio/test_gate_policy.py -x` | ❌ Wave 0 |
| GATE-03 | Ceiling/floor lock | unit | `uv run pytest tests/strategies/portfolio/test_microstructure.py -x` | ❌ Wave 0 |
| GATE-04 | T+2 override of exits | unit | `uv run pytest tests/strategies/portfolio/test_exit_chain.py::test_t2_override -x` | ❌ Wave 0 |
| PORT-01 | Max 8 slots, long-only | unit | `uv run pytest tests/strategies/portfolio/test_sizing.py::test_max_slots -x` | ❌ Wave 0 |
| PORT-02 | Equal-weight 12.5% lot rounding | unit | `uv run pytest tests/strategies/portfolio/test_sizing.py::test_lot_rounding -x` | ❌ Wave 0 |
| PORT-03 | 8% hard stop | unit | `uv run pytest tests/strategies/portfolio/test_exit_chain.py::test_hard_stop -x` | ❌ Wave 0 |
| PORT-04 | MA50 trailing + vol confirm | unit | `uv run pytest tests/strategies/portfolio/test_exit_chain.py::test_ma50_trailing -x` | ❌ Wave 0 |
| PORT-05 | Limit-down exit deferral | unit | `uv run pytest tests/strategies/portfolio/test_exit_chain.py::test_limit_down_defer -x` | ❌ Wave 0 |
| PORT-06 | Exit priority chain + RS<70 streak | unit | `uv run pytest tests/strategies/portfolio/test_exit_chain.py::test_priority_order tests/strategies/portfolio/test_exit_chain.py::test_rs_streak -x` | ❌ Wave 0 |
| PORT-06 | `stock_rs` reader ≥2 historical rows | integration | `uv run pytest tests/strategies/portfolio/test_rs_reader.py -x` | ❌ Wave 0 (requires postgres) |
| PORT-07 | 5-day cooldown after stop, exempt MDM SELL | unit | `uv run pytest tests/strategies/portfolio/test_cooldown.py -x` | ❌ Wave 0 |
| PORT-08 | Entry/exit costs + sell tax | unit | `uv run pytest tests/strategies/portfolio/test_costs.py -x` | ❌ Wave 0 |
| PORT-09 | Liquidity gate ADV20 × 10 | unit | `uv run pytest tests/strategies/portfolio/test_liquidity_gate.py -x` | ❌ Wave 0 |
| PORT-10 | Trade/position/NAV logs + `state[i-1]` | unit + integration | `uv run pytest tests/strategies/portfolio/test_nav_lookback.py tests/strategies/portfolio/test_engine_integration.py -x` | ❌ Wave 0 |
| SC8 | No `state[i]` look-ahead in sizing | unit (critical) | `uv run pytest tests/strategies/portfolio/test_nav_lookback.py::test_no_bar_t_lookahead -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/strategies/portfolio/ -x`
- **Per wave merge:** `uv run pytest tests/strategies/portfolio/ tests/strategies/entry/ tests/strategies/canslim/ -x`
- **Phase gate:** `uv run pytest tests/ -x` green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/strategies/portfolio/conftest.py` — shared synthetic panel fixtures (3 tickers × 60 bars with controllable ceiling/floor days)
- [ ] `tests/strategies/portfolio/fixtures/synthetic_panel.py` — fixture generator
- [ ] All `test_*.py` files listed above — none exist yet
- [ ] Confirm pytest config path (root `pyproject.toml` or `pytest.ini`) and add portfolio tests to collection — verify during Wave 0
- [ ] `stock_rs` schema spike: run `\d stock_rs` via the postgres connector and record column names before writing `load_stock_rs`

## State of the Art

Not applicable — this is pure project-specific domain code with no external library churn. All patterns inherited from Phase 28-30.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md` — all D-01..D-28 decisions
- `.planning/REQUIREMENTS.md` — GATE-01..GATE-04, PORT-01..PORT-10
- `.planning/ROADMAP.md` §Phase 31 — SC1..SC8
- `c:/Users/trant/projects/mdm/strategies/entry/engine.py` — Fill/Unfilled dataclass shapes, inject-all-upstream pattern
- `c:/Users/trant/projects/mdm/connectors/postgres.py` — `get_engine`, existing reader patterns
- `c:/Users/trant/projects/mdm/CLAUDE.md` — project conventions, Code-Docs Sync Rule
- Memory `feedback_equity_formula.md` — 707% bug / `state[i-1]` discipline

### Secondary (MEDIUM confidence)
- `c:/Users/trant/projects/mdm/models/indicators.py` — MA50 helper existence (adjusted-close compatibility unverified, flagged as Open Question 2)

### Tertiary (LOW confidence)
- `stock_rs` table exact schema — user-confirmed it exists, but columns not verified in code; Wave 0 spike required

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — fully inherited from Phase 28-30
- Architecture: HIGH — package layout locked by D-01
- Pitfalls: HIGH — 707% bug is well-known, exit-chain edge cases enumerated by D-13/D-14
- RS reader schema: LOW — spike required

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable — no external library dependencies change this)
