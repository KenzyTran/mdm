# Phase 30: Stock-Level Entry Confirmation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in `30-CONTEXT.md` — this log preserves the back-and-forth.

**Date:** 2026-04-09
**Phase:** 30-stock-level-entry-confirmation
**Mode:** discuss
**Language:** Vietnamese (user preference)

## Areas Identified as Gray

Phase 30 success criteria already lock the Option A / Option C formulas, the 20-day window, and the ATO fill model. The remaining gray areas are:

1. A/B universe scope — raw VN100 vs CANSLIM-qualified subset
2. 20-day window reset semantics when a new MDM BUY fires mid-window
3. Same-window duplicate handling when both detectors fire on the same ticker
4. Package layout for the new entry detectors

## Questions → Answers

### Q1: A/B universe
**User:** Cả hai, báo cáo song song.
→ Decision: produce A/B report twice (raw VN100 + CANSLIM-qualified), side-by-side. (D-16)

### Q2: Window reset semantics
**User:** Reset mỗi lần CASH/SELL→BUY (recommended).
→ Decision: window resets to 20 days on every CASH/SELL→BUY transition; no extension if BUY is continuous. (D-07, D-08)

### Q3: Duplicate fires
**User:** Ghi riêng từng detector (recommended).
→ Decision: Option A and Option C are independent streams; one ticker can contribute a fill to each stream per window. Within a single stream, first-fire-wins per window. (D-14, D-15)

### Q4: Package location
**User:** Package mới strategies/entry/ (recommended).
→ Decision: new `strategies/entry/` package parallel to `strategies/canslim/`. (D-01)

## Notes

- User corrected language mid-discussion (English → Vietnamese). Re-asked the four questions in Vietnamese; answers received on second pass.
- No scope creep attempted — user stayed within Phase 30 boundary.
- No canonical specs were referenced mid-discussion beyond what's already in ROADMAP / REQUIREMENTS / Phase 29 context.
