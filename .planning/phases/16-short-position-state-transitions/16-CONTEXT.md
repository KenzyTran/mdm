# Phase 16: Short Position & State Transitions - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

SELL signal opens a real short position (entry price recorded), short cover mechanics (FTD, MA50 breakout, indicator filter), and enforced SELL→CASH→BUY transition sequence. This phase does NOT implement short stop loss (Phase 17) or short P&L reporting/comparison (Phase 18).

</domain>

<decisions>
## Implementation Decisions

### Short position data model
- **D-01:** Mở rộng V2Position hiện tại — thêm `short_entry_price: float = 0.0` và `short_entry_date: Optional[pd.Timestamp] = None`. Dùng chung dataclass, field nào không áp dụng thì = 0/None.
- **D-02:** `enter_sell()` nhận thêm `price` param, lưu vào `short_entry_price` và `short_entry_date`. Entry price = giá close ngày SELL signal.
- **D-03:** Khi cover short, tính P&L ngay: `(short_entry_price - cover_price) / short_entry_price`. Gain khi market giảm, loss khi market tăng.

### Short cover triggers
- **D-04:** Cover short khi FTD detected → chuyển về CASH (ghi nhận short P&L).
- **D-05:** Cover short khi close > MA50 (MA50 breakout) → chuyển về CASH. Đối xứng với CASH→SELL (close < MA50).
- **D-06:** Indicator filter OVERRIDE/VETO khi đang SELL cũng cover short về CASH. Nhất quán với Phase 13 D-04/D-07 (OVERRIDE = force Cash, áp dụng symmetric BUY→CASH và SELL→CASH).

### SELL→CASH→BUY transition enforcement
- **D-07:** Defense in depth — enforce ở cả engine level VÀ position manager level.
- **D-08:** Position manager: `enter_buy()` có guard — nếu đang SELL thì raise error (bắt bug, không tự động cover).
- **D-09:** Engine: trước khi gọi `enter_buy()`, kiểm tra nếu đang SELL → cover short trước rồi mới BUY.

### Claude's Discretion
- SELL→CASH→BUY timing: Claude quyết định liệu CASH là transient (2 bước trong 1 ngày: cover + buy) hay persistent (CASH ít nhất 1 ngày). Dựa trên cách MDM hoạt động và Dr. K's signal history.
- Tên method mới cho cover short (e.g., `cover_short()` vs `exit_short_to_cash()`)
- Trade record format cho short trades (type field values)
- Thứ tự ưu tiên giữa các cover triggers (FTD vs MA50 vs filter)
- Cách integrate với two-phase commit snapshot/restore pattern

### VN30 vs NASDAQ short mode
- **D-10:** Thêm config flag `short_mode: str = 'direct'` trong config. Giá trị: `'direct'` (VN30 short trực tiếp) hoặc `'inverse_etf'` (NASDAQ inverse ETF concept). Hiện tại cả hai dùng chung logic, flag để mở rộng sau nếu cần logic riêng (VD: inverse ETF decay).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Hybrid engine (modification targets)
- `strategies/mdm_hybrid/position_manager.py` — V2PositionManager with 3-state machine, V2Position dataclass, enter_sell() at line 119, SELL state handling at line 232
- `strategies/mdm_hybrid/mdm_hybrid_engine.py` — HybridEngine with Propose-Filter-Decide pipeline, two-phase commit snapshot/restore
- `strategies/mdm_hybrid/config.py` — HybridConfig with MDMV2Config composition, filter_enabled, filter_config
- `strategies/mdm_hybrid/indicator_filter.py` — IndicatorFilter.evaluate() returning Verdict (CONFIRM/VETO/OVERRIDE)
- `strategies/mdm_hybrid/performance.py` — Performance analyzer treating SELL as 0% invested (needs update for short P&L)
- `strategies/mdm_hybrid/stop_loss.py` — StopLossChecker (no short stop loss yet — Phase 17)

### Prior phase context
- `.planning/phases/11-foundation-two-phase-commit/11-CONTEXT.md` — D-03 (snapshot/restore pattern), D-06 (config composition)
- `.planning/phases/13-hybrid-engine-integration/13-CONTEXT.md` — D-04 (OVERRIDE=Cash), D-06/D-07 (cash insertion symmetric)
- `.planning/phases/15-advanced-features/15-CONTEXT.md` — D-01/D-02 (HA filter), confidence scoring

### Requirements
- `.planning/REQUIREMENTS.md` — SHORT-01 (short entry), SHORT-04 (short cover), TRANS-01 (SELL→CASH→BUY)

### Data
- `data/signals/nasdaq_signals_full.csv` — 962-signal ground truth for validation
- NASDAQ OHLCV data via DataLoader

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `V2Position` dataclass — extend with short fields (D-01)
- `V2PositionManager.enter_sell()` — modify to accept price param (D-02)
- `V2PositionManager.exit_to_cash()` — pattern reference for short cover P&L calculation
- `V2PositionManager.degrade_to_cash()` — already handles SELL→CASH for indicator override
- `HybridEngine._snapshot_components()` / `_restore_components()` — two-phase commit already working
- `IndicatorFilter.evaluate()` — already returns OVERRIDE for SELL state (symmetric cash insertion from Phase 13)

### Established Patterns
- DataFrame-centric: engine.run(df) returns DataFrame with signal columns
- Two-phase commit: snapshot before daily processing, decide after
- State machine: V2MarketState enum with BUY/CASH/SELL
- Trade recording: append dict to self.trades list with type, date, price, pnl fields
- Config composition: HybridConfig contains v2_config + hybrid-specific flags

### Integration Points
- `position_manager.py` line 232-236: SELL→BUY direct transition — needs SELL→CASH→BUY enforcement
- `position_manager.py` line 119-130: `enter_sell()` — needs price param and short_entry_price storage
- `mdm_hybrid_engine.py` line 318: proposal handling — needs short cover logic before BUY
- `performance.py` line 73: "0% on SELL" — Phase 18 will update for short returns
- Config: add `short_mode` flag

</code_context>

<specifics>
## Specific Ideas

- Dr. K's MDM: SELL signal = market bearish, model goes short. Cover khi có FTD (bullish confirmation) hoặc MA50 breakout.
- Phase 13 D-07: Cash insertion áp dụng symmetric — đã có pattern SELL→CASH qua indicator filter. Phase 16 mở rộng thêm short P&L khi cover.
- State blocker: "No SHORT or WAITING_SELL states (per D-03)" comment ở position_manager.py dòng 5 — cần update comment vì SELL giờ là real short position.

</specifics>

<deferred>
## Deferred Ideas

- Short stop loss (1% trên DD5 high) — Phase 17 (SHORT-03, RISK-03)
- Inverse ETF decay modeling cho NASDAQ — future enhancement nếu cần
- Short P&L reporting và comparison dashboard — Phase 18 (SHORT-02, TRANS-02)
- Anti-whipsaw / cooldown logic cho short transitions — FUT-03

</deferred>

---

*Phase: 16-short-position-state-transitions*
*Context gathered: 2026-03-30*
