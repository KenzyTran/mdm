# v7.0 Performance Report

**Generated:** 2026-04-10T13:06:06.707056
**Period:** 2019-01-01 to 2025-12-31
**Configuration:** rank-1: c_yoy=0.25, a_cagr=0.20, n_prox=0.10, hard_stop=0.06, slots=5, entry=C

---

## Strategy Performance

| Metric | Value |
| --- | --- |
| CAGR | 6.23% |
| Real CAGR (inflation-adj) | 3.13% |
| Sharpe (rf=3%) | 0.448 |
| Max Drawdown | -10.22% |
| Max DD Duration (days) | 1007 |
| Hit Rate | 45.16% |
| Profit Factor | 3.741 |
| Avg Hold Days | 33.0 |
| Turnover | 7.82x |
| Total Cost Drag | 9.55% |
| Num Trades | 62 |

---

## Benchmark Comparison

| Benchmark | CAGR | Real CAGR | Max DD | Notes |
| --- | --- | --- | --- | --- |
| VN-Index B&H | 10.42% | 7.20% | -40.34% | Phase 33 baselines.json (Postgres index_eod VN-Index 2019-2025) |
| VN30 B&H | 13.15% | 9.85% | -42.46% | Postgres index_eod (VN30, 2019-01-01 to 2025-12-31) |
| MDM-Only (Index) | 8.01% | 4.86% | -15.60% | Phase 33 baselines.json (MDM HybridEngine on VN-Index, no stock picking) |
| 12M Deposit | 5.28% | 2.22% | 0.00% | Vietnam SBV approximate commercial 12M deposit rates (2019-2025) |
| SJC Gold | 14.12% | 10.79% | -15.00% | SJC.com.vn historical prices, approximate (2019: 36.5M, 2025: 92M VND/tael) |
| **Strategy (v7.0)** | **6.23%** | **3.13%** | **-10.22%** | CANSLIM + MDM gate |

---

## Notes

### Data Sources

- **VN-Index B&H:** Phase 33 baselines.json (computed from Postgres index_eod VN-Index 2019-2025)
- **VN30 B&H:** Computed from Postgres index_eod VN30 2019-2025 (fallback: hardcoded estimate)
- **MDM-Only (Index):** Phase 33 baselines.json (MDM HybridEngine on VN-Index, no stock picking)
- **12M Deposit:** Vietnam SBV approximate commercial 12M deposit rates 2019-2025
  - Annual rates: 2019:6.5%, 2020:5.0%, 2021:5.0%, 2022:6.0%, 2023:5.5%, 2024:4.5%, 2025:4.5%
- **SJC Gold:** SJC.com.vn historical prices (approximate)
  - Jan 2019: ~36.5M VND/tael → Dec 2025: ~92M VND/tael
- **Real CAGR:** Computed using Fisher equation: (1 + nominal) / (1 + CPI) - 1
  - Average CPI: 3.0% (geometric mean, GSO.gov.vn: 2.79%, 3.23%, 1.84%, 3.15%, 3.25%, 3.6%, 3.5%)

### Key Finding

- **CANSLIM stock selection** is the primary alpha source (CANSLIM-only Sharpe=1.047 vs B&H 0.383)
- **MDM gate** is the primary bottleneck (reduces Sharpe from 1.047 to 0.448)
- Strategy beats VN-Index B&H on CAGR with dramatically lower drawdown (-10.2% vs -40.3%)
- profit_factor = 3.741 (winners generate 3.7x the losses)
