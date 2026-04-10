# CANSLIM + MDM Portfolio Engine — Rules

**Code-Docs Sync Rule (CLAUDE.md):** This document is the canonical specification
for the multi-stock long-only portfolio engine living in `strategies/portfolio/`.
Any change to engine logic, primitives, or parameters MUST update this file in
the same commit.

**Scope:** Phase 31 shipped the engine, primitives, and audit writers. Phase 32
ran in-sample parameter sweeps. Phase 33 validated out-of-sample with locked
parameters.

---

## Overview

The CANSLIM+MDM portfolio engine is an event-driven, long-only, max-8-position
bar-by-bar loop over a Vietnamese-market OHLCV panel (T+2.5 settlement, 7%
ceiling/floor price limits). It composes Wave 0–4 primitives into a single
`PortfolioEngine.run()` that emits a `PortfolioResult` (trades, daily NAV,
daily positions, unfilled log). Covers requirements **GATE-01..04** and
**PORT-01..10**.

Key implementation: `strategies/portfolio/engine.py` (Phase 31 Plan 04).

## Locked Parameters (rank-1)

Selected as rank-1 from Phase 32 in-sample sweep (2014-2018) and locked for
Phase 33 OOS validation (2019-2025).

| Parameter | Value | Description |
|-----------|-------|-------------|
| c_yoy | 0.25 | Quarterly EPS YoY growth threshold (25%) |
| a_cagr | 0.20 | 3-year EPS CAGR threshold (20%) |
| n_prox | 0.10 | Proximity to 252-day high (within 10%) |
| hard_stop | 0.06 | Hard stop-loss from cost basis (6%) |
| slots | 5 | Maximum concurrent positions |
| entry | C | Entry option: Pocket Pivot (Option C) |
| slot_weight | 0.20 | Per-position weight (1/5 = 20% of NAV) |

## MDM Gate (Policy A) — D-08

The MDM state (BUY / CASH / SELL) from `HybridEngine + fail-safe` (best v6.0
model) is the capital-allocation gate:

- **BUY** — admit new entry candidates; existing positions unaffected.
- **CASH** — drop all entry candidates for the bar (logged as
  `unfilled.reason="gate_cash"`); existing positions continue running exits.
- **SELL** — liquidate all open positions at next open under the `mdm_sell`
  exit reason; MDM SELL exits are the ONLY exit type that does **not**
  register cooldown (D-20). Satisfies **GATE-01..04**.

## Entry Feed (A∪C Union) — D-04

Entry candidates are the union of the Option-A (pivot breakout) and Option-C
(base/RS) fill streams produced by `strategies/entry/` (Phase 30). Dedupe is
per `(ticker, window_id)` keeping the earliest `fill_date`, with A beating C
on ties. Satisfies **PORT-01**.

## Slot Allocation — D-09, D-10, D-11

- **Max slots:** Default `max_slots=8` in engine code; locked production config
  uses `slots=5` (rank-1). `slot_weight = 1/slots = 0.20`.
- **Slot weight:** `config.slot_weight = 1/8 = 0.125` of NAV[t-1] per new
  entry (D-09); rank-1 locked config uses 0.20 (1/5).
- **Tie-break when candidates > free_slots:** sort by `canslim_score` desc,
  drop rows with missing scores and log them as
  `unfilled.reason="canslim_score_missing"` (D-10, PORT-02).
- **Lot rounding:** shares = `floor(target_notional / fill_price / 100) * 100`.
  Residual stays in cash; zero-share entries are dropped with
  `unfilled.reason="shares_zero"` (D-11, PORT-03).

## Exit Priority Chain — D-13, D-14, D-16, D-19

Per `strategies/portfolio/exits.py`, first-match-wins within a single bar:

1. **T+2 block (D-14):** if `bar_idx < earliest_sell_bar`, NO exit can fire
   on this bar (PORT-05).
2. **MDM SELL** (Policy A liquidation) — top priority once T+2 clears.
3. **Hard stop (O'Neil 7–8%):** stop-loss from `cost_basis`. If the bar is a
   **limit-down floor lock**, the stop is **deferred** to the next non-locked
   bar (D-19, PORT-07).
4. **MA50 break:** close below MA50 with optional volume confirmation.
5. **RS streak:** N consecutive bars of RS below threshold; **fail-closed on
   NaN** (D-16) — any NaN in the streak window resets to zero and cannot
   trigger an exit.

Exit execution: at next-bar open unless floor-locked (deferred).

## Cooldown — D-20, D-21

Implemented in `CooldownRegistry` (`state.py`). After any exit **except
`mdm_sell`**, earliest re-entry bar is `exit_bar + cooldown_days + 1`
(default `cooldown_days=5` → D+6). The MDM SELL exemption is a hard contract
locked into `test_cooldown.py`. Satisfies **PORT-07**.

## Costs — D-22, D-23

Per `strategies/portfolio/costs.py`:

- **Entry debit:** `notional * (1 + 0.35%)` — includes fees + slippage.
- **Exit haircut:** `gross * (1 - 0.45%)`.
- **Cost basis:** `fill_price * (1 + entry_comm + entry_slip)` — used by
  the hard-stop rule. Satisfies **PORT-08**.

## Liquidity Gate (ADV20) — D-24

An entry candidate passes the liquidity gate iff
`target_notional ≤ adv_mult * ADV20`, where ADV20 is the 20-bar mean of
`close * volume` computed from bars **strictly before** the candidate bar
(explicit `iloc[-20:]` slice, no rolling, for SC8 audit-clarity). NaN ADV20
fails closed. Failures log `unfilled.reason="liquidity_gate"`. Satisfies
**PORT-09**.

## NAV Rule — SC8 `state[i-1]` Discipline

**NON-NEGOTIABLE (SC8, per `memory/feedback_equity_formula.md`):** any bar-t
sizing decision uses **only** NAV and ADV20 computed from bars strictly
before t. The engine computes `nav_prev = _compute_nav(bar_idx - 1)` BEFORE
any bar-t entry materialization, and the precomputed ADV20 series is shifted
by 1. Mutating `close[t]` in the input panel after NAV is computed must not
change bar-t entry shares or fill prices — proven by
`test_nav_lookback.py::test_no_bar_t_lookahead`. This is the same class of
bug that produced the historical 707% vs. 93% divergence; protecting state[i-1]
is the single most important invariant in this engine.

## T+2 & Ceiling/Floor Locks — D-17, D-18

- **T+2 (D-17):** `earliest_sell_bar = buy_bar + t_plus + 1`, default
  `t_plus=2` → earliest sell is `buy_bar + 3`.
- **Ceiling/floor (D-18):** `compute_ceiling(prev_close) = prev_close * 1.07`,
  `compute_floor(prev_close) = prev_close * 0.93`. A bar is
  ceiling/floor-locked iff `open == high == low == limit` (within tolerance
  0.02 VND to absorb VN tick rounding). Ceiling-locked bars block entry fills
  (`unfilled.reason="ceiling_lock"`); floor-locked bars defer hard-stop exits
  to the next bar. Satisfies **GATE-03, GATE-04, PORT-05**.

## Audit Output (D-27)

`strategies/portfolio/ab_report.py::write_all(result, out_dir)` writes the
canonical 4-CSV set — `trades.csv`, `positions.csv`, `nav.csv`,
`unfilled.csv` — under `docs/audits/phase31/`. Column schemas are enforced
and stable; empty results still produce header-only CSVs. Phase 32 parameter
sweeps consume these exact schemas. Satisfies **PORT-10**.

## OOS Performance (2019-2025)

Phase 33 OOS validation results using rank-1 locked parameters on current-vn100
universe mode (2019-01-01 to 2025-12-31):

| Metric | Value |
|--------|-------|
| CAGR | 6.23% |
| Sharpe_rf3 | 0.448 |
| MaxDD | -10.22% |
| MaxDD duration | 1007 days |
| Hit rate | 45.16% |
| Num trades | 62 |
| Avg hold days | 33.0 |

BT-08 verdict: Sharpe uplift +0.064 vs VN-Index B&H (target >0.20 FAIL);
MaxDD reduction 74.7% (target >30% PASS). Overall FAIL.

Key finding: CANSLIM stock selection IS the alpha source (Sharpe 1.047
standalone); MDM gate reduces Sharpe but dramatically cuts MaxDD from -40%
to -10%.

---

*Last updated: 2026-04-10 -- Phase 34 (locked rank-1 params from Phase 32 sweep, OOS results from Phase 33).*
