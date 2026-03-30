# Project Research Summary

**Project:** MDM V2 Signal Quality & Macro Filter (v5.0)
**Domain:** Global Liquidity macro filter + SELL acceleration + BUY selectivity for market timing engine
**Researched:** 2026-03-30
**Confidence:** MEDIUM-HIGH

## Executive Summary

This milestone enhances the existing MDM V2 engine with three features directly confirmed by Dr. K's 2013 webinar statements: a QE floor filter that suppresses SELL signals during central bank liquidity expansion, a SELL acceleration condition requiring momentum deterioration before transitioning to SELL, and a BUY quality gate that rejects low-setup entries. The technical implementation is straightforward — no new dependencies are needed, and the existing pandas/numpy stack handles all required calculations. The key engineering challenge is correctness, not complexity: look-ahead bias in weekly-to-daily liquidity alignment and the previously-documented state[i] vs state[i-1] index error are the two highest-risk issues that must be addressed in Phase 1 before any results are trusted.

The recommended approach builds three gating components (`LiquidityLoader`, `SellAccelerator`, `BuyQualityScorer`) as peers in the existing `strategies/mdm_v2/` module structure, using a filter-gate pattern where each component suppresses or modifies state transitions proposed by the existing logic. All new config parameters default to disabled (backward-compatible), enabling rigorous A/B comparison against the V2 baseline (190.8% total return reference). The architecture is additive: the existing FTD detector, distribution day counter, rally tracker, and position manager are unchanged — the new components insert as a processing layer immediately before `process_day()`.

The primary risk is over-engineering. The hybrid engine experiment already demonstrated that multi-condition BUY indicator ensembles (47% rejection rate, 43% correct — near random) do not work. The QE floor filter is the highest-value feature because it directly implements confirmed Dr. K behavior and uses simple, non-overfit logic (`liquidity_roc_20w > 0`). SELL acceleration and BUY selectivity carry overfitting risk if parameterized too aggressively — they must be validated on bear-market sub-periods (2008, 2022), not just the 2009-2021 bull run.

## Key Findings

### Recommended Stack

No new dependencies required. The existing pandas >= 2.0.0, numpy >= 1.24.0, Python >= 3.10 stack handles all three features. The critical implementation choices are `pd.merge_asof(direction='backward')` for weekly-to-daily liquidity alignment (not `resample().ffill()`, which creates non-trading day rows), and pure pandas `pct_change(n)` + `.diff()` for momentum/acceleration calculations. Three new custom modules are added to `strategies/mdm_v2/` — they are code, not library dependencies.

**Core technologies:**
- pandas >= 2.0.0: All data manipulation, merge_asof for time-series alignment — already installed, no upgrade needed
- numpy >= 1.24.0: Numerical calculations for acceleration and quality scoring — already installed
- Python >= 3.10: Runtime — already installed

**New custom modules (not libraries):**
- `strategies/mdm_v2/liquidity.py`: LiquidityLoader + LiquidityRegime enum
- `strategies/mdm_v2/sell_accelerator.py`: SellAccelerator momentum checks
- `strategies/mdm_v2/buy_quality.py`: BuyQualityScorer FTD quality scoring

**What to avoid:** pandas-ta and ta-lib (unnecessary dependencies for trivial calculations), scikit-learn classifiers (overfitting risk on ~100 sell signals), FRED API (data already in CSV through March 2026), `statsmodels` for regime detection (simple threshold beats HMM given only 3 QE cycles).

### Expected Features

**Must have (table stakes — directly implements confirmed Dr. K behavior):**
- Liquidity Data Loader: Load `global_liquidity.csv`, forward-fill weekly to daily with publication lag, expose `liquidity_regime` column
- QE Floor Filter: When `liquidity_roc_20w > 0`, block CASH->SELL transition — Dr. K confirmed this is a real model feature
- SELL Acceleration Condition: Require at least one of: price ROC 5-day < -3%, OR 3+ DD in last 10 days, OR MA50 break with volume confirmation
- BUY Quality Gate (MVP): Reject BUY when MA10 < MA50 — simplest, most robust filter consistent with Dr. K's selectivity language
- A/B Backtest Comparison: V2 baseline vs V2+filters on VN30 and NASDAQ; report delta in return, CAGR, drawdown, Sharpe, trade count

**Should have (differentiators — add after P1 features validated):**
- FTD Quality Scoring: Score by gain magnitude + volume ratio + rally depth; threshold sweep
- Post-FTD Confirmation Window: Track DD in first 3 days after BUY entry; early DD = immediate exit (IBD research: 95% failure rate when DD appears on days 1-2 after FTD)
- DD Clustering Metric: Formalize "3+ DD in 10 days" into reusable component
- Dashboard: Liquidity overlay on price chart, sell acceleration indicator panel, buy signal quality annotations

**Defer (v2+):**
- Liquidity-adjusted position sizing (requires Kelly Criterion integration, adds complexity before core filters are validated)
- Adaptive acceleration threshold by volatility (needs fixed threshold proven first)
- VN30-specific liquidity proxy (SBV data availability uncertain; global liquidity applicability to Vietnam is unproven)
- Multi-timeframe liquidity analysis (more parameters to overfit on only 3 QE cycles in 18 years of data)

### Architecture Approach

The target architecture inserts three new components as a processing layer between the existing indicator calculations and V2PositionManager. The filter-gate pattern is used throughout: each new component acts as a gate that can suppress a state transition proposed by the existing logic, running after the existing logic determines a transition but before it executes. This is simpler than the Hybrid engine's two-phase approach because V2 is being modified directly rather than wrapped. The engine (`mdm_v2_engine.py`) remains the sole orchestrator; all new components are instantiated in `__init__` and called in `run()`, consistent with the existing pattern. Config additions are additive with all new parameters defaulting to disabled.

**Major components:**
1. `LiquidityLoader` (NEW) — Load weekly CSV, forward-fill to daily with publication lag offset, expose `LiquidityRegime` enum; pre-loop merge before daily iteration
2. `SellAccelerator` (NEW) — Check momentum conditions (price ROC, DD clustering, volume-confirmed MA50 break) before allowing SELL transition; stateless checker
3. `BuyQualityScorer` (NEW) — Score FTD/breakout quality; suppress entries below threshold; stateless checker
4. `MDMV2Config` (MODIFIED) — Additive dataclass fields with defaults preserving current behavior; grouped by feature with clear comments
5. `V2PositionManager` (MODIFIED) — Accept `liquidity_regime`, `sell_accelerated`, `buy_quality` in `process_day()`; priority hierarchy: liquidity filter > sell acceleration > buy quality
6. `MDMV2Engine` (MODIFIED) — Orchestrate liquidity merge pre-loop, wire three gate signals into daily processing loop at step 5a-5c

### Critical Pitfalls

1. **Look-ahead bias in weekly-to-daily liquidity merge** — Apply publication lag offset (minimum 7 days, conservative 14 days) before `merge_asof`; verify with unit test that no daily row uses a liquidity value published after that row's date. This must be correct before any backtesting begins or all downstream results are invalid.

2. **State[i] vs state[i-1] contamination** — The project already experienced this exact bug (707% vs 93% equity difference). When the liquidity filter overrides a SELL signal, the override must take effect on the next day's equity calculation, not the current day. Enforce with regression test: V2 baseline equity must equal 190.8% +/- 0.1% with new code in place and all filters disabled.

3. **Overfitting SELL acceleration to the 2009-2021 bull run** — Any condition that makes it harder to exit mechanically increases holding time and total return in bull markets without providing real alpha. Must validate on 2008 and 2022 bear markets specifically: if acceleration conditions delay the first correct SELL by > 5 trading days vs V2 baseline, reject them.

4. **BUY selectivity becoming a curve-fit ensemble** — The hybrid engine already proved multi-condition indicator scoring does not work. Limit to 2-3 independent conditions (pairwise correlation < 0.5); use `check_degradation()` to verify < 10% out-of-sample degradation.

5. **Conflicting filter signals trapping capital in CASH** — All three gates can interact to simultaneously suppress exits and block re-entries. Establish and enforce priority hierarchy; track average CASH days vs baseline; require dedicated integration testing in Phase 4.

## Implications for Roadmap

Based on research, a 4-phase structure is recommended, matching the pitfall-to-phase mapping identified in PITFALLS.md.

### Phase 1: Global Liquidity Integration
**Rationale:** The QE floor filter is the highest-confidence feature (directly confirmed by Dr. K) and the foundational data pipeline for all subsequent features. Look-ahead bias and state[i] correctness must be locked in first — getting this wrong invalidates all downstream results.
**Delivers:** `LiquidityLoader` with publication lag offset, weekly-to-daily merge, `LiquidityRegime` enum, QE floor filter in `V2PositionManager`, backward-compatible config additions, unit test for publication lag, regression test verifying V2 baseline equity unchanged.
**Addresses:** Liquidity Data Loader + QE Floor Filter (P1 must-have features), NaN handling for pre-2007 dates.
**Avoids:** Look-ahead bias (Pitfall 1), state[i] contamination (Pitfall 2), data gap NaN crashes (Pitfall 6).

### Phase 2: SELL Acceleration Conditions
**Rationale:** Second confirmed Dr. K feature; depends on momentum indicators that can be built on top of the liquidity infrastructure from Phase 1. Bear-market validation must be a hard acceptance criterion, not an afterthought.
**Delivers:** `SellAccelerator` component, price ROC calculation, DD clustering metric, volume-confirmed MA50 break check, bear-market sub-period validation (2008 and 2022 max drawdown not worse than V2 baseline), A/B results for SELL acceleration in isolation.
**Uses:** Pure pandas `pct_change()` and `.diff()` — no new dependencies.
**Implements:** SellAccelerator gate in the filter-gate architecture pattern.
**Avoids:** Asymmetric overfit to bull markets (Pitfall 4).

### Phase 3: BUY Selectivity Improvement
**Rationale:** Most experimental feature; positioned after Phases 1-2 so the macro regime dimension is already handled by the liquidity filter. Must start from the simplest possible implementation (MA10 > MA50 boolean) and escalate complexity only if the simple version proves insufficient. The hybrid engine failure is the primary anti-pattern to avoid.
**Delivers:** `BuyQualityScorer` with MA alignment gate (MVP), optional FTD quality scoring, post-FTD confirmation window, correlation analysis between score components, walk-forward validation confirming < 10% out-of-sample degradation.
**Avoids:** Curve-fit ensemble problem (Pitfall 5); hybrid engine failure as documented baseline.

### Phase 4: Combined Integration and Validation
**Rationale:** Filter interactions only emerge when all three gates operate simultaneously. VN30-specific validation requires treating global liquidity as unproven for Vietnam and testing independently. Dashboard extensions should wait until all features are stable.
**Delivers:** Integration tests covering all 8 filter combinations (liquidity x sell_accel x buy_quality on/off), CASH duration metrics vs V2 baseline (must stay < 130%), walk-forward validation (train 2007-2018, test 2019-2026, degradation < 10%), VN30 vs NASDAQ comparison with liquidity filter, dashboard extensions (liquidity overlay, signal quality annotations), final A/B report.
**Avoids:** Whipsaw amplification from conflicting filters (Pitfall 7), overfitting to post-2008 QE regime on VN30 (Pitfall 3).

### Phase Ordering Rationale

- Phase 1 must be first because the liquidity data pipeline is a prerequisite for all other features, and correctness invariants (publication lag, state[i] regression) must be established before any performance comparisons mean anything.
- Phase 2 before Phase 3 because SELL quality is more directly confirmed by Dr. K's statements and easier to validate objectively (bear-market drawdown test is a clear pass/fail). BUY selectivity is more experimental and benefits from a stable SELL foundation.
- Phase 4 is a dedicated integration phase rather than simply "enable all features together" because PITFALLS.md identifies filter interaction effects that only appear in combined testing and require their own acceptance criteria (CASH duration, 8-combination coverage).
- Dashboard extensions are deferred to Phase 4 because they depend on all features being stable — building visualization on unstable feature implementations wastes iteration time.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (VN30 Adaptation):** Global liquidity filter applicability to Vietnam is unproven. SBV (State Bank of Vietnam) liquidity proxy data availability is unknown. If global liquidity hurts VN30 performance, a market-specific proxy or disabling the filter entirely for VN30 may be needed.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Liquidity Integration):** `pd.merge_asof` pattern is fully documented; data file is available; implementation approach is completely specified in ARCHITECTURE.md with working code samples.
- **Phase 2 (SELL Acceleration):** Momentum calculations (`pct_change`, `diff`) are standard pandas; no ambiguity in implementation approach.
- **Phase 3 (BUY Quality):** Start with MA alignment boolean; if that fails, the hybrid engine failure analysis already documents why multi-condition approaches do not work — the path forward is known.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies; all calculations fit existing patterns; verified against codebase |
| Features | MEDIUM | QE floor, SELL acceleration, BUY selectivity confirmed by direct Dr. K quotes; specific thresholds (ROC cutoff, acceleration magnitude) require backtesting to determine |
| Architecture | HIGH | Filter-gate pattern is clear; component boundaries specified; code samples provided in ARCHITECTURE.md; matches existing project structure exactly |
| Pitfalls | HIGH | Two of seven pitfalls are based on known project bugs (state[i] error documented, hybrid engine failure documented with numbers); remainder based on solid quantitative finance principles |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **QE floor threshold parameterization:** Research recommends `liquidity_roc_20w > 0` as starting point to avoid overfitting on 3 QE cycles. Correct threshold is a swept parameter in Phase 1, not a pre-determined constant.
- **VN30 liquidity applicability:** Global liquidity (Fed + ECB + BOJ) correlates with VN30 through capital flows, but the relationship is indirect. Do not enable the liquidity filter for VN30 until Phase 4 provides independent evidence. May require a Vietnam-specific proxy.
- **Sell acceleration magnitude:** Dr. K confirmed the concept but not specific thresholds. "-3% 5-day ROC" is a reasonable starting point, not a confirmed parameter. All acceleration thresholds are swept parameters in Phase 2.
- **Publication lag in global_liquidity.csv:** The pre-computed `global_liquidity` figure combines Fed, ECB, and BOJ data. ECB and BOJ have longer publication delays than the Fed's WALCL (Thursday release for prior Wednesday). Verify the lag assumptions embedded in the CSV before finalizing the offset in Phase 1.

## Sources

### Primary (HIGH confidence)
- Dr. K 2013 webinar transcripts — QE floor quote, sell acceleration quote, buy selectivity quote (confirmed model features)
- Project codebase: `strategies/mdm_v2/mdm_v2_engine.py`, `strategies/mdm_v2/performance.py`, `strategies/mdm_hybrid/indicator_filter.py` — known bugs and failure rates documented with numbers
- `data/global_liquidity.csv` — 987 weekly rows verified, 2007-2026, pre-computed columns confirmed
- pandas `merge_asof` documentation — standard weekly-to-daily alignment pattern

### Secondary (MEDIUM confidence)
- IBD research (FTD failure rates): DD on days 1-2 after FTD = 95% failure; DD on day 3 = 70% failure — informs post-FTD confirmation window priority
- Morpheus Trading timing model — DD clustering as sell acceleration proxy, distribution day proximity to FTD
- [Global Liquidity Index TradingView by QuantitativeAlpha](https://www.tradingview.com/script/lG8KoR4f-Global-Liquidity-Index/) — central bank balance sheet composition methodology
- [Quantified Strategies: FTD backtest](https://www.quantifiedstrategies.com/follow-through-day/) — FTD failure rate statistics and whipsaw patterns
- [Alvarez Quant: Reducing whipsaws with MA timing](https://alvarezquanttrading.com/blog/reducing-whipsaws-when-using-200-day-moving-average-for-market-timing/) — delay/confirmation techniques

### Tertiary (LOW confidence)
- VantMacro global liquidity and market regimes — general regime filter implementation patterns, not MDM-specific
- Market regime detection via HMM literature — evaluated and rejected in favor of simple threshold approach given data constraints

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
