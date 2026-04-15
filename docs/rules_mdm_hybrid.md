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
| **OVERRIDE** | Khôi phục snapshot rồi ép chuyển về CASH. Nếu trước đó là BUY: `exit_to_cash` (ghi nhận P&L). Nếu trước đó là SELL: `cover_short()` (ghi nhận P&L short). Nếu đề xuất CASH: giữ nguyên (đã đúng hướng) |

### Trường hợp 2: Trạng thái KHÔNG ĐỔI (V2 không đề xuất thay đổi)

Bộ lọc vẫn đánh giá tình hình chỉ báo:

| Verdict | Hành động |
| :--- | :--- |
| **CONFIRM** | Không làm gì (giữ nguyên trạng thái) |
| **VETO hoặc OVERRIDE** (khi ở BUY) | Thoát vị thế: `exit_to_cash` với lý do "indicator degradation" (ghi P&L) |
| **VETO hoặc OVERRIDE** (khi ở SELL) | Cover short: `cover_short()` với lý do "indicator degradation from SELL" (ghi nhận P&L) |
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
* Điều kiện: Đang ở CASH và `_days_in_current_state > cash_deterioration_days` (NASDAQ: 10, VN30: 20 ngày)
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

---

## X. VỊ THẾ SHORT TRONG HYBRID ENGINE

*Cập nhật v4.0: Hybrid Engine hỗ trợ vị thế short thật sự khi ở trạng thái SELL, tích hợp với two-phase commit và indicator filter.*

### 1. Mở vị thế Short trong Hybrid:
* Khi hybrid engine chuyển sang **SELL** (sau khi qua two-phase commit và indicator filter), vị thế short được mở.
* **Quan trọng:** Trong hybrid, SELL có thể bị **VETO** bởi indicator filter → short chỉ được mở khi filter **CONFIRM** hoặc khi `filter_enabled = False`.
* Giá entry = Giá đóng cửa phiên chuyển sang SELL.
* Config: `short_mode = 'direct'` (mặc định — VN30 short trực tiếp) hoặc `'inverse_etf'` (NASDAQ — dùng SQQQ/UVXY).

### 2. Tương tác giữa Short và Indicator Filter:

| Tình huống | Verdict | Hành động |
| :--- | :--- | :--- |
| V2 đề xuất SELL | CONFIRM | Mở short, chuyển sang SELL |
| V2 đề xuất SELL | VETO | Rollback — **không mở short**, giữ trạng thái cũ |
| V2 đề xuất SELL | OVERRIDE | Ép về CASH — **không mở short** |
| Đang ở SELL, V2 giữ SELL | VETO/OVERRIDE | Cover short qua `cover_short()`, chuyển về CASH |
| Đang ở SELL, V2 giữ SELL | CONFIRM | Giữ nguyên vị thế short |

**Điểm quan trọng:** Indicator filter có thể **OVERRIDE** từ SELL về CASH → tương đương cover short với P&L. Trong trường hợp này, engine gọi `cover_short()` (không phải `degrade_to_cash()`) để ghi nhận P&L short.

### 3. Short Cover Triggers (giống V2):

**Điều kiện 1: Short Stop Loss (DD5 high)** — Ưu tiên cao nhất, kiểm tra trước filter.

**Điều kiện 2: FTD được phát hiện** → cover short, chuyển về CASH.

**Điều kiện 3: MA50 breakout** → cover short, chuyển về CASH.

**Điều kiện 4 (Hybrid-specific): Indicator degradation** → Khi V2 không đề xuất thay đổi nhưng chỉ báo xấu đi (VETO/OVERRIDE khi ở SELL), engine tự động cover short về CASH.

### 4. Short P&L:
$$pnl = \frac{gia\_entry - gia\_cover}{gia\_entry}$$
* Dương khi thị trường giảm, âm khi thị trường tăng.

### 5. Equity Curve:
* Khi `prev_state = SELL` (có short): sử dụng inverse return $equity[i] = equity[i-1] \times \frac{close[i-1]}{close[i]}$
* Khi `long_only_equity = True`: equity giữ nguyên (flat) khi ở SELL.

**Quy tắc quan trọng — Tránh Look-Ahead Bias:**
* Equity curve **phải** dùng trạng thái ngày hôm trước (`state[i-1]`) để quyết định return ngày hôm nay.
* **Sai:** `if state[i] == 'BUY': capture return[i]` — nhìn trước signal hôm nay.
* **Đúng:** `if state[i-1] == 'BUY': capture return[i]` — quyết định dựa trên signal đã có từ hôm qua.

---

## XI. QUY TẮC CHUYỂN TRẠNG THÁI MỞ RỘNG (v4.0)

*Cập nhật v4.0: Enforce đúng chuỗi chuyển trạng thái SELL -> CASH -> BUY, bao gồm hybrid OVERRIDE paths.*

### 1. Quy tắc bắt buộc: SELL -> CASH -> BUY

* **KHÔNG cho phép** chuyển trực tiếp từ SELL sang BUY.
* `enter_buy()` sẽ raise `ValueError` nếu trạng thái hiện tại là SELL.
* Tất cả chuyển từ SELL về CASH **phải** qua `cover_short()` để tính P&L.
* Sau khi cover short về CASH, engine mới có thể chuyển sang BUY.

### 2. MA50 Breakout từ SELL:
* Khi ở SELL và giá vượt MA50: chỉ **cover short về CASH**.
* **Không mua trực tiếp** — phải chờ tín hiệu mua riêng khi đã ở CASH.

### 3. Hybrid-specific: OVERRIDE verdict từ SELL:
* Khi indicator filter trả về OVERRIDE khi đang ở SELL: engine cover short về CASH qua `cover_short()`.
* OVERRIDE từ SELL **không** chuyển thẳng sang BUY — luôn qua CASH.
* Đây là cơ chế bảo vệ bổ sung so với V2: indicator filter có thể ép cover short sớm hơn khi chỉ báo cải thiện.

### 4. Sơ đồ chuyển trạng thái cập nhật (v4.0 + Hybrid):

```
BUY -> SELL    : DD count >= threshold (CONFIRM bởi filter)
BUY -> CASH    : Stop loss, MA10 breakdown, VETO/OVERRIDE từ filter
SELL -> CASH   : FTD, MA50 breakout, Short stop loss (DD5 high),
                 OVERRIDE/VETO từ filter (indicator degradation)
CASH -> BUY    : FTD, MA50 breakout, 52-week breakout (CONFIRM bởi filter)
SELL -> BUY    : KHÔNG CHO PHÉP (phải qua CASH trước)
```

### 5. So sánh với Hybrid cũ:

| Chuyển trạng thái | Hybrid cũ | Hybrid v4.0 |
| :--- | :--- | :--- |
| SELL -> BUY | Cho phép (FTD/MA50 + CONFIRM) | **Cấm** — phải qua CASH |
| SELL -> CASH (OVERRIDE) | `degrade_to_cash()` (không P&L) | `cover_short()` **(có P&L)** |
| SELL -> CASH (indicator degradation) | `degrade_to_cash()` | `cover_short()` **(có P&L)** |

---

## XII. CẬP NHẬT STOP LOSS (v4.0)

*Cập nhật v4.0: Stop loss linh hoạt theo volatility, giảm mặc định xuống 1.5%, thêm short stop loss dựa trên DD5 high.*

### 1. Long Stop Loss — Giảm xuống 1.5%:
* Mặc định: $C < P_{buy} \times (1 - 0.015)$ (giảm **1.5%** từ giá mua).
* Thay đổi từ 2.5% (cũ) xuống 1.5% theo quy tắc Dr. K.
* Config: `stop_loss_pct = 0.015`.

### 2. Volatility-Adaptive Stop Loss (ATR):
* Sử dụng **ATR (Average True Range)** / baseline ratio để điều chỉnh stop loss.
* Công thức: $effective\_pct = stop\_loss\_pct \times \frac{ATR_{current}}{ATR_{baseline}}$
* Ratio được **clamp** trong khoảng **[0.5x, 2.5x]**:
  * Khi ATR cao (thị trường volatile): stop loss rộng hơn (ví dụ $1.5\% \times 2.0 = 3.0\%$)
  * Khi ATR thấp (thị trường ổn định): stop loss chặt hơn (ví dụ $1.5\% \times 0.7 = 1.05\%$)
* Config: `atr_period = 14`, `volatility_adaptive = True`

### 3. Short Stop Loss — DD5 High:
* **DD5 high** = Giá cao nhất ($H$) của ngày phân phối thứ 5 (ngày DD kích hoạt chuyển sang SELL).
* DD5 high được **lock** vào engine khi chuyển sang trạng thái SELL.
* Mỗi phiên khi ở SELL, kiểm tra: $C > DD5_{high} \times (1 + short\_stop\_pct)$
* Mặc định: 1% trên DD5 high → $C > DD5_{high} \times 1.01$
* Khi kích hoạt: cover short, chuyển về **CASH**.
* **Hybrid-specific:** Short stop loss được kiểm tra **TRƯỚC** khi indicator filter đánh giá — đảm bảo stop loss luôn được ưu tiên.
* Config: `short_stop_pct_above_dd5 = 0.01`

### 4. Thứ tự kiểm tra trong Hybrid Engine:

```
[1] Short stop loss (DD5 high)     ← Ưu tiên cao nhất, trước filter
[2] V2 state machine xử lý        ← FTD, MA50, DD counting
[3] Indicator filter đánh giá      ← CONFIRM/VETO/OVERRIDE
[4] Long stop loss (1.5% + ATR)    ← Trong V2 processing
```

### 5. Bảng thông số Stop Loss cập nhật:

| Thông số | Giá trị cũ | Giá trị v4.0 | Mô tả |
| :--- | :---: | :---: | :--- |
| `stop_loss_pct` | 0.025 (2.5%) | **0.015 (1.5%)** | Phần trăm cắt lỗ long từ giá mua |
| `volatility_adaptive` | Không có | **True** | Bật/tắt ATR adaptive scaling |
| `atr_period` | Không có | **14** | Số phiên tính ATR |
| `short_stop_pct_above_dd5` | Không có | **0.01 (1%)** | Phần trăm trên DD5 high để cover short |

---

## XIII. THÔNG SỐ THEO THỊ TRƯỜNG (Market-Specific Presets)

Dashboard VN30 sử dụng **VN30_PRESET** với các thông số đã calibrate:

| Thông số | NASDAQ (mặc định) | VN30 (optimized) | Lý do |
| :--- | :---: | :---: | :--- |
| `correction_threshold` | -0.10 | **-0.06** | VN30 corrections nông hơn |
| `ma10_cash_consecutive` | 2 | **3** | Giảm whipsaw |
| `cash_deterioration_days` | 10 | **20** | Giảm thời gian short (VN30 uptrend dài hạn) |

Sử dụng: `from strategies.mdm_hybrid.config import VN30_PRESET, NASDAQ_PRESET`

### Kết quả backtest VN30 (2015-2026):

| Config | Tổng lợi nhuận | CAGR | MaxDD |
| :--- | :---: | :---: | :---: |
| **VN30 preset + fail-safe** | **+239%** | **11.5%** | **-28.2%** |
| VN30 preset (không fail-safe) | +192% | 10.0% | -31.8% |
| Mua & Nắm giữ | +205% | 10.4% | -48.1% |

Walk-forward validation (train 2015-2021, test 2022-2026): CAGR degradation 40% (trong ngưỡng chấp nhận).

---

## XIV. CƠ CHẾ FAIL-SAFE (SAFE-01, SAFE-02)

Cơ chế fail-safe giảm lỗ từ false SELL signal bằng cách tự động thoát SELL khi thị trường phục hồi nhanh, theo định nghĩa của Dr. K trong VOSI FAQ.

### 1. Nguyên lý hoạt động

Khi engine chuyển sang trạng thái SELL, hệ thống ghi nhận HIGH của **standby-sell day** (ngày trước sell signal day) làm `fail_safe_threshold`. Đây là mức giá tham chiếu để xác định thị trường đã phục hồi hay chưa.

### 2. Quy tắc chuyển trạng thái

Trong trạng thái SELL, mỗi ngày hệ thống kiểm tra:
- Nếu `close > fail_safe_threshold` -> tự động cover short, chuyển về **CASH** (fail-safe triggered)
- Nếu `close <= fail_safe_threshold` -> giữ nguyên trạng thái SELL

**Thứ tự ưu tiên:** Fail-safe check có ưu tiên **cao nhất** trong trạng thái SELL (trước short stop loss, FTD cover, MA50 cover).

### 3. Thông số cấu hình

| Thông số | Kiểu | Mặc định | Mô tả |
| :--- | :--- | :---: | :--- |
| `fail_safe_enabled` | bool | `True` | Công tắc bật/tắt cơ chế fail-safe |

### 4. Kết quả

Trên VN30 2015-2026: 35 lần fail-safe trigger, cải thiện return từ +192% lên +239% và giảm MaxDD từ -31.8% xuống -28.2%.

---

## XV. PORTFOLIO ENGINE — MDM SELL PARTIAL LIQUIDATION (Phase 999.1)

*Áp dụng cho `strategies/portfolio/engine.py` (PortfolioEngine), không phải HybridEngine trực tiếp.*

Khi `PortfolioEngine` nhận tín hiệu MDM SELL, thay vì thanh lý **tất cả** vị thế đang mở, hệ thống chỉ đóng **50% yếu nhất** (theo Relative Strength).

### 1. Hành vi cũ (trước Phase 999.1)

MDM SELL → đóng toàn bộ vị thế đang mở với `exit_reason="mdm_sell"`.

### 2. Hành vi mới — Partial Liquidation (Phase 999.1)

MDM SELL → xếp hạng vị thế theo RS, đóng **nhóm yếu nhất**, giữ lại **nhóm mạnh nhất**.

**Thuật toán:**

```
1. Lấy danh sách eligible positions (chưa scheduled exit, chưa retained, đã qua earliest_sell_bar)
2. n_keep = math.ceil(len(eligible) * sell_retain_pct)  # mặc định 50%, làm tròn lên
3. Xếp hạng eligible theo RS giảm dần (NaN/None → -inf, đóng trước)
4. Top n_keep vị trí → thêm vào _sell_retained_ids (giữ lại)
5. Phần còn lại → schedule exit với reason="mdm_sell" tại bar tiếp theo
6. Các lần SELL bar tiếp theo: bỏ qua vị trí đã retained (không evaluate lại)
```

**Quy tắc xử lý đặc biệt:**
- RS = NaN hoặc None → coi là RS = -inf (yếu nhất, đóng trước)
- Làm tròn: `math.ceil` (ưu tiên giữ lại, ví dụ: 3 vị trí × 0.5 → ceil(1.5) = 2 giữ)
- Retained positions bị skip trong `evaluate_exits` khi tìm MDM SELL exits → tránh double-exit
- **Retained positions KHÔNG được giữ vô thời hạn**: vẫn bị đóng bởi `evaluate_exits` thông qua hard_stop, ma50_break, rs_streak nếu điều kiện kích hoạt
- **MDM SELL dispatch**: được xử lý **hoàn toàn** bởi engine section (3). Hàm `evaluate_exits` KHÔNG có MDM SELL dispatch riêng — loại bỏ để tránh đóng các retained positions ngoài ý muốn

### 3. Thông số cấu hình

| Thông số | Kiểu | Mặc định | Mô tả |
| :--- | :--- | :---: | :--- |
| `sell_retain_pct` | float | `0.5` | Tỷ lệ vị trí giữ lại (top RS). Phạm vi: (0.0, 1.0] |

**Validation:** `0 < sell_retain_pct <= 1.0`. Giá trị 0.0 raise ValueError. Giá trị 1.0 hợp lệ (giữ lại tất cả, không đóng gì khi SELL).

### 4. Tác động đến exit_reason

- Số lượng `mdm_sell` exits giảm so với behavior cũ (chỉ đóng phần yếu — bottom 50%)
- Retained positions tiếp tục được quản lý bình thường: vẫn bị đóng bởi `hard_stop`, `ma50_break`, `rs_streak` nếu điều kiện kích hoạt
- Không có "giữ vô thời hạn" — chỉ là không bị forced-close bởi MDM SELL

### 5. Kết quả OOS (2019-2025, Phase 999.1)

So với Phase 33 OOS baseline (trước fix). Kết quả sau khi sửa bug `evaluate_exits` (commit d218ce3):

| Chỉ số | Phase 33 (old, full liquidation) | Phase 999.1 (partial liquidation, sau fix) | Thay đổi |
| :--- | :---: | :---: | :--- |
| CAGR | 6.23% | 10.18% | +3.95pp |
| Sharpe_rf3 | 0.448 | 0.813 | +0.365 |
| MaxDD | -10.22% | -16.31% | -6.09pp |
| Closed trades | 62 | 59 | -3 |
| mdm_sell exits | nhiều | 5 | Chỉ đóng bottom 50% mỗi lần SELL |

**Lưu ý quan trọng (bug đã sửa):** Phiên bản đầu tiên của Phase 999.1 có bug trong `evaluate_exits` — hàm này có MDM SELL dispatch riêng đóng cả retained positions. Bug đã được sửa (commit d218ce3): `evaluate_exits` không còn MDM SELL dispatch; engine section (3) xử lý hoàn toàn. Kết quả trên là sau khi sửa bug.

---

## XVI. ATR BUFFER ZONE — MA50 BREAKDOWN FILTER (Phase 38, ATR-01/ATR-03)

*Thêm vào v9.0: Thay trigger SELL hiện tại (`close < MA50`) bằng rule có đệm để giảm whipsaw từ các nhịp nhúng giả trong SELL signal.*

### 1. Mục tiêu

84% tín hiệu SELL đến từ MA50 breakdown. Khi thị trường có nhịp "kéo xả" tạm thời (large-cap pulling down VN30 để thanh lý phái sinh F1), close có thể vi phạm MA50 trong 1-2 phiên rồi hồi lại. ATR Buffer Zone đặt ngưỡng vi phạm thấp hơn MA50 một khoảng `k × ATR_N`, yêu cầu close phải xuống dưới ngưỡng đó trong `m` phiên liên tiếp mới kích hoạt SELL.

### 2. Công thức

```
violation_threshold[t] = MA50[t] - k × ATR_N[t]
```

Tín hiệu SELL kích hoạt khi: `close[t-m+1 .. t]` đều < `violation_threshold[t-m+1 .. t]` tương ứng.

- `m = 1`: tương đương rule v6.0 (khi `violation_threshold ≡ MA50`)
- `k = 0` + `m = 1`: byte-identical với v6.0

### 3. Tham số cấu hình (MDMV2Config)

| Thông số | Kiểu | Mặc định | Mô tả |
| :--- | :--- | :---: | :--- |
| `atr_buffer_enabled` | bool | `False` | Feature gate — tắt = hành vi v6.0 (ATR-04) |
| `atr_buffer_k` | float | `0.5` | Hệ số nhân ATR: `violation_threshold = MA50 - k × ATR_N` |
| `atr_buffer_period` | int | `14` | Lookback ATR (tách biệt với `atr_period` dùng cho stop-loss) |
| `atr_buffer_consecutive_days` | int | `2` | Số phiên `m` liên tiếp close phải < violation_threshold |

### 4. Chỉ báo: `Indicators.add_violation_threshold_column(df, k, period)`

- Static method trong `strategies/mdm_hybrid/indicators.py`
- Ghi column `violation_threshold` = `ma50 - k * atr_buf`
- Dùng column name riêng `atr_buf` / `true_range_buf` để **không ghi đè** `atr` / `true_range` của stop-loss
- Input: DataFrame có cột `high`, `low`, `close`, `ma50`
- Output: DataFrame với `violation_threshold`, `atr_buf`, `true_range_buf`

### 5. Quy tắc áp dụng (phạm vi)

- **Chỉ** áp dụng cho trigger CASH→SELL entry (MA50 breakdown)
- **Không** áp dụng cho:
  - Short cover SELL→CASH (`close > MA50`) — giữ nguyên (D-10)
  - BUY-state MA50 exit trong stop_loss.py — giữ nguyên (D-11)
- m-day rule là backward-looking: trigger fires hôm nay khi `m` phiên gần nhất đều vi phạm ngưỡng
- Trong `m` ngày đầu tiên (warm-up): rule không fire (D-04)

### 6. Bảo toàn backward compatibility (ATR-04)

Khi `atr_buffer_enabled=False`, engine phải tái lập **byte-identical** signal log của v6.0 baseline trên VN30 2015-2026. Regression test (`tests/test_phase38_backward_compat.py`) bảo vệ invariant này bằng fixture parquet (`tests/fixtures/phase38_v6_baseline_signal_log.parquet`).

### 7. Sweep tham số (Phase 40)

- `k ∈ [0.3, 0.5, 0.7, 1.0]` × `N ∈ [10, 14, 20]` × `m ∈ [1, 2, 3]` = 36 combos
- In-sample 2015-2021, metric: max Sharpe với MaxDD ≤ -30%
