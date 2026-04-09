---
phase: 31
name: multi-stock-portfolio-engine
status: complete
date: 2026-04-09
---

# Phase 31 Audit — Multi-Stock Portfolio Engine

## Scope

Phase 31 built the CANSLIM+MDM multi-stock long-only portfolio engine in
`strategies/portfolio/` and its Vietnam-microstructure primitives. The
engine is a bar-by-bar orchestrator that composes entry feed dedupe, MDM
gate dispatch (Policy A), slot allocation with CANSLIM tie-break, ADV20
liquidity gating, T+2 earliest-sell, 7% ceiling/floor locks, cooldown,
cost model, and the O'Neil-style exit priority chain into a single
`PortfolioEngine.run() -> PortfolioResult`.

**Engine-only phase.** There is **no production VN100 backtest run in this
phase**; end-to-end VN100 sweeps are deferred to **Phase 32**.

See `docs/rules_canslim_mdm.md` for the canonical rules spec.

## Deliverables

| Wave | Plan | Deliverable | Files |
|------|------|-------------|-------|
| 0 | 31-01 | Config, state, RS reader, synthetic panel fixture | `strategies/portfolio/config.py`, `state.py`; `connectors/postgres.py::load_stock_rs`; fixture |
| 2 | 31-02 | Microstructure + costs + cooldown primitives | `microstructure.py`, `costs.py`; cooldown tests |
| 3 | 31-03 | Exit chain + sizing + liquidity gate | `exits.py`, `sizing.py` |
| 4 | 31-04 | PortfolioEngine orchestrator + SC8 regression | `engine.py`; gate/nav-lookback/integration tests |
| 5 | 31-05 | Audit CSV writers + audit report + rules doc | `ab_report.py`; this file; `rules_canslim_mdm.md` |

## Test Coverage

All under `tests/strategies/portfolio/` — **64 tests passing** (62 from
plans 31-01..04 plus 2 round-trip tests added in 31-05):

| Test file | Focus | Count |
|-----------|-------|-------|
| `test_config.py` | PortfolioConfig fail-loud validation | 5 |
| `test_rs_reader.py` | `load_stock_rs` live postgres schema | 2 |
| `test_microstructure.py` | Ceiling/floor lock + T+2 math | 8 |
| `test_costs.py` | Entry debit / exit haircut / cost basis | 4 |
| `test_cooldown.py` | D+6 semantics + MDM SELL exemption | 4 |
| `test_exit_chain.py` | First-match priority + T+2 block + RS fail-closed | 13 |
| `test_sizing.py` | Slot notional + lot-floor + CANSLIM tie-break | 6 |
| `test_liquidity_gate.py` | ADV20 + no-lookahead | 6 |
| `test_gate_policy.py` | Policy A gate dispatch | 4 |
| `test_nav_lookback.py` | **SC8** — `state[i-1]` discipline | 3 |
| `test_engine_integration.py` | End-to-end synthetic integration | 5 |
| `test_ab_report.py` | 4-CSV round-trip + empty result | 2 |

## Success Criteria Status

| # | Criterion | Status |
|---|-----------|--------|
| SC1 | Engine runs bar-by-bar over a panel, emits `PortfolioResult` | **PASS** |
| SC2 | MDM gate (Policy A) admits/drops/liquidates per state | **PASS** (`test_gate_policy.py`) |
| SC3 | Max 8 slots; CANSLIM tie-break selects top-N | **PASS** (`test_engine_integration.py::test_canslim_tiebreak_selects_top`) |
| SC4 | T+2 blocks early exits; cooldown blocks re-entry | **PASS** (`test_t2_blocks_early_exit`, `test_cooldown_blocks_reentry`) |
| SC5 | Ceiling lock blocks entry; floor lock defers hard stop | **PASS** (`test_ceiling_lock_blocks_entry`, `test_exit_chain`) |
| SC6 | Exit priority first-match-wins (D-13) | **PASS** (`test_exit_chain.py`) |
| SC7 | ADV20 liquidity gate uses only prior bars | **PASS** (`test_liquidity_gate.py::test_adv20_no_lookahead`) |
| **SC8** | **NAV/sizing uses only `state[i-1]` — no bar-t lookahead** | **PASS (MANDATORY)** |

> **BOLD CALLOUT — SC8 is MANDATORY.** Per `memory/feedback_equity_formula.md`,
> bar-t mutations of `close` must not affect bar-t entries. The regression
> test `test_nav_lookback.py::test_no_bar_t_lookahead` mutates AAA close
> from bar 25 onward by 1.5× and asserts identical entries and final
> positions. This is the same class of bug that caused the historical
> 707% vs 93% divergence. Guarding SC8 is the single most important
> invariant before any production backtest is trusted.

## CSV Output Paths

`strategies/portfolio/ab_report.py::write_all(result, out_dir)` emits:

| File | Columns | Sort |
|------|---------|------|
| `docs/audits/phase31/trades.csv` | ticker, buy_date, buy_price, buy_cost_vnd, sell_date, sell_price, sell_cost_vnd, pnl_vnd, pnl_pct, exit_reason | sell_date |
| `docs/audits/phase31/positions.csv` | date, ticker, shares, mark_price, mark_value | (date, ticker) |
| `docs/audits/phase31/nav.csv` | date, nav, cash, deployed_pct, open_slots | date |
| `docs/audits/phase31/unfilled.csv` | date, ticker, reason, detail | (natural append order) |

Unfilled `reason` vocabulary: `ceiling_lock`, `liquidity_gate`, `cooldown`,
`no_free_slot`, `canslim_score_missing`, `shares_zero`, `insufficient_cash`,
`gate_cash`, `no_price_data`, `no_next_bar`, `already_open`.

Phase 31 ships these writers but does **not** run a production backtest;
sweep artifacts under `docs/audits/phase31/` will be populated in Phase 32.

## Deferred to Phase 32

- End-to-end VN100 sweep across all date ranges (no production run in
  Phase 31; engine-only).
- Parameter sweep over `max_slots`, `slot_weight`, `cooldown_days`,
  `adv_mult`, `ma50_vol_mult`, `rs_threshold`.
- Comparison vs. `rank_top_stocks.diem_canslim` baseline.
- Performance reporting (CAGR, Sharpe, MaxDD, win rate vs. VN100 benchmark).

## References

- Rules: `docs/rules_canslim_mdm.md` (Code-Docs Sync target)
- CONTEXT: `.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md`
- Plan summaries: `31-01-SUMMARY.md` .. `31-05-SUMMARY.md`
- Memory: `memory/feedback_equity_formula.md` (707% bug rationale for SC8)
