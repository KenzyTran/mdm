# Pitfalls Research: MDM Reverse-Engineering

## Critical Pitfalls

### 1. Overfitting to Published Signals
- **Risk:** HIGH
- **What:** Tuning rules to perfectly match ~100 published signals creates a model that works on history but fails forward
- **Warning signs:** Match rate >95% with many special-case rules; parameter values that are oddly specific (e.g., 3.7% threshold)
- **Prevention:**
  - Split signals into train (2017-2022) and test (2023-2026) sets
  - Count the number of rules/parameters — fewer is better
  - Prefer rules that match the spirit of O'Neil methodology over arbitrary curve-fitting
  - Any rule should have a market-logic explanation, not just statistical fit
- **Phase:** Validation phase — must validate on held-out data

### 2. Lookahead Bias in Signal Comparison
- **Risk:** HIGH
- **What:** Using future price data to determine if a signal "should have" triggered — the model can only see data available at signal time
- **Warning signs:** Model performs better in backtest than published signals; signals trigger "perfectly" at tops/bottoms
- **Prevention:**
  - Strict point-in-time data only — each bar only sees current and prior data
  - MA calculations use only data available at that point
  - Test by running model sequentially (not vectorized with full history)
- **Phase:** Implementation phase — must be enforced in engine architecture

### 3. Data Normalization Errors (US Market Data)
- **Risk:** HIGH
- **What:** NASDAQ/S&P500 data has prices scaled by ~1000x. If not normalized correctly, all percentage calculations (FTD >=1%, DD >=0.2%, stop losses) will be wrong
- **Warning signs:** Absurd signal counts, percentages that don't match reality
- **Prevention:**
  - Verify normalization by spot-checking known prices (e.g., NASDAQ on specific dates against Yahoo Finance)
  - Unit test: normalized price should match known index values within 0.1%
  - Log actual percentage changes and sanity-check early
- **Phase:** Data normalization phase — first thing to get right

### 4. Confusing TECL Signals with NASDAQ Signals
- **Risk:** MEDIUM-HIGH
- **What:** Dr. K publishes signals for both TECL (3x leveraged NASDAQ ETF) and NASDAQ Composite. The signals and returns differ because TECL amplifies moves. The MDM generates ONE signal set applied to both, but returns differ due to leverage.
- **Warning signs:** Trying to match TECL % returns with NASDAQ % changes
- **Prevention:**
  - Use NASDAQ Composite signals as ground truth for signal timing (Buy/Sell/Cash dates)
  - TECL returns are just 3x leveraged exposure to the same signals
  - Validate signal DATES match, not return percentages
- **Phase:** Signal parsing phase

### 5. Same-Day Signal Interpretation
- **Risk:** MEDIUM-HIGH
- **What:** Published data shows same-day Buy→Cash (e.g., 06-15-2020) or rapid switching. This could mean: (a) intraday signal change, (b) signal triggered at open but reversed by close, (c) data display artifact
- **Warning signs:** Model can't reproduce same-day switches; forcing it creates fragile rules
- **Prevention:**
  - Document each same-day event and check if it's an artifact
  - Some may be "signal changed during the day" which daily bars can't capture
  - Accept that some signals may be irreproducible with daily data — target high match rate, not perfection
- **Phase:** Divergence analysis phase

### 6. Survivorship Bias in Signal History
- **Risk:** MEDIUM
- **What:** Published signals may have been retroactively adjusted or the worst signals explained away (marked with * or **)
- **Warning signs:** Model produces signals that aren't in published history, or vice versa
- **Prevention:**
  - Treat the ** marker (Feb 2019 change) as a regime boundary — don't mix pre/post 2019 for rule discovery
  - Accept that pre-2019 signals follow different rules
  - Focus reverse-engineering on post-Feb-2019 signals only
- **Phase:** Signal analysis phase

## Market Adaptation Pitfalls (US → VN30)

### 7. Different Market Microstructure
- **Risk:** HIGH
- **What:** VN30 has fundamentally different characteristics than NASDAQ:
  - **7% daily price limit** — prevents panic selling, creates artificial floors/ceilings
  - **T+2.5 settlement** — can't immediately re-enter after exit
  - **Derivative expiry effects** — existing rules already note this (skip DD on expiry days)
  - **Lower liquidity** — volume patterns behave differently
  - **Trading hours** — no pre/post-market, different session structure
- **Warning signs:** Rules that work on NASDAQ produce excessive false signals on VN30
- **Prevention:**
  - After validating on NASDAQ, DON'T blindly copy parameters to VN30
  - Adjust thresholds systematically: FTD % threshold, DD % threshold, MA periods
  - Account for price limit days (these are NOT normal distribution days)
  - Filter derivative expiry days (already in original rules)
- **Phase:** VN30 adaptation phase — dedicated phase after NASDAQ validation

### 8. Volume Interpretation Differences
- **Risk:** MEDIUM-HIGH
- **What:** US and Vietnamese markets have very different volume profiles. "Volume higher than previous day" has different statistical properties in each market.
- **Warning signs:** Too many or too few distribution days on VN30 compared to NASDAQ
- **Prevention:**
  - Compare volume distribution statistics between markets
  - Consider relative volume (vs. 50-day average) instead of absolute previous-day comparison
  - Test volume conditions with different thresholds for VN30
- **Phase:** VN30 adaptation phase

### 9. Index Composition Effects
- **Risk:** MEDIUM
- **What:** VN30 has only 30 stocks vs NASDAQ's thousands. Single large-cap moves can dominate the index, creating false technical signals.
- **Warning signs:** Signals triggered by single-stock events rather than broad market moves
- **Prevention:**
  - Monitor breadth indicators alongside index signals
  - Consider adding an advance/decline check as a filter
  - Be cautious with signals near index rebalancing dates
- **Phase:** VN30 adaptation phase

### 10. Assuming Post-2019 Rules are a Simple Modification
- **Risk:** MEDIUM
- **What:** The "material change" might not be a parameter tweak — it could be a fundamentally different architecture (e.g., adding new indicators, different state machine)
- **Warning signs:** No parameter set on classic rules matches post-2019 behavior; divergences are structural, not threshold-based
- **Prevention:**
  - Start with parameter tweaks but be ready to hypothesize structural changes
  - The Cash state and rapid switching suggest architectural change, not just parameter tuning
  - Consider that the 2019 change might involve new inputs (e.g., VIX, breadth, relative strength)
- **Phase:** Divergence analysis → hypothesis phase

## Process Pitfalls

### 11. Premature VN30 Application
- **Risk:** MEDIUM
- **What:** Jumping to VN30 before thoroughly validating on NASDAQ wastes time and makes debugging harder
- **Prevention:** Strict phase ordering — NASDAQ validation first, VN30 adaptation second

### 12. Not Version-Controlling Rule Hypotheses
- **Risk:** LOW-MEDIUM
- **What:** Testing many rule variations without tracking what was tried, what worked, what didn't
- **Prevention:** Each rule set should be a named, versioned configuration (e.g., "mdm_v2_hypothesis_3")

---
*Researched: 2026-03-27*
*Confidence: HIGH for data/implementation pitfalls, MEDIUM-HIGH for market adaptation pitfalls*
