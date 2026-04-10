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

## Milestone: v7.0 — CANSLIM + MDM on VN100

**Shipped:** 2026-04-10
**Phases:** 28-34 + 999.1 (8 phases) | **Plans:** 34 plans | **Timeline:** 2 days (2026-04-08 → 2026-04-10)

### What Was Built
- Postgres + MySQL connectors; VN100 data audit (2936 stockcodes, 852 delisted, 16 EPS-sparse tickers)
- VN100 universe loader (100-ticker static, 3 sensitivity modes: current-vn100, liquidity-reconstructed, vn30-only)
- CANSLIM scorer (C/A/N/S/L/I/M + liquidity) validated vs diem_canslim baseline (OOS rho=0.365)
- Entry confirmation: Option A (52w breakout) + Option C (pocket pivot), next-day ATO fills
- Multi-stock portfolio engine: max 8 positions, 8% hard stop, MA50 trailing stop, T+2 settlement, 0.35% costs
- MDM capital allocation gate (HybridEngine + fail-safe from v6.0)
- In-sample sweep 2014-2018 (Phase 32) + OOS validation 2019-2025 (Phase 33)
- Performance report: profit_factor=3.74, real_CAGR, 5-benchmark comparison
- Phase 999.1: RS-ranked partial liquidation on MDM SELL → OOS CAGR=10.18%, Sharpe=0.813, MaxDD=-16.31%

### What Worked
- Pipeline architecture: precompute_static → build_canslim_raw → run_backtest made sweep/OOS trivial with no data leakage
- Separation of concerns: connectors → scorer → entry → engine → report (each independently testable)
- TDD-first on portfolio engine and 999.1 caught integration bugs early
- Phase 33 gap closure process fixed two cache contamination bugs (D-03, D-06) and one SQL schema bug
- 999.1 RS-ranked partial exit was a backlog item that significantly improved OOS: +3.95% CAGR, +0.365 Sharpe

### What Was Inefficient
- BT-08 target was set too high (Sharpe uplift >0.20 vs benchmark) without knowing MDM gate is a drag on CANSLIM alpha
- liquidity-reconstructed universe mode had SQL schema bug (closeindex vs closeprice) — discovered late in Phase 33
- Many SUMMARY.md one-liner fields left as placeholders ("One-liner:") — made milestone complete tool output noisy

### Patterns Established
- Cache key includes date range to prevent in-sample/OOS contamination in multi-run pipelines
- Sensitivity runs should always include a "strategy-only baseline" (CANSLIM-only, MDM-only) to decompose attribution
- RS-ranked partial exit on market timing signals: keep strong, shed weak (reusable pattern for other strategies)

### Key Lessons
1. **Stock selection is the alpha source, market timing is risk management:** CANSLIM alone Sharpe=1.047 >> MDM+CANSLIM Sharpe=0.448. MDM cuts MaxDD 74.7% (from -40% to -10%) but costs 6pt return. This reframes the MDM gate's role.
2. **Partial liquidation > full liquidation on SELL:** Keeping top 50% positions by RS when MDM signals SELL improved OOS from CAGR=6.23% to 10.18%. Market timing signals should trigger "risk reduction", not "full exit".
3. **Baselines matter for attribution:** BT-08 FAIL was initially diagnosed as CANSLIM scoring being the bottleneck. Adding the CANSLIM-only baseline proved the opposite — CANSLIM generates alpha, MDM gate suppresses it.
4. **state[i-1] discipline remains non-negotiable:** The 707% vs 93% look-ahead bias pattern was actively prevented via PositionBook design discipline throughout Phase 31.

### Cost Observations
- Model mix: ~80% sonnet, ~20% opus
- Sessions: ~5 sessions across 2 days (high velocity sprint)
- Notable: 34 plans in 2 days — fastest milestone by plan/day ratio

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
| v6.0 | 2 days | 5 | Fail-safe + gap filter + 6% threshold + banding |
| v7.0 | 2 days | 8 | CANSLIM+MDM multi-stock portfolio engine on VN100 |

### Top Lessons (Verified Across Milestones)

1. Each filter/feature needs its own A/B validation before combining — compound effects are unpredictable
2. Bear market sub-periods (2008, 2022) as mandatory regression gates prevent signal degradation
3. Human checkpoints for dashboard/UI changes catch issues that automated tests miss
