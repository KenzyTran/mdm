# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v5.0 — Signal Quality & Macro Filter

**Shipped:** 2026-03-31
**Phases:** 4 | **Plans:** 8 | **Timeline:** 5 days (2026-03-27 → 2026-03-31)

### What Was Built
- QE Floor filter — suppress SELL during central bank liquidity expansion (LiquidityLoader + suppress_sell gate)
- SELL Acceleration Gate — require downside momentum (ROC < -4%, DD clustering ≥ 3, or volume-confirmed MA50 breakdown)
- BUY Selectivity — MA10/MA50 trend filter rejects weak FTDs + 3-day confirmation window with DD cancellation
- Combined validation — A/B comparison, walk-forward (no overfitting), 16 parametrized bear market tests
- Dashboard export extended with V2 filtered model + Global Liquidity overlay, deployed to S3

### What Worked
- TDD approach for each filter module (write failing tests first) caught integration bugs early
- Bear market sub-period validation (2008, 2022) proved filters don't degrade in worst-case scenarios
- Walk-forward split at 2020-01-01 validates across COVID regime change
- Wave-based parallel execution kept phase 22 efficient (2 tasks per plan)

### What Was Inefficient
- QE Floor designed for NASDAQ was applied to VN30 dashboard — discovered during human review that it degrades performance (93.7% vs 190.8%). Should have validated market applicability before dashboard integration
- Dashboard HTML was hardcoded for 3 models — had to manually update to add/remove tabs instead of dynamic rendering from metadata

### Patterns Established
- Each filter module follows pattern: standalone module → config flag → engine wiring → A/B validation script
- Bear market sub-period validation as mandatory gate for any signal-affecting change
- Walk-forward as standard overfitting check for all new filters

### Key Lessons
1. **Market-specific filters matter:** QE Floor is NASDAQ-specific (Fed liquidity). Blindly applying it to VN30 wastes a config slot and confuses dashboard users. Always validate filter applicability per market before enabling
2. **Default config IS the production config:** V2's defaults already had 3/4 filters ON. The "all filters" model only added QE Floor — meaning the real comparison was "V2 default" vs "V2 + QE Floor", not "baseline" vs "all filters"
3. **Human checkpoint caught the key issue:** Automated tests passed (drawdown within tolerance) but human review immediately spotted the 50% performance drop. Quantitative gates don't replace qualitative review

### Cost Observations
- Model mix: ~70% opus (execution), ~30% sonnet (verification)
- Sessions: ~4 sessions across 5 days
- Notable: Phase 22 execution with parallel worktree agents completed in ~10 minutes per plan

---

## Milestone: v7.0 -- CANSLIM + MDM on VN100

**Shipped:** 2026-04-10
**Phases:** 28-34 (7 phases) | **Plans:** ~18 plans | **Timeline:** ~3 days

### What Was Built
- Multi-stock CANSLIM+MDM portfolio engine: long-only, event-driven, max 5 slots (locked)
- VN100 universe loader with 3 modes (current-vn100, liquidity-reconstructed, vn30-only)
- CANSLIM scorer (C/A/N/S/L/I rules) with configurable thresholds
- Entry confirmation: Option A (pivot breakout) and Option C (pocket pivot)
- MDM capital allocation gate from HybridEngine + fail-safe
- In-sample sweep (Phase 32) + OOS validation (Phase 33)
- Comprehensive performance report with 5-way benchmark comparison

### What Worked
- Pipeline architecture: precompute_static -> build_canslim_raw -> run_backtest made sweep/OOS trivial
- Separation of concerns: connectors (data) -> scorer (signals) -> engine (execution) -> report (output)
- Phase 33 gap closure process caught and fixed SQL bugs (closeindex -> closeprice)

### What Was Inefficient
- CANSLIM scoring is the alpha source (Sharpe 1.047 standalone) but MDM gate reduces it (0.448 combined)
- BT-08 Sharpe uplift target FAILED (+0.064 vs target >0.20)
- liquidity-reconstructed universe mode has data quality issues, effectively unusable

### Key Lessons
1. Stock selection (CANSLIM) generates alpha; market timing (MDM) reduces drawdown but costs returns
2. MDM gate dramatically reduces MaxDD (-10% vs -40% B&H) -- its value is risk management, not return enhancement
3. Parameter sweep rank-1 is sensitive to universe mode -- current-vn100 significantly outperforms others
4. state[i-1] discipline remains critical for avoiding look-ahead bias

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Timeline | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 2 days | 6 | Foundation — established data loaders, v2 engine |
| v2.0 | 1 day | 4 | Rule discovery with indicators and decision trees |
| v3.0 | 1 day | 5 | Hybrid engine with Propose-Filter-Decide |
| v4.0 | 1 day | 3 | Short signals and risk management |
| v5.0 | 5 days | 4 | Signal quality filters with A/B validation |

### Top Lessons (Verified Across Milestones)

1. Each filter/feature needs its own A/B validation before combining — compound effects are unpredictable
2. Bear market sub-periods (2008, 2022) as mandatory regression gates prevent signal degradation
3. Human checkpoints for dashboard/UI changes catch issues that automated tests miss
