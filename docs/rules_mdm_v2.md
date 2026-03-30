# BỘ QUY TẮC MÔ HÌNH MDM V2 - MÁY TRẠNG THÁI 3 BƯỚC (BUY/CASH/SELL)

## I. TỔNG QUAN

MDM V2 là phiên bản cải tiến của MDM Classic, thay đổi từ máy trạng thái 4 bước (CASH/HOLDING/WAITING_SELL/SHORT) thành máy trạng thái 3 bước đơn giản hơn:

| Trạng thái | Mô tả |
| :--- | :--- |
| **CASH** | Không giữ vị thế, chờ tín hiệu mua |
| **BUY** | Đang giữ vị thế Long |
| **SELL** | Tín hiệu giảm - thị trường xấu đi, chỉ chờ FTD để quay lại BUY |

**Cải tiến chính so với Classic:**
- Bỏ trạng thái WAITING_SELL và SHORT (không bán khống nữa)
- Thêm cơ chế chuyển CASH -> SELL khi thị trường xấu đi (MA50 breakdown hoặc ở CASH quá lâu)
- Thêm điều kiện thoát BUY -> CASH qua MA10 (đóng cửa dưới MA10 nhiều phiên liên tiếp)
- Giữ nguyên các điều kiện mua (FTD, MA50 breakout, 52-week breakout)

---

## II. DỮ LIỆU ĐẦU VÀO VÀ CHỈ BÁO KỸ THUẬT

### 1. Dữ liệu đầu vào:
* Giá Mở cửa ($O$), Cao nhất ($H$), Thấp nhất ($L$), Đóng cửa ($C$), Khối lượng ($V$).
* Dữ liệu chỉ số (VNINDEX hoặc NASDAQ).

### 2. Các chỉ báo được tính:
* **MA10**: Trung bình động 10 phiên của giá đóng cửa.
* **MA50**: Trung bình động 50 phiên của giá đóng cửa.
* **MA50 Volume**: Trung bình động 50 phiên của khối lượng.
* **P_loc** (Vị thế khung giá): $P_{loc} = \frac{C - L}{H - L}$
* **Rolling High**: Đỉnh cao nhất tích lũy.
* **High 52 tuần**: Đỉnh cao nhất trong 252 phiên giao dịch.
* **Drawdown**: Mức giảm từ đỉnh: $\frac{C - Rolling\_High}{Rolling\_High}$
* **Price Change %**: Phần trăm thay đổi giá so với phiên trước.
* **Volume Up**: Khối lượng cao hơn phiên trước ($V > V_{prev}$).

### 3. Xử lý ngày đáo hạn phái sinh:
* Nếu cột `is_expiry_day` tồn tại trong dữ liệu, các phiên đáo hạn sẽ bị tắt cờ `volume_up = False`.
* Điều này ngăn việc đếm ngày phân phối sai do khối lượng tăng đột biến vào ngày đáo hạn.

---

## III. TRẠNG THÁI 1: CASH (TÌM KIẾM CƠ HỘI)

*Trạng thái hiện tại: 100% tiền mặt, không giữ vị thế.*

### 1. Theo dõi Rally Attempt (Nỗ lực hồi phục):

**Điều kiện vào "Giai đoạn điều chỉnh":**
* Chỉ số giảm >= 10% từ đỉnh cao nhất gần nhất ($drawdown \le -0.10$).
* Khi đạt đỉnh mới (high mới), giai đoạn điều chỉnh được reset.

**Ngày 1 (Day 1) của Rally Attempt:**
* Điều kiện (1 trong 2):
  * Giá đóng cửa tăng so với phiên trước ($C > C_{prev}$).
  * HOẶC: Giá đóng cửa ở nửa trên khung giá ($P_{loc} > 0.5$), kể cả khi giá giảm.
* **Quy tắc hủy đế:** Nếu giá phá thủng đáy thấp nhất của Ngày 1 ($L_{hiện\_tại} < L_{Day1}$) -> Hủy đếm, bắt đầu lại từ đầu.

### 2. Tín hiệu Mua (FTD - Follow-Through Day):

* **Thời gian:** Xuất hiện từ **Ngày thứ 4 đến Ngày thứ 12** của đợt nỗ lực hồi phục (config: `ftd_min_rally_day=3`, `ftd_max_rally_day=12`, nhưng engine kiểm tra `rally_day >= 4`).
* **Điều kiện Giá:** Tăng >= 1% so với phiên trước ($price\_change\_pct \ge 0.01$).
* **Điều kiện Khối lượng:** Cao hơn phiên trước ($volume\_up = True$).
* **Hành động:**
  * Chuyển trạng thái: CASH -> **BUY**.
  * Reset bộ đếm ngày phân phối: $Count_{DD} = 0$.
  * Ghi nhận **Giá Mua** = Giá đóng cửa phiên FTD.
  * Reset rally tracker.

### 3. Tín hiệu Mua (Phá vỡ lên trên MA50):

* **Điều kiện (tất cả phải thỏa mãn):**
  1. Drawdown từ đỉnh >= 6% ($drawdown\_pct \le -0.06$).
  2. Phiên trước đóng cửa **dưới hoặc bằng** MA50 của phiên trước ($C_{prev} \le MA50_{prev}$).
  3. Phiên hiện tại đóng cửa **vượt lên trên** MA50 ($C > MA50$).
  4. Khối lượng cao hơn phiên trước ($volume\_up = True$).
* **Hành động:** Tương tự FTD, chuyển sang BUY, reset DD counter.

### 4. Tín hiệu Mua (Vượt đỉnh 52 tuần):

* **Điều kiện:** Giá đóng cửa vượt đỉnh 52 tuần ($C > High_{52w}$).
* **Hành động:** Chuyển sang BUY.
* **Stop loss đặc biệt:** Đặt stop loss tại $L_{ngày\_mua} \times 0.99$ (1% dưới đáy ngày mua).

### 5. Chuyển CASH -> SELL (Thị trường xấu đi):

Nếu không có tín hiệu mua, kiểm tra 2 điều kiện chuyển sang SELL:

* **MA50 Breakdown** (khi `ma50_sell_enabled=True`):
  * Giá đóng cửa dưới MA50 ($C < MA50$).
  * -> Chuyển sang trạng thái SELL.

* **Cash Deterioration** (Xuống cấp do ở CASH quá lâu):
  * Số ngày ở trạng thái CASH >= `cash_deterioration_days` (mặc định: 10 ngày).
  * -> Chuyển sang trạng thái SELL.

**Thứ tự ưu tiên:** FTD > MA50 Breakout > 52-Week Breakout > MA50 Sell > Cash Deterioration.

---

## IV. TRẠNG THÁI 2: BUY (NẮM GIỮ VỊ THẾ)

*Trạng thái hiện tại: Đang giữ vị thế Long.*

### 1. Đếm Ngày phân phối (Distribution Day):

**Loại 1 (Giảm mạnh - Heavy Selling):**
* Giá giảm >= 0.2% ($price\_change\_pct \le -0.002$).
* Khối lượng tăng ($volume\_up = True$).

**Loại 2 (Chững lại - Stalling):**
* Giá tăng nhẹ, trong khoảng $0 \le price\_change\_pct < 0.001$.
* Khối lượng tăng ($volume\_up = True$).
* Đóng cửa ở phần dưới khung giá ($P_{loc} \le 0.20$).

**Bộ đếm DD:**
* Đếm số ngày phân phối trong cửa sổ trượt 20 phiên gần nhất.
* Reset về 0 khi xuất hiện tín hiệu mua (FTD).

### 2. Điều kiện thoát BUY -> CASH:

**Điều kiện 1: Stop Loss (Ưu tiên cao nhất)**
* Xem Mục V (Quy tắc cắt lỗ) bên dưới.

**Điều kiện 2: Ngưỡng DD đạt**
* Tổng số ngày phân phối trong 20 phiên >= `dd_cash_threshold` (mặc định: 5).
* CHỈ khi ngày hiện tại là ngày phân phối ($is\_dd = True$).
* -> Chuyển sang CASH, ghi nhận P&L.

**Điều kiện 3: Đóng cửa dưới MA10 liên tiếp**
* Khi `ma10_cash_enabled=True` (mặc định: True).
* Giá đóng cửa dưới MA10 trong `ma10_cash_consecutive` phiên liên tiếp (mặc định: 2 phiên).
* Bộ đếm reset về 0 khi giá đóng cửa trên MA10.
* -> Chuyển sang CASH, ghi nhận P&L.

**Thứ tự ưu tiên:** Stop Loss > DD Threshold > MA10 Below.

---

## V. QUY TẮC CẮT LỖ (STOP LOSS)

Chỉ áp dụng khi đang ở trạng thái BUY. Không có stop loss cho SHORT (đã bỏ SHORT trong V2).

### 1. Cắt lỗ theo phần trăm (Rule 1):
* Giá đóng cửa giảm quá `stop_loss_pct` từ giá mua.
* Mặc định: $C < P_{buy} \times (1 - 0.025)$ (giảm 2.5%).

### 2. Phá thủng đáy ngày mua (Rule 2):
* Giá đóng cửa thấp hơn giá thấp nhất của ngày mua ($C < L_{buy\_day}$).

### 3. Phá vỡ xuống dưới MA50 (Rule 3):
* Phiên trước đóng cửa **trên hoặc bằng** MA50 trước ($C_{prev} \ge MA50_{prev}$).
* Phiên hiện tại đóng cửa **dưới** MA50 ($C < MA50$).
* Khối lượng phiên hiện tại cao hơn phiên trước ($V > V_{prev}$).

### 4. Quy tắc đặc biệt cho 52-Week Breakout:
* Nếu tín hiệu mua là 52-Week Breakout, chỉ áp dụng stop loss:
  * $C < L_{buy\_day} \times 0.99$ (1% dưới đáy ngày mua).
* Không áp dụng Rule 1, 2, 3 thông thường.

**Thứ tự kiểm tra:** Rule đặc biệt 52-Week trước -> Rule 1 -> Rule 2 -> Rule 3.

---

## VI. TRẠNG THÁI 3: SELL (THỊ TRƯỜNG XẤU)

*Trạng thái hiện tại: Tín hiệu thị trường xấu, không giữ vị thế.*

### Đặc điểm:
* SELL là trạng thái **bền vững** (persistent) -- chỉ có FTD hoặc MA50 breakout hoặc 52-Week breakout mới chuyển về BUY.
* Không có cơ chế tự động thoát SELL (khác với Classic có SHORT và cover).
* Khi ở SELL, rally attempt vẫn được theo dõi để phát hiện FTD.

### Chuyển SELL -> BUY:
* Cùng điều kiện như CASH -> BUY:
  * FTD signal, hoặc
  * MA50 breakout, hoặc
  * 52-Week breakout.
* -> Chuyển thẳng sang BUY, bỏ qua CASH.

---

## VII. SƠ ĐỒ CHUYỂN TRẠNG THÁI

```
                    FTD / MA50 breakout / 52-Week
            +----------------------------------------+
            |                                        |
            v                                        |
    +-------+-------+     DD >= 5 (on DD day)    +---+---+
    |               | ----------------------->   |       |
    |     BUY       |     Stop Loss triggered    | CASH  |
    |               | ----------------------->   |       |
    +-------+-------+     MA10 below N days      +---+---+
            ^                                        |
            |                                        |
            |              MA50 breakdown            v
            |              Cash deterioration    +-------+
            +-------- FTD / MA50 breakout -------|       |
                                                 | SELL  |
                                                 +-------+
```

---

## VIII. BẢNG THÔNG SỐ CẤU HÌNH (MDMV2Config)

| Thông số | Giá trị mặc định | Mô tả |
| :--- | :---: | :--- |
| `correction_threshold` | -0.10 | Ngưỡng giảm từ đỉnh để xác nhận điều chỉnh (-10%) |
| `ftd_min_rally_day` | 3 | Ngày tối thiểu trong rally để kiểm tra FTD |
| `ftd_max_rally_day` | 12 | Ngày tối đa trong rally để kiểm tra FTD |
| `ftd_min_price_gain` | 0.01 | Mức tăng giá tối thiểu cho FTD (1%) |
| `ma50_breakout_correction` | -0.06 | Ngưỡng drawdown tối thiểu cho MA50 breakout (-6%) |
| `dd_window_size` | 20 | Số phiên trong cửa sổ trượt đếm DD |
| `dd_price_drop_threshold` | -0.002 | Ngưỡng giảm giá cho DD Loại 1 (-0.2%) |
| `dd_price_stall_threshold` | 0.001 | Ngưỡng tăng giá tối đa cho DD Loại 2 (0.1%) |
| `dd_stall_p_loc_threshold` | 0.20 | Ngưỡng P_loc tối đa cho DD Loại 2 |
| `dd_cash_threshold` | 5 | Số DD kích hoạt chuyển BUY -> CASH |
| `ma10_cash_enabled` | True | Bật/tắt điều kiện thoát theo MA10 |
| `ma10_cash_consecutive` | 2 | Số phiên liên tiếp dưới MA10 để kích hoạt |
| `ma50_sell_enabled` | True | Bật/tắt MA50 breakdown cho CASH -> SELL |
| `cash_deterioration_days` | 10 | Số ngày ở CASH trước khi tự động chuyển SELL |
| `stop_loss_pct` | 0.025 | Phần trăm cắt lỗ từ giá mua (2.5%) |
| `name` | "default" | Tên giả thuyết (metadata) |

---

## IX. GHI CHÚ QUAN TRỌNG

1. **Không có vị thế SHORT:** V2 bỏ hoàn toàn cơ chế bán khống. SELL chỉ là tín hiệu cảnh báo, không mở vị thế bán khống.

2. **DD chỉ đếm khi BUY:** Ngày phân phối chỉ được đếm khi đang ở trạng thái BUY. Khi ở CASH hoặc SELL, bộ đếm DD không hoạt động.

3. **FTD reset rally tracker:** Sau khi phát hiện FTD, rally tracker được reset hoàn toàn (`full_reset`), bao gồm cả trạng thái điều chỉnh và đỉnh.

4. **Rally tracking ở cả CASH và SELL:** Cả hai trạng thái CASH và SELL đều theo dõi rally attempt để phát hiện FTD.

5. **Thứ tự ưu tiên tín hiệu mua:** FTD truyền thống -> MA50 breakout -> 52-Week breakout. Chỉ tín hiệu đầu tiên được chấp nhận.

6. **Stop loss chỉ cho Long:** Không có stop loss cho vị thế Short (vì không có Short).

7. **DD day là điều kiện cần:** Chuyển BUY -> CASH do DD chỉ xảy ra khi ngày hiện tại cũng là ngày phân phối (không phải bất cứ ngày nào có dd_count >= threshold).

---

## X. VỊ THẾ SHORT (BÁN KHỐNG)

*Cập nhật v4.0: MDM V2 hỗ trợ vị thế short thật sự khi ở trạng thái SELL (theo Dr. K webinar — SELL = short thật, dùng SQQQ/UVXY trên US market, short trực tiếp chỉ số trên VN30).*

### 1. Mở vị thế Short:
* Khi engine chuyển sang trạng thái **SELL**, vị thế short được mở tự động.
* **Giá entry** = Giá đóng cửa phiên chuyển sang SELL.
* Cấu hình: `short_mode = True` (mặc định) để bật vị thế short khi SELL.
* Khi `short_mode = False`, SELL chỉ là tín hiệu cảnh báo, không mở vị thế bán khống (hành vi V2 cũ).

### 2. Công thức tính P&L cho Short:
$$pnl = \frac{gia\_entry - gia\_cover}{gia\_entry}$$
* **Dương** khi thị trường giảm (gia_cover < gia_entry) — lợi nhuận từ vị thế short.
* **Âm** khi thị trường tăng (gia_cover > gia_entry) — thua lỗ từ vị thế short.

### 3. Điều kiện Cover Short (Đóng vị thế short):

Có **3 điều kiện** cover short, theo thứ tự ưu tiên:

**Điều kiện 1: Short Stop Loss (Ưu tiên cao nhất)**
* Xem Mục XII — Stop loss cho vị thế short.
* Kiểm tra **trước** FTD/MA50 cover signals mỗi phiên.

**Điều kiện 2: FTD được phát hiện**
* Follow-Through Day xuất hiện -> cover short, chuyển về **CASH**.
* P&L được ghi nhận qua `cover_short()`.

**Điều kiện 3: Giá vượt lên trên MA50**
* Phiên trước đóng cửa dưới hoặc bằng MA50 ($C_{prev} \le MA50_{prev}$).
* Phiên hiện tại đóng cửa vượt lên trên MA50 ($C > MA50$).
* -> Cover short, chuyển về **CASH** (không mua trực tiếp).

### 4. Equity Curve khi Short:
* Khi ở trạng thái SELL (có short):
$$equity[i] = equity[i-1] \times \frac{close[i-1]}{close[i]}$$
* Đây là **inverse return** — equity tăng khi thị trường giảm, giảm khi thị trường tăng.
* Khi `short_mode = False` hoặc `long_only_equity = True`: equity giữ nguyên (flat) khi ở SELL.

---

## XI. QUY TẮC CHUYỂN TRẠNG THÁI MỞ RỘNG (v4.0)

*Cập nhật v4.0: Enforce đúng chuỗi chuyển trạng thái SELL -> CASH -> BUY theo Dr. K model.*

### 1. Quy tắc bắt buộc: SELL -> CASH -> BUY

* **KHÔNG cho phép** chuyển trực tiếp từ SELL sang BUY.
* `enter_buy()` sẽ raise `ValueError` nếu trạng thái hiện tại là SELL.
* Tất cả chuyển từ SELL về CASH **phải** qua `cover_short()` để tính P&L cho vị thế short.
* Sau khi cover short về CASH, engine mới có thể chuyển sang BUY qua FTD/MA50 breakout bình thường.

### 2. MA50 Breakout từ SELL:
* Khi ở trạng thái SELL và giá vượt MA50: chỉ **cover short về CASH**.
* **Không mua trực tiếp** — phải chờ tín hiệu mua riêng khi đã ở CASH.

### 3. Sơ đồ chuyển trạng thái cập nhật (v4.0):

```
BUY -> SELL    : DD count >= threshold (trên ngày DD)
BUY -> CASH    : Stop loss, MA10 breakdown
SELL -> CASH   : FTD, MA50 breakout, Short stop loss (DD5 high)
CASH -> BUY    : FTD, MA50 breakout, 52-week breakout
SELL -> BUY    : KHÔNG CHO PHÉP (phải qua CASH trước)
```

### 4. So sánh với V2 cũ:

| Chuyển trạng thái | V2 cũ | V2 v4.0 |
| :--- | :--- | :--- |
| SELL -> BUY | Cho phép (FTD/MA50) | **Cấm** — phải qua CASH |
| SELL -> CASH | Không tồn tại | cover_short() + P&L |
| BUY -> SELL | DD threshold | DD threshold (giữ nguyên) |
| BUY -> CASH | Stop loss, MA10 | Stop loss, MA10 (giữ nguyên) |

---

## XII. CẬP NHẬT STOP LOSS (v4.0)

*Cập nhật v4.0: Stop loss linh hoạt theo volatility, giảm mặc định xuống 1.5%, thêm short stop loss dựa trên DD5 high.*

### 1. Long Stop Loss — Giảm xuống 1.5%:
* Mặc định: $C < P_{buy} \times (1 - 0.015)$ (giảm **1.5%** từ giá mua).
* Thay đổi từ 2.5% (v2 cũ) xuống 1.5% theo quy tắc Dr. K.
* Config: `stop_loss_pct = 0.015`.

### 2. Volatility-Adaptive Stop Loss (ATR):
* Sử dụng **ATR (Average True Range)** / baseline ratio để điều chỉnh stop loss theo mức biến động thị trường.
* Công thức: $effective\_pct = stop\_loss\_pct \times \frac{ATR_{current}}{ATR_{baseline}}$
* Ratio được **clamp** trong khoảng **[0.5x, 2.5x]**:
  * Khi ATR cao (thị trường volatile): stop loss rộng hơn (ví dụ $1.5\% \times 2.0 = 3.0\%$)
  * Khi ATR thấp (thị trường ổn định): stop loss chặt hơn (ví dụ $1.5\% \times 0.7 = 1.05\%$)
* Config: `atr_period = 14`, `atr_adaptive_enabled = True` (mặc định: `volatility_adaptive = True`)

### 3. Short Stop Loss — DD5 High:
* **DD5 high** = Giá cao nhất ($H$) của ngày phân phối thứ 5 (ngày DD kích hoạt chuyển sang SELL).
* DD5 high được **lock** (cố định) vào engine khi chuyển sang trạng thái SELL.
* Mỗi phiên khi ở SELL, kiểm tra: $C > DD5_{high} \times (1 + short\_stop\_pct)$
* Mặc định: 1% trên DD5 high → $C > DD5_{high} \times 1.01$
* Khi kích hoạt: cover short, chuyển về **CASH**.
* **Thứ tự kiểm tra:** Short stop loss được kiểm tra **trước** FTD/cover signals mỗi phiên.
* Config: `short_stop_pct_above_dd5 = 0.01`

### 4. Bảng thông số Stop Loss cập nhật:

| Thông số | Giá trị cũ | Giá trị v4.0 | Mô tả |
| :--- | :---: | :---: | :--- |
| `stop_loss_pct` | 0.025 (2.5%) | **0.015 (1.5%)** | Phần trăm cắt lỗ long từ giá mua |
| `volatility_adaptive` | Không có | **True** | Bật/tắt ATR adaptive scaling |
| `atr_period` | Không có | **14** | Số phiên tính ATR |
| `short_stop_pct_above_dd5` | Không có | **0.01 (1%)** | Phần trăm trên DD5 high để cover short |
