# Stock-Level Entry Confirmation — Research Findings

**Project:** MDM + CANSLIM long-only backtest (v7.0)
**Confidence:** MEDIUM (O'Neil is semi-qualitative; academic coverage thin but present)

---

## 1. Pivot Buy Point — definition & volume

The pivot is the end-of-base "point of least resistance" where the stock enters new high ground. Pivot rules by base type:

| Base | Duration | Depth | Pivot |
|---|---|---|---|
| **Flat base** | ≥5 weeks | ≤15% | high of base + ~$0.10 buffer |
| **Cup** | 7–65 weeks (typ 7–15) | 15–33% (to ~50% in bears) | left-cup high |
| **Cup-with-handle** | cup 7+ wks, handle 1–2 wks | cup 15–33%; handle ≤12–15%, must form in upper half of cup, drift **down** on light volume | handle high + ~$0.10 |
| **Double bottom** | 7+ weeks | 15–33% | middle peak + $0.10 |
| **Ascending base** | 9–16 weeks | 3 successive 10–20% pullbacks, each bottoming higher | high of 3rd pullback |

**Canonical O'Neil volume rule:** breakout day volume **≥ 1.5× avgvol50** (+50% vs average). 2×–3× = stronger. Confirmed across IBD, TraderLion, AAII, and the O'Neil Global Advisors 1995–2021 quant study.

**Buy zone:** pivot to pivot + 5%. Above +5% = "extended" (lower expected return, higher shakeout risk).

**$0.10 buffer:** for VND-denominated VN30 tickers, use a proportional ~0.1% buffer instead of a fixed cents amount.

**Confidence:** HIGH.

---

## 2. Follow-Through Day per stock?

**No — FTD is index-level only** (market bottom detection). That's the role MDM already fills.

**Stock-level analogue = Pocket Pivot** (Chris Kacher, 2005, built inside the O'Neil framework):

> An up-day whose volume exceeds the volume of **any down-day in the prior 10 trading days**, occurring while the stock is in or emerging from a base and typically at/above its 50-day MA.

Pocket pivots fire *earlier* than classical breakouts — they flag "institutional footprints" inside a base. This is the cleanest mechanical rule in the CANSLIM family.

Other stock-level "FTD-like" signals: first big-volume up-day after a 15–25% stock correction (Minervini's institutional-support marker); 50dma reclaim on >1.5× volume.

**Confidence:** HIGH.

---

## 3. Base-detection algorithms

### Programmatic rules

**Flat base (5 weeks):**
```
N = 25 trading days
base_high = max(highestprice, T-N..T-1)
base_low  = min(lowestprice,  T-N..T-1)
depth     = (base_high - base_low) / base_high
is_flat_base = depth <= 0.15 AND close[T-1] within 8% of base_high
```

**Cup:**
```
W in [35, 325] days
left_peak  = local max near start
bottom     = min(lowestprice) inside W
right_peak = local max near end
depth = (left_peak - bottom) / left_peak
cup = 0.15 <= depth <= 0.33 AND right_peak >= 0.95*left_peak
pivot = left_peak
```

**Cup-with-handle:** after a cup, detect 5–15 day drift where handle depth ≤12–15%, shallower than cup, in upper half of cup, with volume contraction vs. avgvol50. Pivot = max high inside handle.

### Open-source implementations
- **HumanRupert/marketsmith_pattern_recognition** (Python / zipline-reloaded) — cup-with-handle detector
- **kanwalpreet18/canslimTechnical** (Python) — algorithmic cup-and-handle
- **carlamHS/vcp_screener** (Python) — VCP + cup-handle US screener
- **haikulabs.com** — published cup-with-handle search algorithm (pseudo-code + criteria)
- **Bulkowski / thepatternsite.com** — pattern criteria reference
- TrendSpider, Deepvue, Chartink — documented rule sets (commercial)

**Confidence:** MEDIUM — all open implementations use slightly different threshold tuning; expect to calibrate for VN30.

---

## 4. Breakout confirmation & false-breakout filters

**Canonical confirmation (same day):**
1. **Close** (not intraday high) above pivot + buffer
2. Breakout volume **≥ 1.5× avgvol50**
3. Close in **upper half of day's range**
4. Breakout day price gain typically ≥1.5%

**Confirmation window:** O'Neil does not require multi-day confirmation; the breakout day itself triggers. Academic refinement: require close to hold above pivot on T+1 and T+2 — reduces fakeouts ~20–30% at cost of worse entry.

**Failure rule:** if close drops back below pivot within 3–5 days → failed breakout, exit. Universal stop = −8% from entry (O'Neil's rule).

**Quality filters:**
- Handle must be in **upper half of cup** (low handles fail more)
- Avoid **late-stage bases** (4th+ base since last correction)
- Prefer **tight** bases (ATR contraction) over wide-and-loose
- Only take breakouts while index in confirmed uptrend → **MDM already provides this gate**
- IBD **RS Rank ≥ 80** at breakout

**Confidence:** HIGH on canonical rules; MEDIUM on refinements.

---

## 5. Alternative mechanical entry triggers

| Trigger | Rule | Pros | Cons |
|---|---|---|---|
| **52-week high + vol** | `close > max(close,252) AND totalvol > 1.5*avgvol50` | Trivial, well-studied, robust | No base-quality filter |
| **Weinstein Stage 2** | Close > MA150, MA150 rising, close > 30-week MA; breakout from base on 2×–3× vol; hold above 50/150/200dma post-breakout; healthy pullback = within 5% of 30-week MA | Mechanical, trend-following | Later entry, larger stops |
| **Minervini VCP** | (1) close > MA50 > MA150 > MA200, MA200 rising ≥30d; (2) 2–6 successive pullbacks each smaller than prior (e.g. 20→10→5%); (3) volume contracts with each pullback; (4) RS ≥ 70; (5) breakout close above contraction high on ≥1.5× avg vol. TraderLion/sharpely studies show 90%+ success in confirmed uptrends. | Highest quality | Hardest to quantify — requires swing-point detection |
| **Pocket Pivot** | up-day + volume > max(down-day vol, last 10d) + close ≥ MA50, inside/near base | Very clean, fires early | Can fire multiple times in wide base → needs debounce |
| **Donchian-20** | close > max(high, 20) | Trivially mechanical, well-backtested | Not CANSLIM-aligned, no volume filter |
| **MA20×MA50 cross + vol** | cross + `totalvol > 1.3*avgvol50` | Simplest | Lagging, whipsaw-prone |

---

## 6. Entry timing window after MDM BUY

No canonical O'Neil number. Common choices:

- **Qualitative IBD guidance:** best leaders break out in first 1–3 weeks of a new uptrend; after ~3–5 weeks, most fresh breakouts underperform.
- **Aggressive:** 5 trading days
- **Standard (most used):** 20 trading days (~1 month)
- **Permissive:** until MDM exits BUY (risk: late-stage entries)
- **Minervini/Kacher practice:** window stays open while index in uptrend, but only buy breakouts from **fresh** bases.

**Recommendation:** 20-trading-day window from each MDM BUY event, PLUS require the base to be "fresh" — its lowest point within the last ~60 trading days.

---

## 7. Academic results — pivot vs. naïve top-RS

- **Lutey et al. (2013/2014) — OPBM II** (Journal of Applied Finance): simplified CANSLIM beat NASDAQ 100 by ~0.94%/month 1999–2013. Entries rebalance-based, not pivot-based.
- **Olson et al. (1998)** and **Cheh et al. (2012)**: CANSLIM produces positive alpha vs. S&P 500; neither isolates pivot timing.
- **O'Neil Global Advisors — "Breakouts: Pump Up the Volume" (1995–2021 US):** the single strongest empirical evidence.
  - Avg O'Neil pattern breakout: **+3.2% raw / +1.1% alpha over 63 trading days**.
  - **High-volume breakouts (>1.5×, esp. >2×) dramatically outperform low-volume breakouts** — volume is the dominant discriminator.
  - Breakouts during confirmed uptrends far outperform breakouts during corrections → validates the MDM gate.
- **Towards a Simplified CAN SLIM Model** (Applied Finance Letters, 2023): confirms simplified CANSLIM beats benchmarks.
- **Naïve top-RS (Jegadeesh-Titman momentum):** ~1%/month momentum premium before costs, but higher drawdowns than pivot-gated entries. **Pivot filter trades signal frequency for quality.**

---

## Recommended entry confirmation mechanism for this project

All three options use only `stock_eod(openprice, closeprice, highestprice, lowestprice, totalvol, avgvol50)`.

### Option A — 52-week high + volume surge  (RECOMMENDED MVP)
**Complexity:** very low. **Fires:** frequently.

```
breakout_A(i, T) =
      closeprice[i,T]  >  MAX(closeprice[i, T-252..T-1])
  AND closeprice[i,T]  >  openprice[i,T]
  AND (closeprice[i,T] - lowestprice[i,T])
        / NULLIF(highestprice[i,T] - lowestprice[i,T], 0) >= 0.5
  AND totalvol[i,T]    >= 1.5 * avgvol50[i,T]
```
Entry at `closeprice[T]` (or next-day open for execution realism). Stop: −8% or base_low.

### Option B — Flat-base breakout + volume  (closer to O'Neil canon)
**Complexity:** medium. **Fires:** less often, higher-quality.

```
N = 25
base_high = MAX(highestprice, T-N..T-1)
base_low  = MIN(lowestprice,  T-N..T-1)
depth     = (base_high - base_low) / base_high
is_flat_base = 0.03 <= depth <= 0.15 AND closeprice[T-1] within 8% of base_high
pivot = base_high * 1.001

breakout_B(i,T) =
      is_flat_base
  AND pivot <= closeprice[i,T] <= pivot * 1.05
  AND totalvol[i,T] >= 1.5 * avgvol50[i,T]
  AND closeprice[i,T] > openprice[i,T]
  AND upper_half_close

-- False-breakout exit: if close < pivot within 5 days → exit
```

### Option C — Pocket Pivot (Kacher)  (cleanest single rule)

```
pocket_pivot(i,T) =
      closeprice[i,T]  >  openprice[i,T]
  AND closeprice[i,T]  >= MA50(closeprice)[i,T]
  AND totalvol[i,T]    >  MAX(
          totalvol[i,t] FOR t in (T-10..T-1)
          WHERE closeprice[i,t] < closeprice[i,t-1]
       )
  AND closeprice[i,T]  within 15% of MAX(closeprice[i, T-50..T])
```

### Final recommendation (ranked)

1. **Build Option A first** — validates the full pipeline with minimal moving parts.
2. **Add Option C (Pocket Pivot)** in parallel and A/B test vs. A.
3. **Defer Option B (flat-base detector)** to a later v7.x milestone.

**Entry timing window:** 20 trading days from each MDM BUY event.
**Universal stop:** −8% from entry OR base_low (Option B), whichever tighter.

---

## Sources

- Chris Perruna — How to Calculate a Stock's Pivot Point
- AAII — Predicting Short-Term Trends: The Cup-With-Handle Pattern
- TraderLion — Pivot Points / Flat Base / Cup and Handle / Pocket Pivot / FTD / VCP / Stage Analysis
- Fidelity — Cup with Handle
- Virtue of Selfish Investing (Kacher) — Pocket Pivot FAQ
- QuantifiedStrategies — FTD Backtest / CANSLIM Backtest
- sharpely.in — VCP Rule-Based Screener
- Deepvue — Weinstein Stage Analysis
- Lutey et al. — OPBM II: An Interpretation of the CAN SLIM Investment Strategy
- Towards a Simplified CAN SLIM Model (Applied Finance Letters 2023)
- O'Neil Global Advisors — Breakouts: Pump Up the Volume (1995–2021)
- Wikipedia — CAN SLIM
- GitHub: HumanRupert/marketsmith_pattern_recognition, kanwalpreet18/canslimTechnical, carlamHS/vcp_screener
- Haiku Labs — Cup-With-Handle Search Algorithm
