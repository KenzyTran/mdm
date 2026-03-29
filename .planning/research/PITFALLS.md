# Pitfalls Research: Hybrid MDM Engine (v3.0)

**Domain:** Hybrid state machine + indicator filter trading model
**Researched:** 2026-03-29
**Confidence:** HIGH (grounded in project-specific findings from Phases 9-10 and established quantitative finance pitfalls)

## Critical Pitfalls

### Pitfall 1: Signal Authority Ambiguity — Who Has Final Say?

**What goes wrong:**
The hybrid model has two decision layers: the state machine (DD/FTD/Rally) proposes signals, and the indicator filters (EMA/MACD) confirm or override. Without a strict authority hierarchy, the system degenerates into ad-hoc logic where sometimes the state machine wins, sometimes the indicator wins, and no one can reason about why a particular signal fired. This creates untestable, un-debuggable spaghetti logic.

**Why it happens:**
Developers add indicator overrides case-by-case when they find signals that "should have been different." Each override is locally reasonable but globally they create contradictions. The state machine says BUY (FTD fired), the EMA filter says no (price below EMA 55), but MACD histogram is positive — what wins? Without a designed resolution protocol, every edge case gets its own if-else branch.

**How to avoid:**
Define a strict signal authority chain before writing any code:
1. State machine proposes a signal transition (e.g., BUY via FTD)
2. Indicator filter layer has exactly two powers: CONFIRM or VETO (not propose new signals)
3. If vetoed, the state machine stays in its current state — it does not jump to a different state
4. Document every override path with a named rule (e.g., "EMA55_VETO: FTD buy vetoed when close < EMA55")

Never let indicators propose signals that the state machine didn't originate. Indicators are filters, not signal generators.

**Warning signs:**
- Code has `if indicator_says_X and not state_machine_says_Y` patterns
- More than 3-4 override rules accumulating
- Signal log shows transitions that neither the state machine nor indicators alone would produce
- Unit tests for individual components pass but integration tests fail

**Phase to address:**
Architecture design phase — must be resolved before any code is written. This is a design decision, not an implementation detail.

---

### Pitfall 2: Look-Ahead Bias in Indicator Computations

**What goes wrong:**
EMA/MACD calculations use the full price series (including future data) when computed via pandas vectorized operations like `ewm()`. The indicator values at time T are mathematically correct, but the model "knows" the EMA at the exact close price — in reality, the EMA value shifts during the trading day. More subtly, the feature snapshot from Phase 9 already computed indicators on the full OHLCV history and joined them to signal dates. If the hybrid engine reuses these pre-computed snapshots rather than computing indicators incrementally, any indicator that depends on future normalization (e.g., min-max scaling) introduces look-ahead.

**Why it happens:**
The existing `core/indicators.py` computes EMA/SMA/MACD on entire DataFrames in one pass — this is standard and mathematically equivalent to incremental computation for these specific indicators (EMA, SMA, MACD are causal filters). The danger is when someone adds a non-causal indicator (e.g., Bollinger Band percentile rank, Z-score normalization, or any indicator using `shift(-1)` or future-looking windows).

**How to avoid:**
- The existing EMA/SMA/MACD computations in `core/indicators.py` are safe (causal, no future leakage). Keep using vectorized computation for these.
- Add a mandatory code review checklist item: "Does this indicator use only past and current data?"
- Never use `shift(-1)`, `rolling().apply()` with center=True, or any look-ahead normalization
- Test: for any indicator, compare its value at row N computed on df[:N+1] vs df[:]. They must be identical.
- The feature snapshot approach (Phase 9) is fine for statistical analysis but the hybrid engine must compute indicators on the live DataFrame, not from pre-joined snapshots.

**Warning signs:**
- Indicator values change when you truncate the DataFrame at different endpoints
- Model accuracy drops sharply when run on streaming data vs. full-history backtest
- Bollinger Band or Z-score indicators appear in the filter layer

**Phase to address:**
Engine implementation phase — enforce during indicator integration into the hybrid engine.

---

### Pitfall 3: Overfitting Indicator Filter Thresholds to 95 Post-2019 Signals

**What goes wrong:**
The post-2019 era has only 95 signals (Phase 9 confirmed: Pre-2019=867, Post-2019=95). The decision tree achieved 58.9% accuracy on this small sample with class_weight='balanced'. Tuning indicator filter thresholds (e.g., "veto FTD when close < EMA55 AND MACD histogram < -0.5") against 95 signals almost guarantees overfitting. With 8 boolean features and 3 signal classes, the combinatorial space is large relative to the sample size.

**Why it happens:**
The temptation is strong: each indicator threshold tuned to match one more signal feels like progress. But 95 signals is roughly 30 per class — with 8 binary features, you can construct 256 possible feature combinations. Many combinations appear only once or twice in the data, making any rule based on them statistically meaningless.

**How to avoid:**
- Limit the hybrid model to at most 2-3 indicator filter rules total (not per-signal-type)
- Each filter rule must match at least 10 signals to be considered statistically meaningful
- Use Leave-One-Out Cross-Validation (LOOCV) or k-fold CV (k=5) on the 95-signal set — never train and evaluate on the same data
- Pre-register the filter rules before testing them: decide what EMA/MACD conditions to test based on trading logic, not by scanning the data
- The 867 pre-2019 signals are useful for checking that filters don't catastrophically break on historical data, even though the rules differ

**Warning signs:**
- Post-2019 match rate jumps from 58.9% to >80% with added filters (suspicious given the sample size)
- Any filter rule that triggers on fewer than 5 historical signals
- Filter thresholds that are oddly specific (e.g., "MACD > 0.37" instead of "MACD > 0")
- Cross-validation accuracy is much lower than training accuracy

**Phase to address:**
Filter tuning phase — must use disciplined validation methodology. Consider this the single most likely failure mode of the v3.0 milestone.

---

### Pitfall 4: State Machine Corruption from Indicator Overrides

**What goes wrong:**
The existing v2 state machine has carefully designed state transitions: CASH->BUY (via FTD or MA50 breakout), BUY->CASH (via DD threshold or stop loss), CASH->SELL (via MA50 breakdown or deterioration timer). Adding indicator filters that can veto transitions creates "stuck states" — the state machine wants to transition but the filter keeps vetoing, leaving the model in a state that has no natural exit path.

Example: State machine fires FTD (CASH->BUY transition), but EMA filter vetoes. Model stays in CASH. DD counter was reset when FTD fired (as it does in current code). Now the model is in CASH with a reset DD counter and no pending rally attempt — it has no mechanism to re-trigger a buy signal until a new correction-and-rally cycle begins. This could leave the model stuck in CASH for weeks.

**Why it happens:**
The state machine components (DD counter, Rally tracker, FTD detector) have internal state that mutates on transitions. If a transition is vetoed after internal state has already been updated, the components are in an inconsistent state. The existing code in `DistributionDayCounter.reset()` clears dd_history on FTD signal — if the FTD is subsequently vetoed, the DD history is already gone.

**How to avoid:**
- Implement a two-phase commit for state transitions:
  1. Phase 1: State machine proposes transition, returns the proposed action WITHOUT mutating internal state
  2. Phase 2: Indicator filter confirms/vetoes
  3. Phase 3: Only if confirmed, commit the state mutation
- The current code mutates state eagerly (DD counter resets in `check_ftd()` call chain). This must be refactored to separate proposal from commitment.
- Add invariant checks: after every day's processing, verify the state machine is in a valid state (e.g., if in CASH, verify there's a path to exit CASH)

**Warning signs:**
- Model stays in CASH or SELL for unusually long periods (>30 trading days without any transition attempt)
- Signal log shows "proposed BUY, vetoed by filter" followed by silence
- DD counter is 0 but model is in CASH without a recent buy signal

**Phase to address:**
Engine architecture phase — must refactor state mutation logic before adding filters. This is the hardest integration pitfall because it requires changing existing v2 engine internals.

---

### Pitfall 5: Conflating "Cash" State Semantics Between State Machine and Indicators

**What goes wrong:**
The v2 state machine's CASH state means "the market is deteriorating but not fully bearish — reduce exposure." The indicator layer's concept of "neutral" (e.g., EMA 9 near EMA 21, MACD near zero) is a different thing entirely. If the indicator layer can trigger CASH independently of the state machine, the CASH state loses its specific meaning and becomes a grab-bag for "anything that's not clearly bullish or bearish."

Phase 10 found that the decision tree uses different features for Cash classification pre-2019 vs post-2019 (close_above_ema9 dominant pre-2019, close_above_ema55 dominant post-2019). This means "Cash" is not a stable indicator concept — it shifted structurally. Building indicator filters for Cash based on one era's patterns will fail on the other.

**Why it happens:**
Cash is the hardest state to define because it's the absence of a strong signal. Both the state machine and indicators struggle with it. The temptation is to let either system trigger Cash, which doubles the confusion.

**How to avoid:**
- Only the state machine should propose BUY->CASH transitions (via DD accumulation or stop loss)
- Indicators should only be allowed to veto BUY proposals (keeping model in current state), not to propose new CASH entries
- Accept that Cash will be the lowest-accuracy signal type — the Phase 9 decision tree already showed this
- Do not add Cash-specific indicator filters; focus filter effort on Buy and Sell accuracy

**Warning signs:**
- Cash signals in the hybrid model that don't correspond to any DD accumulation or stop loss event
- Cash accuracy improving but Buy/Sell accuracy degrading
- More than 2 distinct code paths leading to CASH state

**Phase to address:**
State machine design phase — define Cash semantics clearly before implementation.

---

### Pitfall 6: Era-Dependent Filter Rules Creating a Fragile Model

**What goes wrong:**
Phase 9 revealed a structural shift: close_above_ema9 was the dominant feature pre-2019 (importance=0.702) while close_above_ema55 became dominant post-2019 (importance=0.687), with no overlap in top-2 features between eras. If the hybrid model uses post-2019 era features exclusively (e.g., EMA 55 filter), it will fail when market conditions shift again. If it tries to use both eras' features, the rules conflict.

**Why it happens:**
The 2019 structural change was a deliberate model update by Dr. K, not a market regime change. The hybrid model is trying to reverse-engineer a system that was intentionally redesigned. Using statistical patterns from the post-2019 era assumes those patterns are stable going forward — but Dr. K could update the model again.

**How to avoid:**
- Design the hybrid model to be explicitly post-2019 only. Do not try to create a single model that works across both eras.
- Accept the 21.3% cross-era degradation as evidence that era-specific models are necessary.
- Make the filter layer configurable so that when the model breaks (which it will, eventually), swapping filter rules is a configuration change, not a code rewrite.
- Track filter rule performance over time with a simple monitoring mechanism (match rate per quarter).

**Warning signs:**
- Temptation to "unify" pre-2019 and post-2019 into one set of filter rules
- Filter rules that work well on 2019-2023 but poorly on 2024-2026
- Model performance degrading on most recent signals

**Phase to address:**
Filter design phase — make era-awareness explicit in the architecture. Validation phase — test on most recent signals as held-out set.

---

### Pitfall 7: Indicator Calculation Divergence from Dr. K's Platform

**What goes wrong:**
Dr. K uses TradingView for charting. The project's `core/indicators.py` uses `adjust=False` for EMA to match TradingView behavior. But subtle differences remain: TradingView's MACD implementation, Heikin Ashi Smoothed algorithm, and EMA initialization (first value) can differ from pandas implementations. If the hybrid model's indicator values diverge by even 0.1% from what Dr. K sees, filter thresholds calibrated to match his signals will misfire.

**Why it happens:**
EMA with `adjust=False` initializes with the first data point. TradingView may use a different initialization (e.g., SMA of first N points). Over long histories this difference washes out, but near the initialization point or after data gaps, values can diverge. MACD is particularly sensitive because it's a difference of two EMAs — small divergences compound.

**How to avoid:**
- Validate indicator values against TradingView by spot-checking 5-10 dates manually
- For MACD, check the sign of the histogram (above/below zero) rather than exact values — the sign is what matters for boolean features
- Use boolean features (e.g., "MACD > 0", "close > EMA55") rather than continuous thresholds — this is more robust to small calculation differences
- The existing 8 boolean features from Phase 9 are the right approach; do not regress to continuous thresholds

**Warning signs:**
- Filter using "MACD > 0.5" instead of "MACD > 0" — continuous thresholds are fragile
- Indicator values at signal dates that don't match TradingView screenshots
- EMA values diverging more at recent dates than historical dates (initialization issue)

**Phase to address:**
Indicator validation phase — spot-check before building filters on top.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding filter rules in engine `process_day()` | Fast to implement, easy to test one rule | Adding/removing filters requires engine code changes; rules become entangled with state logic | Never — filter rules should be in config or a separate filter layer |
| Reusing v2 engine directly with if-else patches | No refactoring needed | State machine internals become impossible to reason about; DD counter reset bug (Pitfall 4) | Only for quick proof-of-concept, must refactor before validation |
| Training filter rules on all 95 post-2019 signals | Maximum data for fitting | No held-out test set; impossible to detect overfitting | Never — always hold out at least 20% (19 signals minimum) |
| Copying `strategies/mdm_v2/` wholesale to `strategies/mdm_v3/` | Clean separation | Code duplication; bug fixes must be applied in two places; DD counter, Rally tracker, FTD detector are identical | Acceptable if v2 is frozen and archived |
| Using continuous indicator values as filter thresholds | More expressive filtering | Fragile to calculation differences (Pitfall 7); overfitting risk (Pitfall 3) | Never for this project — stick to boolean features |

## Integration Gotchas

Common mistakes when connecting the hybrid engine to existing components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| v2 state machine + indicator filter | Mutating DD counter/Rally tracker state before filter confirmation | Two-phase commit: propose transition, filter confirms, then commit state changes |
| `core/indicators.py` + v2 engine `Indicators` | Using two different indicator modules with different MA calculations | Hybrid engine should use `core/indicators.py` (EMA/MACD) for filter layer and v2's `Indicators` (MA10/MA50/price_location) for state machine — but verify no naming conflicts |
| Feature snapshot (Phase 9) + live engine | Reusing pre-computed snapshots instead of computing indicators on-the-fly | Snapshots are for analysis; the engine must compute indicators from the DataFrame each run |
| `V2MarketState` enum + new filter states | Adding filter-specific states (e.g., PENDING_BUY, VETOED) to the enum | Keep `V2MarketState` as-is (BUY/CASH/SELL). Filter decisions are internal to the filter layer, not visible states |
| Signal validation against 962 signals | Comparing hybrid signals using exact date match | Allow +/- 1 day tolerance for signal dates (weekend snapping, same-day signals) |

## Performance Traps

Patterns that work at small scale but fail as data grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Recomputing all indicators on every `process_day()` call | Slow backtest (seconds per day instead of milliseconds) | Compute indicators once on full DataFrame before main loop (current v2 approach is correct) | Never for this project — 962 signals is tiny |
| Storing full DataFrame copies at each state transition for debugging | Memory growth, slow backtest | Store only the state diff (date, proposed signal, filter decision, final signal) in a lightweight log | >10,000 backtest iterations during parameter sweeps |
| Grid search over filter thresholds | Combinatorial explosion: 3 filters x 10 threshold values = 1000 backtests | Use boolean features only (no thresholds to sweep); limit to 2-3 filters max | Not applicable if boolean-only approach is followed |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Filter layer:** Often missing veto-without-stuck-state logic — verify that every vetoed transition has a recovery path
- [ ] **State machine refactor:** Often missing the two-phase commit — verify that `dd_counter.reset()` is NOT called before filter confirmation
- [ ] **Validation:** Often missing held-out test set — verify that at least 19 post-2019 signals were not used during filter tuning
- [ ] **Signal log:** Often missing filter decision details — verify log records "proposed X, filter said Y, final Z" not just "final Z"
- [ ] **Cross-era check:** Often missing pre-2019 regression test — verify filters don't catastrophically break pre-2019 accuracy even though model targets post-2019
- [ ] **Indicator parity:** Often missing TradingView spot-check — verify EMA/MACD boolean values match TradingView at 5+ dates
- [ ] **Cash state semantics:** Often conflated between "state machine Cash" and "indicator neutral" — verify only state machine proposes CASH transitions
- [ ] **Config separation:** Often hardcoded in engine — verify filter rules are in configuration, not in `process_day()` logic

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Signal authority ambiguity (P1) | MEDIUM | Audit all signal paths, document each as "state machine" or "filter"; remove any indicator-originated signals |
| Look-ahead bias (P2) | HIGH | Must re-validate all results from the point of introduction; compare truncated vs full DataFrame indicator values |
| Overfitting filters (P3) | MEDIUM | Remove all filter rules, re-introduce one at a time with LOOCV validation; accept lower match rate |
| State machine corruption (P4) | HIGH | Refactor to two-phase commit; audit every `reset()` call; add invariant checks; re-run full backtest |
| Cash semantics confusion (P5) | LOW | Remove indicator-originated Cash transitions; re-restrict Cash to DD accumulation and stop loss paths only |
| Era-dependent fragility (P6) | LOW | Restrict model to post-2019 explicitly; add quarterly performance monitoring |
| Indicator divergence (P7) | MEDIUM | Spot-check against TradingView; switch to boolean-only features if continuous thresholds are in use |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1: Signal authority ambiguity | Architecture/Design phase | Design doc specifies authority chain; code review confirms no indicator-originated signals |
| P2: Look-ahead bias | Engine implementation phase | Test: indicator at row N identical whether computed on df[:N+1] or df[:] |
| P3: Overfitting to 95 signals | Filter tuning phase | LOOCV or 5-fold CV accuracy reported; no filter rule triggers on <10 signals |
| P4: State machine corruption | Engine refactoring phase | Unit test: vetoed FTD does not reset DD counter; invariant check passes after every day |
| P5: Cash semantics | State machine design phase | Code review: only 2 paths to CASH (DD threshold, stop loss); no indicator-originated CASH |
| P6: Era-dependent fragility | Filter design + Validation phase | Model explicitly scoped to post-2019; held-out 2024-2026 accuracy reported separately |
| P7: Indicator divergence | Indicator validation phase | 5+ dates spot-checked against TradingView; boolean feature values match |

## Sources

- Project Phase 9 findings: Pre-2019 CV accuracy 53.9%, Post-2019 CV accuracy 58.9%, structural feature shift between eras
- Project Phase 10 findings: 21.3% cross-era degradation, 962 signals validated, era-specific trees required
- Existing v2 engine code: `strategies/mdm_v2/position_manager.py`, `config.py`, `distribution_day.py`, `ftd_signal.py`
- [Understanding Look-Ahead Bias in Trading Strategies](https://www.marketcalls.in/machine-learning/understanding-look-ahead-bias-and-how-to-avoid-it-in-trading-strategies.html)
- [Backtesting Traps: Common Errors to Avoid](https://www.luxalgo.com/blog/backtesting-traps-common-errors-to-avoid/)
- [Heuristic Based Trading System on Forex Data Using Technical Indicator Rules](https://www.sciencedirect.com/science/article/abs/pii/S1568494616300369) — signal conflict resolution via weighted majority voting
- [5 Steps to Build Rule-Based Trading Strategies](https://www.luxalgo.com/blog/5-steps-to-build-rule-based-trading-strategies/)

---
*Pitfalls research for: Hybrid MDM v3.0 Engine (state machine + indicator filters)*
*Researched: 2026-03-29*
