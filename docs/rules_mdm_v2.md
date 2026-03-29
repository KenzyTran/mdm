# BO QUY TAC MO HINH MDM V2 - MAY TRANG THAI 3 BUOC (BUY/CASH/SELL)

## I. TONG QUAN

MDM V2 la phien ban cai tien cua MDM Classic, thay doi tu may trang thai 4 buoc (CASH/HOLDING/WAITING_SELL/SHORT) thanh may trang thai 3 buoc don gian hon:

| Trang thai | Mo ta |
| :--- | :--- |
| **CASH** | Khong giu vi the, cho tin hieu mua |
| **BUY** | Dang giu vi the Long |
| **SELL** | Tin hieu giam - thi truong xau di, chi cho FTD de quay lai BUY |

**Cai tien chinh so voi Classic:**
- Bo trang thai WAITING_SELL va SHORT (khong ban khong nua)
- Them co che chuyen CASH -> SELL khi thi truong xau di (MA50 breakdown hoac o CASH qua lau)
- Them dieu kien thoat BUY -> CASH qua MA10 (dong cua duoi MA10 nhieu phien lien tiep)
- Giu nguyen cac dieu kien mua (FTD, MA50 breakout, 52-week breakout)

---

## II. DU LIEU DAU VAO VA CHI BAO KY THUAT

### 1. Du lieu dau vao:
* Gia Mo cua ($O$), Cao nhat ($H$), Thap nhat ($L$), Dong cua ($C$), Khoi luong ($V$).
* Du lieu chi so (VNINDEX hoac NASDAQ).

### 2. Cac chi bao duoc tinh:
* **MA10**: Trung binh dong 10 phien cua gia dong cua.
* **MA50**: Trung binh dong 50 phien cua gia dong cua.
* **MA50 Volume**: Trung binh dong 50 phien cua khoi luong.
* **P_loc** (Vi the khung gia): $P_{loc} = \frac{C - L}{H - L}$
* **Rolling High**: Dinh cao nhat tich luy.
* **High 52 tuan**: Dinh cao nhat trong 252 phien giao dich.
* **Drawdown**: Muc giam tu dinh: $\frac{C - Rolling\_High}{Rolling\_High}$
* **Price Change %**: Phan tram thay doi gia so voi phien truoc.
* **Volume Up**: Khoi luong cao hon phien truoc ($V > V_{prev}$).

### 3. Xu ly ngay dao han phai sinh:
* Neu cot `is_expiry_day` ton tai trong du lieu, cac phien dao han se bi tat co `volume_up = False`.
* Dieu nay ngan viec dem ngay phan phoi sai do khoi luong tang dot bien vao ngay dao han.

---

## III. TRANG THAI 1: CASH (TIM KIEM CO HOI)

*Trang thai hien tai: 100% tien mat, khong giu vi the.*

### 1. Theo doi Rally Attempt (No luc hoi phuc):

**Dieu kien vao "Giai doan dieu chinh":**
* Chi so giam >= 10% tu dinh cao nhat gan nhat ($drawdown \le -0.10$).
* Khi dat dinh moi (high moi), giai doan dieu chinh duoc reset.

**Ngay 1 (Day 1) cua Rally Attempt:**
* Dieu kien (1 trong 2):
  * Gia dong cua tang so voi phien truoc ($C > C_{prev}$).
  * HOAC: Gia dong cua o nua tren khung gia ($P_{loc} > 0.5$), ke ca khi gia giam.
* **Quy tac huy de:** Neu gia pha thung day thap nhat cua Ngay 1 ($L_{hien\_tai} < L_{Day1}$) -> Huy dem, bat dau lai tu dau.

### 2. Tin hieu Mua (FTD - Follow-Through Day):

* **Thoi gian:** Xuat hien tu **Ngay thu 4 den Ngay thu 12** cua dot no luc hoi phuc (config: `ftd_min_rally_day=3`, `ftd_max_rally_day=12`, nhung engine kiem tra `rally_day >= 4`).
* **Dieu kien Gia:** Tang >= 1% so voi phien truoc ($price\_change\_pct \ge 0.01$).
* **Dieu kien Khoi luong:** Cao hon phien truoc ($volume\_up = True$).
* **Hanh dong:**
  * Chuyen trang thai: CASH -> **BUY**.
  * Reset bo dem ngay phan phoi: $Count_{DD} = 0$.
  * Ghi nhan **Gia Mua** = Gia dong cua phien FTD.
  * Reset rally tracker.

### 3. Tin hieu Mua (Pha vo len tren MA50):

* **Dieu kien (tat ca phai thoa man):**
  1. Drawdown tu dinh >= 6% ($drawdown\_pct \le -0.06$).
  2. Phien truoc dong cua **duoi hoac bang** MA50 cua phien truoc ($C_{prev} \le MA50_{prev}$).
  3. Phien hien tai dong cua **vuot len tren** MA50 ($C > MA50$).
  4. Khoi luong cao hon phien truoc ($volume\_up = True$).
* **Hanh dong:** Tuong tu FTD, chuyen sang BUY, reset DD counter.

### 4. Tin hieu Mua (Vuot dinh 52 tuan):

* **Dieu kien:** Gia dong cua vuot dinh 52 tuan ($C > High_{52w}$).
* **Hanh dong:** Chuyen sang BUY.
* **Stop loss dac biet:** Dat stop loss tai $L_{ngay\_mua} \times 0.99$ (1% duoi day ngay mua).

### 5. Chuyen CASH -> SELL (Thi truong xau di):

Neu khong co tin hieu mua, kiem tra 2 dieu kien chuyen sang SELL:

* **MA50 Breakdown** (khi `ma50_sell_enabled=True`):
  * Gia dong cua duoi MA50 ($C < MA50$).
  * -> Chuyen sang trang thai SELL.

* **Cash Deterioration** (Xuong cap do o CASH qua lau):
  * So ngay o trang thai CASH >= `cash_deterioration_days` (mac dinh: 10 ngay).
  * -> Chuyen sang trang thai SELL.

**Thu tu uu tien:** FTD > MA50 Breakout > 52-Week Breakout > MA50 Sell > Cash Deterioration.

---

## IV. TRANG THAI 2: BUY (NAM GIU VI THE)

*Trang thai hien tai: Dang giu vi the Long.*

### 1. Dem Ngay phan phoi (Distribution Day):

**Loai 1 (Giam manh - Heavy Selling):**
* Gia giam >= 0.2% ($price\_change\_pct \le -0.002$).
* Khoi luong tang ($volume\_up = True$).

**Loai 2 (Chung lai - Stalling):**
* Gia tang nhe, trong khoang $0 \le price\_change\_pct < 0.001$.
* Khoi luong tang ($volume\_up = True$).
* Dong cua o phan duoi khung gia ($P_{loc} \le 0.20$).

**Bo dem DD:**
* Dem so ngay phan phoi trong cua so truot 20 phien gan nhat.
* Reset ve 0 khi xuat hien tin hieu mua (FTD).

### 2. Dieu kien thoat BUY -> CASH:

**Dieu kien 1: Stop Loss (Uu tien cao nhat)**
* Xem Muc V (Quy tac cat lo) ben duoi.

**Dieu kien 2: Nguong DD dat**
* Tong so ngay phan phoi trong 20 phien >= `dd_cash_threshold` (mac dinh: 5).
* CHI khi ngay hien tai la ngay phan phoi ($is\_dd = True$).
* -> Chuyen sang CASH, ghi nhan P&L.

**Dieu kien 3: Dong cua duoi MA10 lien tiep**
* Khi `ma10_cash_enabled=True` (mac dinh: True).
* Gia dong cua duoi MA10 trong `ma10_cash_consecutive` phien lien tiep (mac dinh: 2 phien).
* Bo dem reset ve 0 khi gia dong cua tren MA10.
* -> Chuyen sang CASH, ghi nhan P&L.

**Thu tu uu tien:** Stop Loss > DD Threshold > MA10 Below.

---

## V. QUY TAC CAT LO (STOP LOSS)

Chi ap dung khi dang o trang thai BUY. Khong co stop loss cho SHORT (da bo SHORT trong V2).

### 1. Cat lo theo phan tram (Rule 1):
* Gia dong cua giam qua `stop_loss_pct` tu gia mua.
* Mac dinh: $C < P_{buy} \times (1 - 0.025)$ (giam 2.5%).

### 2. Pha thung day ngay mua (Rule 2):
* Gia dong cua thap hon gia thap nhat cua ngay mua ($C < L_{buy\_day}$).

### 3. Pha vo xuong duoi MA50 (Rule 3):
* Phien truoc dong cua **tren hoac bang** MA50 truoc ($C_{prev} \ge MA50_{prev}$).
* Phien hien tai dong cua **duoi** MA50 ($C < MA50$).
* Khoi luong phien hien tai cao hon phien truoc ($V > V_{prev}$).

### 4. Quy tac dac biet cho 52-Week Breakout:
* Neu tin hieu mua la 52-Week Breakout, chi ap dung stop loss:
  * $C < L_{buy\_day} \times 0.99$ (1% duoi day ngay mua).
* Khong ap dung Rule 1, 2, 3 thong thuong.

**Thu tu kiem tra:** Rule dac biet 52-Week truoc -> Rule 1 -> Rule 2 -> Rule 3.

---

## VI. TRANG THAI 3: SELL (THI TRUONG XAU)

*Trang thai hien tai: Tin hieu thi truong xau, khong giu vi the.*

### Dac diem:
* SELL la trang thai **ben vung** (persistent) -- chi co FTD hoac MA50 breakout hoac 52-Week breakout moi chuyen ve BUY.
* Khong co co che tu dong thoat SELL (khac voi Classic co SHORT va cover).
* Khi o SELL, rally attempt van duoc theo doi de phat hien FTD.

### Chuyen SELL -> BUY:
* Cung dieu kien nhu CASH -> BUY:
  * FTD signal, hoac
  * MA50 breakout, hoac
  * 52-Week breakout.
* -> Chuyen thang sang BUY, bo qua CASH.

---

## VII. SO DO CHUYEN TRANG THAI

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

## VIII. BANG THONG SO CAU HINH (MDMV2Config)

| Thong so | Gia tri mac dinh | Mo ta |
| :--- | :---: | :--- |
| `correction_threshold` | -0.10 | Nguong giam tu dinh de xac nhan dieu chinh (-10%) |
| `ftd_min_rally_day` | 3 | Ngay toi thieu trong rally de kiem tra FTD |
| `ftd_max_rally_day` | 12 | Ngay toi da trong rally de kiem tra FTD |
| `ftd_min_price_gain` | 0.01 | Muc tang gia toi thieu cho FTD (1%) |
| `ma50_breakout_correction` | -0.06 | Nguong drawdown toi thieu cho MA50 breakout (-6%) |
| `dd_window_size` | 20 | So phien trong cua so truot dem DD |
| `dd_price_drop_threshold` | -0.002 | Nguong giam gia cho DD Loai 1 (-0.2%) |
| `dd_price_stall_threshold` | 0.001 | Nguong tang gia toi da cho DD Loai 2 (0.1%) |
| `dd_stall_p_loc_threshold` | 0.20 | Nguong P_loc toi da cho DD Loai 2 |
| `dd_cash_threshold` | 5 | So DD kich hoat chuyen BUY -> CASH |
| `ma10_cash_enabled` | True | Bat/tat dieu kien thoat theo MA10 |
| `ma10_cash_consecutive` | 2 | So phien lien tiep duoi MA10 de kich hoat |
| `ma50_sell_enabled` | True | Bat/tat MA50 breakdown cho CASH -> SELL |
| `cash_deterioration_days` | 10 | So ngay o CASH truoc khi tu dong chuyen SELL |
| `stop_loss_pct` | 0.025 | Phan tram cat lo tu gia mua (2.5%) |
| `name` | "default" | Ten gia thuyet (metadata) |

---

## IX. GHI CHU QUAN TRONG

1. **Khong co vi the SHORT:** V2 bo hoan toan co che ban khong. SELL chi la tin hieu canh bao, khong mo vi the ban khong.

2. **DD chi dem khi BUY:** Ngay phan phoi chi duoc dem khi dang o trang thai BUY. Khi o CASH hoac SELL, bo dem DD khong hoat dong.

3. **FTD reset rally tracker:** Sau khi phat hien FTD, rally tracker duoc reset hoan toan (`full_reset`), bao gom ca trang thai dieu chinh va dinh.

4. **Rally tracking o ca CASH va SELL:** Ca hai trang thai CASH va SELL deu theo doi rally attempt de phat hien FTD.

5. **Thu tu uu tien tin hieu mua:** FTD truyen thong -> MA50 breakout -> 52-Week breakout. Chi tin hieu dau tien duoc chap nhan.

6. **Stop loss chi cho Long:** Khong co stop loss cho vi the Short (vi khong co Short).

7. **DD day la dieu kien can:** Chuyen BUY -> CASH do DD chi xay ra khi ngay hien tai cung la ngay phan phoi (khong phai bat cu ngay nao co dd_count >= threshold).
