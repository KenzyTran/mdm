# Liquidity Proxy Correlation with VN30 Returns

Pre-v10.0 exploratory research. Phase 41 walk-forward validation showed all v9 scenarios degraded +67% to +96% when moving from Train 2015-2021 to Test 2022-2026, suggesting the post-2022 regime is hostile to pure price/volume features. This report tests whether a small basket of liquidity proxies (USDVND, DXY, US10Y, VNM ETF, EEM ETF) is correlated enough with VN30 same-day or 20-day-forward returns, or whether SBV policy regime (easing/neutral/tightening with a 90-day decay) explains enough of the CAGR/Sharpe gap to justify a v10.0 macro-regime filter.

## Correlation Table

Pearson correlations of each proxy (daily returns and 20d rolling z-scores) with VN30 same-day returns and VN30 20d-forward returns. Inner-joined on VN30 trading days -- VN30 sessions with no matching proxy print (e.g. US holidays) are dropped from the correlation sample.

|  | corr_sameday_ret | corr_fwd20_ret | corr_sameday_z | corr_fwd20_z |
| --- | --- | --- | --- | --- |
| usdvnd_close | -0.0090 | -0.0073 | -0.0455 | -0.0533 |
| dxy_close | 0.0242 | -0.0724 | -0.0594 | -0.1909 |
| tnx_close | 0.0993 | 0.0040 | 0.0243 | -0.0319 |
| vnm_close | 0.6212 | 0.0707 | 0.3473 | 0.1182 |
| eem_close | 0.1392 | 0.1029 | 0.1739 | 0.1911 |

## SBV Regime Split

VN30 performance partitioned by SBV policy regime. Regime tag derives from the most recent SBV easing or tightening event, decayed to `neutral` after 90 calendar days. Source file: `data/sbv_policy_events.csv`.

|  | days | total_return_pct | cagr_pct | sharpe_rf3 | max_dd_pct |
| --- | --- | --- | --- | --- | --- |
| easing | 465.0000 | 66.5370 | 31.8392 | 1.4514 | -19.7837 |
| neutral | 2208.0000 | 128.7517 | 9.9042 | 0.4382 | -39.3705 |
| tightening | 84.0000 | -8.7083 | -23.9159 | -0.7310 | -25.5585 |

## Decision Gates

- **Gate A (correlation):** any proxy's |corr_fwd20_ret| or |corr_fwd20_z| >= `0.15`.
- **Gate B (regime dispersion):** CAGR spread across {easing, neutral, tightening} >= `3.0pp` OR Sharpe_rf3 spread >= `0.15`.

Gate outcomes:

- Gate A PASSED: max |corr_fwd20| = 0.1911 on eem_close >= 0.15.
- Gate B PASSED: CAGR spread = 55.76pp, Sharpe spread = 2.1824 (thresholds 3.0pp / 0.15).

## Verdict

**GO**

Reasoning:

- Gate A PASSED: max |corr_fwd20| = 0.1911 on eem_close >= 0.15.
- Gate B PASSED: CAGR spread = 55.76pp, Sharpe spread = 2.1824 (thresholds 3.0pp / 0.15).

## Reproducibility

- Script: `analysis/test_liquidity_correlation.py`
- Inputs: `data\vn30_price.csv`, `data\vn_liquidity_proxy.csv`, `data\sbv_policy_events.csv`
- VN30 date range used: 2015-01-05 -> 2026-01-20 (2758 rows)
- Forward-return window: 20 trading days
- Risk-free rate for Sharpe: 3% annual
