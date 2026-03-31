# Phase 20: SELL Acceleration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 20-sell-acceleration
**Areas discussed:** Acceleration conditions, Gate architecture, Bear market validation, Config & parameters

---

## Acceleration Conditions

### Q1: Acceleration conditions ket hop voi SELL trigger hien tai nhu the nao?

| Option | Description | Selected |
|--------|-------------|----------|
| Gate tren trigger cu | MA50 breakdown / cash deterioration van la dieu kien chinh, nhung chi SELL khi co them it nhat 1 acceleration | ✓ |
| Thay the hoan toan | Bo MA50 breakdown va cash deterioration, chi dung he thong acceleration moi | |
| Them trigger doc lap | Giu nguyen MA50/deterioration, them acceleration nhu trigger SELL thu 3 rieng biet | |

**User's choice:** Gate tren trigger cu (Recommended)
**Notes:** None

### Q2: Ba loai acceleration condition -- dung ca 3 hay chi mot so?

| Option | Description | Selected |
|--------|-------------|----------|
| Ca 3 (OR logic) | Price ROC OR DD clustering OR volume-confirmed MA50 breakdown | ✓ |
| Chi ROC + Volume MA50 | Bo DD clustering, don gian hon | |
| Chi DD clustering + Volume MA50 | Bo price ROC, phu hop voi logic DD hien co | |

**User's choice:** Ca 3 (OR logic)
**Notes:** None

### Q3: Acceleration gate ap dung cho ca hai trigger hay chi MA50 breakdown?

| Option | Description | Selected |
|--------|-------------|----------|
| Ca hai trigger | Ca MA50 breakdown lan cash deterioration deu can qua acceleration gate | ✓ |
| Chi MA50 breakdown | Cash deterioration giu nguyen, khong can acceleration | |

**User's choice:** Ca hai trigger
**Notes:** None

---

## Gate Architecture

### Q4: Acceleration gate nen dat o dau trong code?

| Option | Description | Selected |
|--------|-------------|----------|
| Trong position_manager | Them acceleration check truc tiep trong process_day() | |
| Module rieng (sell_acceleration.py) | Tao class SellAccelerationGate rieng | ✓ |
| Trong engine | Engine tinh acceleration va truyen co suppress vao position_manager | |

**User's choice:** Module rieng (sell_acceleration.py)
**Notes:** None

### Q5: Module sell_acceleration.py tuong tac voi engine nhu the nao?

| Option | Description | Selected |
|--------|-------------|----------|
| Engine goi, truyen co vao PM | Engine goi SellAccelerationGate.check(), truyen bool vao position_manager | ✓ |
| Gate bao boc position_manager | SellAccelerationGate wrap position_manager, chan SELL output | |

**User's choice:** Engine goi, truyen co vao PM (same pattern as QE floor suppress_sell)
**Notes:** None

---

## Bear Market Validation

### Q6: Chien luoc validate bear market?

| Option | Description | Selected |
|--------|-------------|----------|
| Script A/B so sanh | 1 script chay V2 baseline vs V2+acceleration tren sub-period | ✓ |
| Test tu dong trong pytest | Unit test assert delay va drawdown thresholds | |
| Ca hai | Script + pytest | |

**User's choice:** Script A/B so sanh
**Notes:** Following existing analysis/validate_v2.py pattern

### Q7: Script A/B chay tren ca NASDAQ va VN30?

| Option | Description | Selected |
|--------|-------------|----------|
| Ca hai | NASDAQ (2008 + 2022) va VN30 (2022) | ✓ |
| Chi NASDAQ | VN30 de Phase 22 | |

**User's choice:** Ca hai
**Notes:** None

---

## Config & Parameters

### Q8: Tham so moi cho acceleration thiet ke the nao?

| Option | Description | Selected |
|--------|-------------|----------|
| Enable flag + defaults | sell_acceleration_enabled, roc_threshold, roc_window, dd_cluster_count, dd_cluster_window | ✓ |
| Toi gian | Chi enable flag, hardcode thresholds | |
| Full parameterize | Moi threshold vao config, them per-condition enable flags | |

**User's choice:** Enable flag + defaults
**Notes:** None

### Q9: Preset NASDAQ vs VN30 co can khac nhau?

| Option | Description | Selected |
|--------|-------------|----------|
| Cung defaults, tune sau | Bat dau voi cung tham so, tach preset sau neu can | ✓ |
| Tach preset ngay | VN30 co 7% price limit, can preset rieng tu dau | |

**User's choice:** Cung defaults, tune sau
**Notes:** None

---

## Claude's Discretion

- Exact default values for ROC threshold, ROC window, DD cluster count/window
- Volume confirmation logic details
- Script file naming and output format
- Whether to log acceleration gate decisions in results DataFrame

## Deferred Ideas

None -- discussion stayed within phase scope
