# Phase 11: Foundation & Two-Phase Commit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 11-foundation-two-phase-commit
**Areas discussed:** Kiến trúc package, Cơ chế two-phase commit, Thiết kế HybridConfig, Chiến lược regression test

---

## Kiến trúc package

| Option | Description | Selected |
|--------|-------------|----------|
| Fork toàn bộ v2 | Copy strategies/mdm_v2/ → strategies/mdm_hybrid/, sửa trực tiếp. Không phụ thuộc ngược vào v2. | ✓ |
| Compose/delegate tới v2 | strategies/mdm_hybrid/ chỉ chứa hybrid logic, import v2 modules trực tiếp. | |
| Thin wrapper + shared core | Tách shared modules ra core/ hoặc shared/, cả v2 và hybrid import từ đó. | |

**User's choice:** Fork toàn bộ v2 (Recommended)
**Notes:** Consistent with Phase 4 pattern (classic → v2 fork)

| Option | Description | Selected |
|--------|-------------|----------|
| hybrid_engine.py | Ngắn gọn, class HybridEngine | |
| mdm_hybrid_engine.py | Theo pattern v2 (mdm_v2_engine.py) | ✓ |

**User's choice:** mdm_hybrid_engine.py
**Notes:** Follows existing naming convention

---

## Cơ chế two-phase commit

| Option | Description | Selected |
|--------|-------------|----------|
| Snapshot/restore | Deepcopy state trước khi chạy, restore nếu veto | ✓ |
| Propose/commit tách biệt | Sửa mỗi component thêm propose()/commit() methods | |
| Immutable state + new state | Functional style, tạo state mới mỗi ngày | |

**User's choice:** Snapshot/restore (Recommended)
**Notes:** Đơn giản nhất, không cần sửa v2 modules

**Components protected by 2PC:**
- ✓ DD counter reset
- ✓ Position manager
- ✓ Rally tracker
- ✓ FTD detector

| Option | Description | Selected |
|--------|-------------|----------|
| Deepcopy objects | copy.deepcopy() tất cả 4 components | ✓ |
| save_state()/restore_state() methods | Thêm method vào mỗi component | |

**User's choice:** Deepcopy objects (Recommended)
**Notes:** Không cần sửa v2 modules

---

## Thiết kế HybridConfig

| Option | Description | Selected |
|--------|-------------|----------|
| Compose | HybridConfig chứa v2_config: MDMV2Config + filter flags | ✓ |
| Kế thừa (inherit) | class HybridConfig(MDMV2Config) | |
| Flatten | Copy tất cả v2 fields + thêm fields mới | |

**User's choice:** Compose (Recommended)
**Notes:** Clear separation between v2 params and hybrid flags

| Option | Description | Selected |
|--------|-------------|----------|
| Default True | two_phase_enabled luôn bật | ✓ |
| Default False | Chỉ bật khi có filter | |

**User's choice:** Default True (Recommended)

---

## Chiến lược regression test

| Option | Description | Selected |
|--------|-------------|----------|
| So sánh signal sequence | Chạy v2 và hybrid trên cùng data, bit-for-bit match | ✓ |
| Unit test scenarios | Test cases với data giả lập cho từng kịch bản | |
| Cả hai | Integration + unit tests | |

**User's choice:** So sánh signal sequence (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| NASDAQ full (1974-2026) | Toàn bộ NASDAQ data | ✓ |
| NASDAQ 2019-2026 | Chỉ post-change period | |
| Subset 1000 ngày | 1000 ngày gần nhất | |

**User's choice:** NASDAQ full (1974-2026) (Recommended)

---

## Claude's Discretion

- Snapshot helper function location
- Exact deepcopy implementation
- Which v2 modules need modification
- Test organization and fixtures
- Proposal object structure for Phase 12

## Deferred Ideas

None — discussion stayed within phase scope
