# BỘ QUY TẮC MÔ HÌNH MDM HYBRID - TWO-PHASE COMMIT + INDICATOR FILTER

## I. TỔNG QUAN

MDM Hybrid là phiên bản nâng cao nhất, kết hợp:
1. **Máy trạng thái V2** (BUY/CASH/SELL) làm cơ sở
2. **Two-Phase Commit** (snapshot/restore) cho khả năng rollback quyết định
3. **Indicator Filter Layer** (bộ lọc chỉ báo kỹ thuật) để xác nhận hoặc phủ quyết tín hiệu
4. **Contextual Transitions** (chuyển trạng thái theo ngữ cảnh) để thích ứng với trạng thái thị trường

**Kiến trúc:** V2 state machine đề xuất tín hiệu -> Indicator Filter đánh giá -> Quyết định cuối cùng (giữ hoặc rollback).

---

## II. CƠ CHẾ TWO-PHASE COMMIT

### 1. Nguyên lý hoạt động:

Trước mỗi phiên giao dịch, engine thực hiện:

1. **Snapshot** (`_snapshot_components`): Sao lưu trạng thái của 4 component:
   - `dd_counter` (bộ đếm ngày phân phối)
   - `rally_tracker` (theo dõi rally attempt)
   - `ftd_detector` (phát hiện FTD)
   - `position_manager` (quản lý vị thế)

2. **Xử lý phiên:** Chạy tất cả logic V2 bình thường (rally tracking, FTD detection, DD counting, stop loss, position update).

3. **Đánh giá:** So sánh trạng thái trước và sau xử lý:
   - Nếu trạng thái thay đổi: tạo **đề xuất** (proposal) = trạng thái mới
   - Nếu trạng thái không đổi: đề xuất = trạng thái hiện tại

4. **Quyết định:** Indicator filter đánh giá đề xuất:
   - **CONFIRM**: Giữ các thay đổi (commit)
   - **VETO**: Hủy các thay đổi, khôi phục snapshot (rollback)
   - **OVERRIDE**: Ép chuyển về CASH bất kể đề xuất

### 2. Cấu hình:
* `two_phase_enabled` (mặc định: True) -- bật/tắt cơ chế snapshot/restore
* `filter_enabled` (mặc định: False) -- bật/tắt bộ lọc chỉ báo

Khi `filter_enabled=False`, two-phase commit vẫn chạy nhưng luôn CONFIRM (không có bộ lọc nào để phủ quyết).

---

## III. INDICATOR FILTER LAYER (BỘ LỌC CHỈ BÁO)

### 1. Nguyên tắc:
* Bộ lọc **KHÔNG tạo tín hiệu** -- chỉ đánh giá (CONFIRM/VETO/OVERRIDE) tín hiệu từ máy trạng thái V2.
* Sử dụng **majority-vote** (bỏ phiếu đa số) của các điều kiện kỹ thuật.
* **Stateless**: Mỗi lần đánh giá độc lập, không lưu trữ trạng thái.
* **NaN-safe**: Tất cả giá trị NaN được xử lý an toàn -- NaN -> False cho cả bullish và bearish.

### 2. 7 Điều kiện kỹ thuật:

| # | Điều kiện | Bullish | Bearish | Mặc định |
| :---: | :--- | :--- | :--- | :---: |
| 1 | **Close > EMA55** | $C > EMA55$ | $C < EMA55$ | BẬT |
| 2 | **MACD Histogram > 0** | $MACD\_hist > 0$ | $MACD\_hist < 0$ | BẬT |
| 3 | **EMA9 > EMA21** | $EMA9 > EMA21$ | $EMA9 < EMA21$ | BẬT |
| 4 | **Close > MA200** | $C > MA200$ | $C < MA200$ | TẮT |
| 5 | **Close > EMA9** | $C > EMA9$ | $C < EMA9$ | TẮT |
| 6 | **MACD > Signal** | $MACD > Signal$ | $MACD < Signal$ | TẮT |
| 7 | **HA Smoothed 55 Bullish** | $HA\_close > HA\_open$ | $HA\_close < HA\_open$ | TẮT |

**Lưu ý quan trọng:** Điều kiện bearish KHÔNG phải là phép phủ định đơn giản của bullish. Khi dữ liệu là NaN, cả bullish và bearish đều trả về False (theo quy tắc D-06).

### 3. Majority Vote (Bỏ phiếu đa số):

* **Điểm tin cậy (Confidence Score):** $confidence = \frac{so\_dieu\_kien\_dong\_y}{tong\_dieu\_kien\_bat}$
* **Ngưỡng đa số (Majority Threshold):** Mặc định $\frac{2}{3} \approx 0.667$ (2 trên 3 điều kiện phải đồng ý).

**Logic bỏ phiếu:**

| Tình huống | Kết quả |
| :--- | :--- |
| Không có điều kiện nào bật (hoặc tất cả NaN) | **CONFIRM** (không có ý kiến) |
| $confidence = 0.0$ và >= 3 điều kiện bật | **OVERRIDE** (tất cả phản đối) |
| $confidence \ge majority\_threshold$ | **CONFIRM** (đa số đồng ý) |
| $confidence < majority\_threshold$ | **VETO** (không đủ đồng ý) |

### 4. Cách áp dụng vote cho từng loại đề xuất:

* **Đề xuất BUY:** Kiểm tra các điều kiện **bullish** (close trên EMA, MACD dương, v.v.)
* **Đề xuất SELL hoặc CASH:** Kiểm tra các điều kiện **bearish** (close dưới EMA, MACD âm, v.v.)

---

## IV. LOGIC XỬ LÝ VERDICT (QUYẾT ĐỊNH)

### Trường hợp 1: Trạng thái THAY ĐỔI (đề xuất chuyển trạng thái)

| Verdict | Hành động |
| :--- | :--- |
| **CONFIRM** | Giữ nguyên các thay đổi từ V2 state machine (commit) |
| **VETO** | Khôi phục snapshot, hủy tất cả thay đổi (rollback). Trạng thái giữ nguyên như trước |
| **OVERRIDE** | Khôi phục snapshot rồi ép chuyển về CASH. Nếu trước đó là BUY: `exit_to_cash` (ghi nhận P&L). Nếu trước đó là SELL: `degrade_to_cash` (không P&L). Nếu đề xuất CASH: giữ nguyên (đã đúng hướng) |

### Trường hợp 2: Trạng thái KHÔNG ĐỔI (V2 không đề xuất thay đổi)

Bộ lọc vẫn đánh giá tình hình chỉ báo:

| Verdict | Hành động |
| :--- | :--- |
| **CONFIRM** | Không làm gì (giữ nguyên trạng thái) |
| **VETO hoặc OVERRIDE** (khi ở BUY) | Thoát vị thế: `exit_to_cash` với lý do "indicator degradation" (ghi P&L) |
| **VETO hoặc OVERRIDE** (khi ở SELL) | Xuống cấp: `degrade_to_cash` với lý do "indicator degradation from SELL" |
| **VETO hoặc OVERRIDE** (khi ở CASH) | Bỏ qua -- đã ở CASH rồi, không cần làm gì |

**Điểm quan trọng:** Bộ lọc có thể *ép bán* (exit BUY) hoặc *làm dịu* (degrade SELL về CASH) ngay cả khi V2 state machine không đề xuất thay đổi nào.

---

## V. CONTEXTUAL TRANSITIONS (CHUYỂN TRẠNG THÁI THEO NGỮ CẢNH)

### 1. Theo dõi lịch sử trạng thái:

Engine lưu lại lịch sử các trạng thái đã qua:
```python
state_history = [
    {'state': 'CASH', 'entered_date': ..., 'duration': 15},
    {'state': 'BUY', 'entered_date': ..., 'duration': 8},
    {'state': 'SELL', 'entered_date': ..., 'duration': 12},
    ...
]
```

Biến `_days_in_current_state` đếm số ngày ở trạng thái hiện tại.

### 2. Điều chỉnh ngưỡng theo ngữ cảnh (`_get_contextual_threshold`):

Áp dụng triết lý "ưu tiên giữ tiền mặt" (favor cash) của Dr. K:

**Quy tắc 1: Ở CASH quá lâu -> nghiêm ngặt hơn với BUY**
* Điều kiện: Đang ở CASH và `_days_in_current_state > cash_deterioration_days` (mặc định: > 10 ngày)
* Hành động: Ngưỡng đa số = **1.0** (100% -- tất cả điều kiện phải đồng ý)
* Ý nghĩa: Thị trường ở CASH lâu -> cẩn thận hơn trước khi mua

**Quy tắc 2: CASH từ SELL -> chế độ bearish**
* Điều kiện: Đang ở CASH và trạng thái trước là SELL và đã ở CASH > 5 ngày
* Hành động: Ngưỡng đa số = **1.0** (100% -- tất cả điều kiện phải đồng ý)
* Ý nghĩa: Chuyển từ SELL về CASH là dấu hiệu thị trường xấu, cần tất cả chỉ báo xác nhận trước khi mua

**Các trường hợp khác:** Giữ nguyên ngưỡng mặc định ($\frac{2}{3}$).

**Phạm vi áp dụng:** Chỉ ảnh hưởng đề xuất BUY khi đang ở CASH. Đề xuất SELL và CASH không bị điều chỉnh.

---

## VI. SIGNAL LOG (NHẬT KÝ TÍN HIỆU)

Mỗi phiên giao dịch được ghi lại:
* `old_state`: Trạng thái trước khi xử lý
* `proposed`: Đề xuất từ V2 state machine (BUY/CASH/SELL)
* `verdict`: Kết quả bộ lọc (CONFIRM/VETO/OVERRIDE)
* `confidence`: Điểm tin cậy ($0.0$ đến $1.0$)

Các cột này hỗ trợ phân tích và debug sau backtest.

---

## VII. BẢNG THÔNG SỐ CẤU HÌNH

### FilterConfig (Bộ lọc chỉ báo):

| Thông số | Giá trị mặc định | Mô tả |
| :--- | :---: | :--- |
| `ema55_enabled` | True | Bật điều kiện Close > EMA55 |
| `macd_enabled` | True | Bật điều kiện MACD Histogram > 0 |
| `ema9_21_enabled` | True | Bật điều kiện EMA9 > EMA21 |
| `ma200_enabled` | False | Bật điều kiện Close > MA200 |
| `ema9_enabled` | False | Bật điều kiện Close > EMA9 |
| `macd_signal_enabled` | False | Bật điều kiện MACD > Signal Line |
| `ha_smooth_enabled` | False | Bật điều kiện HA Smoothed 55 Bullish |
| `majority_threshold` | 0.667 (2/3) | Tỷ lệ đồng ý tối thiểu để CONFIRM |

**Cảnh báo:** Khuyến nghị chỉ bật 2-3 điều kiện để tránh overfitting (D-04). Nếu bật > 3 điều kiện, hệ thống sẽ phát ra cảnh báo.

### HybridConfig (Cấu hình tổng hợp):

| Thông số | Giá trị mặc định | Mô tả |
| :--- | :---: | :--- |
| `v2_config` | MDMV2Config() | Cấu hình V2 state machine (xem bảng V2 config) |
| `two_phase_enabled` | True | Bật cơ chế snapshot/restore |
| `filter_enabled` | False | Bật bộ lọc chỉ báo (cần bật để filter hoạt động) |
| `filter_config` | FilterConfig() | Cấu hình bộ lọc chỉ báo |

---

## VIII. SƠ ĐỒ XỬ LÝ MỖI PHIÊN

```
Bắt đầu phiên
    |
    v
[1] Snapshot 4 components
    |
    v
[2] V2 State Machine xử lý
    (Rally tracking, FTD, DD, Stop loss, Position update)
    |
    v
[3] So sánh trạng thái cũ và mới -> Tạo đề xuất (proposal)
    |
    v
[4] Tính ngưỡng ngữ cảnh (contextual threshold)
    |
    v
[5] Indicator Filter đánh giá (evaluate)
    -> Thu thập votes (bullish hoặc bearish)
    -> Tính confidence score
    -> Xác định verdict (CONFIRM / VETO / OVERRIDE)
    |
    v
[6] Áp dụng verdict:
    - CONFIRM: Giữ thay đổi
    - VETO: Rollback snapshot
    - OVERRIDE: Rollback + ép về CASH
    |
    v
[7] Cập nhật state history
    |
    v
[8] Ghi kết quả vào DataFrame
```

---

## IX. GHI CHÚ QUAN TRỌNG

1. **Filter không tạo tín hiệu:** Bộ lọc chỉ CONFIRM hoặc phủ quyết tín hiệu từ V2. Nó không bao giờ tự tạo tín hiệu mua hoặc bán.

2. **OVERRIDE khác VETO:** VETO chỉ chặn đề xuất, giữ trạng thái cũ. OVERRIDE chủ động ép về CASH, có thể gây bán vị thế (exit BUY).

3. **Indicator degradation:** Ngay cả khi V2 không đề xuất thay đổi gì, nếu chỉ báo xấu đi (VETO/OVERRIDE), engine có thể tự động thoát BUY hoặc degrade SELL.

4. **Contextual threshold chỉ ảnh hưởng BUY:** Các quy tắc ngữ cảnh (ở CASH lâu, từ SELL) chỉ làm nghiêm ngặt hơn điều kiện mua, không ảnh hưởng điều kiện bán.

5. **NaN không phải bearish:** Khi dữ liệu chỉ báo là NaN, điều kiện trả về False cho cả bullish và bearish. Điều này tránh việc NaN bị hiểu nhầm là tín hiệu bearish.

6. **Two-phase có thể tắt:** Khi `two_phase_enabled=False`, engine chạy giống hệt V2 (không snapshot, không rollback). Khi `filter_enabled=False`, two-phase vẫn chạy nhưng luôn confirm.

7. **EMA/MACD được tính từ `core.indicators`:** Khi filter được bật, engine gọi `build_indicator_dataframe()` từ module `core/indicators.py` để tính các cột EMA9, EMA21, EMA55, MACD, MA200, HA Smoothed.

8. **Pitfall - CASH override:** Nếu đề xuất là CASH và verdict là OVERRIDE, engine giữ nguyên chuyển CASH (không cần ép lại vì đã đúng hướng).

9. **Pitfall - CASH degradation:** Khi ở CASH và verdict là VETO/OVERRIDE, engine bỏ qua (không làm gì vì đã ở CASH rồi).
