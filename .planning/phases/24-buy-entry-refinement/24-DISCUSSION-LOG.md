# Phase 24: Buy Entry Refinement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 24-buy-entry-refinement
**Areas discussed:** Gap-up scope, 6% threshold logic, Module architecture, Validation strategy

---

## Gap-up scope

### Signal scope

| Option | Description | Selected |
|--------|-------------|----------|
| Chi classic FTD | Consistent voi Phase 21 — MA50/52week la strong signals, khong can filter | ✓ |
| Tat ca buy signals | Ap dung cho ca FTD, MA50, 52week | |
| FTD + MA50 | Chi 52-week bypass, MA50 van bi filter | |

**User's choice:** Chi classic FTD
**Notes:** User confirmed consistent with Phase 21 pattern

### Gap definition

| Option | Description | Selected |
|--------|-------------|----------|
| Chi low < prev_close | Simple, dung theo Dr. K. De backtest | ✓ |
| Low < prev_close AND close < open | Them bearish candle condition | |
| Low < prev_close voi margin | 0.5% buffer de tranh noise | |

**User's choice:** Chi low < prev_close
**Notes:** None

---

## 6% threshold logic

### Decline calculation

| Option | Description | Selected |
|--------|-------------|----------|
| Dung existing drawdown_pct | Engine da tinh drawdown_pct, reuse luon | ✓ |
| Tinh tu rally_tracker.peak_high | Dung peak_high cua RallyAttemptTracker | |

**User's choice:** Dung existing drawdown_pct

### Correction requirement

| Option | Description | Selected |
|--------|-------------|----------|
| Van can correction | Chi relax FTD timing, van can correction phase | ✓ |
| Bo correction check khi < 6% | Bat ky ngay up voi volume la FTD | |

**User's choice:** Van can correction

### Threshold interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Ha correction_threshold xuong -6% | Rally tracking bat dau som hon | |
| Giu -10%, them 6% logic rieng | correction_threshold van -10%, them logic rieng cho 6% | ✓ |

**User's choice:** Giu -10%, them 6% logic rieng
**Notes:** User shared past experience: previously lowered to -6% and encountered excessive signal noise

### FTD min day implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Bypass rally_tracker khi -6% to -10% | Engine check drawdown rieng, cho phep FTD check truc tiep | ✓ |
| Them shallow mode vao rally_tracker | rally_tracker co 2 mode: shallow va deep | |

**User's choice:** Bypass rally_tracker khi -6% to -10%

### Config parameters

| Option | Description | Selected |
|--------|-------------|----------|
| Co, them ca 2 params | rally_threshold_enabled + rally_threshold_pct. Consistent voi pattern | ✓ |
| Chi enabled flag | Hardcode -6%, chi them enabled flag | |

**User's choice:** Co, them ca 2 params

---

## Module architecture

| Option | Description | Selected |
|--------|-------------|----------|
| 1 module moi: buy_entry.py | Gop ca gap_filter va rally_threshold vao 1 class | ✓ |
| 2 module rieng | gap_filter.py + rally_threshold.py | |
| Extend engine truc tiep | Them logic vao mdm_v2_engine.py | |

**User's choice:** 1 module moi: buy_entry.py

---

## Validation strategy

### Script structure

| Option | Description | Selected |
|--------|-------------|----------|
| 1 script chung | validate_buy_entry.py voi 3 scenarios | ✓ |
| 2 scripts rieng | Moi feature 1 script | |
| Extend validate_combined.py | Them vao script Phase 22 | |

**User's choice:** 1 script chung

### Success metrics

| Option | Description | Selected |
|--------|-------------|----------|
| 3+ instances + overall return | Verify instances va check khong giam total return | ✓ |
| Chi theo ROADMAP criteria | 3+ instances la du | |

**User's choice:** 3+ instances + overall return comparison

---

## Claude's Discretion

- BuyEntryFilter internal design
- Integration order in engine loop
- Validation script output format
- DataFrame column logging decisions
- Historical instance identification method

## Deferred Ideas

None
