# Phase 18: Short P&L & Comparative Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 18-short-p-l-comparative-validation
**Areas discussed:** Short P&L in equity curve, Comparison report format, Rule docs update scope, VN30 short parameters

---

## Short P&L in equity curve

| Option | Description | Selected |
|--------|-------------|----------|
| Inverse return khi SELL | prev_state=SELL: equity = equity * (close_prev/close). Single blended curve. | ✓ |
| Tach rieng long + short equity | 2 equity curves rieng (long-only, short-only), roi ket hop. | |
| Chi dung trade-level P&L | Khong sua equity curve, bao cao short trades rieng trong summary. | |

**User's choice:** Inverse return khi SELL (Recommended)
**Notes:** None

---

## Comparison report format

| Option | Description | Selected |
|--------|-------------|----------|
| Script + chart | Script Python xuat bang metrics + chart matplotlib. Tuong tu Phase 5. | ✓ |
| Jupyter notebook | Notebook tuong tac de kham pha ket qua. | |
| Ca hai | Script + notebook. | |

**User's choice:** Script + chart (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Chung 1 script | 1 script chay cho ca NASDAQ va VN30 (truyen tham so market). | ✓ |
| 2 script rieng | Script rieng cho NASDAQ va VN30. | |
| 1 script, 1 chart gop | Chart 2x2 tren cung 1 figure. | |

**User's choice:** Chung 1 script (Recommended)
**Notes:** None

---

## Rule docs update scope

| Option | Description | Selected |
|--------|-------------|----------|
| Them section short + stop loss | Them section moi vao ca 2 file rule docs. Giu cau truc hien tai. | ✓ |
| Viet lai toan bo | Cap nhat toan bo 2 file. | |
| Chi cap nhat hybrid | Chi sua rules_mdm_hybrid.md. | |

**User's choice:** Them section short + stop loss (Recommended)
**Notes:** None

---

## VN30 short parameters

| Option | Description | Selected |
|--------|-------------|----------|
| Cung logic, cung tham so | NASDAQ va VN30 dung chung logic short. Khac biet chi o config san co. | ✓ |
| VN30 can dieu chinh | VN30 co gioi han gia 7%, T+2.5 — co the can stop loss rong hon. | |
| Bo qua VN30 short | Chi chay comparison tren NASDAQ. | |

**User's choice:** Cung logic, cung tham so (Recommended)
**Notes:** None

---

## Claude's Discretion

- Long-only backtest mode implementation approach
- Chart styling, colors, layout
- Rule doc section structure and formatting
- Per-trade short P&L breakdown inclusion
- Script file naming and location

## Deferred Ideas

- Separate short-only equity curve — future enhancement
- Inverse ETF decay modeling — future
- Interactive notebook — add later if needed
- Anti-whipsaw / cooldown logic — FUT-03
