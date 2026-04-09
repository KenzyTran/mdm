# Phase 30 — Entry A/B Audit (Option A vs Option C)

**Source commit:** `9a878bb`
**MDM state coverage:** 2014-01-02 → 2025-12-31  (D-18)
**Universe size (tickers with loadable prices):** 100

> Phase 30 assumes every next-day open is tradable. T+2 / 7% ceiling-floor lock handling is deferred to Phase 31 per D-13.

## Side-by-side metrics

#### Raw VN100 (no CANSLIM gate) — Option A and Option C

| detector | total_fills | unique_tickers | windows_with_fills | mean_fills_per_window | days_since_buy_histogram | ab_overlap_count |
| --- | --- | --- | --- | --- | --- | --- |
| A | 468 | 95 | 23 | 16.714 | 1:53, 2:48, 3:36, 4:29, 5:32, 6:27, 7:25, 8:22, 9:16, 10:24, 11:14, 12:28, 13:20, 14:15, 15:21, 16:9, 17:14, 18:11, 19:14, 20:10 | 456 |
| C | 1733 | 100 | 27 | 61.893 | 1:358, 2:216, 3:128, 4:119, 5:102, 6:75, 7:70, 8:56, 9:58, 10:62, 11:66, 12:61, 13:51, 14:88, 15:38, 16:51, 17:35, 18:39, 19:33, 20:27 | 456 |

#### CANSLIM-qualified — Option A and Option C

| detector | total_fills | unique_tickers | windows_with_fills | mean_fills_per_window | days_since_buy_histogram | ab_overlap_count |
| --- | --- | --- | --- | --- | --- | --- |
| A | 4 | 4 | 3 | 0.143 | 4:1, 10:2, 16:1 | 3 |
| C | 3 | 3 | 3 | 0.107 | 4:1, 10:1, 16:1 | 3 |

## Days-since-buy distribution

#### Days-since-buy histogram — Raw

- Option A: 1:53, 2:48, 3:36, 4:29, 5:32, 6:27, 7:25, 8:22, 9:16, 10:24, 11:14, 12:28, 13:20, 14:15, 15:21, 16:9, 17:14, 18:11, 19:14, 20:10
- Option C: 1:358, 2:216, 3:128, 4:119, 5:102, 6:75, 7:70, 8:56, 9:58, 10:62, 11:66, 12:61, 13:51, 14:88, 15:38, 16:51, 17:35, 18:39, 19:33, 20:27

#### Days-since-buy histogram — CANSLIM-qualified

- Option A: 4:1, 10:2, 16:1
- Option C: 4:1, 10:1, 16:1
