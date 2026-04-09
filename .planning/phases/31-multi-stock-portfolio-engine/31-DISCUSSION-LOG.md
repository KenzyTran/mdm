# Phase 31: Multi-Stock Portfolio Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents. Decisions captured in 31-CONTEXT.md.

**Date:** 2026-04-09
**Mode:** discuss (interactive)
**Areas discussed:** Entry source, Tie-breaker, RS source, Lot residual, Cooldown clock, Slot reuse, MA50 stop semantics, RS trigger window

## Gray Areas Identified

Locked by REQUIREMENTS (not discussed): 8 slots, 12.5%/slot, 100-share round-down, 8% hard stop, MA50 trailing (vol ≥1.25×), T+2, 7% ceiling/floor lock, cooldown length (5d), cost percentages, liquidity gate (20d ADV > 10×), `state[i-1]` discipline, exit priority chain order.

Carry-forward from Phase 30: package layout (`strategies/portfolio/`), Python dataclass config, `adjust_ohlc()` mandatory, markdown+CSV artifacts, HybridEngine MDM source, next-bar ATO fill model.

## Questions & Answers

### Batch 1

**Q1: Entry source stream**
- Options: A∪C union / A only / C only / config-driven default union
- **Selected:** A ∪ C (union, dedup)
- Follow-up: config exposes `entry_mode` so Phase 32 can sweep all three

**Q2: Tie-breaker when candidates > free slots**
- Options: CANSLIM score desc / alphabetical / 20d volume / seeded random
- **Selected:** CANSLIM score descending (recommended)

**Q3: RS source for PORT-06 exit**
- Options: Reuse Phase 29 S-letter / IBD composite / simple 6m return rank
- **Selected (Other):** "SELECT * FROM stock_rs LIMIT 10, ở postgres có dữ liệu này"
- **Interpretation:** Pre-existing postgres table `stock_rs`. Phase 31 adds reader to `connectors/postgres.py`. Must validate against known rows before use.

**Q4: Lot-rounding residual cash**
- Options: Stays in cash / redistribute / bump 1 extra lot
- **Selected:** Stays in cash (recommended)

### Batch 2

**Q5: Cooldown clock**
- Options: 5 trading days from D+1 / 5 trading days from D / 5 calendar days
- **Selected:** 5 trading days from D+1 (earliest re-entry = D+6)

**Q6: Slot reuse within same bar**
- Options: Next bar ATO / same-bar reuse allowed
- **Selected:** Next bar ATO (recommended) — consistent with Phase 30 fill model

**Q7: MA50 trailing stop vol-confirm timing**
- Options: Same bar / close break + confirm on t or t+1 / 2 consecutive closes
- **Selected:** Same bar — both conditions on bar t, exit fill open[t+1]

**Q8: RS<70 for 5 sessions semantics**
- Options: 5 consecutive / 5 of last 10 / 5 consecutive AND day-5 RS<70
- **Selected:** 5 consecutive trading days (strictest)

## Scope Guardrails Applied

- Short positions: out of scope (long-only milestone)
- Sector concentration limits: not in requirements, deferred
- Alternative gate policies: deferred to Phase 32 sweep (if at all)
- Dashboard/reporting: deferred to Phase 34

## Notes

- User communicates in Vietnamese; technical terms kept in English.
- RS source answer revealed a new integration point (stock_rs postgres table) that was not in prior artifacts — added to canonical refs as a new reader requirement.
- No scope creep raised during discussion.
