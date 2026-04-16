# Phase 41: A/B & Walk-Forward Validation - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate v9.0 candidates against v6.0 baseline on VN30 2015-2026 and decide the production candidate (ATR-only vs ATR+DD vs v6.0 retention). Produce:

1. A/B comparison report with 4 scenarios (baseline / +ATR / +DD / +both) on full 2015-2026
2. Walk-forward validation (Train 2015-2021 / Test 2022-2026) with CAGR degradation check
3. Whipsaw reduction diagnostic (SELL count + MA50-breakdown share vs baseline 124 / 84%)
4. Pass/fail verdict against VAL-03 success criterion (CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%))
5. Production candidate recommendation feeding Phase 42

Phase 42 owns `docs/rules_mdm_hybrid.md` updates, dashboard JSON emission, and the formal v9.0 audit report — Phase 41 produces only the validation evidence + recommendation.

**Explicitly out of scope (Phase 42):**
- Rule doc updates
- Dashboard JSON writing
- Audit report (`docs/audits/v9_0_report.md`)

</domain>

<decisions>
## Implementation Decisions

### Script structure & output layout
- **D-01:** Single unified script `analysis/validate_v9.py`. Mirrors [analysis/validate_combined_v6.py](analysis/validate_combined_v6.py) pattern: one file, `main()` entry, log-to-list pattern for report capture. Expected ~300-400 lines. Reason: v6 precedent proven, single entry point, no orchestration glue.
- **D-02:** ATR + DD winner params loaded at script startup from `output/v9_atr_best.json` and `output/v9_dd_best.json` (Phase 40 JSON outputs). If either file missing, raise `FileNotFoundError` with remediation message pointing to Phase 40 sweep commands. Single source of truth — Phase 40 rerun automatically propagates. Matches Phase 40 D-13 handoff pattern.
- **D-03:** Output artifacts (in addition to mandatory `output/v9_ab_comparison.txt`):
  - `output/v9_ab_comparison.txt` — human-readable unified report (VAL-01..VAL-04 all sections, whipsaw embedded, production candidate section)
  - `output/v9_ab_scenarios.csv` — one row per scenario (baseline/+ATR/+DD/+both) with full metrics (sharpe_rf3, cagr_pct, max_dd_pct, transitions, sell_count, ma50_breakdown_sell_share, buy_count, buy_pct, cash_pct, sell_pct, plus train/test split columns for walk-forward)
  - No per-scenario signal-log parquet in Phase 41 (Phase 42 dashboard will emit if needed)
- **D-04:** Whipsaw diagnostic (VAL-04) embedded as a section inside `v9_ab_comparison.txt`, not a separate file. Scenario rows in `v9_ab_scenarios.csv` carry the same whipsaw columns. Keeps audit trail single-file for reviewers.

### Scenario configuration
- **D-05:** Four scenarios built via `dataclasses.replace(VN30_PRESET, **overrides)` (Phase 40 D-04 pattern):
  1. **baseline**: `atr_buffer_enabled=False, refined_dd_enabled=False` — v6.0 shipped VN30_PRESET (HybridEngine + fail-safe). This is the pairwise reference.
  2. **+ATR only**: `atr_buffer_enabled=True` with params from `v9_atr_best.json` (k=1.0, N=20, m=2), `refined_dd_enabled=False`.
  3. **+DD only**: `atr_buffer_enabled=False`, `refined_dd_enabled=True` with params from `v9_dd_best.json` (large_drop=-0.007, small_drop=-0.003, small_vol_percentile=3). See D-07 for bias caveat.
  4. **+both**: `atr_buffer_enabled=True`, `refined_dd_enabled=True` with all locked params from both JSONs. This is the "canonical v9.0 full stack".
- **D-06:** Refined DD fixed params use Phase 39 defaults: `large_vol_rule='vol_ma20'`, `small_vol_lookback=50`. Out of grid per Phase 40 deferred items. No sensitivity sweep in Phase 41.
- **D-07:** **DD-only bias caveat** — Phase 40 Stage-2 DD sweep ran with ATR already locked ON, so Stage-2 winner params are optimized conditional on ATR=True. Using them for +DD only (ATR off) introduces conditional-optimization bias. Decision: use winner params as-is (the only DD config with sweep evidence + Stage-2 had 9-way tie) but write a dedicated "Methodological Note" caveat paragraph in the report. DD-only result is an upper-bound estimate of DD's isolated value.

### Walk-forward methodology
- **D-08:** Run engine once on full 2015-2026 for each scenario, then slice Test metrics from `date >= 2022-01-01`. Preserves indicator warmup continuity (MA50, MA200, ATR all need history). Matches [validate_combined_v6.py:134-137](analysis/validate_combined_v6.py#L134-L137) precedent.
- **D-09:** Train metrics: run engine on `df[df['date'] <= '2021-12-31']` slice (separate engine run). This matches v6 precedent — train run is independent of full-period run so Train metrics reflect an engine that truly never saw post-2021 data.
- **D-10:** CAGR degradation formula: `(cagr_train - cagr_test) / abs(cagr_train)`. Threshold 50% per VAL-02 (v6 used 10% but spec for v9.0 is 50%). Reported as percentage; if exceeds threshold, log explicit FAIL line but VAL-02 is NOT a blocker for VAL-03 verdict (see D-14).

### Whipsaw diagnostic granularity
- **D-11:** For each scenario, report:
  - **SELL count** (total SELL signals, target: drop from 124 baseline)
  - **MA50-breakdown share** of SELL signals (target: drop from 84% baseline)
  - **BUY count** + **buy_pct / cash_pct / sell_pct** (time-in-state from Phase 40 metrics schema)
  - **Transition count** (total state transitions — whipsaw proxy)
- **D-12:** Signal-source breakdown (FTD / 52w-breakout / MA50-breakdown share of BUYs; cash-deterioration / MA50-breakdown share of SELLs) reused from Phase 40 D-20 pattern: scan HybridEngine signal_log `action` column. If action-string parsing requires engine changes, fallback to just SELL count + MA50-breakdown share (VAL-04 floor). Plan will confirm label availability against current engine output.
- **D-13:** Delta-vs-baseline column: report `sell_count_delta` and `ma50_share_delta` per scenario for at-a-glance whipsaw reduction evidence.

### Pass/fail enforcement
- **D-14:** Exit code 0 always. VAL-03 pass/fail written as explicit text verdict in report; spec allows "failure-mode writeup explains the gap" so documented failure is acceptable. Does NOT block auto-advance — Phase 42 reviewer consumes report and decides.
- **D-15:** VAL-03 is the sole verdict gate. VAL-01/02/04 are reported evidence but not gates. A scenario that fails VAL-02 walk-forward but passes VAL-03 full-period still counts as "v9.0 candidate passes" with caveat noted.
- **D-16:** Failure-mode writeup (if VAL-03 fails for ALL v9 scenarios): include (1) exact metric gaps per scenario (e.g., "+ATR: CAGR 10.2% missed 11.5% by 1.3pp"), (2) the closest-to-criterion scenario, (3) hypothesized reasons (overfitting, 2022-2026 regime change, DD-only bias). Actionable for v10.0 planning.
- **D-17:** Buy & Hold VN30 row included in the main A/B table (matches v6 precedent). +205% Return / MaxDD -48.1% reference stays in the table so readers see v9 vs passive benchmark alongside v9 vs v6.

### Production candidate decision
- **D-18:** Decision rule: **OOS Test-period Sharpe_rf3 (2022-2026)** is the primary metric. Parsimony tiebreak: if OOS Sharpe within 5% relative delta, prefer simpler model (ATR-only over ATR+DD). Phase 40 showed DD has zero in-sample alpha over ATR-only — OOS must justify the extra complexity to earn the slot.
- **D-19:** Recommendation placement: **Final section in `v9_ab_comparison.txt`** titled "Production Candidate". Includes: (1) the pick, (2) decision-rule citation, (3) 2-3 sentence justification, (4) any caveats (e.g., walk-forward degradation flag). Phase 42 audit report can link/quote.
- **D-20:** Recommendation decisiveness: **Clear, committed recommendation** ("v9.0 production candidate: ATR-only" or "ATR+DD" or "v6.0 remains production"). Phase 42 can override with explicit justification, but Phase 41 default is committed.
- **D-21:** If ALL v9 scenarios fail VAL-03: recommend **"v6.0 HybridEngine + fail-safe remains production model"** — explicit v9.0 rejection. Phase 42 will roll dashboard/docs accordingly. Matches PROJECT.md "best model" discipline (memory: `project_best_model.md`).

### Claude's Discretion
- Exact formatting of report sections (table widths, separator styles — follow v6 precedent ≈70-char dashes)
- Whether to emit a single-chart equity overlay PNG (nice-to-have, not spec requirement; Phase 42 dashboard proper)
- Order of scenarios in table (suggest: baseline first, then +ATR, +DD, +both for monotone complexity)
- Per-scenario signal_log caching to avoid re-running engine for whipsaw diagnostic (optimization, not functional)
- Exact column order in `v9_ab_scenarios.csv` (follow Phase 40 sweep schema conventions)
- Fail-loud behavior if engine raises on any scenario (follow Phase 40 D-10 fail-loud + traceback-to-report pattern)

### Folded Todos
None — init report empty matches for Phase 41.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap + Requirements
- `.planning/ROADMAP.md` §Phase 41 (lines 775-783) — Goal, 4 success criteria (VAL-01..04), walk-forward threshold 50%, full-period 2015-2026
- `.planning/REQUIREMENTS.md` §A/B + Walk-Forward Validation (VAL-01..04) — Output path `output/v9_ab_comparison.txt`, scenario list, whipsaw metric target (124/84%)

### Phase 40 outputs (consumed as inputs)
- `output/v9_atr_best.json` — Locked ATR params {k=1.0, period=20, consecutive_days=2} + metrics
- `output/v9_dd_best.json` — Locked DD params {large_drop=-0.007, small_drop=-0.003, small_vol_percentile=3} + metrics (caveat: ATR-locked sweep)
- `output/v9_atr_best.txt`, `output/v9_dd_best.txt` — Human-readable siblings

### Upstream phase contexts
- `.planning/phases/40-grid-search-sweeps/40-CONTEXT.md` — Full Phase 40 decisions D-01..D-22 (config template, metrics schema, Sharpe_rf3 convention, whipsaw metric derivation)
- `.planning/phases/39-refined-distribution-day-module/39-CONTEXT.md` — Refined DD module shape + DD-04 backward-compat invariant
- `.planning/phases/38-atr-buffer-zone-module/38-CONTEXT.md` — ATR Buffer module shape + ATR-04 backward-compat invariant

### Precedent script (template for Phase 41)
- `analysis/validate_combined_v6.py` — 2-scenario A/B + walk-forward + dashboard check for Phase 27 (v6.0). Phase 41 extends to 4 scenarios + whipsaw diagnostic + production candidate section.
  - `compute_metrics()` (lines 39-68) — reuse pattern, extend with whipsaw columns per Phase 40 D-19
  - `run_engine()` (lines 71-79) — HybridConfig construction pattern
  - `main()` (lines 82+) — report structure (header / sections / summary / save)

### Engine entry points (consume read-only, no changes in Phase 41)
- `strategies/mdm_hybrid/mdm_hybrid_engine.py::HybridEngine.run()` — main engine invoked per scenario
- `strategies/mdm_hybrid/config.py::VN30_PRESET` (line 129) — base config template, override via `dataclasses.replace`
- `core/data_loader.py::DataLoader('vn30').load(start, end)` — data source, full 2015-2026
- `core/indicators.py::build_indicator_dataframe(df)` — precompute non-ATR/DD indicators

### Strategy rules doc (sync target per CLAUDE.md Code-Docs Sync Rule)
- `docs/rules_mdm_hybrid.md` — **NOT updated in Phase 41** (scope of Phase 42 DOC-01). Phase 41 is read-only validation; no rule logic changes.

### Memory anchors
- v6.0 baseline VN30 2015-2026: Return +238.8%, CAGR 11.5%, MaxDD -28.2%, 124 SELL (84% MA50-breakdown), B&H VN30 +205% (memory: `project_best_model.md`)
- v9.0 success criterion: CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%) (memory: `project_v9_whipsaw.md`)
- Equity formula rule: `state[i-1]` discipline to avoid look-ahead bias (memory: `feedback_equity_formula.md`)
- Best-model doc discipline: always record the best model clearly (memory: `feedback_best_model_docs.md`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analysis/validate_combined_v6.py::compute_metrics()` — template for equity + Sharpe + MaxDD + transitions computation. Phase 41 extends with whipsaw columns (sell_count, ma50_breakdown_sell_share, etc.) matching Phase 40 D-18/D-19 schema.
- `analysis/sweep_v9_atr.py::compute_metrics()` (if more recent than v6) — already has whipsaw columns; Phase 41 can import or copy.
- `dataclasses.replace(VN30_PRESET, **overrides)` — Phase 40 D-04 pattern for clean immutable config mutation.
- `HybridEngine(HybridConfig(v2_config=cfg, two_phase_enabled=True, filter_enabled=False))` — engine construction pattern from v6 + Phase 40.
- `DataLoader('vn30').load(start, end)` + `build_indicator_dataframe(df)` — data pipeline, load once, copy per scenario.
- Log-to-list + save-to-file report pattern from `validate_combined_v6.py:83-202` — `print()` + `lines.append()` inside a `log()` closure.

### Established Patterns
- **Unified validation script per phase**: Phase 27 precedent (`validate_combined_v6.py`). Phase 41 follows same structure.
- **Output to `output/` directory**: v6_combined_validation.txt, v9_atr_sweep.csv etc. Phase 41 writes `v9_ab_comparison.txt` + `v9_ab_scenarios.csv` alongside.
- **Hard-coded train/test boundaries + runtime asserts**: Phase 40 D-12. Phase 41 asserts `df['date'].max() >= '2026-01-01'` (full period required, not OOS-guard).
- **Fail-loud on broken scenarios**: Phase 40 D-10 traceback-to-report + top-row guard. Phase 41 inherits for defensive robustness.
- **Sharpe_rf3 formula**: `(ann_return − 0.03) / (daily_returns.std() × √252)`, Phase 40 D-19.
- **Signal-log action-string parsing** for whipsaw attribution: Phase 40 D-20 (scan `action` column for 'ma50_breakdown' substring). Phase 41 consumes the same labels — **Plan must verify labels haven't drifted since Phase 40**.

### Integration Points
- **Inputs:**
  - VN30 OHLCV data → `DataLoader('vn30').load('2015-01-01', '2026-12-31')`
  - `VN30_PRESET` template → `strategies/mdm_hybrid/config.py:129`
  - Phase 40 locked params → `output/v9_atr_best.json` + `output/v9_dd_best.json`
  - HybridEngine pipeline → Phase 38/39 modules wired behind feature flags
- **Outputs (Phase 41 creates):**
  - `output/v9_ab_comparison.txt` — human-readable unified report (VAL-01..04 sections + Production Candidate)
  - `output/v9_ab_scenarios.csv` — one row per scenario with full metrics (train + test + full-period columns)
- **Downstream consumers (Phase 42):**
  - `docs/audits/v9_0_report.md` will quote/link `v9_ab_comparison.txt`
  - `dashboard/data/mdm_v9.json` will be built from the production-candidate scenario's signal_log (Phase 42 re-runs engine if needed; Phase 41 does not emit signal_log parquet)
  - `docs/rules_mdm_hybrid.md` will reflect the production-candidate config

</code_context>

<specifics>
## Specific Ideas

- **"Follow the v6 validate_combined_v6.py skeleton precisely"** — user confirmed single-script layout. Phase 41 is essentially v6-validator-with-extra-scenarios + whipsaw + production recommendation. Don't redesign.
- **DD-only bias caveat is non-negotiable** — dedicated paragraph in report. Future readers must understand Stage-2 winner came from ATR-locked sweep.
- **Production candidate recommendation is committed, not data-only** — Phase 41 picks a winner (or picks v6.0 retention). Phase 42 can override but default is committed.
- **Parsimony tiebreak**: ATR-only wins over ATR+DD unless OOS Sharpe margin > 5% relative. Complexity must earn its slot.
- **B&H VN30 row stays in A/B table** — v6 precedent + reference benchmark for context.
- **No rule doc / dashboard changes in Phase 41** — all docs/dashboard work is Phase 42 DOC-01/DOC-02/DOC-03.

</specifics>

<deferred>
## Deferred Ideas

- **DD-only unbiased sweep** — Run DD grid with ATR=False to find truly-best DD-only params. Would resolve D-07 bias but doubles Phase 40 compute. Deferred to v10.0 if Phase 41 OOS evidence suggests DD-only has signal.
- **Joint ATR × DD grid search** — 1,944 combos. Deferred per Phase 40 out-of-scope list.
- **Per-scenario equity curve PNG chart** — Nice-to-have; Phase 42 dashboard is the proper home.
- **Dashboard JSON emission for v9 model** — Phase 42 DOC-02 scope. Phase 41 is read-only validation.
- **Rule documentation update** — Phase 42 DOC-01 scope.
- **v9.0 audit report** (`docs/audits/v9_0_report.md`) — Phase 42 DOC-03 scope.
- **Short-cover ATR buffer** — Phase 38 deferred; if Phase 41 whipsaw diagnostic shows short-cover whipsaw is material, open new phase in v10.0+.
- **SBV liquidity signal** for VN market regime — PROJECT.md future-requirements item, out of scope v9.0.
- **Sensitivity sweep on NASDAQ preset** — Phase 40/41 VN30-only; NASDAQ sensitivity is a separate research track.

### Reviewed Todos (not folded)
No pending todos match Phase 41 scope (init tool reports empty).

</deferred>

---

*Phase: 41-ab-walk-forward-validation*
*Context gathered: 2026-04-16*
