# Phase 13: Hybrid Engine Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 13-hybrid-engine-integration
**Areas discussed:** Propose-Filter-Decide wiring, Override behavior, Cash insertion logic, Backtest script output

---

## Propose-Filter-Decide Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| A) Diff-based | Compare old_state (snapshot) vs new_state (after mutation). State change = proposal. VETO = restore. | ✓ |
| B) Explicit proposal | Detect intended transition before mutation, create proposal object, filter decides before commit. Cleaner but needs significant refactor. | |

**User's choice:** A) Diff-based
**Notes:** Simpler, leverages existing engine flow. Only adds comparison logic at the filter block.

---

## Override Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| A) Force Cash | OVERRIDE always forces Cash regardless of proposed direction. Safe, matches Dr. K "favor cash" philosophy. | ✓ |
| B) Force opposite signal | OVERRIDE forces Buy->Sell or Sell->Buy. Aggressive, risk of overfitting. | |
| C) Asymmetric | Force Cash when in BUY, force BUY when in SELL. Complex asymmetric logic. | |

**User's choice:** A) Force Cash
**Notes:** Aligns with 2012 VMAP webinar finding. Phase 15 can upgrade.

---

## Cash Insertion Logic (HYB-05)

| Option | Description | Selected |
|--------|-------------|----------|
| A) EMA crossover bearish | Single condition (ema9 < ema21) triggers Cash insertion. Simple but rigid. | |
| B) Use IndicatorFilter | Run filter with "confirm current state" proposal on no-change days. VETO/OVERRIDE = degrade to Cash. Reuses existing logic. | ✓ |
| C) Separate threshold | Count bearish indicators independently, separate from filter. Redundant logic. | |

**User's choice:** B) Use IndicatorFilter
**Notes:** Elegant reuse of Phase 12 logic. No new degradation detection code needed.

---

## Backtest Script Output

| Option | Description | Selected |
|--------|-------------|----------|
| A) Signal log only | Detailed CSV per day: date, proposed, verdict, final. No summary. | |
| B) Summary only | Console performance metrics. No per-day detail. | |
| C) Both | CSV signal log + console summary. Log feeds Phase 14 diagnosis. | ✓ |

**User's choice:** C) Both
**Notes:** Phase 14 success criteria #3 requires "proposed X, filter said Y, final Z" log.

---

## Claude's Discretion

- Proposal representation format (string vs enum)
- old_state extraction method
- Console summary metrics selection
- Signal log CSV location
- Verdict columns in results DataFrame

## Deferred Ideas

- Contextual transitions — Phase 15
- Leading stocks confirmation — no data available
- Banding/volatility-aware filter — Phase 15
