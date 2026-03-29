# Rule Discovery Report
Generated: 2026-03-29

## Dataset Summary
- Total signals: 962
- Pre-2019 (before 2019-02-09): 867 signals (Buy=296, Cash=296, Sell=275)
- Post-2019 (from 2019-02-09): 95 signals (Buy=37, Cash=43, Sell=15)

## Pre-2019 Statistical Profile

**Total signals:** 867

**Class distribution:**
- Buy: 296 (34.1%)
- Cash: 296 (34.1%)
- Sell: 275 (31.7%)

### Boolean Feature Frequencies (% True)

| Feature | Buy | Cash | Sell |
| --- | --- | --- | --- |
| ema9_above_ema21 | 38.9% | 52.4% | 50.5% |
| ema21_above_ema55 | 48.0% | 59.5% | 65.8% |
| close_above_ma200 | 65.5% | 67.6% | 68.0% |
| close_above_ema9 | 84.1% | 42.9% | 21.5% |
| close_above_ema21 | 64.2% | 44.6% | 29.8% |
| close_above_ema55 | 55.7% | 54.1% | 48.0% |
| macd_histogram_positive | 59.1% | 47.0% | 33.1% |
| macd_above_signal | 59.1% | 47.0% | 33.1% |

### Continuous Feature Summary (mean +/- std)

| Feature | Buy | Cash | Sell |
| --- | --- | --- | --- |
| macd | -7.19 +/- 40.49 | -3.01 +/- 38.12 | -4.56 +/- 32.92 |
| macd_signal | -7.78 +/- 38.87 | -1.24 +/- 37.66 | -1.61 +/- 33.46 |
| macd_histogram | 0.59 +/- 9.83 | -1.78 +/- 12.37 | -2.94 +/- 11.94 |
| ema9 | 1999.77 +/- 1924.77 | 2284.83 +/- 1982.07 | 1782.35 +/- 1748.53 |
| ema21 | 2006.03 +/- 1923.35 | 2288.76 +/- 1984.85 | 1788.37 +/- 1757.10 |
| ema55 | 2011.55 +/- 1914.39 | 2285.95 +/- 1979.10 | 1786.58 +/- 1760.47 |
| ma200 | 1967.50 +/- 1849.95 | 2230.39 +/- 1913.75 | 1741.07 +/- 1717.13 |


## Post-2019 Statistical Profile

**Total signals:** 95

**Class distribution:**
- Buy: 37 (38.9%)
- Cash: 43 (45.3%)
- Sell: 15 (15.8%)

### Boolean Feature Frequencies (% True)

| Feature | Buy | Cash | Sell |
| --- | --- | --- | --- |
| ema9_above_ema21 | 75.7% | 51.2% | 13.3% |
| ema21_above_ema55 | 81.1% | 81.4% | 60.0% |
| close_above_ma200 | 94.6% | 88.4% | 73.3% |
| close_above_ema9 | 86.5% | 27.9% | 20.0% |
| close_above_ema21 | 91.9% | 34.9% | 13.3% |
| close_above_ema55 | 91.9% | 55.8% | 6.7% |
| macd_histogram_positive | 62.2% | 20.9% | 26.7% |
| macd_above_signal | 62.2% | 20.9% | 26.7% |

### Continuous Feature Summary (mean +/- std)

| Feature | Buy | Cash | Sell |
| --- | --- | --- | --- |
| macd | 92.93 +/- 181.12 | 30.01 +/- 176.79 | -113.59 +/- 225.41 |
| macd_signal | 81.38 +/- 170.93 | 60.83 +/- 170.00 | -80.42 +/- 176.83 |
| macd_histogram | 11.55 +/- 66.60 | -30.82 +/- 53.93 | -33.18 +/- 114.62 |
| ema9 | 15445.28 +/- 4347.15 | 15161.87 +/- 4450.40 | 16262.71 +/- 3696.20 |
| ema21 | 15358.60 +/- 4356.83 | 15157.93 +/- 4441.13 | 16386.13 +/- 3648.97 |
| ema55 | 15144.59 +/- 4347.50 | 14973.99 +/- 4391.60 | 16446.13 +/- 3592.87 |
| ma200 | 14148.95 +/- 4031.96 | 13973.43 +/- 4010.12 | 15697.52 +/- 3418.97 |


## Decision Tree: Pre-2019
Feature set: ema9_above_ema21, ema21_above_ema55, close_above_ma200, close_above_ema9, close_above_ema21, close_above_ema55, macd_histogram_positive, macd_above_signal
Train accuracy: 56.7%
Cross-validated accuracy: 53.9%

```
|--- close_above_ema9 <= 0.50
|   |--- ema21_above_ema55 <= 0.50
|   |   |--- macd_above_signal <= 0.50
|   |   |   |--- close_above_ma200 <= 0.50
|   |   |   |   |--- weights: [15.62, 27.34, 38.88] class: Sell
|   |   |   |--- close_above_ma200 >  0.50
|   |   |   |   |--- weights: [7.81, 8.79, 4.20] class: Cash
|   |   |--- macd_above_signal >  0.50
|   |   |   |--- close_above_ma200 <= 0.50
|   |   |   |   |--- weights: [3.91, 30.27, 25.22] class: Cash
|   |   |   |--- close_above_ma200 >  0.50
|   |   |   |   |--- weights: [0.00, 13.67, 9.46] class: Cash
|   |--- ema21_above_ema55 >  0.50
|   |   |--- macd_above_signal <= 0.50
|   |   |   |--- close_above_ema21 <= 0.50
|   |   |   |   |--- weights: [13.67, 60.53, 107.19] class: Sell
|   |   |   |--- close_above_ema21 >  0.50
|   |   |   |   |--- weights: [1.95, 7.81, 25.22] class: Sell
|   |   |--- macd_above_signal >  0.50
|   |   |   |--- close_above_ema21 <= 0.50
|   |   |   |   |--- weights: [0.00, 9.76, 11.56] class: Sell
|   |   |   |--- close_above_ema21 >  0.50
|   |   |   |   |--- weights: [2.93, 6.83, 5.25] class: Cash
|--- close_above_ema9 >  0.50
|   |--- ema9_above_ema21 <= 0.50
|   |   |--- close_above_ema21 <= 0.50
|   |   |   |--- close_above_ma200 <= 0.50
|   |   |   |   |--- weights: [39.05, 6.83, 2.10] class: Buy
|   |   |   |--- close_above_ma200 >  0.50
|   |   |   |   |--- weights: [23.43, 3.91, 4.20] class: Buy
|   |   |--- close_above_ema21 >  0.50
|   |   |   |--- close_above_ma200 <= 0.50
|   |   |   |   |--- weights: [27.34, 12.69, 2.10] class: Buy
|   |   |   |--- close_above_ma200 >  0.50
|   |   |   |   |--- weights: [47.84, 9.76, 6.31] class: Buy
|   |--- ema9_above_ema21 >  0.50
|   |   |--- close_above_ema55 <= 0.50
|   |   |   |--- weights: [1.95, 0.98, 5.25] class: Sell
|   |   |--- close_above_ema55 >  0.50
|   |   |   |--- macd_histogram_positive <= 0.50
|   |   |   |   |--- weights: [29.29, 34.17, 14.71] class: Cash
|   |   |   |--- macd_histogram_positive >  0.50
|   |   |   |   |--- weights: [74.20, 55.65, 27.32] class: Buy
```

### Extracted Rules (Pre-2019)

1. Sell when NOT close_above_ema9 AND NOT ema21_above_ema55 AND NOT macd_above_signal AND NOT close_above_ma200: 48% confidence (N=81)
2. Cash when NOT close_above_ema9 AND NOT ema21_above_ema55 AND NOT macd_above_signal AND close_above_ma200: 42% confidence (N=21)
3. Cash when NOT close_above_ema9 AND NOT ema21_above_ema55 AND macd_above_signal AND NOT close_above_ma200: 51% confidence (N=59)
4. Cash when NOT close_above_ema9 AND NOT ema21_above_ema55 AND macd_above_signal AND close_above_ma200: 59% confidence (N=23)
5. Sell when NOT close_above_ema9 AND ema21_above_ema55 AND NOT macd_above_signal AND NOT close_above_ema21: 59% confidence (N=178)
6. Sell when NOT close_above_ema9 AND ema21_above_ema55 AND NOT macd_above_signal AND close_above_ema21: 72% confidence (N=34)
7. Sell when NOT close_above_ema9 AND ema21_above_ema55 AND macd_above_signal AND NOT close_above_ema21: 54% confidence (N=21)
8. Cash when NOT close_above_ema9 AND ema21_above_ema55 AND macd_above_signal AND close_above_ema21: 46% confidence (N=15)
9. Buy when close_above_ema9 AND NOT ema9_above_ema21 AND NOT close_above_ema21 AND NOT close_above_ma200: 81% confidence (N=49)
10. Buy when close_above_ema9 AND NOT ema9_above_ema21 AND NOT close_above_ema21 AND close_above_ma200: 74% confidence (N=32)
11. Buy when close_above_ema9 AND NOT ema9_above_ema21 AND close_above_ema21 AND NOT close_above_ma200: 65% confidence (N=43)
12. Buy when close_above_ema9 AND NOT ema9_above_ema21 AND close_above_ema21 AND close_above_ma200: 75% confidence (N=65)
13. Sell when close_above_ema9 AND ema9_above_ema21 AND NOT close_above_ema55: 64% confidence (N=8)
14. Cash when close_above_ema9 AND ema9_above_ema21 AND close_above_ema55 AND NOT macd_histogram_positive: 44% confidence (N=79)
15. Buy when close_above_ema9 AND ema9_above_ema21 AND close_above_ema55 AND macd_histogram_positive: 47% confidence (N=159)

## Decision Tree: Post-2019
Feature set: ema9_above_ema21, ema21_above_ema55, close_above_ma200, close_above_ema9, close_above_ema21, close_above_ema55, macd_histogram_positive, macd_above_signal
Train accuracy: 62.1%
Cross-validated accuracy: 58.9%
**NOTE:** Post-2019 has only 95 samples (Sell=15). Rules are tentative.

```
|--- close_above_ema55 <= 0.50
|   |--- macd_histogram_positive <= 0.50
|   |   |--- close_above_ma200 <= 0.50
|   |   |   |--- weights: [0.00, 2.95, 4.22] class: Sell
|   |   |--- close_above_ma200 >  0.50
|   |   |   |--- weights: [1.71, 9.57, 19.00] class: Sell
|   |--- macd_histogram_positive >  0.50
|   |   |--- weights: [0.86, 1.47, 6.33] class: Sell
|--- close_above_ema55 >  0.50
|   |--- close_above_ema9 <= 0.50
|   |   |--- close_above_ema21 <= 0.50
|   |   |   |--- weights: [0.86, 6.63, 0.00] class: Cash
|   |   |--- close_above_ema21 >  0.50
|   |   |   |--- weights: [1.71, 3.68, 0.00] class: Cash
|   |--- close_above_ema9 >  0.50
|   |   |--- ema21_above_ema55 <= 0.50
|   |   |   |--- weights: [4.28, 0.74, 0.00] class: Buy
|   |   |--- ema21_above_ema55 >  0.50
|   |   |   |--- macd_histogram_positive <= 0.50
|   |   |   |   |--- weights: [7.70, 2.95, 0.00] class: Buy
|   |   |   |--- macd_histogram_positive >  0.50
|   |   |   |   |--- weights: [14.55, 3.68, 2.11] class: Buy
```

### Extracted Rules (Post-2019)

1. Sell when NOT close_above_ema55 AND NOT macd_histogram_positive AND NOT close_above_ma200: 59% confidence (N=6)
2. Sell when NOT close_above_ema55 AND NOT macd_histogram_positive AND close_above_ma200: 63% confidence (N=24)
3. Sell when NOT close_above_ema55 AND macd_histogram_positive: 73% confidence (N=6)
4. Cash when close_above_ema55 AND NOT close_above_ema9 AND NOT close_above_ema21: 89% confidence (N=10)
5. Cash when close_above_ema55 AND NOT close_above_ema9 AND close_above_ema21: 68% confidence (N=7)
6. Buy when close_above_ema55 AND close_above_ema9 AND NOT ema21_above_ema55: 85% confidence (N=6)
7. Buy when close_above_ema55 AND close_above_ema9 AND ema21_above_ema55 AND NOT macd_histogram_positive: 72% confidence (N=13)
8. Buy when close_above_ema55 AND close_above_ema9 AND ema21_above_ema55 AND macd_histogram_positive: 72% confidence (N=23)

## Era Comparison (DISC-04)

### Feature Importance Changes

| Feature | Pre-2019 Importance | Post-2019 Importance | Change |
| --- | --- | --- | --- |
| ema9_above_ema21 | 0.138 | 0.000 | -0.138 |
| ema21_above_ema55 | 0.042 | 0.005 | -0.037 |
| close_above_ma200 | 0.029 | 0.004 | -0.026 |
| close_above_ema9 | 0.702 | 0.273 | -0.429 |
| close_above_ema21 | 0.019 | 0.011 | -0.007 |
| close_above_ema55 | 0.023 | 0.687 | +0.664 |
| macd_histogram_positive | 0.008 | 0.019 | +0.012 |
| macd_above_signal | 0.039 | 0.000 | -0.039 |

### Rule Pattern Differences

**Pre-2019 top features:** close_above_ema9, ema9_above_ema21
**Post-2019 top features:** close_above_ema55, close_above_ema9

Shared dominant features: close_above_ema9

Average rule confidence: Pre-2019=59%, Post-2019=73%

**Warning:** Post-2019 era has only 95 samples with Sell=15. Rules from this era should be treated as tentative hypotheses requiring out-of-sample validation, not definitive trading rules.