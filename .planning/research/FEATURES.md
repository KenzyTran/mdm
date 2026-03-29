# Feature Research: Hybrid MDM Engine (v3.0)

**Domain:** Hybrid state machine + indicator filter trading model
**Researched:** 2026-03-29
**Confidence:** HIGH (grounded in existing codebase + published research on hybrid trading architectures)

## Feature Landscape

### Table Stakes (Users Expect These)

Features required for the hybrid engine to function and beat the existing 56.7% accuracy baseline.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| State machine layer (DD/FTD/Rally) | Core MDM logic -- the structural signal generator. Without it, this is just a pure indicator model | LOW | Reuse `strategies/mdm_v2/` state machine (BUY/CASH/SELL). Already implemented with DD counting, FTD detection, Rally Attempts, MA50 breakout |
| Indicator filter layer (EMA/MACD) | The whole point of v3 -- indicators confirm/override state machine signals. Dr. K's known TradingView setup uses EMA 9/21/55, MA 200, MACD 12-26-9 | MEDIUM | Reuse `core/indicators.py` which already computes all required indicators via `build_indicator_dataframe()` |
| Signal confirmation logic | State machine proposes signal, indicator layer confirms or blocks it. This is the fundamental hybrid interaction pattern | HIGH | Core new code. Needs well-defined confirmation rules (e.g., "BUY signal confirmed only when EMA9 > EMA21 AND MACD histogram positive") |
| Signal override logic | Indicators can force signal changes the state machine wouldn't generate alone (e.g., force CASH when EMA9 < EMA21 even without 5 DDs) | HIGH | Most complex new feature. Must define which indicator conditions can override which state machine transitions |
| Cash state insertion | Post-2019 MDM inserts Cash between Buy and Sell. Hybrid model needs indicator-driven Cash triggers beyond DD counting | HIGH | Existing v2 has DD-based and MA10-based Cash triggers. Hybrid adds EMA/MACD-based Cash triggers |
| Validation against 962 signals | Must score hybrid model against published signal history. Target: beat 56.7% accuracy from pure decision tree | LOW | Reuse `analysis/validate_discovery.py` pattern -- confusion matrix, per-type match rates, cross-era validation |
| Era-aware evaluation | Pre-2019 vs post-2019 eras have different rules. Hybrid model must handle both or be explicitly post-2019 focused | MEDIUM | Reuse `analysis/rule_discovery.py` era splitting. Must decide: unified model or era-specific weights? |
| Configurable confirmation/override rules | Rules must be parameterized, not hardcoded. Enables hypothesis testing and parameter sweeps | MEDIUM | Follow `MDMV2Config` dataclass pattern from `strategies/mdm_v2/config.py` |

### Differentiators (Competitive Advantage)

Features that could significantly improve accuracy beyond the baseline.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Contextual state transitions | Buy->Cash->Sell transitions depend on prior state history (e.g., short-lived Buy->Cash suggests quick deterioration vs long Buy->Cash suggests trend exhaustion). Encodes sequential context | HIGH | Dr. K's post-2019 model shows rapid state switching (sometimes same-day Buy->Cash). Context-dependent transitions could capture this pattern |
| Heikin Ashi Smoothed filter | Dr. K uses HA Smoothed v4 55 on TradingView. Use HA smooth color (bullish/bearish) as trend confirmation. Already computed in `core/indicators.py` | MEDIUM | `compute_heikin_ashi_smoothed(period=55)` already exists. Feature: `ha_smooth_close > ha_smooth_open` = bullish |
| Indicator confidence scoring | Weight confirmation by indicator agreement strength (e.g., 3/4 indicators confirm = HIGH confidence, 1/4 = LOW). Threshold for action configurable | MEDIUM | Builds on 8 boolean features from `core/feature_snapshot.py`. Instead of binary confirm/deny, produce a confidence score |
| Multi-indicator voting | Multiple indicator conditions vote on signal. Weighted majority wins. Weights tunable per era | MEDIUM | Natural extension of confirmation logic. Voting threshold is a key parameter to sweep |
| Three-way comparison dashboard | Side-by-side: pure state machine vs pure decision tree vs hybrid model. Shows where hybrid wins/loses | MEDIUM | Reuse `analysis/validate_discovery.py` dashboard pattern. Adds a third panel for hybrid |
| Transition delay/cooldown | Prevent signal whipsaw by requiring indicator confirmation to persist for N days before allowing state transition | LOW | Simple counter. Addresses the known whipsaw problem in fast-switching periods |
| Adaptive indicator weights by regime | In trending markets, weight EMA crossovers more. In choppy markets, weight MACD more. Market regime detected by MA200 slope or volatility | HIGH | Research shows regime-adaptive models outperform static ones. But adds significant complexity. Defer if time-constrained |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| ML-driven rule discovery replacing state machine | "Let the model find optimal rules" | With only 962 signals (~150 post-2019), ML will overfit catastrophically. The state machine encodes domain knowledge that prevents overfitting | Keep state machine as structural backbone. Use ML-discovered rules (from Phase 9 decision trees) only as indicator filter conditions |
| Continuous indicator values as direct inputs | "Use raw MACD value, not just above/below signal" | Continuous thresholds are fragile and overfit to specific price ranges. MACD=50 means different things in different market periods | Convert to boolean features (MACD above signal line, EMA9 > EMA21) as already done in `core/feature_snapshot.py`. Boolean features generalize better across eras |
| Full ensemble model (random forest, XGBoost) | "Ensemble of many models" | 150 post-2019 samples is nowhere near enough. Ensemble would memorize training data | Single decision tree (max_depth=4) or rule-based filter with explicit conditions. Interpretability matters for a model you need to trust with money |
| Real-time indicator recomputation | "Recompute indicators intraday" | MDM operates on daily bars. Intraday noise contradicts the model's design philosophy | Daily close-based computation only. No streaming |
| Sentiment/macro indicators | "Add VIX, put/call ratio, Global Liquidity" | Moves away from Dr. K's known indicator set. Adds unconstrained parameters. Can't validate against his signals if using indicators he doesn't use | Stick to Dr. K's known TradingView indicators: EMA 9/21/55, MA 200, MACD 12-26-9, HA Smoothed 55 |
| Per-stock signal generation | "Apply MDM to individual stocks" | MDM is a market-level model (NASDAQ Composite). Individual stock signals are a different problem entirely | Keep MDM as market direction only. Use MDM signal as context for stock-level decisions separately |

## Feature Dependencies

```
[core/indicators.py] (existing)
    |
    +---provides-indicators-to--->  [Indicator Filter Layer] (new)
    |                                    |
    |                                    +---confirms/overrides--->  [Signal Confirmation Logic] (new)
    |                                    |                                |
[strategies/mdm_v2/] (existing)          |                                |
    |                                    |                                |
    +---proposes-signals-to--------->  [Hybrid Engine] (new) <-----------+
    |                                    |
    |                                    +---produces--->  [Hybrid Signal Output]
    |                                                          |
    |                                                          v
[analysis/validate_discovery.py]  <----scores----  [Validation Pipeline] (reuse)
    (existing patterns)

[Cash State Insertion] ----requires----> [Signal Override Logic]
                        ----requires----> [Indicator Filter Layer]

[Contextual Transitions] ----requires----> [Hybrid Engine]
                          ----enhances----> [Cash State Insertion]

[Indicator Confidence Scoring] ----enhances----> [Signal Confirmation Logic]

[Three-way Comparison] ----requires----> [Validation Pipeline]
                        ----requires----> [Hybrid Signal Output]
```

### Dependency Notes

- **Indicator Filter Layer requires core/indicators.py:** Already built. No new indicator computation needed, just consumption of existing boolean features
- **Signal Confirmation Logic requires both State Machine and Indicator layers:** This is the central integration point. Cannot be built until both input layers are wired
- **Cash State Insertion requires Signal Override Logic:** Cash insertion IS an override -- indicators forcing a transition the state machine didn't propose
- **Validation Pipeline reuses existing patterns:** `score_predictions()`, `cross_era_validation()`, confusion matrix generation are all reusable from `analysis/validate_discovery.py`
- **Contextual Transitions enhance Cash State Insertion:** Context (e.g., "how long since last Buy?") makes Cash insertion smarter but is not required for basic Cash logic

## MVP Definition

### Launch With (v1 -- Hybrid Proof of Concept)

Build the minimum to prove the hybrid approach beats 56.7%.

- [ ] **Hybrid Engine class** -- Wraps `MDMV2Engine` state machine output with indicator filter layer. Processes daily bars, outputs BUY/CASH/SELL signals
- [ ] **Confirmation rules** -- State machine BUY signal requires at least 2 of 4 indicator conditions: (1) EMA9 > EMA21, (2) MACD histogram positive, (3) close > MA200, (4) HA smooth bullish
- [ ] **Override rules** -- Force BUY->CASH when EMA9 < EMA21 AND MACD histogram negative (indicator-driven exit regardless of DD count). Force CASH->SELL when close < MA200 AND EMA21 < EMA55
- [ ] **Cash state insertion** -- Insert CASH between BUY and SELL based on indicator conditions (not just DD count). EMA crossover bearish = CASH trigger
- [ ] **Parameterized config** -- `HybridConfig` dataclass extending `MDMV2Config` with confirmation/override thresholds
- [ ] **Validation scoring** -- Score against 962 published signals. Report: overall accuracy, per-type accuracy, confusion matrix, comparison vs pure state machine and pure decision tree

### Add After Validation (v1.x)

Features to add once the hybrid approach is validated as better than 56.7%.

- [ ] **Indicator confidence scoring** -- Replace binary confirm/deny with weighted confidence. Trigger: MVP accuracy > 60% but specific signal types are weak
- [ ] **Contextual state transitions** -- Track state history for context-dependent rules. Trigger: Cash insertion accuracy is poor
- [ ] **Transition cooldown** -- Add N-day confirmation persistence. Trigger: high whipsaw rate in output signals
- [ ] **Parameter sweep for hybrid** -- Grid search over confirmation/override thresholds. Trigger: MVP shows promise but exact thresholds are uncertain
- [ ] **Three-way comparison dashboard** -- Visual comparison chart. Trigger: need to present results or debug divergences

### Future Consideration (v2+)

- [ ] **Adaptive indicator weights by regime** -- Defer: requires regime detection infrastructure + significantly more parameters. Only viable with out-of-sample validation
- [ ] **Heikin Ashi Smoothed as primary filter** -- Defer: less well-understood than EMA/MACD. Add only after base hybrid is validated
- [ ] **VN30 adaptation of hybrid model** -- Defer: must first prove hybrid works on NASDAQ before adapting

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Hybrid Engine class | HIGH | MEDIUM | P1 |
| Confirmation rules | HIGH | HIGH | P1 |
| Override rules | HIGH | HIGH | P1 |
| Cash state insertion (indicator-driven) | HIGH | HIGH | P1 |
| Parameterized config | HIGH | LOW | P1 |
| Validation scoring | HIGH | LOW | P1 |
| Indicator confidence scoring | MEDIUM | MEDIUM | P2 |
| Contextual state transitions | MEDIUM | HIGH | P2 |
| Transition cooldown | MEDIUM | LOW | P2 |
| Parameter sweep | MEDIUM | MEDIUM | P2 |
| Three-way comparison dashboard | MEDIUM | MEDIUM | P2 |
| Adaptive indicator weights | LOW | HIGH | P3 |
| HA Smoothed filter | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for hybrid MVP
- P2: Add when MVP validates (>56.7% accuracy)
- P3: Future consideration after hybrid approach is proven

## Interaction Patterns: State Machine + Indicator Filter

### Pattern 1: Confirmation Gate

State machine proposes a signal transition. Indicator layer confirms or blocks.

```
State Machine says: "BUY (FTD detected on day 5 of rally)"
Indicator Filter checks: EMA9 > EMA21? MACD histogram > 0?
  - If >= N confirmations: ALLOW transition -> BUY
  - If < N confirmations: BLOCK transition -> stay in CASH
```

This is the safest pattern. State machine does the heavy lifting, indicators prevent bad entries.

### Pattern 2: Override Injection

Indicator layer detects conditions that force a state change the state machine hasn't proposed.

```
State Machine says: "BUY (still holding, DD count = 2)"
Indicator Filter detects: EMA9 crossed below EMA21 + MACD histogram turned negative
  -> OVERRIDE: Force BUY -> CASH (early exit before DD count reaches threshold)
```

This captures the post-2019 behavior where Dr. K exits faster than classic DD counting allows.

### Pattern 3: Cash Insertion via Indicator Degradation

Indicators degrade while state machine hasn't triggered a full Sell.

```
State Machine says: "BUY (DD count = 3, below sell threshold)"
Indicator Filter detects: close < EMA21 for 2+ days, MACD turning down
  -> INSERT CASH (intermediate state, not full SELL)
  -> If indicators recover within N days: return to BUY
  -> If indicators worsen: proceed to SELL
```

This is the key post-2019 innovation: Cash as a "wait and see" state driven by indicators, not DD counting.

### Pattern 4: Sell Acceleration

Indicators can accelerate Cash -> Sell transition.

```
State Machine says: "CASH (entered 3 days ago via DD count)"
Indicator Filter detects: close < MA200, EMA21 < EMA55, MACD deep negative
  -> ACCELERATE: Cash -> SELL immediately (skip cash_deterioration_days countdown)
```

## Existing Component Reuse Map

| Existing Component | Location | Reuse Strategy |
|-------------------|----------|----------------|
| MDM v2 state machine | `strategies/mdm_v2/mdm_v2_engine.py` | Wrap -- use as signal proposer, do NOT modify internals |
| Indicator computation | `core/indicators.py` | Call `build_indicator_dataframe()` to get all indicators |
| Boolean feature derivation | `core/feature_snapshot.py` | Extract the 8 boolean feature computations into reusable functions |
| Era splitting | `analysis/rule_discovery.py` | Reuse `split_by_era()` and `ERA_SPLIT_DATE` constant |
| Validation scoring | `analysis/validate_discovery.py` | Reuse `score_predictions()`, confusion matrix formatting, `cross_era_validation()` pattern |
| Decision tree rules | `analysis/rule_discovery.py` | Use discovered rules as starting point for indicator filter conditions |
| V2 config pattern | `strategies/mdm_v2/config.py` | Extend `MDMV2Config` dataclass for hybrid config |
| V2 position manager | `strategies/mdm_v2/position_manager.py` | Reuse state enum and trade recording. May need modified transition logic |

## Sources

- Dr. K's known TradingView indicator setup (EMA 9/21/55, MA 200, MACD 12-26-9, HA Smoothed 55) -- from PROJECT.md context
- Existing codebase: `core/indicators.py`, `core/feature_snapshot.py`, `strategies/mdm_v2/`, `analysis/rule_discovery.py`, `analysis/validate_discovery.py`
- [Hybrid AI-Driven Trading System (ComSIA 2026)](https://arxiv.org/html/2601.19504v1) -- regime-adaptive hybrid combining technical indicators with ML
- [TTFM Pro Fractal Indicator -- State Machine Trading Logic](https://www.scribd.com/document/986560248/Technical-Specification-Report-TTFM)
- [Market Regime Detection using Hidden Markov Models](https://medium.com/@pta.forwork/market-regime-detection-using-hidden-markov-models-in-quantitative-trading-part-1-214e6c77bc2e)
- [IBD Distribution Days Study](https://usethinkscript.com/threads/ibd-distribution-days-study-for-thinkorswim.748/page-2)
- [IBD Market School TradingView Indicator](https://www.tradingview.com/script/sbzEKCNa-IBD-Market-School-tradeviZion/)
- [How to Analyze Distribution Days in Market Timing](https://ibdstock.com/analyze-distribution-days-market-timing/)
- Phase 9 rule discovery output (56.7% cross-era validation baseline)
- Phase 10 discovery validation (confusion matrices, degradation deltas confirming structural change at Feb 2019)

---
*Feature research for: Hybrid MDM Engine v3.0*
*Researched: 2026-03-29*
