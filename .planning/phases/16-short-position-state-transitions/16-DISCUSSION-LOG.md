# Phase 16: Short Position & State Transitions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 16-Short Position & State Transitions
**Areas discussed:** Data model short, Điều kiện cover short, SELL→CASH→BUY, VN30 vs NASDAQ

---

## Data model short

### Short position data model

| Option | Description | Selected |
|--------|-------------|----------|
| Mở rộng V2Position | Thêm short_entry_price, short_entry_date vào V2Position hiện tại. Dùng chung dataclass. | ✓ |
| Dataclass riêng ShortPosition | Tạo ShortPosition riêng biệt. Rõ ràng hơn nhưng phức tạp hơn. | |
| Claude quyết định | Claude chọn cách tốt nhất. | |

**User's choice:** Mở rộng V2Position
**Notes:** Đơn giản, ít thay đổi, field không áp dụng thì = 0/None.

### Entry price khi SELL

| Option | Description | Selected |
|--------|-------------|----------|
| Ghi entry price | enter_sell() nhận thêm price param, lưu vào short_entry_price | ✓ |
| Chưa cần giá | Phase 16 chỉ cần state transition đúng, Phase 17/18 thêm sau | |

**User's choice:** Ghi entry price
**Notes:** Cần cho P&L tracking và short stop loss ở phase sau.

### Short P&L khi cover

| Option | Description | Selected |
|--------|-------------|----------|
| Tính P&L luôn | Cover short = đóng vị thế, tính gain/loss ngay | ✓ |
| Để P&L cho Phase 18 | Phase 16 chỉ ghi nhận cover event | |

**User's choice:** Tính P&L luôn
**Notes:** Đầy đủ cho Phase 16, Phase 18 chỉ cần report.

---

## Điều kiện cover short

### Indicator filter cover short

| Option | Description | Selected |
|--------|-------------|----------|
| Có, filter cover | OVERRIDE khi đang SELL cover short về CASH. Nhất quán Phase 13. | ✓ |
| Không, chỉ FTD+MA50 | Chỉ 2 điều kiện cứng. | |
| Claude quyết định | Dựa trên logic hiện tại. | |

**User's choice:** Có, filter cover
**Notes:** Nhất quán với Phase 13 D-04/D-07 — OVERRIDE = force Cash áp dụng symmetric.

### MA50 breakout cover short

| Option | Description | Selected |
|--------|-------------|----------|
| Close > MA50 | Đơn giản, đối xứng với CASH→SELL | ✓ |
| Close > MA50 liên tục 2 ngày | Chặt chẽ hơn, tránh whipsaw | |
| Claude quyết định | Dựa trên pattern hiện tại. | |

**User's choice:** Close > MA50
**Notes:** Đơn giản, đối xứng.

---

## SELL→CASH→BUY enforcement

### Cách enforce

| Option | Description | Selected |
|--------|-------------|----------|
| 2 bước trong 1 ngày | CASH là transient state | |
| CASH ít nhất 1 ngày | CASH là real state, tồn tại ít nhất 1 ngày | |
| Claude quyết định | Dựa trên cách MDM hoạt động | ✓ |

**User's choice:** Claude quyết định
**Notes:** Claude sẽ chọn dựa trên Dr. K's signal history và MDM logic.

### Nơi enforce

| Option | Description | Selected |
|--------|-------------|----------|
| Position manager | enter_buy() tự kiểm tra | |
| Engine level | Engine kiểm tra trước khi gọi enter_buy() | |
| Cả hai | Defense in depth | ✓ |

**User's choice:** Cả hai
**Notes:** Engine xử lý logic, position manager có guard để bắt bug.

---

## VN30 vs NASDAQ

### Code path

| Option | Description | Selected |
|--------|-------------|----------|
| Logic giống nhau | Chung code path, chỉ khác khái niệm | |
| Config flag | short_mode flag cho phép mở rộng sau | ✓ |
| Ghi chú docs | Chỉ ghi chú trong docs | |

**User's choice:** Config flag
**Notes:** short_mode='direct'/'inverse_etf'. Hiện tại logic giống nhau, flag để mở rộng tương lai.

---

## Claude's Discretion

- SELL→CASH→BUY timing (transient vs persistent CASH)
- Tên method mới cho cover short
- Trade record format cho short trades
- Thứ tự ưu tiên giữa các cover triggers
- Cách integrate với two-phase commit

## Deferred Ideas

- Short stop loss (1% trên DD5 high) — Phase 17
- Inverse ETF decay modeling — future
- Short P&L reporting — Phase 18
- Anti-whipsaw cho short transitions — FUT-03
