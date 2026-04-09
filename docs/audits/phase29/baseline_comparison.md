# Phase 29 Baseline Comparison — `canslim` table

Compares `CanslimScorer` output against the upstream MySQL `stocks_backend.canslim` table (composite `tong_diem` + component percentiles), VN100-restricted.

## Methodology

- For each quarter in `canslim` with ≥ `min-tickers` VN100 rows:
  - Map quarter label → last trading day in `stock_eod`.
  - Run `CanslimScorer.score(last_trading_day)`, restrict to VN100.
  - Load baseline `canslim` frame for that quarter, restrict to VN100.
- **Top-10 overlap:** count intersection of top-10 by composite score.
- **Spearman ρ:** rank correlation between our `score` and baseline `tong_diem` on ticker intersection.
- **Per-component agreement:** map our booleans to baseline percentile columns with gate ≥ 70; report (both_pass + both_fail) / total.

**Acceptance gate:** Spearman ρ ≥ 0.5 on ≥ 70% of quarters.

**Quarterly-vs-daily caveat:** baseline is QUARTERLY; scorer is daily. We use the last trading day of the quarter as the `as_of_date` proxy so any intra-quarter drift in daily features (N, S, RS, I, Liq) is visible to the scorer but not to the baseline. Some divergence is EXPECTED here — especially on the technical rules.

## Verdict

- Quarters compared: **28**
- Errors: 0
- Median Spearman ρ: **0.280**
- Quarters with ρ ≥ 0.5: **1/28 (4%)**
- Mean top-10 overlap: 2.43 / 10
- **Result: FAIL**

## Per-quarter metrics

| quarter | as_of | n_ours | n_base | n_common | top10_overlap | spearman | c_agree | a_agree | s_agree |
|---|---|---|---|---|---|---|---|---|---|
| Q1 2019 | 2019-03-31 | 84 | 72 | 62 | 1/10 | 0.184 | 85% | 84% | 71% |
| Q2 2019 | 2019-06-30 | 88 | 97 | 88 | 2/10 | 0.150 | 84% | 82% | 67% |
| Q3 2019 | 2019-09-30 | 89 | 96 | 88 | 2/10 | 0.312 | 81% | 84% | 67% |
| Q4 2019 | 2019-12-31 | 90 | 97 | 90 | 2/10 | 0.265 | 73% | 86% | 73% |
| Q1 2020 | 2020-03-31 | 91 | 98 | 91 | 3/10 | 0.281 | 84% | 85% | 60% |
| Q2 2020 | 2020-06-30 | 92 | 97 | 92 | 2/10 | 0.225 | 73% | 83% | 76% |
| Q3 2020 | 2020-09-30 | 92 | 97 | 92 | 2/10 | 0.323 | 73% | 75% | 67% |
| Q4 2020 | 2020-12-31 | 92 | 98 | 92 | 3/10 | 0.437 | 78% | 73% | 65% |
| Q1 2021 | 2021-03-31 | 92 | 98 | 92 | 2/10 | 0.445 | 73% | 68% | 63% |
| Q2 2021 | 2021-06-30 | 92 | 98 | 92 | 1/10 | 0.530 | 70% | 70% | 60% |
| Q3 2021 | 2021-09-30 | 92 | 98 | 92 | 3/10 | 0.378 | 67% | 66% | 68% |
| Q4 2021 | 2021-12-31 | 94 | 96 | 92 | 2/10 | 0.166 | 72% | 65% | 55% |
| Q1 2022 | 2022-03-31 | 96 | 99 | 96 | 5/10 | 0.279 | 71% | 70% | 60% |
| Q2 2022 | 2022-06-30 | 96 | 99 | 96 | 2/10 | 0.361 | 73% | 71% | 72% |
| Q3 2022 | 2022-09-30 | 97 | 99 | 97 | 2/10 | 0.421 | 74% | 68% | 54% |
| Q4 2022 | 2022-12-31 | 97 | 99 | 97 | 3/10 | 0.444 | 82% | 68% | 79% |
| Q1 2023 | 2023-03-31 | 98 | 99 | 98 | 4/10 | 0.177 | 92% | 77% | 60% |
| Q2 2023 | 2023-06-30 | 98 | 99 | 98 | 3/10 | 0.172 | 68% | 72% | 72% |
| Q3 2023 | 2023-09-30 | 98 | 99 | 98 | 2/10 | 0.240 | 63% | 69% | 79% |
| Q4 2023 | 2023-12-31 | 98 | 99 | 98 | 2/10 | 0.364 | 53% | 72% | 66% |
| Q1 2024 | 2024-03-31 | 98 | 99 | 98 | 1/10 | 0.259 | 49% | 61% | 61% |
| Q2 2024 | 2024-06-30 | 98 | 99 | 98 | 3/10 | 0.186 | 62% | 63% | 65% |
| Q3 2024 | 2024-09-30 | 98 | 99 | 98 | 3/10 | 0.249 | 60% | 60% | 63% |
| Q4 2024 | 2024-12-31 | 98 | 99 | 98 | 4/10 | 0.289 | 53% | 63% | 57% |
| Q1 2025 | 2025-03-31 | 98 | 99 | 98 | 3/10 | 0.325 | 60% | 63% | 64% |
| Q2 2025 | 2025-06-30 | 98 | 99 | 98 | 2/10 | 0.345 | 55% | 56% | 71% |
| Q3 2025 | 2025-09-30 | 99 | 99 | 98 | 2/10 | 0.004 | 49% | 54% | 57% |
| Q4 2025 | 2025-12-31 | 99 | 100 | 99 | 2/10 | 0.151 | 56% | 55% | 64% |

## Per-quarter top-10 lists

### Q1 2019 (2019-03-31) — overlap 1/10, ρ=0.184
- ours: `VCB, VCG, PHR, PPC, BID, EIB, BWE, BCM, VIX, KBC`
- base: `HDG, VCB, FTS, STB, VTP, MBB, ACB, PC1, VIB, NAB`
- overlap: `VCB`

### Q2 2019 (2019-06-30) — overlap 2/10, ρ=0.150
- ours: `VCB, TPB, VCG, PHR, STB, PPC, GVR, EIB, BWE, SAB`
- base: `HDG, DGC, VCB, FTS, ANV, TPB, DGW, VIB, MBB, VHC`
- overlap: `TPB, VCB`

### Q3 2019 (2019-09-30) — overlap 2/10, ρ=0.312
- ours: `VCB, BID, MBB, VPB, PHR, HDC, MWG, FPT, REE, TCH`
- base: `HDG, VCB, DGW, MBB, ANV, VHM, SHB, TPB, MSB, HDB`
- overlap: `MBB, VCB`

### Q4 2019 (2019-12-31) — overlap 2/10, ρ=0.265
- ours: `VCB, BID, VPB, HDB, EIB, MBB, SHB, TCH, HDC, FPT`
- base: `HDB, DGW, TPB, MBB, VHM, OCB, VPI, TCB, CTG, HDG`
- overlap: `HDB, MBB`

### Q1 2020 (2020-03-31) — overlap 3/10, ρ=0.281
- ours: `SHB, CTG, TPB, EIB, VPB, EVF, KOS, VPI, MBB, BID`
- base: `DGW, OCB, VPI, TPB, HDB, VHM, BWE, HDC, EVF, DBC`
- overlap: `EVF, TPB, VPI`

### Q2 2020 (2020-06-30) — overlap 2/10, ρ=0.225
- ours: `HSG, VIB, SHB, DCM, VPB, DGW, DGC, HAG, HPG, FTS`
- base: `DBC, DGW, TPB, SZC, HDB, VPB, MSB, OCB, HDC, TCB`
- overlap: `DGW, VPB`

### Q3 2020 (2020-09-30) — overlap 2/10, ρ=0.323
- ours: `STB, VIB, HDB, SHB, LPB, TPB, DCM, VSC, CTG, HSG`
- base: `DBC, DGW, TPB, TCH, HDB, HPG, PDR, TCB, VND, BWE`
- overlap: `HDB, TPB`

### Q4 2020 (2020-12-31) — overlap 3/10, ρ=0.437
- ours: `VIB, LPB, STB, SHB, VND, CTS, TCB, CTG, HDC, KBC`
- base: `DGW, HPG, VND, VIB, HSG, CTR, VHM, VIX, TCB, DBC`
- overlap: `TCB, VIB, VND`

### Q1 2021 (2021-03-31) — overlap 2/10, ρ=0.445
- ours: `VIB, SHB, TCB, VPB, LPB, CTG, EVF, MBB, ACB, STB`
- base: `HPG, DGW, HSG, VIX, VND, VIB, SIP, TCB, CTR, VCI`
- overlap: `TCB, VIB`

### Q2 2021 (2021-06-30) — overlap 1/10, ρ=0.530
- ours: `LPB, VPB, MBB, TCB, CTG, EIB, SHB, TPB, STB, VIB`
- base: `VND, DGW, HSG, HPG, VIX, HDC, FTS, TCB, NAB, NKG`
- overlap: `TCB`

### Q3 2021 (2021-09-30) — overlap 3/10, ρ=0.378
- ours: `VPB, TPB, EVF, TCB, DPM, DCM, STB, SHB, NKG, HDC`
- base: `NKG, HSG, HPG, HDC, FTS, NAB, TCB, HCM, MSB, VND`
- overlap: `HDC, NKG, TCB`

### Q4 2021 (2021-12-31) — overlap 2/10, ρ=0.166
- ours: `EIB, FRT, MSB, EVF, TPB, DIG, HAG, CII, VND, CTS`
- base: `DGC, FTS, NKG, SZC, CTS, BSI, DPM, SSI, VND, HPG`
- overlap: `CTS, VND`

### Q1 2022 (2022-03-31) — overlap 5/10, ρ=0.279
- ours: `STB, EIB, VGC, EVF, FRT, DPM, DGC, VHC, VIB, DXG`
- base: `DGC, FRT, DCM, DPM, NKG, CTS, FTS, VHC, BSI, VGC`
- overlap: `DGC, DPM, FRT, VGC, VHC`

### Q2 2022 (2022-06-30) — overlap 2/10, ρ=0.361
- ours: `EIB, SSB, STB, PNJ, GAS, HDB, BID, VHC, SHB, ANV`
- base: `VHC, DCM, DGC, DPM, VGC, LPB, GAS, VPI, FRT, TCB`
- overlap: `GAS, VHC`

### Q3 2022 (2022-09-30) — overlap 2/10, ρ=0.421
- ours: `EIB, VCB, BCM, SSB, VPI, LPB, TPB, HDB, BWE, PNJ`
- base: `DCM, DGC, DPM, VHC, LPB, ANV, GAS, PNJ, MBB, TLG`
- overlap: `LPB, PNJ`

### Q4 2022 (2022-12-31) — overlap 3/10, ρ=0.444
- ours: `VCB, CTG, STB, BID, ACB, OCB, SSB, LPB, NT2, KDC`
- base: `HAG, BID, ANV, BMP, EIB, GAS, NT2, DCM, PNJ, STB`
- overlap: `BID, NT2, STB`

### Q1 2023 (2023-03-31) — overlap 4/10, ρ=0.177
- ours: `CTG, BID, STB, VCB, LPB, VRE, ACB, HDB, VCI, KOS`
- base: `HAG, BID, NT2, STB, BMP, VCB, CTG, EIB, ANV, VPI`
- overlap: `BID, CTG, STB, VCB`

### Q2 2023 (2023-06-30) — overlap 3/10, ρ=0.172
- ours: `STB, NAB, SHB, BMP, CTD, BSI, OCB, CTS, SSI, PVD`
- base: `VHM, STB, KBC, IMP, BMP, VRE, HAG, VCB, CTD, CTR`
- overlap: `BMP, CTD, STB`

### Q3 2023 (2023-09-30) — overlap 2/10, ρ=0.240
- ours: `EVF, NAB, HDB, FTS, CTS, BSI, DGC, GMD, FRT, VIX`
- base: `IMP, VHM, STB, VRE, CTD, BMP, SJS, BSI, OCB, VIX`
- overlap: `BSI, VIX`

### Q4 2023 (2023-12-31) — overlap 2/10, ρ=0.364
- ours: `EVF, MBB, VIB, BSI, FTS, NKG, DBC, TCH, HDB, BMP`
- base: `VRE, HAG, STB, VIX, VJC, CTS, CTD, TCH, IMP, BSI`
- overlap: `BSI, TCH`

### Q1 2024 (2024-03-31) — overlap 1/10, ρ=0.259
- ours: `NAB, TCB, LPB, HDB, EVF, ACB, PHR, FRT, CTR, FTS`
- base: `CTS, VIX, VJC, TCH, HDB, VCG, PVD, SSI, PPC, CTD`
- overlap: `HDB`

### Q2 2024 (2024-06-30) — overlap 3/10, ρ=0.186
- ours: `LPB, GVR, HDB, FRT, TCH, CTR, NAB, EVF, DBC, STB`
- base: `HDB, LPB, SSI, TCH, CTD, GEE, SCS, HCM, HPG, PAN`
- overlap: `HDB, LPB, TCH`

### Q3 2024 (2024-09-30) — overlap 3/10, ρ=0.249
- ours: `LPB, HDB, MBB, CTG, STB, NAB, BMP, BID, FRT, GVR`
- base: `LPB, HDB, NAB, SCS, TCH, PAN, HPG, CTD, VJC, TLG`
- overlap: `HDB, LPB, NAB`

### Q4 2024 (2024-12-31) — overlap 4/10, ρ=0.289
- ours: `CTG, LPB, STB, HDB, NAB, BCM, TLG, EIB, FRT, BMP`
- base: `SCS, FRT, LPB, DBC, GEE, VIC, STB, TLG, CTD, GVR`
- overlap: `FRT, LPB, STB, TLG`

### Q1 2025 (2025-03-31) — overlap 3/10, ρ=0.325
- ours: `CTG, SHB, STB, EIB, VIC, LPB, GEE, NAB, VHM, MSB`
- base: `GEE, FRT, SCS, VHM, STB, DBC, SJS, GVR, NLG, GEX`
- overlap: `GEE, STB, VHM`

### Q2 2025 (2025-06-30) — overlap 2/10, ρ=0.345
- ours: `MBB, EIB, TCB, CTG, DBC, PAN, GEX, SBT, STB, NAB`
- base: `FRT, DBC, GEE, ANV, GVR, SJS, STB, MWG, BMP, DXS`
- overlap: `DBC, STB`

### Q3 2025 (2025-09-30) — overlap 2/10, ρ=0.004
- ours: `LPB, STB, SHB, HDB, GEE, CII, GEX, VPB, VRE, HT1`
- base: `CTS, ANV, VIX, FRT, SHB, PHR, VCG, STB, DBC, DXS`
- overlap: `SHB, STB`

### Q4 2025 (2025-12-31) — overlap 2/10, ρ=0.151
- ours: `VPB, HDB, STB, SHB, GEE, SBT, EVF, VJC, PVD, MWG`
- base: `ANV, VIX, FRT, MWG, NT2, CTS, VPB, DIG, CTD, KBC`
- overlap: `MWG, VPB`

## Per-component aggregate agreement

| our_rule | baseline_col | mean_agree_rate | n_quarters |
|---|---|---|---|
| c_pass | eps_quy_gan_nhat | 69% | 28 |
| a_pass | eps_trailing_12_thang | 70% | 28 |
| s_pass | sale_quy_gan_nhat | 66% | 28 |
