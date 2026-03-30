# Feature Research: Signal Quality & Macro Filter (v5.0)

**Domain:** Macro liquidity regime filter + momentum-based sell conditions + buy quality scoring for market timing model
**Researched:** 2026-03-30
**Confidence:** MEDIUM (Dr. K webinar quotes are direct evidence; implementation patterns draw from established market timing literature but specific parameterization requires backtesting)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that directly implement Dr. K's stated model behavior. Without these, the V2 engine contradicts known model characteristics.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| QE Floor: Suppress SELL when liquidity expanding | Dr. K 2013: "model refrained from going to a sell because it's factoring in the QE floor." This is a confirmed model feature, not an enhancement | MEDIUM | Data exists: `data/global_liquidity.csv` has `liquidity_roc_20w` and `qe_floor` columns (987 weeks, 2007-2026). Weekly data needs interpolation to daily. Implementation: when `liquidity_roc_20w > threshold`, block CASH->SELL transition |
| SELL acceleration condition | Dr. K 2013: "as far as sell signals... it really needs to see an acceleration to the downside." Current V2 uses only DD count + time-in-cash -- no momentum/acceleration check | MEDIUM | Current SELL triggers: MA50 breakdown OR cash_deterioration_days exceeded. Neither checks for acceleration. Need: rate of price decline, DD clustering, or momentum divergence as required condition |
| BUY selectivity filter | Dr. K 2013: "model often will not take the buy signals unless everything's set up just right." Current V2 accepts ALL FTD/MA50 breakout/52-week signals unconditionally | MEDIUM | Need quality gate on buy signals. Candidates: MA alignment (MA10 > MA50), price above key MAs, momentum direction, FTD strength (gain magnitude, volume ratio) |
| Backtest comparison before/after | Cannot claim improvement without rigorous A/B comparison on same data | LOW | Reuse `V2PerformanceAnalyzer`. Compare: total return, CAGR, max drawdown, Sharpe, win rate, number of trades. Run on both VN30 and NASDAQ |
| Dashboard visualization of new metrics | Liquidity regime, acceleration indicators, buy quality scores must be visible for debugging and trust | MEDIUM | Extends existing dashboard. Add: liquidity overlay on price chart, sell acceleration indicator panel, buy signal quality annotations |

### Differentiators (Competitive Advantage)

Features that go beyond confirmed Dr. K behavior to improve V2 performance.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-condition SELL gate (not just DD count) | Combines DD clustering + price momentum + MA breakdown into a composite sell trigger. Reduces false sells in choppy markets while catching real breakdowns faster | HIGH | Current V2 SELL path: BUY->CASH (DD count or MA10) then CASH->SELL (MA50 or time). Composite gate would require 2+ conditions met simultaneously, matching Dr. K's "acceleration" language |
| FTD quality scoring with tiered acceptance | Score each FTD by: gain magnitude, volume ratio, rally attempt depth, MA alignment. Only accept FTDs scoring above threshold. Addresses the 50%+ FTD failure rate documented in IBD research | MEDIUM | Research shows: DD on days 1-2 after FTD = 95% failure rate. DD on day 3 = 70% failure. Quality scoring can pre-filter weak FTDs before they generate whipsaw trades |
| Liquidity regime as position sizing input | Beyond binary suppress/allow, use liquidity trend strength to scale position size. Full size in strong QE, reduced size in neutral, no shorts in QE expansion | MEDIUM | Extends QE floor from binary gate to continuous signal. Requires Kelly Criterion integration (existing `vn30_vsa/kelly.py` pattern) |
| Adaptive sell acceleration threshold by volatility | In high-volatility periods, require stronger acceleration to trigger SELL (noise is higher). In low-volatility periods, smaller acceleration is meaningful | HIGH | Uses ATR or realized volatility to normalize the acceleration threshold. Prevents false sells during normal volatility expansion |
| Post-FTD confirmation window | After FTD triggers BUY, monitor for distribution in first 3-5 days. Early DD = exit immediately (95% failure rate from IBD data). Reduces average losing trade size | LOW | Simple counter: track DD count in first N days after BUY entry. If DD appears on day 1-2, exit to CASH immediately. Low implementation cost, high expected value |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time liquidity data feed | "Use live Fed balance sheet data" | This is a backtesting research project. Live data adds API dependencies, error handling, and no validation benefit. Weekly liquidity data has inherent lag anyway | Use static CSV updated periodically. `data/global_liquidity.csv` already has 987 weeks through March 2026 |
| Complex ML model for sell prediction | "Train a model to predict market tops" | 962 total signals, maybe 100 sell signals. Way too few samples for ML. Will overfit to noise | Rule-based acceleration conditions with parameterized thresholds. Sweep parameters, don't train models |
| Sentiment indicators (VIX, put/call ratio) | "Add fear/greed as sell filter" | Moves away from Dr. K's known indicator set. Cannot validate against his signals if using indicators he does not use | Stick to Dr. K's confirmed inputs: price, volume, MAs, MACD, and now confirmed Global Liquidity Index |
| Per-stock leading stock analysis | Dr. K mentions "confirming action in leading stocks" for FTD validation | Requires defining "leading stocks," tracking individual stock breakouts, massive data expansion. Different problem domain entirely | Use index-level proxies: breadth of rally (price location relative to 52-week range), volume confirmation. These approximate leading stock health at index level |
| Intraday acceleration detection | "Check for intraday sell-off pattern" | MDM is a daily-close model. Intraday noise contradicts design philosophy. Dr. K's model operates on daily bars | Use daily close-to-close rate of change. Multi-day clustering patterns. No intraday data needed |
| Dynamic QE floor threshold via optimization | "Optimize the liquidity threshold" | Only ~3 QE cycles in the data (2009-2014, 2020-2021, partial 2023). Optimizing on 3 samples = pure overfitting | Use simple, robust threshold: liquidity_roc_20w > 0 means expanding. Binary regime, not optimized cutoff |

## Feature Dependencies

```
[data/global_liquidity.csv] (existing)
    |
    +---loaded-by--->  [Liquidity Data Loader] (new)
    |                       |
    |                       +---interpolates-to-daily--->  [QE Floor Filter] (new)
    |                                                          |
    |                                                          +---gates--->  [CASH->SELL transition]
    |                                                          |
    |                                                          +---optional-input--->  [Position Sizing]
    |
[strategies/mdm_v2/position_manager.py] (existing)
    |
    +---currently-handles--->  [CASH->SELL: MA50 or deterioration_days]
    |                               |
    |                               +---enhanced-by--->  [SELL Acceleration Condition] (new)
    |                                                        |
    |                                                        +---requires--->  [Momentum Indicators] (new)
    |                                                        |                    (ROC, DD clustering, price velocity)
    |                                                        |
    |                                                        +---blocked-by--->  [QE Floor Filter]
    |
    +---currently-handles--->  [CASH/SELL->BUY: FTD or MA50 breakout]
                                    |
                                    +---gated-by--->  [BUY Quality Score] (new)
                                                          |
                                                          +---requires--->  [MA Alignment Check]
                                                          +---requires--->  [FTD Strength Metrics]
                                                          +---optional--->  [Post-FTD Confirmation Window]

[Dashboard] (existing)
    +---extended-by--->  [Liquidity Overlay Panel] (new)
    +---extended-by--->  [Sell Acceleration Indicator] (new)
    +---extended-by--->  [Buy Quality Annotations] (new)
```

### Dependency Notes

- **QE Floor Filter requires Liquidity Data Loader:** Weekly CSV must be interpolated to daily frequency and joined with OHLCV data before the engine can use it. Forward-fill interpolation (each week's value applies until next week's data).
- **SELL Acceleration requires Momentum Indicators:** Need price ROC (rate of change), DD clustering metric, or similar momentum measure computed before position_manager can check acceleration condition.
- **BUY Quality Score requires MA Alignment Check:** The quality score depends on indicator values (MA10 vs MA50 relationship, price vs MA50, momentum direction) that must be computed in the indicator layer.
- **QE Floor blocks SELL Acceleration:** Even if acceleration conditions are met, QE floor can suppress the SELL. QE floor is the higher-priority gate.
- **Post-FTD Confirmation enhances BUY Quality Score:** Confirmation window is a post-entry quality check, while quality score is a pre-entry gate. Both reduce whipsaw but at different points.
- **Dashboard extensions require all new features:** Each visualization panel needs the corresponding feature's computed data. Build features first, then dashboard.

## MVP Definition

### Launch With (v1 -- Core Signal Quality Improvements)

Minimum to validate the QE floor + acceleration + selectivity hypothesis against V2 baseline.

- [ ] **Liquidity Data Loader** -- Load `global_liquidity.csv`, interpolate weekly to daily, join with OHLCV DataFrame. Output: `qe_expanding` boolean column
- [ ] **QE Floor Filter in position_manager** -- When `qe_expanding=True`, block CASH->SELL transition (stay in CASH). Simple binary gate
- [ ] **SELL Acceleration Condition** -- Require at least one acceleration indicator before CASH->SELL: (a) price ROC over 5 days < -3%, OR (b) 3+ DD in last 10 trading days, OR (c) close breaks below MA50 with increasing volume. Currently CASH->SELL triggers on MA50 breakdown alone or time -- add acceleration requirement
- [ ] **BUY Quality Gate** -- Reject FTD/MA50 breakout signals when MA10 < MA50 (trend not aligned). Simple boolean filter on existing computed values
- [ ] **A/B Backtest Comparison** -- Run V2 baseline vs V2+filters on both VN30 and NASDAQ. Report delta in: total return, CAGR, max drawdown, Sharpe, win rate, trade count

### Add After Validation (v1.x)

Features to add once core filters demonstrate improvement over V2 baseline.

- [ ] **FTD Quality Scoring** -- Score FTDs by gain magnitude + volume ratio + rally depth. Threshold sweep. Trigger: if BUY quality gate helps but some bad FTDs still slip through
- [ ] **Post-FTD Confirmation Window** -- Track DD in first 3 days after BUY entry. Early DD = immediate exit. Trigger: if average losing trade is still too large
- [ ] **DD Clustering metric** -- Formalize "3+ DD in 10 days" into a reusable clustering score. Trigger: if sell acceleration needs tuning
- [ ] **Dashboard: Liquidity overlay** -- Plot global liquidity and QE regime on price chart. Trigger: need to visually debug QE floor behavior
- [ ] **Dashboard: Signal quality annotations** -- Mark rejected signals (blocked BUYs, suppressed SELLs) on chart. Trigger: need to understand filter impact

### Future Consideration (v2+)

- [ ] **Liquidity-adjusted position sizing** -- Scale position size by liquidity regime strength. Defer: requires Kelly Criterion integration and adds complexity
- [ ] **Adaptive acceleration threshold** -- Normalize sell acceleration by ATR/volatility. Defer: need to prove fixed threshold works first
- [ ] **Multi-timeframe liquidity analysis** -- Use 4-week, 12-week, 20-week liquidity ROC together. Defer: more parameters to overfit
- [ ] **VN30-specific liquidity proxy** -- Vietnam does not have Fed/ECB/BOJ. Need SBV (State Bank of Vietnam) liquidity proxy. Defer: data availability uncertain

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| QE Floor Filter | HIGH | LOW | P1 |
| SELL Acceleration Condition | HIGH | MEDIUM | P1 |
| BUY Quality Gate (MA alignment) | HIGH | LOW | P1 |
| A/B Backtest Comparison | HIGH | LOW | P1 |
| Liquidity Data Loader | HIGH | LOW | P1 |
| FTD Quality Scoring | MEDIUM | MEDIUM | P2 |
| Post-FTD Confirmation Window | MEDIUM | LOW | P2 |
| DD Clustering Metric | MEDIUM | LOW | P2 |
| Dashboard: Liquidity Overlay | MEDIUM | MEDIUM | P2 |
| Dashboard: Signal Quality Annotations | MEDIUM | MEDIUM | P2 |
| Liquidity-adjusted Position Sizing | LOW | HIGH | P3 |
| Adaptive Acceleration Threshold | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have -- directly implements confirmed Dr. K model behavior
- P2: Should have -- improves quality after core filters are validated
- P3: Nice to have -- optimization layer, defer until P1+P2 prove value

## Implementation Detail: Key Feature Specifications

### QE Floor Filter

**What Dr. K said:** "The model refrained from going to a sell because it's factoring in the QE floor" (2013 webinar)

**Mechanism:** Central bank balance sheet expansion (QE) creates a liquidity floor that supports equity markets. During active QE, sell signals are unreliable because the liquidity backdrop overrides normal technical deterioration.

**Data available:** `data/global_liquidity.csv` with columns:
- `global_liquidity`: Sum of Fed + ECB + BOJ balance sheets (USD)
- `liquidity_roc_20w`: 20-week rate of change (percentage)
- `qe_floor`: Pre-computed flag (currently all 0, needs population)

**Implementation approach:**
```
qe_expanding = liquidity_roc_20w > 0  (simple: any positive growth = QE regime)
-- OR --
qe_expanding = liquidity_roc_20w > 2.0  (stricter: need meaningful expansion)
```

**Key decision:** Threshold for `liquidity_roc_20w`. Start with > 0 (any expansion), sweep to find optimal. But given only ~3 QE cycles, keep it simple to avoid overfitting.

**Weekly-to-daily interpolation:** Forward-fill. Each week's liquidity value applies Monday through Friday until next week's data arrives. This matches how the market processes weekly Fed data.

### SELL Acceleration Condition

**What Dr. K said:** "As far as sell signals... it really needs to see an acceleration to the downside" (2013 webinar)

**Current V2 SELL path:**
1. BUY->CASH: DD count >= 5, OR MA10 below for 2+ days, OR stop loss
2. CASH->SELL: MA50 breakdown (close < MA50), OR 10+ days in cash

**Problem:** Step 2 has no acceleration requirement. A slow grind below MA50 triggers the same SELL as a sharp breakdown. Dr. K's quote implies the model distinguishes between these.

**Acceleration candidates (implement at least one):**
1. **Price ROC check:** 5-day rate of change < -X% (price falling fast, not just below MA50)
2. **DD clustering:** 3+ distribution days in last 10 trading days (concentrated selling pressure)
3. **Volume-confirmed MA50 break:** Close < MA50 AND volume > 1.5x average (institutional participation)
4. **Multi-day decline:** Close < close[N days ago] for N consecutive days (sustained selling, not one-day spike)

**Recommended approach:** Require MA50 breakdown AND at least one acceleration indicator. This tightens the current SELL trigger without removing it.

### BUY Quality Gate

**What Dr. K said:** "The model often will not take the buy signals unless everything's set up just right" (2013 webinar)

**Current V2 BUY triggers (all accepted unconditionally):**
1. Classic FTD (day 4+ of rally, price gain, volume up)
2. MA50 breakout (close crosses above MA50 from below)
3. 52-week breakout (close exceeds 52-week high)

**Quality filters to apply:**
1. **MA alignment:** Reject BUY when MA10 < MA50 (short-term trend below long-term = not set up right). This is the simplest, most robust filter
2. **Price above MA50:** Reject FTD when close is still below MA50 (FTD happened during a deep correction, trend not recovered)
3. **Momentum direction:** Reject BUY when 10-day ROC is still negative (price still falling despite the one-day rally)

**Recommended MVP approach:** Start with MA alignment only (MA10 > MA50 required for BUY). This is one boolean check on already-computed values. Sweep: require MA10 > MA50, OR require close > MA50, OR require both.

## Competitor Feature Analysis

| Feature | IBD Market Pulse | Morpheus Trading | Dr. K MDM | Our V2 Approach |
|---------|-----------------|------------------|-----------|-----------------|
| Liquidity regime filter | Not used (pure technical) | Not used | Confirmed: QE floor suppresses sells | Binary gate on global liquidity ROC |
| Sell acceleration | DD count only | DD clustering + leading stock breakdown | "Needs acceleration to the downside" | MA50 break + momentum/ROC requirement |
| Buy signal quality | FTD on day 4+ with 1.7%+ gain | Proprietary scoring | "Won't buy unless everything set up right" | MA alignment + optional FTD scoring |
| Whipsaw reduction | Accept all FTDs, exit on DD clustering | Tighten stops after sell signal | Cash state as buffer | Quality gate pre-entry + post-FTD confirmation |
| Position sizing by regime | Not used | Not mentioned | Not confirmed | Deferred (P3) |

## Sources

- Dr. K 2013 webinar transcripts (QE floor quote, sell acceleration quote, buy selectivity quote) -- from PROJECT.md context
- [Global Liquidity Index TradingView Indicator by QuantitativeAlpha](https://www.tradingview.com/script/lG8KoR4f-Global-Liquidity-Index/) -- central bank balance sheet composition
- [Follow Through Day Trading Strategy Backtest](https://www.quantifiedstrategies.com/follow-through-day/) -- FTD failure rate statistics, whipsaw patterns
- [Morpheus Trading: Timing Model Sell Signal](https://www.morpheustrading.com/blog/timing-model-sell-mode) -- DD clustering as sell acceleration, distribution day proximity to FTD
- [IBD Market School TradingView Indicator](https://www.tradingview.com/script/sbzEKCNa-IBD-Market-School-tradeviZion/) -- IBD distribution day counting methodology
- [Rate of Change (ROC) Indicator](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc) -- momentum acceleration measurement
- [Reducing Whipsaws When Using Moving Averages](https://alvarezquanttrading.com/blog/reducing-whipsaws-when-using-200-day-moving-average-for-market-timing/) -- delay/confirmation techniques for MA-based timing
- [Market Regime Detection using HMM](https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/) -- regime filter implementation patterns
- Existing codebase: `strategies/mdm_v2/` engine, `data/global_liquidity.csv`, `strategies/mdm_v2/vn30_filters.py` pattern
- IBD research (from search): DD on days 1-2 after FTD = 95% failure rate; DD on day 3 = 70% failure

---
*Feature research for: Signal Quality & Macro Filter v5.0*
*Researched: 2026-03-30*
