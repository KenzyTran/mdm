# Phase 33 Plan 02: OOS Pass/Fail Verdict

**Generated:** 2026-04-10
**OOS Period:** 2019-01-01 .. 2025-12-31
**Locked config:** rank-1 (c_yoy=0.25, a_cagr=0.20, n_prox=0.10, hard_stop=0.06, slots=5, entry=C)

---

## 1. OOS Performance (rank-1 config)

| Metric | Value |
|--------|-------|
| CAGR | 6.23% |
| Sharpe_rf3 | 0.448 |
| MaxDD | -10.22% |
| MaxDD duration | 1007 days |
| Hit rate | 45.16% |
| Num trades | 62 |
| Avg hold days | 33.0 |
| Turnover | 7.822 |
| Cost drag (ratio) | 9.5521 |

---

## 2. VN-Index B&H Benchmark

| Metric | Value |
|--------|-------|
| CAGR | 10.42% |
| Sharpe_rf3 | 0.383 |
| MaxDD | -40.34% |
| MaxDD duration | 882 days |

---

## 3. BT-08 Pass/Fail Verdict

| Target | Threshold | Strategy | Benchmark | Delta | Verdict |
|--------|-----------|----------|-----------|-------|---------|
| Sharpe uplift | > 0.20 | 0.448 | 0.383 | +0.064 | FAIL |
| MaxDD reduction | > 30% | -10.2% | -40.3% | 74.7% | PASS |

**Overall: FAIL**

---

## 4. Sensitivity Analysis

9-run sensitivity matrix: 3 universe modes × 3 locked configs. Period: 2019-01-01 .. 2025-12-31.


### Sharpe_rf3 Pivot (universe mode x rank)

| Mode | Rank 1 | Rank 2 | Rank 3 |
|------|--------|--------|--------|
| current-vn100 | 0.448 (F) | 0.381 (F) | 0.381 (F) |
| liquidity-reconstructed | 0.064 (F) | 0.052 (F) | 0.052 (F) |
| vn30-only | 0.268 (F) | 0.302 (F) | 0.302 (F) |

P = Sharpe uplift > 0.20 vs VN-Index B&H. F = fails BT-08 Sharpe target.


---

## 5. Baseline Comparison

| Baseline | CAGR | Sharpe_rf3 | MaxDD |
|----------|------|------------|-------|
| Strategy (rank-1) | 6.23% | 0.448 | -10.22% |
| CANSLIM-only (no MDM gate) | 16.43% | 1.047 | -32.24% |
| MDM-only-on-index | 8.01% | 0.508 | -15.60% |
| VN-Index B&H | 10.42% | 0.383 | -40.34% |

---

## 6. diem_canslim Ranking Comparison (OOS)


| Metric | OOS (2019-2025) | In-Sample (Phase 29) |
|--------|-----------------|----------------------|
| Median Spearman rho | 0.365 | 0.280 |
| Mean top-10 overlap | 2.83/10 | 2.43/10 |
| Quarters compared | 24 | 28 |

OOS rho (0.365) vs in-sample (0.280): OOS ranking agreement is higher — CANSLIM scorer generalizes well OOS."


---

## 7. Failure Attribution

### Sharpe Uplift Failure

**Primary reason:** MDM gate

Strategy Sharpe (0.448) is lower than CANSLIM-only Sharpe (1.047), suggesting the MDM gate is reducing exposure during profitable periods. The HybridEngine may be keeping the portfolio in CASH/SELL during VN-market bull runs that do not match the NASDAQ-calibrated MDM patterns.

**Component breakdown:**
- Strategy Sharpe: 0.448
- CANSLIM-only Sharpe: 1.047
- MDM-only-index Sharpe: 0.508
- VN-Index B&H Sharpe: 0.383
- Cost drag (ratio): 9.5521

**Actionable conclusion:** The primary reason for Sharpe uplift failure is **MDM gate** because Strategy Sharpe (0.448) is lower than CANSLIM-only Sharpe (1.047), suggesting the MDM gate is reducing exposure during profitable periods. The HybridEngine may be keeping the portfolio in CASH/SELL during VN-market bull runs that do not match the NASDAQ-calibrated MDM patterns.
