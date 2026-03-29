# BO QUY TAC MO HINH MDM HYBRID - TWO-PHASE COMMIT + INDICATOR FILTER

## I. TONG QUAN

MDM Hybrid la phien ban nang cao nhat, ket hop:
1. **May trang thai V2** (BUY/CASH/SELL) lam co so
2. **Two-Phase Commit** (snapshot/restore) cho kha nang rollback quyet dinh
3. **Indicator Filter Layer** (bo loc chi bao ky thuat) de xac nhan hoac phu quyet tin hieu
4. **Contextual Transitions** (chuyen trang thai theo ngu canh) de thich ung voi trang thai thi truong

**Kien truc:** V2 state machine de xuat tin hieu -> Indicator Filter danh gia -> Quyet dinh cuoi cung (giu hoac rollback).

---

## II. CO CHE TWO-PHASE COMMIT

### 1. Nguyen ly hoat dong:

Truoc moi phien giao dich, engine thuc hien:

1. **Snapshot** (`_snapshot_components`): Sao luu trang thai cua 4 component:
   - `dd_counter` (bo dem ngay phan phoi)
   - `rally_tracker` (theo doi rally attempt)
   - `ftd_detector` (phat hien FTD)
   - `position_manager` (quan ly vi the)

2. **Xu ly phien:** Chay tat ca logic V2 binh thuong (rally tracking, FTD detection, DD counting, stop loss, position update).

3. **Danh gia:** So sanh trang thai truoc va sau xu ly:
   - Neu trang thai thay doi: tao **de xuat** (proposal) = trang thai moi
   - Neu trang thai khong doi: de xuat = trang thai hien tai

4. **Quyet dinh:** Indicator filter danh gia de xuat:
   - **CONFIRM**: Giu cac thay doi (commit)
   - **VETO**: Huy cac thay doi, khoi phuc snapshot (rollback)
   - **OVERRIDE**: Ep chuyen ve CASH bat ke de xuat

### 2. Cau hinh:
* `two_phase_enabled` (mac dinh: True) -- bat/tat co che snapshot/restore
* `filter_enabled` (mac dinh: False) -- bat/tat bo loc chi bao

Khi `filter_enabled=False`, two-phase commit van chay nhung luon CONFIRM (khong co bo loc nao de phu quyet).

---

## III. INDICATOR FILTER LAYER (BO LOC CHI BAO)

### 1. Nguyen tac:
* Bo loc **KHONG tao tin hieu** -- chi danh gia (CONFIRM/VETO/OVERRIDE) tin hieu tu may trang thai V2.
* Su dung **majority-vote** (bo phieu da so) cua cac dieu kien ky thuat.
* **Stateless**: Moi lan danh gia doc lap, khong luu tru trang thai.
* **NaN-safe**: Tat ca gia tri NaN duoc xu ly an toan -- NaN -> False cho ca bullish va bearish.

### 2. 7 Dieu kien ky thuat:

| # | Dieu kien | Bullish | Bearish | Mac dinh |
| :---: | :--- | :--- | :--- | :---: |
| 1 | **Close > EMA55** | $C > EMA55$ | $C < EMA55$ | BAT |
| 2 | **MACD Histogram > 0** | $MACD\_hist > 0$ | $MACD\_hist < 0$ | BAT |
| 3 | **EMA9 > EMA21** | $EMA9 > EMA21$ | $EMA9 < EMA21$ | BAT |
| 4 | **Close > MA200** | $C > MA200$ | $C < MA200$ | TAT |
| 5 | **Close > EMA9** | $C > EMA9$ | $C < EMA9$ | TAT |
| 6 | **MACD > Signal** | $MACD > Signal$ | $MACD < Signal$ | TAT |
| 7 | **HA Smoothed 55 Bullish** | $HA\_close > HA\_open$ | $HA\_close < HA\_open$ | TAT |

**Luu y quan trong:** Dieu kien bearish KHONG phai la phep phu dinh don gian cua bullish. Khi du lieu la NaN, ca bullish va bearish deu tra ve False (theo quy tac D-06).

### 3. Majority Vote (Bo phieu da so):

* **Diem tin cay (Confidence Score):** $confidence = \frac{so\_dieu\_kien\_dong\_y}{tong\_dieu\_kien\_bat}$
* **Nguong da so (Majority Threshold):** Mac dinh $\frac{2}{3} \approx 0.667$ (2 tren 3 dieu kien phai dong y).

**Logic bo phieu:**

| Tinh huong | Ket qua |
| :--- | :--- |
| Khong co dieu kien nao bat (hoac tat ca NaN) | **CONFIRM** (khong co y kien) |
| $confidence = 0.0$ va >= 3 dieu kien bat | **OVERRIDE** (tat ca phan doi) |
| $confidence \ge majority\_threshold$ | **CONFIRM** (da so dong y) |
| $confidence < majority\_threshold$ | **VETO** (khong du dong y) |

### 4. Cach ap dung vote cho tung loai de xuat:

* **De xuat BUY:** Kiem tra cac dieu kien **bullish** (close tren EMA, MACD duong, v.v.)
* **De xuat SELL hoac CASH:** Kiem tra cac dieu kien **bearish** (close duoi EMA, MACD am, v.v.)

---

## IV. LOGIC XU LY VERDICT (QUYET DINH)

### Truong hop 1: Trang thai THAY DOI (de xuat chuyen trang thai)

| Verdict | Hanh dong |
| :--- | :--- |
| **CONFIRM** | Giu nguyen cac thay doi tu V2 state machine (commit) |
| **VETO** | Khoi phuc snapshot, huy tat ca thay doi (rollback). Trang thai giu nguyen nhu truoc |
| **OVERRIDE** | Khoi phuc snapshot roi ep chuyen ve CASH. Neu truoc do la BUY: `exit_to_cash` (ghi nhan P&L). Neu truoc do la SELL: `degrade_to_cash` (khong P&L). Neu de xuat CASH: giu nguyen (da dung huong) |

### Truong hop 2: Trang thai KHONG DOI (V2 khong de xuat thay doi)

Bo loc van danh gia tinh hinh chi bao:

| Verdict | Hanh dong |
| :--- | :--- |
| **CONFIRM** | Khong lam gi (giu nguyen trang thai) |
| **VETO hoac OVERRIDE** (khi o BUY) | Thoat vi the: `exit_to_cash` voi ly do "indicator degradation" (ghi P&L) |
| **VETO hoac OVERRIDE** (khi o SELL) | Xuong cap: `degrade_to_cash` voi ly do "indicator degradation from SELL" |
| **VETO hoac OVERRIDE** (khi o CASH) | Bo qua -- da o CASH roi, khong can lam gi |

**Diem quan trong:** Bo loc co the *ep ban* (exit BUY) hoac *lam diu* (degrade SELL ve CASH) ngay ca khi V2 state machine khong de xuat thay doi nao.

---

## V. CONTEXTUAL TRANSITIONS (CHUYEN TRANG THAI THEO NGU CANH)

### 1. Theo doi lich su trang thai:

Engine luu lai lich su cac trang thai da qua:
```python
state_history = [
    {'state': 'CASH', 'entered_date': ..., 'duration': 15},
    {'state': 'BUY', 'entered_date': ..., 'duration': 8},
    {'state': 'SELL', 'entered_date': ..., 'duration': 12},
    ...
]
```

Bien `_days_in_current_state` dem so ngay o trang thai hien tai.

### 2. Dieu chinh nguong theo ngu canh (`_get_contextual_threshold`):

Ap dung triet ly "uu tien giu tien mat" (favor cash) cua Dr. K:

**Quy tac 1: O CASH qua lau -> nghiem ngat hon voi BUY**
* Dieu kien: Dang o CASH va `_days_in_current_state > cash_deterioration_days` (mac dinh: > 10 ngay)
* Hanh dong: Nguong da so = **1.0** (100% -- tat ca dieu kien phai dong y)
* Y nghia: Thi truong o CASH lau -> can than hon truoc khi mua

**Quy tac 2: CASH tu SELL -> che do bearish**
* Dieu kien: Dang o CASH va trang thai truoc la SELL va da o CASH > 5 ngay
* Hanh dong: Nguong da so = **1.0** (100% -- tat ca dieu kien phai dong y)
* Y nghia: Chuyen tu SELL ve CASH la dau hieu thi truong xau, can tat ca chi bao xac nhan truoc khi mua

**Cac truong hop khac:** Giu nguyen nguong mac dinh ($\frac{2}{3}$).

**Pham vi ap dung:** Chi anh huong de xuat BUY khi dang o CASH. De xuat SELL va CASH khong bi dieu chinh.

---

## VI. SIGNAL LOG (NHAT KY TIN HIEU)

Moi phien giao dich duoc ghi lai:
* `old_state`: Trang thai truoc khi xu ly
* `proposed`: De xuat tu V2 state machine (BUY/CASH/SELL)
* `verdict`: Ket qua bo loc (CONFIRM/VETO/OVERRIDE)
* `confidence`: Diem tin cay ($0.0$ den $1.0$)

Cac cot nay ho tro phan tich va debug sau backtest.

---

## VII. BANG THONG SO CAU HINH

### FilterConfig (Bo loc chi bao):

| Thong so | Gia tri mac dinh | Mo ta |
| :--- | :---: | :--- |
| `ema55_enabled` | True | Bat dieu kien Close > EMA55 |
| `macd_enabled` | True | Bat dieu kien MACD Histogram > 0 |
| `ema9_21_enabled` | True | Bat dieu kien EMA9 > EMA21 |
| `ma200_enabled` | False | Bat dieu kien Close > MA200 |
| `ema9_enabled` | False | Bat dieu kien Close > EMA9 |
| `macd_signal_enabled` | False | Bat dieu kien MACD > Signal Line |
| `ha_smooth_enabled` | False | Bat dieu kien HA Smoothed 55 Bullish |
| `majority_threshold` | 0.667 (2/3) | Ty le dong y toi thieu de CONFIRM |

**Canh bao:** Khuyen nghi chi bat 2-3 dieu kien de tranh overfitting (D-04). Neu bat > 3 dieu kien, he thong se phat ra canh bao.

### HybridConfig (Cau hinh tong hop):

| Thong so | Gia tri mac dinh | Mo ta |
| :--- | :---: | :--- |
| `v2_config` | MDMV2Config() | Cau hinh V2 state machine (xem bang V2 config) |
| `two_phase_enabled` | True | Bat co che snapshot/restore |
| `filter_enabled` | False | Bat bo loc chi bao (can bat de filter hoat dong) |
| `filter_config` | FilterConfig() | Cau hinh bo loc chi bao |

---

## VIII. SO DO XU LY MOI PHIEN

```
Bat dau phien
    |
    v
[1] Snapshot 4 components
    |
    v
[2] V2 State Machine xu ly
    (Rally tracking, FTD, DD, Stop loss, Position update)
    |
    v
[3] So sanh trang thai cu va moi -> Tao de xuat (proposal)
    |
    v
[4] Tinh nguong ngu canh (contextual threshold)
    |
    v
[5] Indicator Filter danh gia (evaluate)
    -> Thu thap votes (bullish hoac bearish)
    -> Tinh confidence score
    -> Xac dinh verdict (CONFIRM / VETO / OVERRIDE)
    |
    v
[6] Ap dung verdict:
    - CONFIRM: Giu thay doi
    - VETO: Rollback snapshot
    - OVERRIDE: Rollback + ep ve CASH
    |
    v
[7] Cap nhat state history
    |
    v
[8] Ghi ket qua vao DataFrame
```

---

## IX. GHI CHU QUAN TRONG

1. **Filter khong tao tin hieu:** Bo loc chi CONFIRM hoac phu quyet tin hieu tu V2. No khong bao gio tu tao tin hieu mua hoac ban.

2. **OVERRIDE khac VETO:** VETO chi chan de xuat, giu trang thai cu. OVERRIDE chu dong ep ve CASH, co the gay ban vi the (exit BUY).

3. **Indicator degradation:** Ngay ca khi V2 khong de xuat thay doi gi, neu chi bao xau di (VETO/OVERRIDE), engine co the tu dong thoat BUY hoac degrade SELL.

4. **Contextual threshold chi anh huong BUY:** Cac quy tac ngu canh (o CASH lau, tu SELL) chi lam nghiem ngat hon dieu kien mua, khong anh huong dieu kien ban.

5. **NaN khong phai bearish:** Khi du lieu chi bao la NaN, dieu kien tra ve False cho ca bullish va bearish. Dieu nay tranh viec NaN bi hieu nham la tin hieu bearish.

6. **Two-phase co the tat:** Khi `two_phase_enabled=False`, engine chay giong het V2 (khong snapshot, khong rollback). Khi `filter_enabled=False`, two-phase van chay nhung luon confirm.

7. **EMA/MACD duoc tinh tu `core.indicators`:** Khi filter duoc bat, engine goi `build_indicator_dataframe()` tu module `core/indicators.py` de tinh cac cot EMA9, EMA21, EMA55, MACD, MA200, HA Smoothed.

8. **Pitfall - CASH override:** Neu de xuat la CASH va verdict la OVERRIDE, engine giu nguyen chuyen CASH (khong can ep lai vi da dung huong).

9. **Pitfall - CASH degradation:** Khi o CASH va verdict la VETO/OVERRIDE, engine bo qua (khong lam gi vi da o CASH roi).
