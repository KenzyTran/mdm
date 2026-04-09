# Phase 32: VN100 Backtest + In-Sample Sweep - Discussion Log

> **Audit trail only.** Do not use as input to planning/research/execution.

**Date:** 2026-04-09
**Phase:** 32-vn100-backtest-in-sample-sweep
**Mode:** discuss (interactive, simplified)

## Gray Areas Presented

1. Sweep runtime strategy
2. Entry option sweep semantics (A, C hay thêm union)
3. Sharpe rf assumption
4. Locked-params handoff format
5. Single-run vs sweep script layout
6. Sanity gate SC5 (hard-fail vs soft-flag)
7. **Universe mode (current-VN100 vs liquidity-reconstructed)**
8. MDM gate + costs khoá hay sweep
9. Output location

## User Decisions

- **#7 (Universe mode):** User chọn **Cách 1 = current-VN100** cho đơn giản, dù biết survivorship bias. Đây là decision duy nhất user chủ động chốt.
- **Các mục khác:** User uỷ quyền Claude quyết theo default best practice ("BẠN NÓI GÌ TÔI KHÔNG HIỂU GÌ CẢ" → Claude đơn giản hoá, chỉ hỏi 1 câu quan trọng nhất).

## Claude's Default Choices (applied)

| # | Area | Choice | Rationale |
|---|------|--------|-----------|
| 1 | Runtime | Partial precompute + multiprocessing | Sweep 1,536 configs là nặng, precompute universe + EPS + MDM gate tiết kiệm lớn |
| 2 | Entry sweep | Đúng roadmap {A, C}, không thêm union | Bám spec, tránh scope creep |
| 3 | Sharpe rf | rf = 3% (VN 10Y govt) | Nhất quán với Phase 34 BT-05 |
| 4 | Locked params | JSON tại `docs/audits/phase32/locked_params_top3.json` | Phase 33 dễ load bằng code |
| 5 | Scripts | 2 script riêng: `backtest_vn100.py` + `sweep_vn100.py` | Mirror pattern `sweep_vn30_params.py`, debug dễ hơn |
| 6 | Sanity SC5 | Soft-flag + warning nếu top-3 bị flag | Không abort toàn sweep vì 1 outlier |
| 8 | MDM + costs | Khoá theo Phase 31 D-07 / D-22 | Không ngoài grid roadmap |
| 9 | Output | `docs/audits/phase32/` + `phase32-backtest-sweep.md` | Convention Phase 28/29/30/31 |

## Language Note

User yêu cầu communication bằng Vietnamese. Claude response bằng tiếng Việt từ turn 2 trở đi (memory: `user_language.md`).

## Deferred / Not Discussed

- Liquidity-reconstructed universe rerun (nếu Phase 33 sensitivity cho thấy bias nghiêm trọng)
- `entry_mode=union` post-hoc thử nghiệm
