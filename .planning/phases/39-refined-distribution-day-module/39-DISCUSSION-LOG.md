# Phase 39: Refined Distribution Day Module - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 39-refined-distribution-day-module
**Areas discussed:** Stalling DD (Type 2) fate, Volume comparison semantics, Parameter defaults, DD count interaction

---

## Stalling DD (Type 2) fate

| Option | Description | Selected |
|--------|-------------|----------|
| Giữ Type 2 song song | Giữ nguyên Type 2 stalling bên cạnh dual-threshold mới. Khi refined_dd_enabled=True, cả 3 nguồn DD đều count. An toàn nhất. | ✓ |
| Loại Type 2 khi enabled | Khi refined_dd_enabled=True, chỉ dùng dual-threshold rule mới, tắt Type 2. Giảm noise nhưng có thể miss stalling days. | |
| Tách Type 2 ra flag riêng | Thêm stalling_dd_enabled flag riêng để Phase 40 sweep có thể bật/tắt độc lập. Linh hoạt hơn nhưng thêm complexity. | |

**User's choice:** Giữ Type 2 song song (Recommended)
**Notes:** None

---

## Volume comparison semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Precompute columns | Thêm Indicators.add_volume_ma_column() và add_volume_percentile_column(). Ghi vol_ma20 và vol_percentile_rank vào DataFrame trước loop. | ✓ |
| Compute inline trong DD checker | Truyền raw volume series vào DistributionDayCounter, tính MA20 và percentile rank tại chỗ. | |
| Override volume_up | Thay đổi nghĩa volume_up tuỳ theo refined_dd_enabled. Nguy hiểm vì volume_up còn dùng ở FTD, stop-loss. | |

**User's choice:** Precompute columns (Recommended)
**Notes:** None

---

## Parameter defaults trước sweep

| Option | Description | Selected |
|--------|-------------|----------|
| Giữa sweep range | large_drop=-0.7%, small_drop=-0.4%, small_vol_percentile=5%, small_vol_lookback=50, large_vol_rule='vol_ma20'. Trung vị sweep range. | ✓ |
| Conservative (gần v6.0) | large_drop=-0.2%, small_drop=-0.1%, percentile=10%. Gần giống behavior cũ. | |
| Aggressive | large_drop=-1.0%, small_drop=-0.5%, percentile=3%. Giảm DD count mạnh nhất. | |

**User's choice:** Giữa sweep range (Recommended)
**Notes:** None

---

## DD count interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Giữ nguyên counting | Chỉ thay đổi WHAT counts as DD, không thay HOW. 20-day window, 5DD threshold, DD5 high giữ nguyên. | ✓ |
| Thêm dd_threshold param | Thêm dd_count_threshold (mặc định 5) vào config để Phase 40 sweep có thể tune. Linh hoạt hơn nhưng thêm scope. | |

**User's choice:** Giữ nguyên counting (Recommended)
**Notes:** None

---

## Claude's Discretion

- Method signatures cho volume indicator columns
- Tổ chức logic trong DistributionDayCounter
- Test file naming và fixture format
- Action string annotation khi refined DD fire

## Deferred Ideas

- DD count threshold tuning (dd_count_threshold param) — deferred to future phase
- Type 2 stalling threshold parameterization — deferred
- Dashboard export — Phase 42
