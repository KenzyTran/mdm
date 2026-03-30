# Pitfalls Research

**Domain:** Adding macro liquidity filter, SELL acceleration, and BUY selectivity to MDM V2 market timing engine
**Researched:** 2026-03-30
**Confidence:** HIGH (based on project history, code analysis, and domain research)

## Critical Pitfalls

### Pitfall 1: Look-Ahead Bias in Weekly-to-Daily Liquidity Merge

**What goes wrong:**
Global liquidity data (`data/global_liquidity.csv`) is **weekly** (every Wednesday, ~987 rows from 2007-2026). The V2 engine processes **daily** bars. When merging weekly liquidity into the daily loop, using `merge_asof` or forward-fill without a publication lag creates look-ahead bias: the Wednesday liquidity value gets applied to Monday and Tuesday of the same week, even though that data was not yet published.

Additionally, FRED data has a **publication delay** of 1-2 weeks. The Fed balance sheet (WALCL) released on Thursday covers the prior Wednesday. ECB and BOJ data have even longer delays. Using the `date` column directly means the backtest "knows" the liquidity value before it was publicly available.

**Why it happens:**
The existing V2 engine is purely price-based with no external data merges. Adding weekly macro data is the first time the engine faces a multi-frequency alignment problem. The natural instinct is to forward-fill the weekly value across all daily rows for that week, which is wrong.

**How to avoid:**
1. Apply a **publication lag offset** before merging: shift the weekly liquidity date forward by at least 7 days (conservative: 14 days) to simulate real-world availability
2. Use `pd.merge_asof(direction='backward')` so each daily row gets the most recent weekly value that was **already published** (not the current or future week)
3. The existing `qe_floor` column in `global_liquidity.csv` is pre-computed -- verify it also respects publication lag
4. Create a unit test: for any daily date D, the merged liquidity value must come from a weekly date <= D minus the lag offset

**Warning signs:**
- Liquidity filter appears to "perfectly" predict market turns
- QE floor suppression timing exactly matches market bottoms (too good)
- Performance improvement concentrates around Fed announcement dates
- Filter decisions change when you add 7-14 day lag (if they do, the non-lagged version was using future data)

**Phase to address:**
Phase 1 (Global Liquidity Integration) -- this must be correct BEFORE any backtesting of the filter, or all downstream results are invalid.

---

### Pitfall 2: State[i] vs State[i-1] Contamination in New Filter Logic

**What goes wrong:**
The project already experienced this exact bug: using `state[i]` instead of `state[i-1]` in equity calculations caused a 707% vs 93% difference. When adding the liquidity filter as a new condition in `process_day()`, the same class of bug can recur: the filter reads today's liquidity to decide today's state, but the equity curve must use **yesterday's state** to compute today's return.

More subtly, if the liquidity filter **overrides** a SELL signal on day T, but the equity formula captures the return as if the override was already active on day T (rather than T+1), the backtest leaks information.

**Why it happens:**
The V2 engine loop at line 99 (`for idx in range(len(df))`) processes each day sequentially. The state is updated at step 5 (`process_day` at line 203) and written to the DataFrame at line 232. The performance analyzer correctly uses `prev_state = states[i-1]` (line 94 of performance.py). But when adding a new filter step between steps 4 and 5, the filter might read the **current** row's liquidity to suppress a transition, and if not careful, the suppression takes effect on the same day the data becomes available.

**How to avoid:**
1. The liquidity filter decision for day T should be based on data available BEFORE day T's open (which means the liquidity value must be from at least the prior week)
2. Add an assertion test: run the V2 engine with and without the filter, extract the equity curve, verify that `equity[i]` is computed from `state[i-1]` in BOTH cases
3. The filter should modify the **proposal** going into `process_day()`, not retroactively change the state after it is set
4. Document the rule: "Filter inputs must use `row[i-1]` or earlier data. Filter output modifies the proposal for `state[i]`, which affects returns starting from `i+1`."

**Warning signs:**
- Adding the liquidity filter produces > 50% improvement in total return (suspiciously large)
- Removing the filter causes a proportionally larger performance drop than the number of signals affected
- Performance difference between filter-on and filter-off is asymmetric (huge improvement on one side, tiny degradation on the other)

**Phase to address:**
Phase 1 (Global Liquidity Integration) -- enforce from the first line of code. Add regression test from the known 707% vs 93% bug as a guard.

---

### Pitfall 3: Overfitting Liquidity Filter to Post-2008 QE Regime

**What goes wrong:**
Global liquidity data starts in 2007. QE began in 2008. The entire dataset of 987 weekly points covers ONE macro regime (post-GFC central bank expansion). A "QE floor" filter tuned to suppress SELL signals during Fed balance sheet expansion will look brilliant on 2009-2021 data but has **zero out-of-sample validation** for non-QE environments (2022 QT, pre-2008, or a future regime where central banks are constrained).

The VN30 market adds another layer: Vietnam's State Bank policy does not follow Fed/ECB/BOJ cycles. Global liquidity may correlate with VN30 through capital flows, but the relationship is indirect and regime-dependent.

**Why it happens:**
Only 18 years of weekly data. Only one full QE cycle (2008-2014), one expansion (2020-2021), and one QT episode (2022-2023). With so few regime samples, any filter threshold is essentially "fit to n=3 events."

**How to avoid:**
1. Use the liquidity filter as a **soft suppression** (reduce position size or delay SELL by N days) rather than a hard veto
2. Test with inverted logic: if suppressing SELL during QE expansion helps, does suppressing BUY during QT contraction also help? If only one direction works, the filter may be capturing noise
3. Walk-forward test: train threshold on 2007-2018, test on 2019-2026. If out-of-sample degrades > 10% (use existing `check_degradation()` function), the filter is overfit
4. For VN30: do NOT assume global liquidity applies. Test separately, and require independent evidence (Vietnam credit growth, SBV repo rates) before enabling
5. Keep the filter simple: use only `liquidity_roc_20w > 0` (expansion vs contraction), not a fine-tuned threshold

**Warning signs:**
- Optimal threshold changes significantly between sub-periods
- Filter helps on NASDAQ but hurts on VN30 (or vice versa)
- Parameter sensitivity: small changes in ROC threshold (e.g., 0% vs 2%) cause large performance swings
- The filter's benefit comes primarily from 2020-2021 (pandemic QE), which is a single event

**Phase to address:**
Phase 1 (Global Liquidity Integration) for the filter design, Phase 4 (VN30 Adaptation Backtest) for cross-market validation.

---

### Pitfall 4: SELL Acceleration Conditions Creating Asymmetric Overfit

**What goes wrong:**
Adding momentum/acceleration conditions to SELL transitions (e.g., "require MACD divergence AND price below EMA55 before transitioning BUY->CASH->SELL") sounds prudent but creates an asymmetric bias: you are making it **harder** to exit, which mechanically increases holding time and total return in bull markets. This improvement is not alpha -- it is just "hold longer in backtested bull markets."

In bear markets (2000-2002, 2008, 2022), delayed SELL transitions can be catastrophic. The existing V2 already has `cash_deterioration_days: 10` as an auto-SELL timer. Adding acceleration conditions on top risks making the path BUY->CASH->SELL even slower.

**Why it happens:**
The natural research process is: "V2 has too many false SELL signals, let's add conditions to filter them." But every condition you add to suppress false SELLs also delays true SELLs. In a 52-year backtest dominated by bull markets (~70% of the time), delaying SELLs mechanically improves aggregate returns.

**How to avoid:**
1. Measure SELL quality separately for bull and bear periods. A good acceleration condition should improve both
2. Track **time to first correct SELL** in each bear market (2000, 2008, 2018, 2020, 2022). If acceleration conditions delay the first correct SELL by > 5 trading days vs V2 baseline, reject them
3. Use a **maximum delay cap**: if acceleration conditions delay SELL by more than N days, force the SELL anyway (similar to existing `cash_deterioration_days`)
4. Test on the 2022 bear market specifically -- this is the most recent regime change, and delayed SELLs here would have caused 20-30% drawdowns

**Warning signs:**
- SELL condition changes produce big total return improvements but max drawdown stays the same or worsens
- Number of SELL signals drops by > 30% (too much suppression)
- Average holding period increases by > 20% vs baseline (you are just holding longer, not timing better)
- Performance improvement comes primarily from 2009-2021 (the longest bull run)

**Phase to address:**
Phase 2 (SELL Acceleration Conditions) -- must include bear-market-specific validation as acceptance criteria.

---

### Pitfall 5: BUY Selectivity Score Becoming a Curve-Fit Ensemble

**What goes wrong:**
Building a "BUY quality score" by combining multiple conditions (EMA alignment, MACD histogram, volume confirmation, price location, momentum) quickly becomes an overfitted ensemble. The hybrid engine experiment already demonstrated this: the indicator filter rejected 47% of BUY signals but only 43% were correct rejections -- essentially random. Adding MORE conditions does not fix the problem; it just shifts the random boundary.

**Why it happens:**
Each indicator condition has marginal predictive power (~55-60% accuracy individually). Combining them via majority vote or weighted scoring does not improve accuracy unless the conditions are **uncorrelated**. In practice, EMA9>EMA21, close>EMA55, and MACD>0 are all highly correlated (they all measure "is the trend up?"). Adding correlated conditions inflates apparent robustness in-sample without improving out-of-sample.

**How to avoid:**
1. Learn from the hybrid engine failure: do NOT build a multi-condition BUY filter the same way
2. Instead of scoring BUY signals, focus on **regime-based gating**: only suppress BUY during QT (liquidity filter) or extreme overbought conditions, not based on indicator ensembles
3. If building a score, require each component to be **independently validated** with correlation < 0.5 between components
4. Set a hard limit: maximum 2-3 conditions (the FilterConfig already warns at > 3, per D-04)
5. Use the existing `check_degradation()` function: if BUY selectivity degrades > 10% out-of-sample, reject it

**Warning signs:**
- BUY selectivity score rejects > 30% of signals but win rate on accepted signals improves < 5%
- Score components have pairwise correlation > 0.7
- Optimal score threshold differs between VN30 and NASDAQ datasets
- Adding a 4th or 5th condition improves in-sample but not out-of-sample

**Phase to address:**
Phase 3 (BUY Selectivity Improvement) -- use hybrid engine results as the anti-pattern baseline.

---

### Pitfall 6: Liquidity Data Gap for VN30 Pre-2007

**What goes wrong:**
Global liquidity data starts May 2007. VN30 data may extend earlier (VN30 index launched 2012, but VN-Index data goes back further). Running the combined engine on pre-2007 data will have `NaN` liquidity values. If the code does not handle this gracefully, the filter either crashes, or worse, silently defaults to "no suppression" -- which means the filter is only active for part of the backtest, making performance comparisons misleading.

**Why it happens:**
The V2 engine currently has no external data dependencies. Adding the liquidity merge creates the first data availability boundary. The engine loop does not check for NaN in external columns.

**How to avoid:**
1. Add explicit NaN handling: if liquidity data is missing for a date, the filter should return a **neutral** verdict (neither suppress nor amplify)
2. Document the effective date range of the liquidity filter in config: `liquidity_start_date: "2007-05-02"`
3. When reporting performance, separate metrics into "pre-filter" and "with-filter" periods
4. For VN30 specifically: the liquidity filter is only meaningful from 2012+ (VN30 launch). Test separately

**Warning signs:**
- Backtest results change when you extend the date range beyond 2007
- NaN-related warnings or silent data drops in the merge
- Performance metrics mix filtered and unfiltered periods

**Phase to address:**
Phase 1 (Global Liquidity Integration) -- handle during data loader implementation.

---

### Pitfall 7: Whipsaw Amplification from Conflicting Filter Signals

**What goes wrong:**
Three new features (liquidity filter, SELL acceleration, BUY selectivity) can create conflicting signals. Example: liquidity filter says "suppress SELL" (QE expanding), SELL acceleration says "allow SELL" (momentum deteriorating), BUY selectivity says "reject next BUY" (low quality). The engine enters a state where it is simultaneously suppressing exits AND blocking re-entries, trapping capital in CASH during both rallies and corrections.

**Why it happens:**
Each feature is developed and tested independently. They interact through the state machine but their combined effect is not tested as a system. The existing V2 engine has clean state transitions; adding three parallel filters creates a combinatorial explosion of edge cases.

**How to avoid:**
1. Define a **priority hierarchy**: liquidity filter > SELL acceleration > BUY selectivity. Higher priority overrides lower
2. Add a **conflict resolution rule**: if liquidity filter and SELL acceleration disagree, the more conservative action wins (exit to CASH)
3. Test the COMBINED system, not just each feature in isolation. Create integration tests that cover all 8 combinations of (liquidity: suppress/allow) x (sell_accel: trigger/delay) x (buy_select: accept/reject)
4. Track **days in CASH** as a key metric. If the combined filters increase average CASH days by > 30% vs V2 baseline, the system is over-filtering

**Warning signs:**
- Combined system underperforms individual features applied separately
- Average CASH duration increases significantly
- State oscillation: rapid BUY->CASH->BUY->CASH sequences (whipsaw)
- Performance improves in calm markets but degrades in volatile markets (filters fight each other)

**Phase to address:**
Phase 4 (Combined Integration) -- must be a dedicated integration testing phase, not just stacking features.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding publication lag as 0 days | Faster development, simpler merge | All liquidity filter results are invalid (look-ahead bias) | **Never** |
| Forward-filling weekly data without lag | Clean daily DataFrame, no NaN gaps | Subtle look-ahead bias on Mon-Tue of each week | Never for filter decisions; acceptable for visualization only |
| Testing features independently only | Each feature shows improvement | Combined system has untested interactions, possible degradation | Only in Phase 1-3 dev; Phase 4 must test combined |
| Using same data for threshold tuning and validation | Faster iteration, more data | Overfitting guaranteed with only 18 years of weekly liquidity data | Never for liquidity thresholds; use walk-forward |
| Adding SELL conditions without bear-market testing | Total return improves in aggregate backtest | Catastrophic drawdown in next bear market | Never -- always require bear-specific validation |

## Integration Gotchas

Common mistakes when integrating new features into the V2 engine.

| Integration Point | Common Mistake | Correct Approach |
|-------------------|----------------|------------------|
| Weekly liquidity -> daily engine loop | Merging on exact date match (misses most daily rows) | Use `merge_asof` with backward direction and publication lag offset |
| Liquidity filter -> `process_day()` | Adding filter inside `process_day()`, coupling state machine to external data | Filter modifies the **proposal** before `process_day()`, keeping state machine pure |
| SELL acceleration -> DD counter | Resetting DD count when acceleration condition is not met | DD count should keep accumulating; acceleration only gates the transition |
| BUY selectivity -> FTD detector | Rejecting FTD at detection time (losing the signal permanently) | Detect FTD normally; apply selectivity score to the **transition decision**, so the signal can be reconsidered |
| Performance comparison -> equity curve | Computing equity with new filter on full period including pre-2007 | Split equity calculation at liquidity data boundary; report both periods |
| Config expansion -> MDMV2Config | Adding 10+ new parameters for all three features | Create separate `LiquidityFilterConfig`, `SellAccelConfig`, `BuySelectConfig` composed into MDMV2Config |

## Performance Traps

Patterns that work at small scale but fail as data grows or regime changes.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Liquidity ROC threshold tuned to 2020-2021 | Perfect SELL suppression during pandemic QE | Walk-forward validation; require threshold to work on 2008-2014 QE too | Next QT cycle or non-US market (VN30) |
| SELL acceleration tuned on 2009-2021 bull run | Fewer false SELLs, higher total return | Validate on 2000-2002, 2008, 2022 bear markets separately | Next bear market lasting > 6 months |
| BUY selectivity using correlated indicators | High in-sample accuracy | Require pairwise correlation < 0.5 between score components | Any regime where trend indicators diverge (choppy markets) |
| Fixed publication lag assumption | Works for Fed data | Research actual publication schedule for ECB, BOJ | When data source changes update frequency |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Liquidity merge:** Often missing publication lag -- verify by checking that no daily row uses a liquidity value published AFTER that row's date
- [ ] **SELL acceleration:** Often missing bear-market validation -- verify by running 2008 and 2022 sub-periods and checking max drawdown separately
- [ ] **BUY selectivity:** Often missing correlation analysis between score components -- verify pairwise correlation matrix is computed and logged
- [ ] **Equity calculation:** Often breaks when new filter changes state timing -- verify `state[i-1]` rule still holds by comparing a known date's state with the return captured
- [ ] **VN30 adaptation:** Often assumes global liquidity applies directly -- verify with VN30-specific backtest that filter helps (not just "doesn't hurt")
- [ ] **Combined integration:** Often only tested on full period -- verify with walk-forward: train on 2007-2018, test on 2019-2026, check degradation < 10%
- [ ] **NaN handling:** Often crashes or silently drops rows at data boundaries -- verify by running engine on date range starting before 2007-05-02

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Look-ahead bias discovered after tuning | HIGH | Discard all tuning results. Add lag offset. Re-run entire parameter sweep from scratch |
| State[i] vs state[i-1] bug in new filter | MEDIUM | Fix the index reference. Re-run equity calculation. Compare with known baseline (190.8% V2 return) |
| Overfit liquidity threshold | LOW | Switch to simple binary (expansion/contraction). Remove fine-tuned threshold. Accept lower in-sample performance |
| SELL acceleration too aggressive | MEDIUM | Add maximum delay cap. Re-validate on bear markets. Fall back to V2 baseline SELL logic |
| BUY selectivity near-random | LOW | Remove entirely. The hybrid engine already proved this approach does not work. Focus on liquidity filter instead |
| Combined system conflicts | MEDIUM | Disable all three features. Re-enable one at a time with integration tests. Establish priority hierarchy |
| VN30 liquidity filter hurts performance | LOW | Disable liquidity filter for VN30. Use VN30-specific signals (SBV rates, foreign flow) instead |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Weekly-to-daily look-ahead bias | Phase 1: Liquidity Integration | Unit test: merged liquidity date <= daily date - lag_days |
| State[i] vs state[i-1] contamination | Phase 1: Liquidity Integration | Regression test: V2 baseline equity = 190.8% +/- 0.1% unchanged |
| Overfitting to QE regime | Phase 1: Liquidity Integration | Walk-forward: train 2007-2018, test 2019-2026, degradation < 10% |
| SELL acceleration asymmetric overfit | Phase 2: SELL Acceleration | Bear-market sub-test: 2008 and 2022 drawdown not worse than V2 baseline |
| BUY selectivity curve-fit ensemble | Phase 3: BUY Selectivity | Correlation matrix: all component pairs < 0.5; out-of-sample check_degradation < 10% |
| Liquidity data gap (pre-2007) | Phase 1: Liquidity Integration | Engine runs on 2000-2026 without crash; NaN liquidity returns neutral verdict |
| Whipsaw from conflicting filters | Phase 4: Combined Integration | Integration test covering all 8 filter combinations; CASH days < 130% of V2 baseline |

## Sources

- Project codebase analysis: `strategies/mdm_v2/mdm_v2_engine.py`, `strategies/mdm_v2/performance.py`, `strategies/mdm_hybrid/indicator_filter.py`
- Known bug: equity formula state[i] vs state[i-1] causing 707% vs 93% difference (project history)
- Known result: hybrid indicator filter 47% rejection rate with 43% correct rejections (near random)
- Global liquidity data: `data/global_liquidity.csv` (987 weekly rows, 2007-2026)
- [Look-ahead bias in backtesting](https://www.newsletter.quantreo.com/p/look-ahead-bias-the-invisible-killer)
- [Backtesting traps and common errors](https://www.luxalgo.com/blog/backtesting-traps-common-errors-to-avoid/)
- [Overfitting in trading models](https://arongroups.co/forex-articles/overfitting-in-trading/)
- [Market regime filtering approaches](https://www.emergentmind.com/topics/market-regime-filtering)
- [Seven sins of quantitative investing](https://bookdown.org/palomar/portfoliooptimizationbook/8.2-seven-sins.html)
- [VantMacro global liquidity and market regimes](https://vantmacro.com/learn/guides/market-regimes)

---
*Pitfalls research for: MDM V2 Signal Quality & Macro Filter Integration*
*Researched: 2026-03-30*
