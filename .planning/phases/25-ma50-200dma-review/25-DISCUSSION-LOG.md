# Phase 25: MA50/200dma Review - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 25-ma50-200dma-review
**Areas discussed:** MA50 breakout buy fate, 200dma scope, SELL replacement, Validation script structure

---

## MA50 Breakout Buy Fate

| Option | Description | Selected |
|--------|-------------|----------|
| Tắt luôn (disable all 3 MA50 uses) | V2 sạch không có MA50 — consistent với Dr. K "little value" | |
| Giữ nguyên MA50 breakout buy | Mỗi test độc lập, MA50 breakout là cơ chế riêng | |
| Test cả hai sub-variant | 4 scenarios: baseline / -SELL only / -BUY filter only / -All MA50 | ✓ |

**Follow-up:** Trong scenarios SELL only và BUY filter only — giữ MA50 breakout buy active hay tắt?

| Option | Description | Selected |
|--------|-------------|----------|
| Giữ MA50 breakout buy trong từng test riêng lẽ | SELL only: tắt ma50_sell, giữ MA50 buy. BUY filter only: tắt buy_filter, giữ MA50 buy | ✓ |
| Tất cả scenario đều tắt MA50 breakout buy | Đơn giản hơn | |

**User's choice:** Test 4 sub-variants, giữ MA50 breakout buy trong các test riêng lẽ (cô lập từng tác động).

---

## 200dma Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Chỉ note vắng mặt, không implement | Report MAREVIEW-03 ghi nhận không có 200dma, Dr. K "little value" → không cần add | |
| Add 200dma vào test như một replacement candidate | Thêm scenario 200dma thay MA50 | ✓ |

**Follow-up:** 200dma test như replacement cho cái gì?

| Option | Description | Selected |
|--------|-------------|----------|
| Thay MA50 breakout buy bằng 200dma crossover | Scenario 5: close > 200dma (lần đầu tiên) | |
| Thay MA50 SELL trigger bằng 200dma breakdown | Scenario 5: close < 200dma → SELL | |
| Cả hai (200dma cho buy và sell) | Một scenario thêm: 200dma trong cả buy signal và sell trigger | ✓ |

**Follow-up:** Tổng cộng 5 scenarios — đồng ý?

| Option | Description | Selected |
|--------|-------------|----------|
| Đồng ý — 5 scenarios | Baseline / -SELL only / -BUY filter only / -All MA50 / +200dma replacement | ✓ |
| Bỏ -BUY filter only riêng lẽ, giữ 4 scenario | Compact hơn | |

**User's choice:** 5 scenarios, 200dma thay cả buy signal lẫn SELL trigger.

---

## SELL Replacement When MA50 Removed

| Option | Description | Selected |
|--------|-------------|----------|
| Test nguyên trạng cash_deterioration | Không thêm trigger mới. Đo impact của việc bỏ MA50 SELL với cấu hình hiện tại | ✓ |
| Phân tích và tự đề xuất replacement trong MAREVIEW-03 | A/B chỉ test bỏ MA50, nhưng nếu kết quả xấu thì gợi ý replacement | |

**User's choice:** Test nguyên trạng cash_deterioration — không thêm trigger mới trong Phase 25.

---

## Validation Script Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Một script validate_ma50_review.py | Follow Phase 24 pattern, 5 scenarios + MAREVIEW-03 kết luận cuối | ✓ |
| Tách riêng theo MAREVIEW requirement | Separate scripts per requirement | |

**User's choice:** Single script `analysis/validate_ma50_review.py`.

---

## Claude's Discretion

- sma200 indicator implementation details
- Config parameter naming for 200dma flags
- Handling early bars where 200dma is NaN
- Validation script output format
- Whether to log scenario decisions as DataFrame columns

## Deferred Ideas

- ATR-based replacement SELL trigger — if MA50 removal + 200dma both underperform
- Optimizing cash_deterioration_days threshold post-MA50 removal
