# Phase 38: ATR Buffer Zone Module - Discussion Log

> **Audit trail only.** Không dùng làm input cho planning/research/execution agents.
> Decisions đã được capture vào CONTEXT.md — log này chỉ lưu quá trình thảo luận.

**Date:** 2026-04-15
**Phase:** 38-atr-buffer-zone-module
**Mode:** discuss (interactive, Vietnamese)

## Gray Areas Identified

Sau khi quét codebase (strategies/mdm_hybrid/ + config + indicators + position_manager) và đọc ROADMAP/REQUIREMENTS, 6 gray area được xác định:

1. ATR period — coupling với stop-loss hay tách riêng
2. Ngữ nghĩa m-day consecutive (backward-looking vs streak)
3. Giá trị mặc định (k, N, m) ship trong Phase 38
4. Cách lưu baseline regression v6.0 (parquet fixture vs live compare)
5. Vị trí tính `violation_threshold` (indicator pipeline vs lazy tick)
6. Đối xứng ở short cover (SELL→CASH)

User chọn bàn **cả 6** vùng.

## Decisions Made

| # | Câu hỏi | Quyết định | Lý do user chọn |
|---|---------|------------|-----------------|
| 1 | ATR period coupling | Thêm `atr_buffer_period` riêng (recommended) | Tune độc lập với stop-loss, bảo vệ ATR-04 |
| 2 | m-day semantics | Backward-looking, fire cùng ngày (recommended) | Thuận luồng state machine hiện tại, m=1 tương đương v6.0 |
| 3 | Default (k, N, m) | k=0.5, N=14, m=2 (recommended) | Giữa khoảng sweep Phase 40, testable ngay |
| 4 | Regression baseline | Parquet 1 lần + commit (recommended) | CI nhanh, reproducible |
| 5 | violation_threshold placement | Indicator pipeline, cache column (recommended) | Phù hợp ATR-01, dễ inspect/debug |
| 6 | Short-side symmetry | Bất đối xứng, chỉ SELL entry (recommended) | Giữ scope tối thiểu, dễ attribute whipsaw reduction |

User chọn tất cả phương án **Recommended** ở mọi câu hỏi.

## Scope Guardrails Applied

- Symmetric short cover buffer → **deferred** (scope mới, cần sweep riêng)
- Buffer cho BUY→CASH stop-loss exit (stop_loss.py:136) → **deferred** (không phải ATR-02 scope)
- Dashboard export `violation_threshold` → **deferred sang Phase 42**

## Notes

- Prior memory (v9.0 milestone) khớp hoàn toàn với hướng triển khai: ATR Buffer + Refined DD, mục tiêu CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%).
- Init tool báo `phase_found=false` do bug `extractCurrentMilestone()` cắt section khi gặp "v6.0" trong tên Phase 27 heading. Workaround: tạo phase dir thủ công. Nên note để fix tool sau.
