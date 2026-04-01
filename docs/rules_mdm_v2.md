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

### 5. Chuyen CASH -> SELL (Thi truong xau di):

Neu khong co tin hieu mua, kiem tra 2 dieu kien chuyen sang SELL:

* **MA50 Breakdown** (khi `ma50_sell_enabled=True`):
  * Gia dong cua duoi MA50 ($C < MA50$).

* **Cash Deterioration** (Xuong cap do o CASH qua lau):
  * So ngay o trang thai CASH >= `cash_deterioration_days` (NASDAQ: 10, VN30: 20 ngay).

**Cong tang toc SELL (SELL Acceleration Gate, v5.0 SELL-01):**

Khi `sell_acceleration_enabled=True` (mac dinh), cac dieu kien tren chi duoc thuc hien khi **it nhat 1 dieu kien tang toc** duoc xac nhan (logic OR):

1. **Price ROC < threshold**: Ty le thay doi gia trong `roc_window` phien < `roc_threshold` (mac dinh: ROC 10 phien < -4%). Day la dau hieu dong luc giam manh.
2. **DD Clustering**: Co >= `dd_cluster_count` ngay phan phoi trong `dd_cluster_window` phien gan nhat (mac dinh: 3 DD trong 5 phien). Day la dau hieu to chuc ban ra tap trung.
3. **Volume-confirmed MA50 Breakdown**: Gia vuot xuong duoi MA50 (hom nay close < MA50, hom qua close >= MA50) VA khoi luong tang so voi phien truoc.

**Thu tu uu tien gate:** QE floor suppress > Acceleration gate > Trigger condition.
- Neu QE floor suppress = True -> SELL bi suppress (bat ke acceleration).
- Neu acceleration khong met -> SELL bi defer ("SELL deferred: no acceleration").
- Chi khi ca hai cho phep -> SELL duoc thuc hien.

**Thu tu uu tien trigger:** FTD > MA50 Breakout > 52-Week Breakout > MA50 Sell > Cash Deterioration.

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
| `stop_loss_pct` | 0.025 | Phần trăm cắt lỗ từ giá mua (2.5%) |
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
| `ma200_enabled` | False | Bật chế độ thay thế 200dma (v6.0 MAREVIEW-02) — xem Mục XIII |
| `name` | "default" | Tên giả thuyết (metadata) |

---

## IX. GHI CHÚ QUAN TRỌNG

1. **Vị thế SHORT khi SELL (v4.0):** Khi `short_mode = True` (mặc định), trạng thái SELL mở vị thế short thật sự. Khi `short_mode = False`, SELL chỉ là tín hiệu cảnh báo. Xem Mục X để biết chi tiết.

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

## XIV. BO LOC QE FLOOR - THANH KHOAN TOAN CAU (v5.0)

### 1. Tong quan

Bo loc QE Floor su dung du lieu thanh khoan toan cau (Fed + ECB + BOJ balance sheet) de suppress tin hieu SELL khi thanh khoan dang mo rong. Dua tren insight tu webinar 2013 cua Dr. K: khi cac ngan hang trung uong dang bom thanh khoan (QE), thi truong co "san" va kho giam manh -- do do tin hieu SELL it tin cay hon.

**Nguyen tac co ban:** Khi thanh khoan toan cau dang tang (qe_floor=1), cac chuyen doi CASH->SELL bi suppress. Tat ca cac chuyen doi khac (BUY->CASH, SELL->BUY, CASH->BUY) KHONG bi anh huong.

### 2. Nguon du lieu

File CSV tuan: `data/global_liquidity.csv`

| Cot | Mo ta |
| :--- | :--- |
| `date` | Ngay (Wednesday hang tuan) |
| `WALCL` | Fed balance sheet (triu USD) |
| `fed_net` | Fed net liquidity |
| `ECB_USD` | ECB balance sheet (quy doi USD) |
| `BOJ_USD` | BOJ balance sheet (quy doi USD) |
| `global_liquidity` | Tong thanh khoan = WALCL + ECB_USD + BOJ_USD |
| `liquidity_roc_20w` | Rate of change 20 tuan cua global_liquidity |
| `qe_floor` | 1 neu liquidity_roc_20w > 0 (dang mo rong), 0 neu khong |

Du lieu: 987 hang, tu 2007-05-02 den hien tai.

### 3. Publication lag (chong look-ahead bias)

Du lieu thanh khoan tuan duoc cong bo voi do tre. De tranh look-ahead bias, ngay thanh khoan duoc dich ve phia truoc `publication_lag_days` ngay (mac dinh 7 ngay = 1 tuan).

**Co che merge:** Su dung `pd.merge_asof(direction='backward')` de gan gia tri thanh khoan gan nhat da co cho moi ngay giao dich. Nhu vay, mot trader vao thu Hai se chi thay du lieu cua tuan truoc (hoac cu hon).

### 4. Hanh vi suppress SELL

Khi `qe_floor_enabled=True` va `qe_floor=1` (thanh khoan dang mo rong):

| Chuyen doi | Hanh vi | Ghi chu |
| :--- | :--- | :--- |
| CASH -> SELL (MA50 breakdown) | **SUPPRESS** | Giu trang thai CASH, ghi action "SELL suppressed: QE floor (MA50 breakdown)" |
| CASH -> SELL (cash deterioration) | **SUPPRESS** | Giu trang thai CASH, ghi action "SELL suppressed: QE floor (cash deterioration)" |
| BUY -> CASH (stop loss) | Khong anh huong | Tat ca exit rule van hoat dong binh thuong |
| BUY -> CASH (DD threshold) | Khong anh huong | |
| BUY -> CASH (MA10 exit) | Khong anh huong | |
| SELL -> BUY (FTD) | Khong anh huong | |
| CASH -> BUY (FTD) | Khong anh huong | |

**Implementation trong `position_manager.py`:**

```python
# Trong nhanh CASH state:
elif self.config.ma50_sell_enabled and ma50 is not None and close < ma50:
    if not suppress_sell:
        self.enter_sell(date, f"MA50 breakdown ...")
    else:
        action = "SELL suppressed: QE floor (MA50 breakdown)"
```

### 5. Xu ly du lieu truoc 2007 (pre-data period)

Cac ngay truoc khi du lieu thanh khoan bat dau (truoc 2007-05-02) nhan `qe_floor=0` (NaN duoc fill thanh 0). Dieu nay dam bao:
- Khong co false SELL suppression cho du lieu lich su (NASDAQ tu 1974)
- He thong chay binh thuong ma khong can dieu kien dac biet

### 6. Thong so cau hinh

| Thong so | Kieu | Mac dinh | Mo ta |
| :--- | :--- | :---: | :--- |
| `qe_floor_enabled` | bool | `False` | Cong tac chinh, mac dinh TAT de dam bao backward compatibility |
| `publication_lag_days` | int | `7` | So ngay dich du lieu thanh khoan ve phia truoc |
| `liquidity_csv_path` | str | `"data/global_liquidity.csv"` | Duong dan den file CSV thanh khoan tuan |

**Luu y:** Khi `qe_floor_enabled=False` (mac dinh), engine hoat dong hoan toan giong nhu truoc khi them QE floor -- khong co bat ky thay doi nao ve ket qua backtest.

### 7. Ghi chu ve so do chuyen trang thai (Section VII)

So do chuyen trang thai o Section VII can them annotation cho QE floor gate:

```
CASH -> SELL transitions:
  - MA50 breakdown     [QE Floor Gate: suppress khi qe_floor=1]
  - Cash deterioration  [QE Floor Gate: suppress khi qe_floor=1]

Tat ca cac chuyen doi khac: KHONG bi anh huong boi QE floor.
```

### 8. Su dung trong code

```python
from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine

# Bat QE floor filter
config = MDMV2Config(
    qe_floor_enabled=True,
    publication_lag_days=7,
    liquidity_csv_path="data/global_liquidity.csv",
)
engine = MDMV2Engine(config)
results = engine.run(df)

# Kiem tra suppress actions
suppressed = results[results['action'].str.contains('SELL suppressed', na=False)]
print(f"So SELL bi suppress: {len(suppressed)}")
```

---

## Co che Fail-Safe (SAFE-01, SAFE-02)

Co che fail-safe giam lo tu false SELL signal bang cach tu dong thoat SELL khi thi truong phuc hoi nhanh, theo dinh nghia cua Dr. K trong VOSI FAQ.

### 1. Nguyen ly hoat dong

Khi V2 engine phat SELL signal (tu MA50 breakdown hoac cash deterioration), he thong ghi nhan HIGH cua **standby-sell day** (ngay truoc sell signal day) lam `fail_safe_threshold`. Day la muc gia tham chieu de xac dinh thi truong da phuc hoi hay chua.

### 2. Quy tac chuyen trang thai (SAFE-02)

Trong trang thai SELL, moi ngay he thong kiem tra:
- Neu `close > fail_safe_threshold` -> tu dong chuyen ve **CASH** (fail-safe triggered)
- Neu `close <= fail_safe_threshold` -> giu nguyen trang thai SELL

**Thu tu uu tien:** Fail-safe check co uu tien **cao hon** FTD check trong trang thai SELL. Neu ca hai dieu kien deu thoa man (close > threshold VA co FTD), fail-safe se kich hoat truoc va chuyen ve CASH thay vi BUY.

### 3. Ghi nhan threshold (SAFE-01)

- `fail_safe_threshold` duoc ghi tu `prev_high` (HIGH cua ngay truoc khi SELL signal phat)
- Gia tri nay luu trong `V2Position.fail_safe_threshold`
- Duoc truyen qua `enter_sell(date, reason, fail_safe_threshold=prev_high)`

### 4. Trade record

Khi fail-safe trigger, he thong ghi trade voi:
- `type`: `FAIL_SAFE_EXIT`
- `reason`: `"Fail-safe: close {close} > standby-sell HIGH {threshold}"`
- `price`: gia close tai thoi diem trigger

### 5. Thong so cau hinh

| Thong so | Kieu | Mac dinh | Mo ta |
| :--- | :--- | :---: | :--- |
| `fail_safe_enabled` | bool | `True` | Cong tac bat/tat co che fail-safe |

Co the tat bang `fail_safe_enabled=False` trong config. Khi tat, SELL state hoat dong nhu truoc (chi FTD moi chuyen ve BUY).

### 6. Muc dich

- Giam lo tu false SELL signal khi thi truong phuc hoi nhanh
- Tranh giu SELL qua lau khi thi truong da reclaim muc gia truoc khi sell
- Dua tren dinh nghia "fail-safe" cua Dr. K: "standby-sell day HIGH" la nguong tham chieu

---

## XV. BUY ENTRY REFINEMENT (v6.0)

*Cap nhat v6.0: Hai co che loc tin hieu mua (buy entry filter) tu webinar Dr. K.*

### 1. Gap-Up Invalidation (GAP-01)

**Muc dich:** Loai bo tin hieu FTD gia khi gap-up bi pha (intraday low xuong duoi previous close).

**Dieu kien kich hoat:** `gap_filter_enabled = True` (mac dinh: True)

**Logic:**
* Chi ap dung cho tin hieu FTD classic. MA50 breakout va 52-week breakout **BYPASS** filter nay (per D-01).
* Gap-up bi pha khi: `signal_day_low < previous_day_close` (per D-02)
* Khong co margin/buffer -- so sanh truc tiep.

**Hanh dong:**
* Neu gap-up bi pha: `is_ftd = False`, `buy_rejected = True`
* Neu gap-up con nguyen (low >= prev_close): cho phep tin hieu FTD di tiep qua cac gate khac

**Thu tu gate:** Gate 0 (Gap filter) -> Gate 1 (MA10/MA50 filter) -> Gate 2 (Confirmation window)

### 2. Rally Threshold - Do Sau Dieu Chinh (RALLY-01, RALLY-02)

**Muc dich:** Cho phep FTD som hon khi thi truong chi giam nhe (< 6%), giu nguyen yeu cau day-3+ khi giam sau (>= 6%).

**Dieu kien kich hoat:** `rally_threshold_enabled = True` (mac dinh: True)

**Logic:**
* Su dung `drawdown_pct` (tinh tu `Indicators.drawdown_from_peak(close, rolling_high)`) -- KHONG thay doi `correction_threshold` (per D-03)
* Rally tracker van yeu cau `in_correction = True` (per D-05) -- 6% rule khong bypass correction detection
* `rally_threshold_pct = -0.06` (mac dinh)

**Hai truong hop:**

| Drawdown | Dieu kien | Hanh dong |
|----------|-----------|-----------|
| 0% den -6% (shallow pullback) | `drawdown_pct > rally_threshold_pct` | FTD co the trigger bat ky ngay nao (khong can rally_day >= 4) |
| >= -6% (deep correction) | `drawdown_pct <= rally_threshold_pct` | FTD yeu cau rally_day >= 4 (classic timing) |

**Xu ly Pitfall 2 (FTD Detector day-count):**
* Khi early FTD duoc cho phep va `rally_day < ftd_min_rally_day`: truyen `max(rally_day, ftd_min_rally_day)` vao `check_ftd()` de bypass internal min check, giu nguyen upper bound check.

### 3. Config Parameters

| Parameter | Type | Default | Mo ta |
|-----------|------|---------|-------|
| `gap_filter_enabled` | bool | True | Bat/tat gap-up invalidation |
| `rally_threshold_enabled` | bool | True | Bat/tat 6% rally threshold |
| `rally_threshold_pct` | float | -0.06 | Nguong phan biet shallow vs deep pullback |

---

## XVI. MA50/200DMA REVIEW (v6.0, MAREVIEW-01, MAREVIEW-02)

*Cap nhat v6.0: Them co che A/B test de danh gia vai tro cua MA50 va 200dma.*

### 1. Muc dich

Dr. K noi MA50/200dma co "little value" trong model hien tai. Phase nay A/B test cac ket hop:
- Tat MA50 SELL trigger
- Tat MA50 breakout BUY filter
- Thay the bang 200dma (SMA200)

### 2. Config Parameters

| Parameter | Type | Default | Mo ta |
|-----------|------|---------|-------|
| `ma50_breakout_enabled` | bool | True | Bat/tat MA50 breakout buy signal (True = hanh vi hien tai) |
| `ma200_enabled` | bool | False | Che do thay the 200dma (False = tat, mac dinh per v5.0) |

### 3. Chi bao SMA200

Phuong thuc `Indicators.add_sma200_column(df)` tinh trung binh dong 200 phien:

```python
df['sma200'] = df['close'].rolling(window=200, min_periods=1).mean()
```

Su dung `min_periods=1` de tranh NaN (tuong tu add_ma50_column). WARMUP_DAYS=300 trong validation scripts da du de warm up SMA200.

### 4. Wiring Logic (Plan 02)

**MA50 Breakout gating:**
- Khi `ma50_breakout_enabled=False`: engine khong goi `check_ma50_breakout()` -> tat hoan toan tin hieu MA50 breakout BUY.
- Khi `ma50_breakout_enabled=True` (mac dinh): hanh vi giu nguyen nhu truoc.

**200dma BUY signal (khi `ma200_enabled=True`):**
- Engine tinh `sma200` va `prev_sma200` columns.
- Check `check_200dma_breakout()`: C crosses above SMA200, volume up, drawdown >= 6%.
- Signal type: `"200DMA"`.
- Uu tien: FTD -> MA50 breakout (neu bat) -> 200dma breakout -> 52-week breakout.

**200dma SELL trigger (khi `ma200_enabled=True`):**
- CASH state: khi `close < sma200` (thay vi `close < ma50`).
- QE floor suppression va acceleration gate ap dung tuong tu MA50 SELL.
- Chi fires khi `ma50_sell_enabled=False` (vi logic elif chain).

**Backward compatibility:** Voi config mac dinh (`ma50_breakout_enabled=True, ma200_enabled=False`), tat ca hanh vi giu nguyen 100%.

**Thu tu uu tien SELL:** MA50 SELL (neu bat) -> 200dma SELL (neu bat) -> Cash Deterioration.

### 5. A/B validation (Plan 03)

- Script so sanh 5 scenarios: baseline, no-MA50-sell, no-MA50-breakout, no-MA50-all, 200dma-replace
- Metrics: total return, CAGR, MaxDD, Sharpe, win rate
