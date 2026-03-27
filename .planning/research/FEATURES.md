# Features Research: MDM Reverse-Engineering System

## Table Stakes (Must Have)

These are essential for the reverse-engineering and backtesting workflow.

### 1. Data Normalization Layer
- **What:** Unified data loader that normalizes US data (prices scaled ~1000x) and VN30 data into consistent OHLCV format
- **Complexity:** Low
- **Dependencies:** None — foundational

### 2. Signal Comparison Engine
- **What:** Tool to compare model-generated signals (Buy/Sell/Cash + dates) against published signal history, with match scoring
- **Complexity:** Medium
- **Dependencies:** Data normalization
- **Note:** This is the single biggest gap in the current codebase — there is no way to score generated signals against published history

### 3. MDM Classic Rules on US Data
- **What:** Run existing pre-2019 rules on NASDAQ data (not just VNINDEX) to establish baseline
- **Complexity:** Low (rules exist, just need different data feed)
- **Dependencies:** Data normalization

### 4. Divergence Analysis Report
- **What:** Identify where classic rules diverge from published post-2019 signals — dates, signal types, durations
- **Complexity:** Medium
- **Dependencies:** Signal comparison engine, MDM classic on NASDAQ

### 5. Cash State Modeling
- **What:** Implement Cash as an intermediate state between Buy and Sell (not present in original rules)
- **Complexity:** High — this is the most significant post-2019 behavioral change
- **Dependencies:** Divergence analysis (to understand when/why Cash triggers)

### 6. Parameterized Rule Engine
- **What:** MDM v2 engine where thresholds and conditions are configurable (DD count, FTD window, MA periods, etc.)
- **Complexity:** Medium
- **Dependencies:** Cash state modeling

### 7. Backtesting with Performance Metrics
- **What:** Equity curve, drawdown, win rate, Sharpe ratio, comparison vs buy-and-hold
- **Complexity:** Low-Medium (partially exists)
- **Dependencies:** Rule engine

### 8. Published Signal History as Test Data
- **What:** Parse and store Dr. K's published TECL and NASDAQ signals as structured test fixtures
- **Complexity:** Low
- **Dependencies:** None

## Differentiators (Advanced Capabilities)

### 9. Hypothesis Testing Framework
- **What:** Systematic way to propose, test, and score rule modifications (e.g., "what if FTD threshold is 2% instead of 1%?")
- **Complexity:** Medium
- **Dependencies:** Parameterized rule engine, signal comparison
- **ROI:** High — enables systematic exploration

### 10. Visual Signal Overlay
- **What:** Chart showing price data with model signals AND published signals overlaid for visual comparison
- **Complexity:** Medium
- **Dependencies:** Data normalization, signal comparison
- **ROI:** High — visual patterns often reveal what statistics miss

### 11. Parameter Sweep / Grid Search
- **What:** Automated sweep over rule parameters to find best match with published signals
- **Complexity:** Medium
- **Dependencies:** Parameterized rule engine, signal comparison

### 12. Rolling Window Validation
- **What:** Train rules on pre-2022 signals, validate on 2022-2026 to check stability
- **Complexity:** Medium
- **Dependencies:** Parameter sweep

### 13. VN30 Market Adaptation Module
- **What:** Adjustments for Vietnamese market specifics (T+2.5, 7% price limits, derivative expiry filtering)
- **Complexity:** Medium-High
- **Dependencies:** Validated MDM v2 rules

### 14. Signal Confidence Scoring
- **What:** Rate each generated signal's confidence based on how many conditions were met, volume strength, etc.
- **Complexity:** Medium
- **Dependencies:** Parameterized rule engine

### 15. Multi-Timeframe Analysis
- **What:** Cross-reference daily signals with weekly trend for confirmation
- **Complexity:** Medium
- **Dependencies:** Core rule engine

### 16. Trade-by-Trade Attribution
- **What:** For each published signal, explain which rule(s) triggered it in the model
- **Complexity:** Medium
- **Dependencies:** Signal comparison, rule engine

### 17. Regime Detection
- **What:** Classify market periods (trending, ranging, volatile) to understand when MDM performs best/worst
- **Complexity:** Medium-High
- **Dependencies:** Backtesting

### 18. Interactive Analysis Notebooks
- **What:** Jupyter notebooks for exploratory analysis of signal patterns
- **Complexity:** Low
- **Dependencies:** Core libraries

## Anti-Features (Do NOT Build)

| Feature | Why Not |
|---------|---------|
| **ML/Genetic programming for rule discovery** | Model is rule-based and must remain interpretable. ML will overfit on ~100 signals. |
| **Real-time trading integration** | Out of scope — research/backtest only |
| **Web dashboard** | Command-line/notebook analysis is sufficient |
| **Automated data scraping** | Explicit out-of-scope per PROJECT.md |
| **Options/derivatives strategies** | Beyond basic long/short/cash is out of scope |
| **Intraday tick data analysis** | MDM operates on daily bars; intraday adds noise |
| **Social/sentiment data integration** | MDM is purely technical (price + volume) |

## Feature Dependencies (Build Order)

```
Data Normalization ──┬── MDM Classic on NASDAQ ──┐
                     │                            ├── Divergence Analysis
Published Signals ───┴── Signal Comparison ───────┘
                                                     │
                                                     ▼
                                              Cash State Modeling
                                                     │
                                                     ▼
                                           Parameterized Rule Engine
                                                     │
                                              ┌──────┼──────┐
                                              ▼      ▼      ▼
                                          Hypothesis  Visual  Parameter
                                          Testing    Overlay  Sweep
                                                     │
                                                     ▼
                                              VN30 Adaptation
```

## MVP Recommendation

**Minimum viable for reverse-engineering:**
1. Data normalization + published signal parsing
2. Signal comparison engine
3. MDM classic on NASDAQ (baseline)
4. Divergence analysis report
5. Cash state hypothesis + parameterized engine

**Then iterate:** Use divergence report to guide rule modifications, validate with signal comparison engine.

## Open Questions

- Whether the 2% FTD threshold mentioned in Dr. K's FAQ applies post-2019 or was always the rule
- Whether intraday prices matter or if close-only is sufficient
- How the "material change" on Feb 9, 2019 relates to the Cash state behavior

---
*Researched: 2026-03-27*
*Confidence: HIGH for table stakes, MEDIUM for differentiators*
