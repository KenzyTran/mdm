# CANSLIM Quantitative Rules — Research Findings for VN100

**Researched:** 2026-04-08
**Confidence:** MEDIUM-HIGH (HIGH for US academic basis, LOW for Vietnam-specific)

## 1. Executive Summary

Three waves of academic operationalization:
1. **Reinganum (1988)** — pre-CANSLIM academic basis; 9-screen and 4-screen models from 222 doublers 1970-1983
2. **Lutey, Crum, Rayome (2014, 2017)** — canonical modern replications; distill to 3-4 computable rules
3. **AAII CANSLIM Revised 3rd Ed** (live since 1998) + **Validea O'Neil Guru Model**

| Letter | Academic consensus | VN100 feasibility | Confidence |
|---|---|---|---|
| C | HIGH (18-25% YoY) | HIGH | HIGH |
| A | HIGH (20-25% CAGR) | MEDIUM | MEDIUM-HIGH |
| N | HIGH (within 5-15% of 52wk high) | HIGH | HIGH |
| S | MEDIUM | LOW (float data unreliable) | MEDIUM |
| L | HIGH (IBD RS ≥ 80) | HIGH (price-only) | HIGH |
| I | LOW (proxies only) | LOW | LOW |
| M | Replaced by MDM | N/A | N/A |

---

## 2. Letter-by-Letter

### C — Current Quarterly EPS Growth (YoY)

- O'Neil: ≥18-20%, prefers 25%+. Acceleration: current > prior quarters' growth.
- Lutey OPBM II: ≥25%
- AAII Revised 3rd Ed: ≥20% + accelerating vs prior 2 Q
- Validea O'Neil: ≥18% pass / ≥25% top
- Reinganum: acceleration rule (last 5Q > prior 5Q)

**Data:** Quarterly diluted EPS + **announcement date** (avoid look-ahead). Last 8 quarters.

### A — Annual EPS Growth

- O'Neil: ≥25% each of 3 years
- Lutey OPBM II: 5-yr avg >20% (strict each-year leaves no survivors)
- AAII Revised 3rd Ed: 3-yr avg ≥25%, no yearly decline
- Validea: 3-yr avg ≥25%, EPS positive each of 5 yr

**Data:** Annual EPS for 5 fiscal years; ROE optional.

### N — New Highs

- Lutey: close > max(close[-252]) OR within 5%
- AAII: within 10%
- Validea: within 15% pass / 5% top
- **George & Hwang (2004) JF "The 52-Week High and Momentum Investing"** — peer-reviewed validation that nearness to 52wk high predicts returns independently of Jegadeesh-Titman

**Data:** Daily adjusted close prior 252 days. Trivial.

### S — Supply & Demand

- Reinganum: shares out <20M (exact)
- Lutey: dropped (regime-dependent), replaced with price >$10
- AAII: volume ≥1.5× 50d avg + IBD A/D rating
- Validea: float <30M preferred

**Vietnam caveat:** free float misclassified (state/family). **Volume surge is the reliable computable S proxy.**

### L — Leaders (Relative Strength)

**IBD formula (public):**
```
StrengthFactor = 0.4 * ROC(C, 63)
               + 0.2 * ROC(C, 126)
               + 0.2 * ROC(C, 189)
               + 0.2 * ROC(C, 252)
```
Percentile-rank across universe → 1-99.

- O'Neil: ≥80
- Reinganum 4-screen: ≥70 + accelerating
- AAII / Validea: ≥80 / ≥90 top

**Most reliable letter for VN100 — purely price-based.**

### I — Institutional Sponsorship

Most replications drop or proxy. Common proxies:
1. Accumulation/Distribution (up-vol vs down-vol 13W)
2. OBV slope >0
3. MFI rising
4. Rising ADTV QoQ
5. Block trade %

**Vietnam-specific opportunity:** HOSE publishes daily **foreign net buy** (VND). Far cleaner than US A/D hacks. **Recommend `sum(foreign_net_buy[T-20..T-1]) > 0` as primary**, with 13W A/D as fallback.

### M — Market Direction

**REPLACED BY MDM GATE.** Per project scope.

---

## 3. Paper Summaries

### Reinganum (1988) "The Anatomy of a Stock Market Winner" — FAJ Vol 44 No 2
222 NYSE/AMEX/OTC doublers 1970-1983.
- 9-screen (RS accel, RS≥70, P/B<1, 5Q EPS accel, margin rising, shares<20M, insider holdings, within 15% of 2yr high, ≥1Q accel in last 5)
- 4-screen: RS>70 AND RS_curr>RS_prior AND P/B<1 AND shares<20M
- Result: ~37% annual vs S&P ~11% (in-sample, survivorship)
- **P/B<1 contradicts O'Neil's "buy strength"** — Reinganum cited as partial validation only

### Lutey, Crum, Rayome — OPBM II (2014, JAF)
3 rules: 5yr EPS CAGR>20%, current Q EPS YoY>25%, price>$10. Nasdaq 100, 2010-13 quarterly. Beat by ~0.94%/mo.

### Lutey et al. — Live OOS (2017, JAF)
S&P 500/Nasdaq 100/DJIA Jul 2014-Feb 2017. +20%/+9%/+17% cumulative excess. Bull-window only.

### AAII CANSLIM Revised 3rd Ed (live since 1998)
Q EPS YoY≥20% accel; 3yr avg≥25% no decline; ROE≥17%; RS≥80; within 10% 52wk high; brk vol≥1.5× 50d; shareholders growing.
- Since 1998 ~24.4%/yr vs S&P ~8% (paper screen, monthly rebal, no costs)

### Validea O'Neil Guru Model
C≥18%/25% top; A 3yr≥25%, EPS+ each 5yr; RS≥80/90 top; within 15% 52wk high; float<30M. Live ~match S&P 20+ years, higher DD.

### Vietnam / EM
**No peer-reviewed CANSLIM-on-Vietnam study found.** Indonesian study: did NOT outperform. German: "not same effectiveness".
**→ Do not import US thresholds blindly. Validate in-sample 2013-2018, OOS 2019-2025. Be prepared to loosen.**

---

## 4. RECOMMENDED RULES FOR VN100 (v7.0 baseline)

### 4.1 Rule Set

| Letter | Rule | Threshold | Rationale |
|---|---|---|---|
| **C** | Latest Q EPS YoY | **≥20%** | Mid 18-25% band; VN fewer hyper-growers |
| **C+** | EPS acceleration | latest > mean(prior 2Q) | O'Neil acceleration |
| **A** | 3yr EPS CAGR | **≥15%** | Looser than 25% — VN earnings more volatile. Sweep [10,15,20,25] |
| **A+** | EPS positive each of last 3yr | required | Quality |
| **N** | Close within X% of 252d high | **≤15%** | 7% daily limit compresses. Sweep [5,10,15,20] |
| **S** | Brk vol vs 50d avg | **≥1.5×** | Standard |
| **S+** | Shares outstanding | **SKIP** | Float unreliable in VN |
| **L** | IBD RS rating (VN100 universe) | **≥80** | Standard. 0.4/0.2/0.2/0.2 weighted ROC, percentile-rank |
| **I** | Foreign net-buy 20d sum | **>0** | VN-specific, public, cleaner than A/D |
| **I alt** | 13W A/D rating | **≥50 pct** | Fallback if FO room capped |
| **M** | MDM gate | == BUY | Replaces market direction |
| **Liquidity** | 20d median turnover | **≥5B VND** | Tradability |

### 4.2 Entry Logic

```python
BUY ticker on day T if ALL of:
  - C:  eps_q_yoy(t,T) >= 0.20
  - C+: eps_q_yoy(t,T) > mean(eps_q_yoy(t,T-1), eps_q_yoy(t,T-2))
  - A:  eps_annual_cagr_3y(t,T) >= 0.15
  - A+: eps_annual(t,y) > 0 for y in {T-3y, T-2y, T-1y}
  - N:  close(T) / max(close[T-252..T]) >= 0.85
  - S:  volume(T) / mean(volume[T-50..T-1]) >= 1.5
  - L:  rs_rating(t,T,universe=VN100) >= 80
  - I:  sum(foreign_net_buy[T-20..T-1]) > 0
  - M:  mdm_state(T) == BUY
  - Liquidity: 20d median turnover >= 5e9 VND
```

### 4.3 Required Data

| Field | Source | Frequency |
|---|---|---|
| OHLCV daily | Postgres `stock_eod` | Daily |
| **Adjusted close** | Verify; may compute | Daily |
| Quarterly EPS + **announcement date** | MySQL `is_quarter_*` (need publish_date column) | Quarterly |
| Annual EPS | MySQL `is_year_*` | Annual |
| Foreign net buy VND | Postgres `stock_foreign_eod` | Daily |
| Shares outstanding | MySQL `ratios_stock` | Event |
| VN100 membership | HOSE / `stock_list.nhomtop` | Semi-annual |

**CRITICAL:** Use **announcement date + 1**, not `quarter_end_date`.

### 4.4 Sweep Grid

| Param | Grid |
|---|---|
| `c_yoy_threshold` | 0.10, 0.15, 0.20, 0.25 |
| `a_cagr_threshold` | 0.10, 0.15, 0.20, 0.25 |
| `n_proximity_pct` | 0.05, 0.10, 0.15, 0.20 |
| `s_volume_multiple` | 1.25, 1.5, 2.0 |
| `l_rs_threshold` | 70, 80, 90 |
| `i_proxy_window` | 10, 20, 40 days |
| `i_proxy_rule` | foreign_flow / ad_rating / both |

In-sample: 2013-2018. OOS: 2019-2025.

### 4.5 Anti-Rules

1. **Do not** use Reinganum's P/B<1 — contradicts "buy strength"
2. **Do not** require shares out <25M on VN100 — empties universe
3. **Do not** require annual EPS growth ≥25% each year — leaves <5 stocks
4. **Do not** trust reported free-float without verification
5. **Do not** use intraday breakout in V1 — T+2 settlement; close-based only

---

## 5. Open Questions

1. **Adjusted close** — does Postgres `stock_eod.closeprice` adjust for splits/divs/rights? Verify before coding.
2. **EPS announcement date** — does MySQL `is_quarter_*` have publish_date or only `thoigian` (period)?
3. **VN100 point-in-time membership** — `stock_list.nhomtop` static or has effective dates?
4. **FO room capped tickers** — need fallback for FPT/MWG when at limit
5. **VAS quarterly EPS** may include non-operating gains — consider **NPAT attributable to parent** instead

---

## Sources

- Reinganum (1988) — Hillsdale PDF / JSTOR / CFA Institute
- Lutey/Crum/Rayome — OPBM II (JAF 2014); Live OOS (JAF 2017)
- Towards a Simplified CAN SLIM Model — Applied Finance Letters 2023
- AAII — Investing in Proven Growth Using CAN SLIM Revised; Performance History; O'Neil Screen
- Validea Guru Model Matrix
- George & Hwang (2004) — The 52-Week High and Momentum Investing (JF)
- IBD RS — skyte/relative-strength (GitHub), TradingView Skyte
- TraderLion / Liberated Stock Trader / QuantifiedStrategies / Analyzing Alpha CANSLIM guides
