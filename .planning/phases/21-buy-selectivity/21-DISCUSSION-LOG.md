# Phase 21: BUY Selectivity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 21-buy-selectivity
**Areas discussed:** FTD rejection criteria, Confirmation window, Gate architecture, Validation approach

---

## FTD Rejection Criteria

### Filter scope
| Option | Description | Selected |
|--------|-------------|----------|
| Chi FTD | MA50 breakout va 52-week breakout da ngam xac nhan trend manh — loc them se thua. Chi FTD can kiem tra trend. | ✓ |
| Ca 3 loai signal | Ap dung MA10 < MA50 cho tat ca. Nhat quan nhung co the over-filter. | |
| FTD + MA50 breakout | Loc FTD va MA50 breakout, cho phep 52-week breakout qua. | |

**User's choice:** Chi FTD
**Notes:** MA50 breakout tu no da co gia > MA50, 52-week breakout la signal trend manh nhat.

### Extra filter
| Option | Description | Selected |
|--------|-------------|----------|
| Chi MA10 < MA50 | Giu don gian, 1 dieu kien. Ket hop voi confirmation window da du chat. | ✓ |
| Them volume filter | Yeu cau volume FTD day > MA50 volume. | |
| Them EMA alignment | Yeu cau EMA9 > EMA21 ngoai MA10 > MA50. | |

**User's choice:** Chi MA10 < MA50
**Notes:** Khong them filter khac, giu don gian.

---

## Confirmation Window

### Window state
| Option | Description | Selected |
|--------|-------------|----------|
| CASH | Giu CASH trong N ngay, chi chuyen BUY khi du dieu kien. Don gian va an toan. | ✓ |
| Provisional BUY | Vao BUY ngay voi stop loss chat hon. Neu DD trong window thoat ngay ve CASH. | |
| PENDING_BUY state moi | Them state thu 4 trong state machine. Ro rang nhat nhung thay doi kien truc. | |

**User's choice:** CASH
**Notes:** Giu nguyen state machine 3-state hien tai.

### Fail trigger
| Option | Description | Selected |
|--------|-------------|----------|
| Bat ky DD nao | 1 DD trong N ngay huy FTD, reset ve CASH. Nghiem khac. | |
| DD cluster (2+ DD) | Cho phep 1 DD don le, chi huy khi 2+ DD trong window. Linh hoat hon. | ✓ |
| DD + gia giam | DD chi huy FTD khi gia close < FTD price. | |

**User's choice:** DD cluster (2+ DD)
**Notes:** Cho phep 1 DD don le, 2+ DD moi huy FTD.

### Window size
| Option | Description | Selected |
|--------|-------------|----------|
| 3 ngay | Ngan gon, du loc whipsaw ngan han. Pho bien trong he thong IBD/O'Neil. | ✓ |
| 5 ngay | 1 tuan giao dich. Chat hon nhung co the vao muon. | |
| Config parameter | De la tham so cau hinh, default 3, toi uu hoa qua backtest. | |

**User's choice:** 3 ngay
**Notes:** None

### Entry price
| Option | Description | Selected |
|--------|-------------|----------|
| Gia close ngay xac nhan | Lay gia close ngay cuoi cung cua window. Thuc te va don gian. | ✓ |
| Gia FTD goc | Dung gia close ngay FTD. Nhat quan nhung khong phan anh thuc te giao dich. | |

**User's choice:** Gia close ngay xac nhan
**Notes:** None

---

## Gate Architecture

### Module design
| Option | Description | Selected |
|--------|-------------|----------|
| 1 class BuyQualityGate | Gop ca MA10/MA50 filter va confirmation window vao 1 class. | |
| 2 module rieng biet | buy_filter.py cho MA10/MA50 rejection + buy_confirmation.py cho window logic. | ✓ |
| Tich hop vao ftd_signal.py | Them filter logic vao FTDSignalDetector hien tai. | |

**User's choice:** 2 module rieng biet
**Notes:** Tach biet concern — filter va confirmation la 2 logic khac nhau.

### Wiring pattern
| Option | Description | Selected |
|--------|-------------|----------|
| Engine loc truoc | Engine goi BuyFilter.check() truoc khi pass is_ftd cho position_manager. | ✓ |
| Position manager kiem tra | Pass buy_quality_ok param vao process_day(). | |
| Middleware pattern | Tao pipeline: FTD detect -> quality filter -> confirmation -> position manager. | |

**User's choice:** Engine loc truoc
**Notes:** Giong pattern suppress_sell / acceleration_met.

---

## Validation Approach

### Walk-forward split
| Option | Description | Selected |
|--------|-------------|----------|
| Pre-2020 / 2020-2026 | Theo roadmap success criteria. | ✓ |
| Pre-2019 / 2019-2026 | Split tai diem MDM thay doi (Feb 2019). | |
| 70/30 random split | Khong phu thuoc moc thoi gian co dinh. | |

**User's choice:** Pre-2020 / 2020-2026
**Notes:** None

### Metrics
| Option | Description | Selected |
|--------|-------------|----------|
| Trade count + win rate | So sanh so trades va win rate giua baseline va filtered. | ✓ |
| Average hold duration | BUY filtered nen co thoi gian giu lenh dai hon. | |
| Stopped-out-in-5-days ratio | Ti le FTD bi stop loss trong 5 ngay. | |

**User's choice:** Trade count + win rate
**Notes:** None

### Markets
| Option | Description | Selected |
|--------|-------------|----------|
| Ca hai | Chay A/B tren ca NASDAQ va VN30. | ✓ |
| Chi NASDAQ | NASDAQ co data dai hon va la target chinh. | |
| NASDAQ + VN30 rieng | 2 script rieng biet voi config preset khac nhau. | |

**User's choice:** Ca hai
**Notes:** Theo pattern Phase 20.

---

## Claude's Discretion

- Exact class/method naming for buy_filter.py and buy_confirmation.py
- Internal state tracking for confirmation window
- Validation script output format and report structure
- Whether to log filter/confirmation decisions in DataFrame columns

## Deferred Ideas

None — discussion stayed within phase scope
