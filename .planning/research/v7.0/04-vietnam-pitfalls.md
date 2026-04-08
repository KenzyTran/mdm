# Vietnam Market Adaptation Pitfalls — O'Neil/CANSLIM Long-Only Backtest

**Researched:** 2026-04-08
**Overall confidence:** MEDIUM-HIGH

---

## 1. VN100 Index Composition

**Construction:** VN100 = VN30 (large caps) + VNMidcap 70. From VNAllshare parent. Free-float-adjusted market-cap weighted. Liquidity + free-float screens (≥10% FF, ≥10B VND 20-day ADV). ~87-88% HOSE cap coverage. Launched 2014.

**Rebalance:** Semi-annual — **January and July only**. ~2 weeks advance notice. Backtest universe must step-change on those dates.

**Historical turnover:** ~3-8 constituent changes per review. Since 2014 (~23 reviews) cumulative unique tickers ~160-200.

**Practical workaround:**
1. **Gold standard:** Parse HOSE/Fiingroup PDFs for each Jan/Jul 2014-2026 → `vn100_membership(ticker, effective_from, effective_to)`
2. **Proxy fallback** per rebalance date d:
   - Listed on HOSE ≥180 days before d
   - Top-100 by free-float market cap at d
   - 20-day ADV > 10B VND
   - Free-float ≥10%
   - Not suspended at d
3. **NEVER use current VN100 for past dates** — classic trap (FLC, HAG, ITA, HVN, ROS all missing).
4. **IPO cooling-off:** New listings excluded ≥6 months post-listing.

---

## 2. Microstructure Traps

**Settlement:** **T+2** since 2022-08-29. Shares received ~13:00 on T+2. Buy D → sellable starting D+3. Min hold = 2 trading days.

**Price limits:**
- HOSE ±7%, HNX ±10%, UPCOM ±15%
- First trading day: HOSE ±20%, HNX ±30%, UPCOM ±40%
- Post-suspension resume: HOSE ±20%
- **Ceiling lock** → cannot buy; **floor lock** → cannot sell. Execution MUST check `next_open == ceiling AND next_high == next_low` → skip fill.

**Lot size:** 100-share HOSE/HNX. Odd lots on negotiated board only. Round DOWN.

**Costs:**
- Commission 0.10-0.35% per side (retail ~0.15%, inst ~0.10%)
- **Sell tax 0.10% gross** (always)
- Round-trip: 0.35-0.50%

**Sessions (HOSE):** ATO 9:00-9:15, continuous 9:15-11:30, lunch, continuous 13:00-14:30, **ATC 14:30-14:45**. "Open"=ATO, "Close"=ATC. Signal-on-close → fill next-day ATO.

**FOL:** 49% general, 30% banks, 0% defense/telecom. Decree 245/2025 kept sector caps. Informational for domestic VND strategy.

**Halts:** Late disclosure, audit qualifications, 5 consecutive losing quarters, fraud (FLC 2022, HVN 2023). Don't carry close forward — check `volume == 0`.

---

## 3. Fundamental Data Pitfalls

**VAS vs IFRS:** VAS statutory through ~2026. IFRS roadmap 2026-2027. VAS uses cost-basis, slower/smaller impairments. Big write-offs in Q4 audited.

**Restated financials (BIGGEST SILENT TRAP):** Q1/Q3 self-reported → H1 reviewed → annual audited. **Q4 derived by subtraction from audited annual**, often revises 20-50%. Storing only "current best" number stamped with quarter-end date = classic look-ahead.

**Mitigation — report lag rules:** Store BOTH `period_end_date` AND `publish_date`. Signal: `WHERE publish_date <= current_bar_date`. Defaults if missing:

| Period | Earliest usable |
|---|---|
| Q1 (Mar 31) | May 15 |
| Q2 (Jun 30) | Aug 15 |
| Q3 (Sep 30) | Nov 15 |
| Q4/annual | Mar 31 next year |

Regulatory: quarterly 20d (45d consolidated), H1 reviewed 45d, annual audited 90d. **C** and **A** MUST use lag dates, NOT quarter-end.

**Corporate actions:** Par 10,000 VND. TTR (total return) adjustment on major feeds. Bonus, rights, stock/cash dividends. **Must use adjusted OHLCV + adjusted historical EPS/shares.** Mixing → phantom P/E spikes. Verify `stock_eod.close` adjusted or raw.

**Sector-specific schemas:** Project has `is_quarter_stock` (securities firms = CTCK) vs `is_quarter_nonbank` vs `is_quarter_bank` vs `is_quarter_insurance`:
- **Banks** — NII, NPL, CAR; no "revenue/gross margin"
- **Securities firms (CTCK)** — trading/brokerage/margin; very volatile Q-on-Q
- **Non-financials** — standard P&L

For CANSLIM: C/A work for non-financials. Banks substitute **PPOP growth** or NI growth. CTCK EPS too noisy — exclude or 4Q trailing smoothing.

**Currency:** All VND. Verify unit in `stock_eod` (VND vs thousand-VND). Inflation 3-4% CPI — disclose real vs nominal.

---

## 4. Survivorship & Look-Ahead (Vietnam-Specific)

**Delisted tickers (CRITICAL):** First question — does `stock_eod` include delisted with final history? Audit: `SELECT COUNT(DISTINCT stockcode) WHERE max(tradingdate) < '2024-01-01'`. Zero → survivorship baked in, STOP and backfill. Notable delistings: FLC (Mar 2022 fraud), HAI/ROS/AMD (FLC group), HVN (2023).

**Fraud exits:** FLC hit consecutive floors. On halt exit, apply haircut (e.g., -20% from last close) instead of mark-to-last.

**M&A:** SHB-HBB 2012, BID-MHB 2015, HDB-DAF 2018. Map target → acquirer at swap ratio.

**New listings mid-backtest:** VHM 2018, NVL, VCB listing. Filter: `listing_date + 180d <= current_date`.

**Share count changes:** 100% bonus doubles shares → halves EPS. Historical EPS using CURRENT share count is wrong.

---

## 5. Academic Evidence

- **Momentum in Vietnam:** Mixed. Truong (Pacific-Basin Finance Journal) finds 6M/9M profitable some periods, 1-week others, nothing others. **No stable momentum premium.** Root: ~85-90% retail volume → noise-trader dominance → mean reversion beats continuation.
- **CANSLIM on Vietnam:** **No peer-reviewed study found.** VNDirect/SSI practitioner reports claim works, no OOS evidence.
- **Value/Quality:** Positive premia, stronger than momentum — consistent with EM literature.
- **Size:** Positive but partly illiquidity premium.
- **Efficiency:** Semi-strong inefficient. Insider asymmetry material. FTSE Frontier → Secondary Emerging 2025.

**Implication:** Expect lower Sharpe than US CANSLIM. Pure "RS line" weaker in VN. Value/quality overlays (low P/E + high ROE + low debt) likely add more than raw momentum.

---

## 6. Common Backtest Bugs (ranked)

1. **Equity curve `state[t]` vs `state[t-1]` look-ahead** — project hit this (707% vs 93%). Any new equity math MUST cite `state[i-1]`.
2. **Same-bar signal + execution** — fix: fill at `open[t+1]` (ATO)
3. **Forward-looking rolling indicators** — ma50 including today
4. **Ceiling/floor lock ignored**
5. **Halted stock carried forward** — volume check required
6. **Re-entry loops** — 5-day per-ticker cooldown after stop; sector: 3 stops in 10d → disable sector 20d
7. **Survivorship** — `DISTINCT ticker FROM stock_eod` returns only currently-listed
8. **Adjusted/unadjusted mismatch**
9. **Wrong calendar** — Tet ~7 trading days closed Jan/Feb
10. **One-sided costs**
11. **Cash drag ignored** — idle cash at ~3-4% VND deposit
12. **Position sizing not lot-rounded**

---

## 7. Dashboard / Reporting (Vietnam)

**Benchmarks:** VN-Index (universal), VN30 (ETFs/derivs), VN100 (apples-to-apples), E1VFVN30 / FUEVFVND (investable ETFs).

**Standard metrics:**
- Absolute & annualized return (VND)
- Excess vs VN30/VN100
- **Sharpe with risk-free = 10Y VN govt ~3.0-3.5%** (NOT 0)
- MaxDD & duration
- Hit rate, avg win/loss, profit factor
- **Inflation-adjusted CAGR** (CPI 3-4%)
- **vs 12M bank deposit (~5-6%)** — retail opportunity cost
- **vs SJC gold (VND)** — culturally expected
- **Turnover & total cost drag** explicit

---

## Critical Risks & Mitigations — Top 10

| # | Pitfall | Mitigation |
|---|---|---|
| 1 | **`state[t]` vs `state[t-1]` look-ahead** (707% vs 93% bug) | Unit test comparing both; code-review rule |
| 2 | **Delisted tickers missing from `stock_eod`** | Audit query first; STOP and backfill if empty |
| 3 | **Point-in-time VN100 membership unavailable** | Build `vn100_membership` from HOSE PDFs; until built, proxy rule documented as "proxy" |
| 4 | **EPS look-ahead via restated audited numbers** | `publish_date` column; signal `WHERE publish_date <= bar_date`; defaults +45d/+90d |
| 5 | **Ceiling/floor lock unfillable orders** | Skip if `next_open >= ref*1.0699 AND next_high == next_low` |
| 6 | **Same-bar signal+exec** | Signal at `close[t]`, fill at `open[t+1]` (ATO); unit test |
| 7 | **Halted carried forward** | Exclude if `volume[t-5:t].sum() == 0`; frozen positions no P&L until resume |
| 8 | **Adjusted/unadjusted mismatch** | Pick one convention globally; sanity check PE jumps |
| 9 | **Under-modeled costs** | Floor 0.40% round-trip: 0.15%+0.15%+0.10% tax + slippage, both sides |
| 10 | **Re-entry loops after stop** | 5-day per-ticker cooldown; sector filter |

**Honorable mentions:** 100-share lot rounding; Tet calendar; FOL room-full exclusion; bank/CTCK sector EPS handling (PPOP substitution); retail-driven mean reversion → shorter RS lookbacks (3-6M vs O'Neil's US 18M).

---

## Sources

- HOSE-Index Factsheet Jan 2025
- VN30 Constituents (Fiingroup Jul 2025)
- Ho Chi Minh City Stock Exchange — Wikipedia
- Vietnam Stock Market Regulations — Global Referral
- Vietnam reclassified to Emerging — Vietnam Briefing / LSEG FTSE Russell
- Bloomberg — Vietnam IPOs & FOL reform Sep 2025
- IFRS and VAS in Vietnam — Acclime
- KPMG VAS vs IFRS Gap Analysis Nov 2023
- Grant Thornton — VAS vs IFRS Comparison
- Does momentum work? Evidence from Vietnam — ScienceDirect (Truong)
- Towards a Simplified CAN SLIM Model — Applied Finance Letters 2023
