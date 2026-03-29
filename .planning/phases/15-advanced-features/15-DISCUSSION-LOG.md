# Phase 15: Advanced Features - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 15-advanced-features
**Areas discussed:** Contextual transition logic, Heikin Ashi filter integration, Confidence score design, Dashboard scope & format

---

## Contextual Transition Logic (ADV-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Duration + sequence | Track both days-in-state AND prior state sequence | |
| Duration only | Only track how long in current state | |
| Sequence only | Only track prior state path | |

**User's choice:** "quyết định hết giúp tôi" (Claude decides all)
**Notes:** All contextual transition decisions delegated to Claude's discretion.

### Code Location

| Option | Description | Selected |
|--------|-------------|----------|
| Inside IndicatorFilter.evaluate() | Add state_history param, keeps decision logic in one place | |
| In HybridEngine before filter call | Engine checks context first, filter stays stateless | |
| Separate ContextualFilter class | New class wrapping IndicatorFilter | |

**User's choice:** "quyết định hết giúp tôi" (Claude decides all)

---

## Heikin Ashi Filter Integration (ADV-02)

| Option | Description | Selected |
|--------|-------------|----------|
| 7th condition in IndicatorFilter | Add alongside existing 6, toggleable via FilterConfig | ✓ |
| Separate pre-filter layer | Evaluated before IndicatorFilter | |
| You decide | Claude picks | |

**User's choice:** 7th condition in IndicatorFilter (Recommended)
**Notes:** Consistent with existing majority-vote architecture.

---

## Confidence Score Design (ADV-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Simple ratio | agree_count / total_active_conditions, range 0.0-1.0 | ✓ |
| Weighted by importance | Conditions weighted by predictive power | |
| Tiered categories | High/Medium/Low categories | |
| You decide | Claude picks | |

**User's choice:** Simple ratio (Recommended)
**Notes:** Already computed inside IndicatorFilter.evaluate().

---

## Dashboard Scope & Format (ADV-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Static matplotlib script | analysis/ script generating PNG + console report | |
| Interactive Jupyter notebook | Notebook with widgets | |
| Both | Script + notebook | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Claude's Discretion

- Contextual transition logic: approach (duration+sequence vs other), code location, specific rules
- Dashboard format: static/interactive/both
- Dashboard metrics selection

## Deferred Ideas

- Parameter tuning — separate optimization phase
- Anti-whipsaw / cooldown logic — FUT-03
- VN30 adaptation — EXT-04
