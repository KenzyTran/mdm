# Requirements: VN Macro Filter + Baseline Reconciliation (v10.0)

**Defined:** 2026-04-21
**Core Value:** Giảm MaxDD của v6.0 HybridEngine từ -28.6% xuống < -20% trên VN30 2015-2026 bằng VN-native macro filter (DXY/EEM 20d z-scores + SBV regime), sau khi reconcile baseline drift.

## v10.0 Requirements

### Baseline Reconciliation

- [x] **BASE-01**: Forensic audit — identify commit(s) causing baseline CAGR drift from v6.0 shipped (11.5%) to current measured (10.70%) and SELL count drift (124 → 105); produce `docs/audits/v10_baseline_drift.md` with commit hashes, diffs, and root cause
- [x] **BASE-02**: Reconciled baseline — fix forward (preferred) so current `HybridEngine + fail-safe` run matches v6.0 shipped CAGR within ±0.3pp, OR document drift with explicit justification if fix is unsafe/unnecessary
- [x] **BASE-03**: Regression test — engine run determinism verified (same inputs → CAGR ±0.1pp across 3 runs); test committed under `tests/test_baseline_determinism.py`

### Liquidity Data Pipeline

- [x] **LIQ-01**: Canonical `data/vn_liquidity_proxy.csv` (DXY, EEM, VNM, USD/VND, US10Y) regenerable via `analysis/build_liquidity_proxy.py`; script takes `--start` / `--end` CLI args, handles yfinance 401 retries
- [x] **LIQ-02**: Canonical `data/sbv_policy_events.csv` curated from public sources (Reuters, SBV press releases, Vietnam News); columns `date, rate_change_pct, new_refinance_rate_pct, direction`; extensible as new events occur
- [x] **LIQ-03**: Publication-lag handling documented in `docs/liquidity_proxy_spec.md` — DXY/EEM same-day (US close → VN next session), SBV events event-day+1 (intra-session announcements available next day)

### Macro Filter Module

- [x] **MACRO-01**: DXY 20d z-score indicator computed from liquidity proxy, merged to daily VN30 trading dates via `pd.merge_asof` (backward direction, publication-lag aware)
- [x] **MACRO-02**: EEM 20d z-score indicator, same pipeline as DXY
- [x] **MACRO-03**: SBV regime classifier — labels each trading day as easing/neutral/tightening based on most recent rate change event with 90-day decay (user can tune decay window via config)
- [x] **MACRO-04**: `MacroFilter` module integrated into HybridEngine state pipeline, feature-gated via `macro_filter_enabled` flag in `MDMV2Config`; v6.0 parity verified when flag is False (byte-exact signal log)
- [x] **MACRO-05**: Filter policy — DXY easing VETOes SELL, DXY tightening lowers the effective DD threshold, SBV tightening shrinks `stop_loss_max_multiplier` (exact thresholds `dxy_easing_z_threshold`, `dxy_tightening_z_threshold`, `eem_easing_z_threshold`, `eem_tightening_z_threshold`, `dxy_tightening_dd_threshold`, `sbv_tightening_stop_loss_max_multiplier` grid-searched in WF-01; engine binary model preserved per Phase 44 D-05/D-06, fractional sizing deferred to v11+)

### Walk-Forward Discipline

- [x] **WF-01**: Rolling-window grid search infrastructure — train window 2015-2018, annual walk-forward evaluations 2019/2020/2021/2022/2023/2024, held-out test 2025-2026; implementation in `analysis/walkforward_grid.py`
- [x] **WF-02**: Median degradation metric computed per parameter combo across rolling windows (train CAGR vs each walk-forward year CAGR); param combo accepted only if median degradation < 30%
- [x] **WF-03**: Grid search dashboard — `output/v10_grid_results.csv` with per-scenario median CAGR/Sharpe/MaxDD/degradation, sortable, reproducible from locked params JSON

### Validation

- [ ] **VAL-01**: A/B comparison on full 2015-2026 across 5 scenarios (baseline / +DXY / +EEM / +SBV-regime / +all) with canonical metrics (CAGR, Sharpe_rf3, MaxDD, total return, transitions, time-in-state, SELL count, MA50 breakdown share)
- [x] **VAL-02**: OOS test validation (2025-2026 held-out) with HARD gate — MaxDD < -20% AND CAGR ≥ reconciled baseline; script returns exit code reflecting gate verdict
- [x] **VAL-03**: Walk-forward stability gate — median degradation < 30% across all rolling windows for the selected scenario; failure blocks acceptance
- [x] **VAL-04**: v6.0 parity regression test — signal log byte-exact match when macro filter disabled; automated in CI-friendly test suite
- [ ] **VAL-05**: Production Candidate recommendation committed as literal string in `output/v10_validation_report.txt` (literal "v10 macro filter accepted as production" on pass, "v6.0 retained as production" on fail)

### Docs & Dashboard (conditional on VAL-02 pass)

- [ ] **DOC-01**: Update `docs/rules_mdm_hybrid.md` with macro filter rules and policy tables per CLAUDE.md code-docs sync rule (only if VAL-02 passes)
- [ ] **DOC-02**: Update `dashboard/data/` signal log and liquidity overlay with v10 output (only if VAL-02 passes); re-deploy dashboard
- [ ] **DOC-03**: v10.0 audit report appended to `.planning/MILESTONES.md` with result summary (pass or fail), key metrics, and lessons learned

## v2 Requirements (deferred to future milestones)

### Additional Alpha Sources
- **ALPHA-01**: Foreign flow integration (VNM ETF flow or HOSE foreign-buy daily net) — v11.0 candidate
- **ALPHA-02**: Statistical Jump Model (Shu 2024) for regime classification — research track
- **ALPHA-03**: Volatility targeting (Moreira-Muir 2017) — mixed evidence, defer unless v10.0 fails

### Automation
- **AUTO-01**: Auto-refresh liquidity proxy weekly (scheduled job)
- **AUTO-02**: Auto-append new SBV policy events from press release RSS

## Out of Scope

| Feature | Reason |
|---------|--------|
| Changes to `strategies/canslim/`, `strategies/portfolio/` | v7.0 scope — portfolio/stock selection is a different problem |
| Changes to `vn30_vsa/` | Independent strategy, not part of MDM reverse-engineering |
| Real-time / live signal generation | Core Value is research & backtesting only |
| Changes to fail-safe logic | Validated in Phase 23 (v6.0); v6.0 parity must hold |
| SBV OMO raw data scraping | Not publicly available as daily CSV; proxies (DXY/EEM/SBV-events) are the chosen path |
| ATR Buffer / Refined DD retuning | v9.0 REJECTED on walk-forward evidence — don't revisit without new evidence |
| New ML models (Jump Model, neural nets) | Out of scope — v10.0 focused on explicit rule-based macro filter |
| CASH policy rework (hold vs liquidate) | Flagged in PROJECT.md Context for future milestone — not v10.0 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BASE-01 | Phase 42 | Complete |
| BASE-02 | Phase 42 | Complete |
| BASE-03 | Phase 42 | Complete |
| LIQ-01 | Phase 43 | Complete |
| LIQ-02 | Phase 43 | Complete |
| LIQ-03 | Phase 43 | Complete |
| MACRO-01 | Phase 44 | Complete |
| MACRO-02 | Phase 44 | Complete |
| MACRO-03 | Phase 44 | Complete |
| MACRO-04 | Phase 44 | Complete |
| MACRO-05 | Phase 44 | Complete |
| WF-01 | Phase 45 | Complete |
| WF-02 | Phase 45 | Complete |
| WF-03 | Phase 45 | Complete |
| VAL-01 | Phase 46 | Pending |
| VAL-02 | Phase 46 | Complete |
| VAL-03 | Phase 46 | Complete |
| VAL-04 | Phase 46 | Complete |
| VAL-05 | Phase 46 | Pending |
| DOC-01 | Phase 47 | Pending |
| DOC-02 | Phase 47 | Pending |
| DOC-03 | Phase 47 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22 ✓
- Unmapped: 0

**Phase distribution:**
- Phase 42 (Baseline Reconciliation): 3 reqs (BASE-01..03)
- Phase 43 (Liquidity Data Pipeline): 3 reqs (LIQ-01..03)
- Phase 44 (Macro Filter Module): 5 reqs (MACRO-01..05)
- Phase 45 (Walk-Forward Grid Search): 3 reqs (WF-01..03)
- Phase 46 (A/B + OOS Validation): 5 reqs (VAL-01..05)
- Phase 47 (Docs & Dashboard): 3 reqs (DOC-01..03)

---
*Requirements defined: 2026-04-21*
*Last updated: 2026-04-21 after roadmap creation (all 22 requirements mapped to phases 42-47)*
