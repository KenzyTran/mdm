# Phase 31: Multi-Stock Portfolio Engine - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

A long-only multi-stock state machine that consumes Phase 30 entry fills and the MDM (HybridEngine VN30) gate, manages up to 8 equal-weight positions, enforces stops/exits/costs and Vietnam microstructure (T+2, 7% ceiling/floor locks), and emits trade log + position log + daily NAV with strict `state[i-1]` discipline. VN100 end-to-end backtest + parameter sweep belong to Phase 32. No UI.

</domain>

<decisions>
## Implementation Decisions

### Package Layout
- **D-01:** New package `strategies/portfolio/` parallel to `strategies/entry/` and `strategies/canslim/`. Proposed files: `config.py` (PortfolioConfig dataclass), `engine.py` (PortfolioEngine orchestrator), `state.py` (PositionBook / SlotState / CooldownRegistry), `exits.py` (exit priority chain), `costs.py` (commission/tax/slippage), `microstructure.py` (T+2, ceiling/floor lock helpers), `ab_report.py` (trade/position/NAV writers).
- **D-02:** All price/volume reads go through `connectors/adjust.py::adjust_ohlc()` — same discipline carried forward from Phase 28/29/30.
- **D-03:** PortfolioConfig is a Python dataclass (no YAML), fail-loud validation in `__post_init__`, consistent with Phase 29/30.

### Entry Source (GATE + PORT-01)
- **D-04:** Entry feed = `A ∪ C` union of Phase 30's two signal streams, deduped per (ticker, window). If the same ticker fires both A and C inside a single MDM-BUY window, the **earlier fill date wins**; ties broken by detector order A then C.
- **D-05:** PortfolioConfig exposes `entry_mode ∈ {"A", "C", "union"}` with default `"union"`, so Phase 32 can sweep all three. Semantics of each mode: `A`/`C` = that stream only; `union` = D-04.
- **D-06:** Phase 31 consumes Phase 30's `EntryEngine` Fill records directly — does not re-run detectors. Phase 30 is run once upstream and its Fill list is passed into PortfolioEngine at construction.

### MDM Gate (GATE-01, GATE-02)
- **D-07:** Gate source = HybridEngine VN30 state series (v6 config, current best model per memory), identical to Phase 30. Passed in at engine construction; Phase 31 does not re-run MDM.
- **D-08:** Policy A (strict) enforced as: `BUY` → new entries allowed up to 8 slots; `CASH` → hold existing, no new fills (entry candidates on CASH days are dropped, not queued); `SELL` → liquidate all positions at next-day open, subject to floor-lock deferral (GATE-03).

### Slot Allocation & Tie-Breaker (PORT-01, PORT-02)
- **D-09:** Equal-weight sizing: target notional per slot = `NAV[t-1] * 0.125`. Share count = `floor(target_notional / fill_price / 100) * 100`. Uses NAV computed from `state[i-1]` — never `state[i]`.
- **D-10:** When bar `t` has more entry candidates than free slots, **tie-breaker = CANSLIM score descending** (total score from Phase 29 scorer on signal bar `t`). Implementation requires Phase 29 scorer output to be available; if score is missing for a candidate, that candidate is dropped with a log warning (fail-loud).
- **D-11:** Lot-rounding residual (e.g. 125M target, 124.8M filled) **stays in cash** — no redistribution, no bumping up one extra lot. Keeps equal-weight semantics clean and NAV reflects real deployment.
- **D-12:** Free-slot reuse: if exit on bar `t` frees a slot, any entry candidate with signal bar `t` fills at `open[t+1]` following the normal Phase 30 fill model — i.e. slot is considered free for entries dated `t` onward. This is **not** same-bar intraday reuse; it is the natural next-bar ATO fill after an end-of-bar-t exit.

### Exit Priority Chain (PORT-06)
- **D-13:** Per-position exit evaluation order on each bar, first-match-wins:
  1. **MDM SELL** (GATE-02) — liquidate at `open[t+1]`, deferred if floor-lock (GATE-03)
  2. **8% hard stop** (PORT-03) — `low[t] ≤ buy_price * 0.92` triggers; exit fill = `open[t+1]`. Limit-down exception (PORT-05): if `low[t] == floor[t] == high[t]` on stop-hit day, exit deferred to next open that isn't floor-locked.
  3. **MA50 trailing break** (PORT-04) — same-bar trigger: `close[t] < MA50[t]` AND `vol[t] ≥ 1.25 * mean(vol[t-20..t-1])`. Both conditions on bar `t`; exit fill = `open[t+1]`. MA50 = simple MA on adjusted close.
  4. **RS deterioration** (PORT-06) — `stock_rs` value < 70 for **5 consecutive trading sessions**; exit fill = `open[t+1]` where `t` is the 5th consecutive day.
- **D-14:** T+2 hard constraint (GATE-04) overrides **all** exit triggers: a position bought on day D cannot be exited before day D+3. If an exit condition fires on D+1 or D+2, it is deferred until D+3 (or the next non-floor-locked bar).

### RS Source (PORT-06)
- **D-15:** RS values sourced from **postgres table `stock_rs`** — existing data per user. Phase 31 adds a reader in `connectors/postgres.py` (new function, e.g. `load_stock_rs(start, end, tickers)`) that returns a `(date, ticker) → rs_value` frame. Reader must be validated against at least 2 known historical dates before use.
- **D-16:** RS trigger semantics (D-13 item 4): **5 consecutive trading days with rs_value < 70**. Streak resets on any day where rs_value ≥ 70 or rs_value is missing (missing-data fail-closed: no exit trigger).

### Vietnam Microstructure (GATE-03, GATE-04, PORT-05)
- **D-17:** **T+2 settlement (GATE-04):** position bought on bar D with fill at `open[D]` is not eligible for any sell (manual or triggered) until bar D+3. Encoded as `earliest_sell_bar = buy_bar + 3`.
- **D-18:** **Ceiling lock on entry (GATE-03):** skip fill if `open[t+1] == ceiling[t+1] AND high[t+1] == low[t+1]`. Ceiling reference = `prev_close * 1.07` rounded per VN tick rules; if tick rounding helper doesn't exist, use raw `* 1.07` and leave a TODO. Skipped fills are logged as `unfilled: ceiling_lock` and do NOT retry on subsequent bars (the opportunity is gone).
- **D-19:** **Floor lock on exit (GATE-03, PORT-05):** if exit is triggered on bar `t` but `open[t+1] == floor[t+1] AND high[t+1] == low[t+1]`, exit is deferred to the next bar where this lock condition is false. Deferred exits keep their trigger reason in the trade log.

### Cooldown (PORT-07)
- **D-20:** 5-day re-entry cooldown after a stop-out (any of: 8% hard stop, MA50 break, RS deterioration). MDM SELL liquidations do **not** trigger cooldown (market-wide exit, not ticker-specific failure).
- **D-21:** Cooldown clock: **5 trading days from D+1**, where D = exit fill bar. Earliest re-entry bar = D+6 (i.e. 5 full trading sessions must pass). Calendar days not used.

### Costs (PORT-08)
- **D-22:** Entry cost = `0.25% commission + 0.10% slippage` applied to fill notional. Exit cost = `0.25% commission + 0.10% sell tax + 0.10% slippage`. Costs debited from cash at fill time; cost basis for P&L = fill price * (1 + entry_cost_pct).
- **D-23:** All three cost components are PortfolioConfig-overridable for sensitivity testing in Phase 33.

### Liquidity Gate (PORT-09)
- **D-24:** Entry refused if `ADV20[t] < 10 * target_notional` where `ADV20[t] = mean(close[t-20..t-1] * vol[t-20..t-1])` (VND notional, not share count), computed on signal bar `t`. Refused entries logged as `unfilled: liquidity_gate` with the ADV20 value and threshold.

### NAV & Equity Curve (PORT-10)
- **D-25:** Daily NAV[t] = cash[t] + Σ(shares_i * close[t]_i) for all open positions i. Positions marked to `close[t]`, not next-day open. Cash includes all completed trade settlements (commissions deducted, sell tax deducted on exit).
- **D-26:** **`state[i-1]` discipline (memory: equity formula rule):** all sizing, exit checks, and gate reads on bar `t` use state/prices observed at or before bar `t-1` for decisions that affect bar `t` entries. Exit checks that legitimately need bar-`t` data (e.g. `close[t] < MA50[t]`) trigger exits at `open[t+1]`. A unit test MUST assert that no NAV computation or fill-sizing path reads `state[t]` to decide bar `t` actions.

### Output Artifacts
- **D-27:** Report at `docs/audits/phase31-portfolio-engine.md` + CSVs under `docs/audits/phase31/`:
  - `trades.csv` — one row per completed round-trip: ticker, buy_date, buy_price, buy_cost, sell_date, sell_price, sell_cost, pnl_vnd, pnl_pct, exit_reason
  - `positions.csv` — daily snapshot per open position
  - `nav.csv` — daily NAV, cash, deployed_pct, open_slots
  - `unfilled.csv` — rejected entries with reason (ceiling_lock / liquidity_gate / cooldown / no_free_slot / canslim_score_missing)
- **D-28:** No notebooks. Consistent with Phase 28/29/30 markdown+CSV convention.

### Claude's Discretion
- Internal data structure for `PositionBook` (dict vs dataclass list vs frame)
- Exact test fixture layout under `tests/strategies/portfolio/`
- Vectorized vs loop implementation (correctness first)
- Whether to materialize full daily state frame or stream bar-by-bar
- Ceiling/floor tick rounding helper (can use raw `* 1.07` with TODO if no helper exists)
- Logging format for unfilled/deferred events
- Whether `stock_rs` reader lives in `connectors/postgres.py` or a new `connectors/rs.py` file

### Folded Todos
None — no pending todos matched Phase 31 scope at context-gather time.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 31 — Goal, success criteria SC1–SC8
- `.planning/REQUIREMENTS.md` GATE-01..GATE-04, PORT-01..PORT-10 — Complete portfolio engine requirements

### Upstream Phase 30 Artifacts (mandatory reads)
- `.planning/phases/30-stock-level-entry-confirmation/30-CONTEXT.md` — Entry detector semantics, window model, fill model, deferred items (T+2, ceiling/floor, cooldown) that Phase 31 now owns
- `strategies/entry/` — EntryEngine orchestrator; Phase 31 consumes its Fill records
- `docs/audits/phase30-entry-ab.md` — A/B fill counts on VN100; baseline for what Phase 31's entry feed looks like
- `docs/rules_entry.md` — Option A / Option C formulas, window semantics

### Upstream Phase 29 Artifacts (mandatory reads)
- `.planning/phases/29-vn100-universe-canslim-scorer/29-CONTEXT.md` — CANSLIM scorer output shape; **tie-breaker in D-10 reads the total score**
- `strategies/canslim/` — Scorer package; Phase 31 imports total score for tie-breaking

### Upstream Phase 28 Artifacts (mandatory reads)
- `connectors/postgres.py` — Will be extended with `stock_rs` reader (D-15)
- `connectors/adjust.py` — `adjust_ohlc()` mandatory for all price/volume reads

### MDM State Source
- `models/mdm_engine.py` / HybridEngine — VN30 MDM state series (v6 config, current best model)
- `docs/rules_mdm_hybrid.md` — CASH/SELL ↔ BUY transition rules

### Prior related work
- `.planning/phases/23-fail-safe-mechanism/` — Fail-safe is part of HybridEngine state; Phase 31 inherits it via the passed-in state series

### Memory discipline
- **Equity formula rule** (memory `feedback_equity_formula.md`) — `state[i-1]` discipline is non-negotiable; test-enforced per D-26 and SC8
- **Best VN30 model** (memory `project_best_model.md`) — HybridEngine + best sweep config = 190.8% is the MDM gate source

### Rules docs to update per Code-Docs Sync Rule
- `docs/rules_canslim_mdm.md` (new, due Phase 34) — Will document the full CANSLIM+MDM strategy. Phase 31 must add a portfolio-engine section in the same commit that ships the engine, even if the file is later superseded by Phase 34.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `strategies/entry/` (Phase 30) — EntryEngine produces Fill records that Phase 31 consumes directly. Same package structure pattern should be mirrored.
- `strategies/canslim/` (Phase 29) — Scorer output provides total score used for tie-breaker (D-10).
- `models/mdm_engine.py::HybridEngine` — VN30 MDM state series source; already integrated in Phase 30.
- `models/indicators.py` — MA50 helper; reuse if it matches adjusted-close semantics needed by D-13 item 3.
- `connectors/adjust.py::adjust_ohlc()` — Mandatory price reader.
- `connectors/postgres.py` — Existing postgres engine; extend with `stock_rs` reader (not yet present — confirmed by grep).

### Established Patterns
- **`state[i-1]` discipline** — The 707% bug (memory) makes this the #1 enforced invariant. SC8 requires an explicit unit test.
- **Fail-loud config validation** (Phase 29 D-08, Phase 30 D-20) — PortfolioConfig must raise on bad values in `__post_init__`.
- **Markdown + CSV audit artifacts** (Phase 28/29/30) — No notebooks, no Excel.
- **Dataclass config, no YAML** — Phase 29/30 precedent.
- **Adjusted OHLC only** — Zero raw-price reads anywhere in strategy code.
- **Next-bar ATO fill model** (Phase 30 D-11) — Phase 31 inherits this for both entries and exits; same-bar reuse explicitly disallowed (D-12).

### Integration Points
- **Upstream input:** Phase 30 `EntryEngine.run()` → list of Fill records (ticker, signal_bar, fill_bar, fill_price, detector_tag, window_id)
- **Upstream input:** HybridEngine VN30 state series (date → {BUY, CASH, SELL})
- **Upstream input:** Phase 29 scorer output frame (date, ticker → score + per-letter booleans)
- **Upstream input:** `connectors/postgres.py::load_stock_rs(...)` (new, D-15)
- **Upstream input:** `connectors/adjust.py::adjust_ohlc()` for price + ceiling/floor computation
- **Downstream output:** CSVs under `docs/audits/phase31/` consumed by Phase 32 (sweep) and Phase 33 (OOS) and Phase 34 (dashboard)

</code_context>

<specifics>
## Specific Ideas

- RS source is pre-existing postgres table `stock_rs` — user confirmed: "SELECT * FROM stock_rs LIMIT 10, ở postgres có dữ liệu này". Reader must be validated against ≥2 known historical rows before first use (no silent schema drift).
- Engine must pass a unit test asserting no `state[i]` look-ahead. This was the root of the 707% equity bug and is non-negotiable (memory).
- Policy A is strict — no soft/partial modes in Phase 31; sweep alternatives (if any) deferred to Phase 32.

</specifics>

<deferred>
## Deferred Ideas

- **VN100 end-to-end backtest + sweep** — Phase 32 scope (BT-01, BT-02).
- **OOS validation 2019-2025 + sensitivity** — Phase 33.
- **Dashboard + performance reporting + `docs/rules_canslim_mdm.md` finalization** — Phase 34.
- **Alternative gate policies** (B/C modes, partial exposure) — not in roadmap; noted as possible future work.
- **Short positions** — explicitly long-only this milestone.
- **Sector concentration limits** — not in requirements; can be added if sweep results show concentration risk.

</deferred>

---

*Phase: 31-multi-stock-portfolio-engine*
*Context gathered: 2026-04-09*
