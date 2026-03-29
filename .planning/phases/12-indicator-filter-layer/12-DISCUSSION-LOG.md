# Phase 12: Indicator Filter Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 12-indicator-filter-layer
**Areas discussed:** Filter condition rules, Verdict logic, TradingView parity, Filter config design

---

## Filter Condition Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Rules từ Phase 9 | Dùng trực tiếp kết quả decision tree — close_above_ema55 (importance 0.687 post-2019), macd_histogram_positive, ema9_above_ema21. Đã được validate trên 962 signals. | ✓ |
| Hardcode từ domain knowledge | Tự định nghĩa rules từ indicator setup đã biết của Dr. K. Đơn giản hơn nhưng chưa validate bằng data. | |
| Kết hợp cả hai | Phase 9 rules làm chính, thêm domain rules ở chỗ discovery chưa cover. | |

**User's choice:** Rules từ Phase 9 (Recommended)

### Số lượng conditions

| Option | Description | Selected |
|--------|-------------|----------|
| 3 conditions chính | close_above_ema55, macd_histogram_positive, ema9_above_ema21. STATE.md cảnh báo max 2-3 rules. | |
| 5-6 conditions đầy đủ | Thêm close_above_ma200, close_above_ema9, macd_above_signal. Cover nhiều hơn nhưng tăng risk overfit. | ✓ |
| Tất cả 8 boolean features | Implement toàn bộ 8 features từ feature_snapshot.py. Phase 13 sẽ chọn dùng features nào. | |

**User's choice:** 5-6 conditions đầy đủ

### Active conditions mặc định

| Option | Description | Selected |
|--------|-------------|----------|
| 2-3 active mặc định | Implement 5-6 methods nhưng default chỉ bật 3 conditions quan trọng nhất. Còn lại tắt mặc định. | ✓ |
| Tất cả đều active | Bật hết 5-6 conditions. Phase 13/14 sẽ tune lại. | |
| Không cần toggle | Hardcode luôn 5-6 conditions. | |

**User's choice:** Đúng, 2-3 active mặc định (Recommended)

---

## Verdict Logic

| Option | Description | Selected |
|--------|-------------|----------|
| Majority voting | Đếm số conditions đồng ý: >=2/3 active conditions đồng thuận = CONFIRM, <2/3 = VETO. Đơn giản, dễ debug. | ✓ |
| All-must-agree | Tất cả active conditions phải đồng thuận để CONFIRM. Strict hơn, sẽ VETO nhiều hơn. | |
| Weighted by importance | Dùng feature importance từ Phase 9 làm trọng số. Phức tạp hơn nhưng chính xác hơn. | |

**User's choice:** Majority voting (Recommended)

### Per-type verdict

| Option | Description | Selected |
|--------|-------------|----------|
| Khác nhau per proposal type | Buy proposals check bullish conditions, Sell proposals check bearish conditions. Phù hợp Phase 9 findings. | ✓ |
| Giống nhau | Cùng một bộ conditions cho mọi proposal. Đơn giản hơn. | |

**User's choice:** Khác nhau (Recommended)

### OVERRIDE timing

| Option | Description | Selected |
|--------|-------------|----------|
| Chưa implement ở Phase 12 | Chỉ CONFIRM/VETO. OVERRIDE để lại Phase 13. | |
| Implement luôn | Thêm OVERRIDE logic trong Phase 12 khi indicators strongly contradict state machine. | ✓ |

**User's choice:** Implement luôn

---

## TradingView Parity

| Option | Description | Selected |
|--------|-------------|----------|
| 5 dates cố định + tolerance | 5 ngày với unit test hard-coded expected values. | |
| 10+ dates với CSV reference | Tải EMA/MACD data từ TradingView, lưu CSV làm reference. Test đọc CSV và so sánh. | ✓ |
| Manual verification only | Ghi kết quả trong docs, không automated test. | |

**User's choice:** 10+ dates với CSV reference

### Tolerance threshold

| Option | Description | Selected |
|--------|-------------|----------|
| ±0.01% EMA, ±0.1% MACD | EMA/MA cần chính xác cao. MACD cho phép tolerance lớn hơn. | ✓ |
| Strict: ±0.001% | Gần như bit-exact. Có thể fail do floating point. | |
| Loose: ±1% | Chấp nhận sai số lớn hơn. | |

**User's choice:** ±0.01% EMA, ±0.1% MACD (Recommended)

---

## Filter Config Design

| Option | Description | Selected |
|--------|-------------|----------|
| Dataclass với bool toggles | FilterConfig dataclass với 5-6 boolean fields + majority_threshold. HybridConfig chứa FilterConfig. | ✓ |
| Dict-based config | Linh hoạt hơn nhưng mất type safety. | |
| Enum-based rule set | FilterRuleSet.POST_2019, .FULL, .CUSTOM presets. | |

**User's choice:** Dataclass với bool toggles (Recommended)

### IndicatorFilter location

| Option | Description | Selected |
|--------|-------------|----------|
| strategies/mdm_hybrid/indicator_filter.py | Trong hybrid package, cạnh engine. Component của hybrid, không dùng chung. | ✓ |
| core/indicator_filter.py | Trong core/ cạnh indicators.py. Có thể reuse cho VN30 nhưng tạo coupling. | |

**User's choice:** strategies/mdm_hybrid/indicator_filter.py (Recommended)

---

## Claude's Discretion

- Exact method signatures and parameter naming
- How to pass indicator data (DataFrame row vs individual values)
- Internal helper structure for bullish vs bearish evaluation
- Test file organization and pytest fixtures
- CSV reference file format and date selection
- majority_threshold representation (fraction vs count)

## Deferred Ideas

None — discussion stayed within phase scope
