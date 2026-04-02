# BỘ QUY TẮC MÔ HÌNH MDM V2 - MÁY TRẠNG THÁI 3 BƯỚC (BUY/CASH/SELL)

## I. TỔNG QUAN

MDM V2 là phiên bản cải tiến của MDM Classic, thay đổi từ máy trạng thái 4 bước (CASH/HOLDING/WAITING_SELL/SHORT) thành máy trạng thái 3 bước đơn giản hơn:

| Trạng thái | Mô tả |
| :--- | :--- |
| **CASH** | Không giữ vị thế, chờ tín hiệu mua |
| **BUY** | Đang giữ vị thế Long (mua) |
| **SELL** | Đang giữ vị thế Short (bán khống) — lời khi thị trường giảm, lỗ khi tăng |

**Cải tiến chính so với Classic:**
- SELL = vị thế short thật sự (theo Dr. K: dùng SQQQ/UVXY trên US, short trực tiếp trên VN30)
- Thêm cơ chế chuyển CASH -> SELL khi thị trường xấu đi (MA50 breakdown hoặc ở CASH quá lâu)
- Thêm điều kiện thoát BUY -> CASH qua MA10 (đóng cửa dưới MA10 nhiều phiên liên tiếp)
- Enforce SELL -> CASH -> BUY (phải cover short trước khi mua)
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

* **Cash Deterioration** (Xuống cấp do ở CASH quá lâu):
  * Số ngày ở trạng thái CASH >= `cash_deterioration_days` (NASDAQ: 10, VN30: 20 ngày).

**Cổng tăng tốc SELL (SELL Acceleration Gate, v5.0 SELL-01):**

Khi `sell_acceleration_enabled=True` (mặc định), các điều kiện trên chỉ được thực hiện khi **ít nhất 1 điều kiện tăng tốc** được xác nhận (logic OR):

1. **Price ROC < threshold**: Tỷ lệ thay đổi giá trong `roc_window` phiên < `roc_threshold` (mặc định: ROC 10 phiên < -4%). Đây là dấu hiệu động lực giảm mạnh.
2. **DD Clustering**: Có >= `dd_cluster_count` ngày phân phối trong `dd_cluster_window` phiên gần nhất (mặc định: 3 DD trong 5 phiên). Đây là dấu hiệu tổ chức bán ra tập trung.
3. **Volume-confirmed MA50 Breakdown**: Giá vượt xuống dưới MA50 (hôm nay close < MA50, hôm qua close >= MA50) VÀ khối lượng tăng so với phiên trước.

**Thứ tự ưu tiên gate:** QE floor suppress > Acceleration gate > Trigger condition.
- Nếu QE floor suppress = True -> SELL bị suppress (bất kể acceleration).
- Nếu acceleration không met -> SELL bị defer ("SELL deferred: no acceleration").
- Chỉ khi cả hai cho phép -> SELL được thực hiện.

**Thứ tự ưu tiên trigger:** FTD > MA50 Breakout > 52-Week Breakout > MA50 Sell > Cash Deterioration.

### 6. Bộ lọc BUY Selectivity (v5.0, BUY-01, BUY-02)

Hai bộ lọc được áp dụng CHỈ cho tín hiệu FTD cổ điển. MA50 breakout và 52-week breakout bỏ qua cả hai bộ lọc và vào BUY ngay lập tức.

#### 6a. Lọc xu hướng MA10/MA50 (BUY-01)

**Điều kiện từ chối:** FTD bị từ chối khi MA10 < MA50 tại thời điểm FTD.

* **Lý do:** Khi MA10 < MA50, xu hướng ngắn hạn yếu hơn xu hướng trung hạn, cho thấy market chưa xác nhận đảo chiều.
* **Bật/tắt:** `buy_filter_enabled` (mặc định: True)
* **Công thức:** Cho phép FTD khi $MA_{10} \geq MA_{50}$

#### 6b. Cửa sổ xác nhận sau FTD (BUY-02)

**Cơ chế:** Sau khi FTD vượt qua bộ lọc MA10/MA50, engine chờ thêm N ngày giao dịch trước khi vào BUY.

* **Số ngày chờ:** `confirmation_window_days` (mặc định: 3 ngày)
* **Điều kiện hủy:** FTD bị hủy nếu có > `confirmation_max_dd` Distribution Days trong cửa sổ (mặc định: > 1 DD, tức là 2+ DD hủy FTD)
* **Giá vào lệnh:** Giá đóng cửa của ngày xác nhận (ngày thứ 3), KHÔNG phải giá ngày FTD
* **Trạng thái trong cửa sổ:** Engine giữ trạng thái CASH, không mở vị thế
* **Bật/tắt:** `buy_confirmation_enabled` (mặc định: True)

**Quy trình:**
1. FTD cổ điển phát hiện -> kiểm tra MA10 >= MA50
2. Nếu pass -> bắt đầu cửa sổ xác nhận (3 ngày)
3. Mỗi ngày trong cửa sổ: đếm Distribution Days (side-effect-free, không ảnh hưởng DD counter chính)
4. Nếu DD count > 1 -> hủy FTD, quay lại chờ tín hiệu mới
5. Nếu 3 ngày pass (0-1 DD) -> xác nhận BUY, vào lệnh tại giá đóng cửa ngày 3

**Tương tác với tín hiệu khác:**
* MA50 breakout hoặc 52-week breakout trong cửa sổ xác nhận -> hủy cửa sổ, vào BUY ngay
* SELL transition trong cửa sổ -> hủy pending FTD

#### Cấu hình BUY Selectivity

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `buy_filter_enabled` | True | Bật lọc MA10/MA50 |
| `buy_confirmation_enabled` | True | Bật cửa sổ xác nhận |
| `confirmation_window_days` | 3 | Số ngày chờ xác nhận |
| `confirmation_max_dd` | 1 | Số DD tối đa cho phép trong cửa sổ |

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
* Giá đóng cửa dưới MA10 trong `ma10_cash_consecutive` phiên liên tiếp (NASDAQ: 2, VN30: 3 phiên).
* Bộ đếm reset về 0 khi giá đóng cửa trên MA10.
* -> Chuyển sang CASH, ghi nhận P&L.

**Thứ tự ưu tiên:** Stop Loss > DD Threshold > MA10 Below.

---

## V. QUY TẮC CẮT LỖ (STOP LOSS)

Chỉ áp dụng khi đang ở trạng thái BUY. Short stop loss xem Mục XII.

### 1. Cắt lỗ theo phần trăm (Rule 1):
* Giá đóng cửa giảm quá `stop_loss_pct` từ giá mua.
* Mặc định: $C < P_{buy} \times (1 - 0.015)$ (giảm 1.5%, cập nhật v4.0 — xem Mục XII).

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

**CASH -> SELL transitions (v5.0 update):**

CASH -> SELL transitions now require acceleration gate confirmation:
  - MA50 breakdown: C < MA50 AND acceleration_met AND NOT suppress_sell
  - Cash deterioration: days_in_cash >= threshold AND acceleration_met AND NOT suppress_sell

Where `acceleration_met` = at least one of: Price ROC < -4%, DD clustering (3 in 5), volume-confirmed MA50 breakdown.

---

## VIII. BẢNG THÔNG SỐ CẤU HÌNH (MDMV2Config)

| Thông số | Giá trị mặc định | Mô tả |
| :--- | :---: | :--- |
| `correction_threshold` | -0.10 (NASDAQ) / **-0.06 (VN30)** | Ngưỡng giảm từ đỉnh để xác nhận điều chỉnh |
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
| `ma10_cash_consecutive` | 2 (NASDAQ) / **3 (VN30)** | Số phiên liên tiếp dưới MA10 để kích hoạt |
| `ma50_sell_enabled` | True | Bật/tắt MA50 breakdown cho CASH -> SELL |
| `cash_deterioration_days` | 10 (NASDAQ) / **20 (VN30)** | Số ngày ở CASH trước khi tự động chuyển SELL |
| `stop_loss_pct` | 0.015 | Phần trăm cắt lỗ từ giá mua (1.5%, cập nhật v4.0) |
| `sell_acceleration_enabled` | True | Bat/tat cong tang toc SELL (v5.0 SELL-01) |
| `roc_threshold` | -0.04 | Nguong ROC cho dieu kien tang toc (mac dinh -4%) |
| `roc_window` | 10 | So phien tinh ROC (mac dinh 10 phien) |
| `dd_cluster_count` | 3 | So DD toi thieu cho dieu kien clustering |
| `dd_cluster_window` | 5 | Cua so phien cho DD clustering |
| `buy_filter_enabled` | True | Bật lọc MA10/MA50 cho FTD (v5.0 BUY-01) |
| `buy_confirmation_enabled` | True | Bật cửa sổ xác nhận sau FTD (v5.0 BUY-02) |
| `confirmation_window_days` | 3 | Số ngày chờ xác nhận sau FTD |
| `confirmation_max_dd` | 1 | Số DD tối đa cho phép trong cửa sổ xác nhận |
| `ma50_breakout_enabled` | True | Bật/tắt tín hiệu mua MA50 breakout (v6.0 MAREVIEW-01) |
| `ma200_enabled` | False | Bật chế độ thay thế 200dma (v6.0 MAREVIEW-02) — xem Mục XVI |
| `fail_safe_enabled` | True | Bật/tắt cơ chế fail-safe auto-exit SELL (v6.0 SAFE-01) |
| `gap_filter_enabled` | True | Reject FTD khi gap-up bị phá (v6.0 GAP-01) — xem Mục XV |
| `rally_threshold_enabled` | True | Cho phép FTD sớm khi giảm nông < 6% (v6.0 RALLY-01) — xem Mục XV |
| `rally_threshold_pct` | -0.06 | Ngưỡng phân biệt shallow vs deep pullback |
| `volatility_filter_enabled` | False | Bật/tắt bộ lọc biến động ATR (v6.0 BAND-01) — xem Mục XII (Volatility) |
| `volatility_low_threshold` | 1.04 | ATR% dưới mức này = low volatility (P25 VN30) |
| `volatility_high_threshold` | 1.73 | ATR% trên mức này = high volatility (P75 VN30) |
| `atr_period` | 14 | Số phiên tính ATR (dùng cho cả volatility filter và adaptive stop loss) |
| `short_stop_pct_above_dd5` | 0.01 | Phần trăm trên DD5 high để cover short (v4.0) — xem Mục XII |
| `volatility_adaptive` | True | Bật/tắt ATR adaptive stop loss scaling (v4.0) — xem Mục XII |
| `atr_baseline_period` | 50 | Số phiên baseline cho ATR adaptive ratio |
| `stop_loss_min_multiplier` | 0.5 | Hệ số nhân tối thiểu cho adaptive stop loss |
| `stop_loss_max_multiplier` | 2.5 | Hệ số nhân tối đa cho adaptive stop loss |
| `name` | "default" | Tên giả thuyết (metadata) |

---

## IX. GHI CHÚ QUAN TRỌNG

1. **Vị thế SHORT khi SELL (v4.0):** Trạng thái SELL luôn mở vị thế short thật sự trong V2 engine. Equity curve tính inverse return khi ở SELL (xem Mục X). Dùng `long_only_equity=True` trong `V2PerformanceAnalyzer` nếu muốn bỏ qua short P&L.

2. **DD chỉ đếm khi BUY:** Ngày phân phối chỉ được đếm khi đang ở trạng thái BUY. Khi ở CASH hoặc SELL, bộ đếm DD không hoạt động.

3. **FTD reset rally tracker:** Sau khi phát hiện FTD, rally tracker được reset hoàn toàn (`full_reset`), bao gồm cả trạng thái điều chỉnh và đỉnh.

4. **Rally tracking ở cả CASH và SELL:** Cả hai trạng thái CASH và SELL đều theo dõi rally attempt để phát hiện FTD.

5. **Thứ tự ưu tiên tín hiệu mua:** FTD truyền thống -> MA50 breakout -> 52-Week breakout. Chỉ tín hiệu đầu tiên được chấp nhận.

6. **Stop loss:** Long stop loss dùng ATR-adaptive (mặc định 1.5%). Short stop loss dùng DD5 high + 1%. Xem Mục XII.

7. **DD day là điều kiện cần:** Chuyển BUY -> CASH do DD chỉ xảy ra khi ngày hiện tại cũng là ngày phân phối (không phải bất cứ ngày nào có dd_count >= threshold).

8. **Equity curve — Tránh Look-Ahead Bias:** Phải dùng `state[i-1]` (state hôm qua) để tính return ngày `i`. Dùng `state[i]` sẽ tạo look-ahead bias nghiêm trọng (xem Mục X).

---

## X. VỊ THẾ SHORT (BÁN KHỐNG)

*Cập nhật v4.0: MDM V2 hỗ trợ vị thế short thật sự khi ở trạng thái SELL (theo Dr. K webinar — SELL = short thật, dùng SQQQ/UVXY trên US market, short trực tiếp chỉ số trên VN30).*

### 1. Mở vị thế Short:
* Khi engine chuyển sang trạng thái **SELL**, vị thế short được mở tự động.
* **Giá entry** = Giá đóng cửa phiên chuyển sang SELL.
* V2 engine luôn mở short khi SELL. Dùng `long_only_equity=True` trong analyzer nếu muốn tính equity không short.

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
* Khi `long_only_equity = True` trong analyzer: equity giữ nguyên (flat) khi ở SELL.

**Quy tắc quan trọng — Tránh Look-Ahead Bias:**
* Equity curve **phải** dùng trạng thái ngày hôm trước (`state[i-1]`) để quyết định return ngày hôm nay (`i`).
* **Sai:** `if state[i] == 'BUY': capture return[i]` — nhìn trước signal hôm nay.
* **Đúng:** `if state[i-1] == 'BUY': capture return[i]` — quyết định dựa trên signal đã có từ hôm qua.
* Lý do: signal phát ra cuối ngày (dựa trên close), return được tính từ ngày hôm sau.

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
CASH -> BUY    : FTD (qua Gap filter + MA filter + Confirmation), MA50 breakout, 52-week breakout
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
* Config: `atr_period = 14`, `volatility_adaptive = True` (mặc định)

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

---

## XIII. THÔNG SỐ THEO THỊ TRƯỜNG (Market-Specific Presets)

*Cập nhật v4.0: Các thông số mặc định được calibrate cho NASDAQ. VN30 cần preset riêng do đặc điểm thị trường khác biệt (biên độ 7%, T+2.5, thanh khoản thấp hơn).*

### 1. Bảng so sánh NASDAQ vs VN30 preset:

| Thông số | NASDAQ (mặc định) | VN30 (optimized) | Lý do thay đổi |
| :--- | :---: | :---: | :--- |
| `correction_threshold` | -0.10 (10%) | **-0.06 (6%)** | VN30 corrections nông hơn, -10% hiếm khi xảy ra |
| `ma10_cash_consecutive` | 2 | **3** | VN30 biến động mạnh hơn, 2 ngày dưới MA10 tạo quá nhiều whipsaw |
| `cash_deterioration_days` | 10 | **20** | Giảm thời gian SELL (short), VN30 uptrend dài hạn nên short dễ lỗ |
| Các thông số khác | Giữ nguyên | Giữ nguyên | Không cần thay đổi |

### 2. Kết quả backtest VN30 (2015-2026):

| Config | Tổng lợi nhuận | CAGR | MaxDD |
| :--- | :---: | :---: | :---: |
| NASDAQ preset (mặc định) | +113% | 7.0% | -32.4% |
| **VN30 preset (optimized)** | **+191%** | **10.0%** | **-31.8%** |
| Mua & Nắm giữ | +204% | 10.4% | -48.1% |

### 3. Sử dụng trong code:

```python
from strategies.mdm_hybrid.config import VN30_PRESET, NASDAQ_PRESET, HybridConfig

# VN30
config = HybridConfig(v2_config=VN30_PRESET, ...)

# NASDAQ
config = HybridConfig(v2_config=NASDAQ_PRESET, ...)
```

---

## XIV. BỘ LỌC QE FLOOR - THANH KHOẢN TOÀN CẦU (v5.0)

### 1. Tổng quan

Bộ lọc QE Floor sử dụng dữ liệu thanh khoản toàn cầu (Fed + ECB + BOJ balance sheet) để suppress tín hiệu SELL khi thanh khoản đang mở rộng. Dựa trên insight từ webinar 2013 của Dr. K: khi các ngân hàng trung ương đang bơm thanh khoản (QE), thị trường có "sàn" và khó giảm mạnh -- do đó tín hiệu SELL ít tin cậy hơn.

**Nguyên tắc cơ bản:** Khi thanh khoản toàn cầu đang tăng (qe_floor=1), các chuyển đổi CASH->SELL bị suppress. Tất cả các chuyển đổi khác (BUY->CASH, SELL->BUY, CASH->BUY) KHÔNG bị ảnh hưởng.

### 2. Nguồn dữ liệu

File CSV tuần: `data/global_liquidity.csv`

| Cột | Mô tả |
| :--- | :--- |
| `date` | Ngày (Wednesday hàng tuần) |
| `WALCL` | Fed balance sheet (triệu USD) |
| `fed_net` | Fed net liquidity |
| `ECB_USD` | ECB balance sheet (quy đổi USD) |
| `BOJ_USD` | BOJ balance sheet (quy đổi USD) |
| `global_liquidity` | Tổng thanh khoản = WALCL + ECB_USD + BOJ_USD |
| `liquidity_roc_20w` | Rate of change 20 tuần của global_liquidity |
| `qe_floor` | 1 nếu liquidity_roc_20w > 0 (đang mở rộng), 0 nếu không |

Dữ liệu: 987 hàng, từ 2007-05-02 đến hiện tại.

### 3. Publication lag (chống look-ahead bias)

Dữ liệu thanh khoản tuần được công bố với độ trễ. Để tránh look-ahead bias, ngày thanh khoản được dịch về phía trước `publication_lag_days` ngày (mặc định 7 ngày = 1 tuần).

**Cơ chế merge:** Sử dụng `pd.merge_asof(direction='backward')` để gán giá trị thanh khoản gần nhất đã có cho mỗi ngày giao dịch. Như vậy, một trader vào thứ Hai sẽ chỉ thấy dữ liệu của tuần trước (hoặc cũ hơn).

### 4. Hành vi suppress SELL

Khi `qe_floor_enabled=True` và `qe_floor=1` (thanh khoản đang mở rộng):

| Chuyển đổi | Hành vi | Ghi chú |
| :--- | :--- | :--- |
| CASH -> SELL (MA50 breakdown) | **SUPPRESS** | Giữ trạng thái CASH, ghi action "SELL suppressed: QE floor (MA50 breakdown)" |
| CASH -> SELL (cash deterioration) | **SUPPRESS** | Giữ trạng thái CASH, ghi action "SELL suppressed: QE floor (cash deterioration)" |
| BUY -> CASH (stop loss) | Không ảnh hưởng | Tất cả exit rule vẫn hoạt động bình thường |
| BUY -> CASH (DD threshold) | Không ảnh hưởng | |
| BUY -> CASH (MA10 exit) | Không ảnh hưởng | |
| SELL -> BUY (FTD) | Không ảnh hưởng | |
| CASH -> BUY (FTD) | Không ảnh hưởng | |

**Implementation trong `position_manager.py`:**

```python
# Trong nhánh CASH state:
elif self.config.ma50_sell_enabled and ma50 is not None and close < ma50:
    if not suppress_sell:
        self.enter_sell(date, f"MA50 breakdown ...")
    else:
        action = "SELL suppressed: QE floor (MA50 breakdown)"
```

### 5. Xử lý dữ liệu trước 2007 (pre-data period)

Các ngày trước khi dữ liệu thanh khoản bắt đầu (trước 2007-05-02) nhận `qe_floor=0` (NaN được fill thành 0). Điều này đảm bảo:
- Không có false SELL suppression cho dữ liệu lịch sử (NASDAQ từ 1974)
- Hệ thống chạy bình thường mà không cần điều kiện đặc biệt

### 6. Thông số cấu hình

| Thông số | Kiểu | Mặc định | Mô tả |
| :--- | :--- | :---: | :--- |
| `qe_floor_enabled` | bool | `False` | Công tắc chính, mặc định TẮT để đảm bảo backward compatibility |
| `publication_lag_days` | int | `7` | Số ngày dịch dữ liệu thanh khoản về phía trước |
| `liquidity_csv_path` | str | `"data/global_liquidity.csv"` | Đường dẫn đến file CSV thanh khoản tuần |

**Lưu ý:** Khi `qe_floor_enabled=False` (mặc định), engine hoạt động hoàn toàn giống như trước khi thêm QE floor -- không có bất kỳ thay đổi nào về kết quả backtest.

### 7. Ghi chú về sơ đồ chuyển trạng thái (Section VII)

Sơ đồ chuyển trạng thái ở Section VII cần thêm annotation cho QE floor gate:

```
CASH -> SELL transitions:
  - MA50 breakdown     [QE Floor Gate: suppress khi qe_floor=1]
  - Cash deterioration  [QE Floor Gate: suppress khi qe_floor=1]

Tất cả các chuyển đổi khác: KHÔNG bị ảnh hưởng bởi QE floor.
```

### 8. Sử dụng trong code

```python
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine

# Bật QE floor filter
config = MDMV2Config(
    qe_floor_enabled=True,
    publication_lag_days=7,
    liquidity_csv_path="data/global_liquidity.csv",
)
engine = MDMV2Engine(config)
results = engine.run(df)

# Kiểm tra suppress actions
suppressed = results[results['action'].str.contains('SELL suppressed', na=False)]
print(f"Số SELL bị suppress: {len(suppressed)}")
```

---

## Cơ chế Fail-Safe (SAFE-01, SAFE-02)

Cơ chế fail-safe giảm lỗ từ false SELL signal bằng cách tự động thoát SELL khi thị trường phục hồi nhanh, theo định nghĩa của Dr. K trong VOSI FAQ.

### 1. Nguyên lý hoạt động

Khi V2 engine phát SELL signal (từ MA50 breakdown hoặc cash deterioration), hệ thống ghi nhận HIGH của **standby-sell day** (ngày trước sell signal day) làm `fail_safe_threshold`. Đây là mức giá tham chiếu để xác định thị trường đã phục hồi hay chưa.

### 2. Quy tắc chuyển trạng thái (SAFE-02)

Trong trạng thái SELL, mỗi ngày hệ thống kiểm tra:
- Nếu `close > fail_safe_threshold` -> tự động chuyển về **CASH** (fail-safe triggered)
- Nếu `close <= fail_safe_threshold` -> giữ nguyên trạng thái SELL

**Thứ tự ưu tiên:** Fail-safe check có ưu tiên **cao hơn** FTD check trong trạng thái SELL. Nếu cả hai điều kiện đều thỏa mãn (close > threshold VÀ có FTD), fail-safe sẽ kích hoạt trước và chuyển về CASH thay vì BUY.

### 3. Ghi nhận threshold (SAFE-01)

- `fail_safe_threshold` được ghi từ `prev_high` (HIGH của ngày trước khi SELL signal phát)
- Giá trị này lưu trong `V2Position.fail_safe_threshold`
- Được truyền qua `enter_sell(date, reason, fail_safe_threshold=prev_high)`

### 4. Trade record

Khi fail-safe trigger, hệ thống ghi trade với:
- `type`: `FAIL_SAFE_EXIT`
- `reason`: `"Fail-safe: close {close} > standby-sell HIGH {threshold}"`
- `price`: giá close tại thời điểm trigger

### 5. Thông số cấu hình

| Thông số | Kiểu | Mặc định | Mô tả |
| :--- | :--- | :---: | :--- |
| `fail_safe_enabled` | bool | `True` | Công tắc bật/tắt cơ chế fail-safe |

Có thể tắt bằng `fail_safe_enabled=False` trong config. Khi tắt, SELL state hoạt động như trước (chỉ FTD mới chuyển về BUY).

### 6. Mục đích

- Giảm lỗ từ false SELL signal khi thị trường phục hồi nhanh
- Tránh giữ SELL quá lâu khi thị trường đã reclaim mức giá trước khi sell
- Dựa trên định nghĩa "fail-safe" của Dr. K: "standby-sell day HIGH" là ngưỡng tham chiếu

---

## XV. BUY ENTRY REFINEMENT (v6.0)

*Cập nhật v6.0: Hai cơ chế lọc tín hiệu mua (buy entry filter) từ webinar Dr. K.*

### 1. Gap-Up Invalidation (GAP-01)

**Mục đích:** Loại bỏ tín hiệu FTD giả khi gap-up bị phá (intraday low xuống dưới previous close).

**Điều kiện kích hoạt:** `gap_filter_enabled = True` (mặc định: True)

**Logic:**
* Chỉ áp dụng cho tín hiệu FTD classic. MA50 breakout và 52-week breakout **BYPASS** filter này (per D-01).
* Gap-up bị phá khi: `signal_day_low < previous_day_close` (per D-02)
* Không có margin/buffer -- so sánh trực tiếp.

**Hành động:**
* Nếu gap-up bị phá: `is_ftd = False`, `buy_rejected = True`
* Nếu gap-up còn nguyên (low >= prev_close): cho phép tín hiệu FTD đi tiếp qua các gate khác

**Thứ tự gate:** Gate 0 (Gap filter) -> Gate 1 (MA10/MA50 filter) -> Gate 2 (Confirmation window)

### 2. Rally Threshold - Độ Sâu Điều Chỉnh (RALLY-01, RALLY-02)

**Mục đích:** Cho phép FTD sớm hơn khi thị trường chỉ giảm nhẹ (< 6%), giữ nguyên yêu cầu day-3+ khi giảm sâu (>= 6%).

**Điều kiện kích hoạt:** `rally_threshold_enabled = True` (mặc định: True)

**Logic:**
* Sử dụng `drawdown_pct` (tính từ `Indicators.drawdown_from_peak(close, rolling_high)`) -- KHÔNG thay đổi `correction_threshold` (per D-03)
* Rally tracker vẫn yêu cầu `in_correction = True` (per D-05) -- 6% rule không bypass correction detection
* `rally_threshold_pct = -0.06` (mặc định)

**Hai trường hợp:**

| Drawdown | Điều kiện | Hành động |
|----------|-----------|-----------|
| 0% đến -6% (shallow pullback) | `drawdown_pct > rally_threshold_pct` | FTD có thể trigger bất kỳ ngày nào (không cần rally_day >= 4) |
| >= -6% (deep correction) | `drawdown_pct <= rally_threshold_pct` | FTD yêu cầu rally_day >= 4 (classic timing) |

**Xử lý Pitfall 2 (FTD Detector day-count):**
* Khi early FTD được cho phép và `rally_day < ftd_min_rally_day`: truyền `max(rally_day, ftd_min_rally_day)` vào `check_ftd()` để bypass internal min check, giữ nguyên upper bound check.

### 3. Thông số cấu hình

| Thông số | Kiểu | Mặc định | Mô tả |
|-----------|------|---------|-------|
| `gap_filter_enabled` | bool | True | Bật/tắt gap-up invalidation |
| `rally_threshold_enabled` | bool | True | Bật/tắt 6% rally threshold |
| `rally_threshold_pct` | float | -0.06 | Ngưỡng phân biệt shallow vs deep pullback |

---

## XVI. MA50/200DMA REVIEW (v6.0, MAREVIEW-01, MAREVIEW-02)

*Cập nhật v6.0: Thêm cơ chế A/B test để đánh giá vai trò của MA50 và 200dma.*

### 1. Mục đích

Dr. K nói MA50/200dma có "little value" trong model hiện tại. Phase này A/B test các kết hợp:
- Tắt MA50 SELL trigger
- Tắt MA50 breakout BUY filter
- Thay thế bằng 200dma (SMA200)

### 2. Thông số cấu hình

| Thông số | Kiểu | Mặc định | Mô tả |
|-----------|------|---------|-------|
| `ma50_breakout_enabled` | bool | True | Bật/tắt MA50 breakout buy signal (True = hành vi hiện tại) |
| `ma200_enabled` | bool | False | Chế độ thay thế 200dma (False = tắt, mặc định per v5.0) |

### 3. Chỉ báo SMA200

Phương thức `Indicators.add_sma200_column(df)` tính trung bình động 200 phiên:

```python
df['sma200'] = df['close'].rolling(window=200, min_periods=1).mean()
```

Sử dụng `min_periods=1` để tránh NaN (tương tự add_ma50_column). WARMUP_DAYS=300 trong validation scripts đã đủ để warm up SMA200.

### 4. Wiring Logic (Plan 02)

**MA50 Breakout gating:**
- Khi `ma50_breakout_enabled=False`: engine không gọi `check_ma50_breakout()` -> tắt hoàn toàn tín hiệu MA50 breakout BUY.
- Khi `ma50_breakout_enabled=True` (mặc định): hành vi giữ nguyên như trước.

**200dma BUY signal (khi `ma200_enabled=True`):**
- Engine tính `sma200` và `prev_sma200` columns.
- Check `check_200dma_breakout()`: C crosses above SMA200, volume up, drawdown >= 6%.
- Signal type: `"200DMA"`.
- Ưu tiên: FTD -> MA50 breakout (nếu bật) -> 200dma breakout -> 52-week breakout.

**200dma SELL trigger (khi `ma200_enabled=True`):**
- CASH state: khi `close < sma200` (thay vì `close < ma50`).
- QE floor suppression và acceleration gate áp dụng tương tự MA50 SELL.
- Chỉ fires khi `ma50_sell_enabled=False` (vì logic elif chain).

**Backward compatibility:** Với config mặc định (`ma50_breakout_enabled=True, ma200_enabled=False`), tất cả hành vi giữ nguyên 100%.

**Thứ tự ưu tiên SELL:** MA50 SELL (nếu bật) -> 200dma SELL (nếu bật) -> Cash Deterioration.

### 5. A/B validation (Plan 03)

- Script so sánh 5 scenarios: baseline, no-MA50-sell, no-MA50-breakout, no-MA50-all, 200dma-replace
- Metrics: total return, CAGR, MaxDD, Sharpe, win rate

### Kết quả MA50/200dma Review (Phase 25)

*Kết quả thực tế từ `analysis/validate_ma50_review.py` trên VN30 2018-2026.*

#### 5 scenarios được test

| Scenario | Mô tả |
|----------|-------|
| 1_baseline | Tất cả MA50 bật: ma50_sell=True, buy_filter=True, ma50_breakout=True, ma200=False |
| 2_no_ma50_sell | Chỉ tắt MA50 SELL trigger (ma50_sell=False), giữ buy_filter và breakout |
| 3_no_buy_filter | Chỉ tắt MA10<MA50 buy filter, giữ MA50 SELL và breakout |
| 4_no_ma50_all | Tắt toàn bộ MA50: sell=False, buy_filter=False, breakout=False, ma200=False |
| 5_200dma_replace | Tắt toàn bộ MA50 + bật 200dma thay thế (ma200=True) |

Tất cả scenarios giữ nguyên: sell_acceleration=True, buy_confirmation=True, fail_safe=True, gap_filter=True, rally_threshold=True, rally_threshold_pct=-0.06.

#### Kết quả so sánh (VN30 2018-2026)

```
Scenario                   Return      MaxDD   Sharpe   Trades    WinRate
-------------------------------------------------------------------------
1_baseline                  52.8%     -47.9%    0.34       75      28.0%
2_no_ma50_sell              91.2%     -40.5%    0.50       67      31.3%
3_no_buy_filter             29.6%     -46.7%    0.25       88      33.0%
4_no_ma50_all               47.8%     -34.2%    0.35       74      29.7%
5_200dma_replace            37.7%     -34.8%    0.29       76      30.3%
```

#### MAREVIEW-03: Khuyến nghị

**KHUYẾN NGHỊ: LOẠI BỎ MA50 khỏi logic tín hiệu.**

Bằng chứng:
- `4_no_ma50_all` (Sharpe=0.35) > `1_baseline` (Sharpe=0.34) > `5_200dma_replace` (Sharpe=0.29)
- Loại bỏ toàn bộ MA50 cải thiện risk-adjusted returns: Sharpe 0.34 -> 0.35, MaxDD -47.9% -> -34.2%
- `2_no_ma50_sell` có Sharpe cao nhất (0.50) và return (+91.2%), cho thấy MA50 SELL trigger là nguyên nhân chính kéo giảm hiệu suất
- SELL fallback về cash_deterioration_days (per D-04)

**Chi tiết theo từng vai trò MA50:**
- MA50 SELL trigger: loại bỏ cải thiện mạnh (Sharpe 0.34->0.50, return +38.4%)
- MA10<MA50 buy filter: giữ nguyên có lợi (loại bỏ làm giảm return -23.2%, Sharpe xuống 0.25)
- MA50 breakout buy signal: neutral (loại bỏ ít ảnh hưởng, included in 4_no_ma50_all)

**Điều chỉnh trong Phase 27 (combined validation):**
- Thay đổi này chưa được áp dụng vào default config
- Khi tích hợp, cần xem xét: tắt ma50_sell_enabled=False, giữ buy_filter_enabled=True (buy filter có giá trị)
- 4_no_ma50_all Sharpe cao hơn baseline nhưng 2_no_ma50_sell (Sharpe=0.50) cho thấy tắt MA50 SELL là quan trọng nhất

**Lưu ý phạm vi:** Stop loss Rule 3 và sell acceleration gate vẫn sử dụng MA50 bất kể scenario.
Đây là đúng per phase scope -- đây là các concern riêng biệt.

---

## XII. VOLATILITY FILTER (BANDING)

**Source:** Dr. K's "banding width" concept -- when the market trades in a narrow band, signals are unreliable.

**Mechanism:**
- ATR-14 is computed as percentage of close price (ATR%) for each trading day
- Volatility regime classification: low (ATR% < 1.04%), normal (1.04-1.73%), high (>= 1.73%)
- Thresholds calibrated to VN30's historical ATR distribution (P25=1.04%, P75=1.73%)

**Signal Suppression:**
- When regime = low: both BUY entries and CASH->SELL transitions are suppressed
- Engine stays in current state until volatility returns to normal/high
- Stop loss exits (BUY->CASH) are NEVER suppressed -- protective exits always active
- Fail-safe exits (SELL->CASH) are NEVER suppressed -- safety mechanism always active

**Config:**
- `volatility_filter_enabled`: Master switch (default OFF)
- `volatility_low_threshold`: ATR% boundary for low regime (default 1.04)
- `volatility_high_threshold`: ATR% boundary for high regime (default 1.73, informational)
- `atr_period`: ATR lookback window (default 14)

**A/B Validation Results (VN30 2011-2026):**

| Period | Baseline transitions | Filtered transitions | Reduction |
| :--- | ---: | ---: | ---: |
| 2019 Apr-Sep (low vol) | 14 | 3 | 78.6% |
| 2025 Q1 (low vol) | 10 | 5 | 50.0% |

Trending period trade timing (2020 crash, 2021 rally) remains identical between baseline and filtered variants.

**Note:** Filter is default OFF. When Phase 27 integrates all v6.0 features, volatility filter will be evaluated in combination with other signal refinements.
