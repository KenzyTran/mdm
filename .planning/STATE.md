---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: VN Macro Filter + Baseline Reconciliation
status: defining
stopped_at: Milestone v10.0 started
last_updated: "2026-04-21T08:30:00.000Z"
last_activity: 2026-04-21
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** Discover MDM rules + apply on Vietnamese market — current focus: reduce v6.0 HybridEngine MaxDD from -28.6% to < -20% via VN-native macro filter (DXY/EEM/SBV regime), after reconciling baseline drift (shipped 11.5% → measured 10.70%).
**Current focus:** Defining requirements for v10.0

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-21 — Milestone v10.0 started

Progress: [░░░░░░░░░░] 0% (requirements definition in progress)

## Accumulated Context

### Baseline (HybridEngine + fail-safe, v6.0)

- Full period 2015-2026: Return +238.8%, CAGR 11.5%, MaxDD -28.2%
- B&H VN30: +205%, MaxDD -48.1%
- Walk-forward Train (2015-2021): CAGR 13.6%, MaxDD -15.3%
- Walk-forward Test (2022-2026): CAGR 8.1%, MaxDD -28.2%
- Signal breakdown: 60 BUY (43% FTD, 40% 52w-breakout, 17% MA50-breakout), 124 SELL (84% MA50-breakdown, 16% cash-deterioration)
- Exit breakdown: 59 BUY-exits (49% MA10-3day, 24% stop-loss, 14% DD-threshold), 133 SELL-exits (46% MA50-cover, 26% fail-safe, 25% FTD-cover)
- Time in state: BUY 30.5%, SELL 32.1%, CASH 37.4%

### Diagnostic driving v9.0

- **Whipsaw source #1:** 84% of SELL signals come from MA50 breakdown — target for ATR Buffer Zone (Phase 38)
- **Whipsaw source #2:** 22 BUY-exits from stop-loss + DD threshold — target for Refined DD definition (Phase 39)
- **Hypothesis:** Large-cap "kéo xả" (VIC, VCB) to liquidate retail F1 derivatives creates false breakdowns that ATR buffer will absorb

### v9.0 phase plan

- Phase 38: ATR Buffer Zone module (ATR-01..04) — indicator + trigger + config flag + regression
- Phase 39: Refined Distribution Day module (DD-01..04) — dual-threshold + config flag + regression
- Phase 40: Grid search (SWEEP-01..04) — ATR sweep (36 runs) → lock best → DD sweep (54 runs) → select max Sharpe with MaxDD ≤ -30%
- Phase 41: A/B + walk-forward validation (VAL-01..04) — 4 scenarios, Train 2015-2021 / Test 2022-2026, whipsaw diagnostic
- Phase 42: Documentation + dashboard (DOC-01..03) — rules_mdm_hybrid.md, v9 dashboard JSON, audit report

### Grid search budget

- ATR sweep: 36 combos (4 multiplier × 3 period × 3 consecutive_days) on train 2015-2021
- DD sweep: 54 combos (6 large_drop × 3 small_drop × 3 vol_percentile) on train 2015-2021, locked ATR
- Sequential (ATR first, lock best, then DD): 90 total runs
- Selection: max Sharpe with MaxDD ≤ -30% constraint, tie-break by CAGR

### Success criterion

CAGR ≥ 11.5% AND (Sharpe > baseline OR MaxDD < -25%) on full 2015-2026 period.

### Phase 39 Plan 01 Decisions (shipped 2026-04-16)

- Refined DD validation in `MDMV2Config.__post_init__` is gated behind `refined_dd_enabled=True` (Pitfall 5) so disabled configs accept arbitrary placeholder params — prevents Phase 40 sweep wiring from accidentally tripping on placeholder values
- Volume indicators (`vol_ma20`, `vol_top_pct`) use `min_periods=1` matching existing `add_*_column` convention — no NaN handling needed in Plan 02 DD counter loop
- `vol_top_pct` cast to bool dtype via `.astype(bool)` for cheap downstream branch logic and self-describing parquet fixtures
- Both VN30_PRESET and NASDAQ_PRESET ship `refined_dd_enabled=False` (D-07) preserving v6.0 byte-identical behavior — DD-04 backward-compat invariant intact

### Phase 39 Plan 02 Decisions (shipped 2026-04-16)

- `DistributionDayCounter.is_distribution_day_type1` branches on `refined_dd_enabled`: classic v6.0 rule (drop ≤ dd_price_drop_threshold AND volume_up) when disabled, dual-threshold rule (large_drop + vol_above_ma20) OR (small_drop + vol_top_pct) when enabled. Type 2 stalling untouched per D-01/D-04.
- `check_distribution_day` grew `vol_above_ma20` and `vol_top_pct` kwargs (default False) — existing positional callers including Plan 03 regression fixture and other downstream code work unchanged (Pitfall 4).
- HybridEngine precompute block gated on `refined_dd_enabled=True` (D-05): disabled path adds zero new columns, preserving DD-04 byte-identical invariant. Smoke test confirmed `'vol_ma20' not in result.columns` when disabled.
- Belt-and-braces expiry suppression for refined DD: column-level `df.loc[is_expiry_day, 'vol_top_pct'] = False` during precompute AND row-level `if not is_expiry:` guard in daily BUY-state block. Needed because `vol_above_ma20` is computed per-row from raw `volume` vs `vol_ma20` and cannot be masked at column level (Pitfall 1 extended).
- 11 unit tests green covering: 3 classic fallback, 2 refined large-drop, 3 refined small-drop, 1 Type 2 invariance, 2 check_distribution_day kwarg forwarding / backward-compat. Phase 38 regression still green — no side effects.

### Phase 39 Plan 03 Decisions (shipped 2026-04-16)

- Fixture COLS use engine column name `dd_count` (not `dd_count_20d` from decision-language). Engine has always exposed the column without the `_20d` suffix; renaming would have meant a chained refactor across `position_manager`, signal log code, and downstream notebooks — out of Plan 03 scope. Doc Section XVII clarifies the naming explicitly.
- Regression test uses boolean/integer exact equality (no float tolerance) for `is_dd`, `dd_type`, `dd_count`. Discrete columns demand byte-identical match to catch 5DD-threshold regressions (e.g., `dd_count` 4→5 is the difference between "stay BUY" and "trigger SELL").
- Code-docs sync deferred to terminal plan (03) rather than touching docs in every plan. `docs/rules_mdm_hybrid.md` Section XVII covers the completed feature surface atomically — avoids merge conflicts and keeps the doc update coherent with shipped behavior (CLAUDE.md Code-Docs Sync Rule honored at phase level).
- Phase 39 shipped: 2 backward-compat tests + 11 DD-logic tests + 14 indicator tests = 27 Phase 39 tests, all green. Phase 38 regression (2 tests) still green. Total 29 passed in 13.78s.

### Plan 03 Metrics

| Plan | Duration | Tasks | Files | Commits |
| :--- | :---: | :---: | :---: | :--- |
| 39-03 | ~14 min | 2 | 4 (3 created, 1 modified) | `e713624`, `ba1ac02` |

### Phase 40 Plan 02 Decisions (shipped 2026-04-16)

- `analysis/select_v9_best.py` implements D-15 selection (MaxDD>=-30 filter) + D-17 3-tier tiebreak (sharpe_rf3/cagr_pct/max_dd_pct desc) + D-16 strict abort (RuntimeError + exit 1, NO unconstrained fallback) + D-21 JSON schema `{params, metrics, selected_at, train_window='2015-01-01..2021-12-31'}` + D-22 dual TXT/JSON artifact. Single file, 155 lines, pure stdlib + pandas.
- `STAGE_CONFIG` dispatch table encapsulates all stage-specific paths/fields -- adding a future stage (e.g., joint ATR×DD in v10.0) is a one-line dict entry, not a code-path refactor.
- NaN `sharpe_rf3` rows dropped BEFORE MaxDD filter so error rows from plan 40-01's fail-loud protocol cannot pollute selection. RuntimeError message reports both non-error row count AND best achievable max_dd_pct for actionable diagnostics.
- Native Python type cast via `.item()` helper with AttributeError fallback — clean JSON (int stays int, float stays float, no numpy.int64 leakage).
- No TDD split: single-file utility, verified via 5 synthetic algorithm tests + end-to-end write_outputs test in-session. All passed first run.

### Phase 40 Plan 02 Metrics

| Plan | Duration | Tasks | Files | Commits |
| :--- | :---: | :---: | :---: | :--- |
| 40-02 | ~5 min | 1 | 1 (created) | `5085146` |

### Phase 40 Plan 01 Decisions (shipped 2026-04-16)

- `analysis/sweep_v9_atr.py` extends Phase 32 `compute_metrics` with Sharpe_rf3 (rf=3%: `(ann_return − 0.03) / (daily_returns.std() × √252)`) + whipsaw diagnostics (`sell_count`, `ma50_breakdown_sell_share`, `buy_count`, `buy_pct`, `cash_pct`, `sell_pct`) per D-18/D-19. Canonical 15-column CSV order (config → core → whipsaw → error) locked for Plan 40-02/03 downstream consumption.
- `ma50_breakdown_sell_share` metric treats both `SELL signal: MA50 breakdown` (classic v6.0 label) and `SELL signal: ATR buffer zone` (buffered label) as MA50-breakdown-path hits — both strings are emitted from the same `ma50_sell_enabled` branch in `position_manager.py:280-309`, so counting both correctly attributes ATR-buffer impact to the 84% whipsaw source targeted by v9.0.
- OOS-guard hard-coded: `TRAIN_START='2015-01-01'`, `TRAIN_END='2021-12-31'`, runtime assert `df['date'].max() <= pd.Timestamp(TRAIN_END)` (line 141). No CLI override — SWEEP-04 enforced by code path, not docs.
- Fail-loud-per-config (D-10): per-cell `try/except` captures traceback to `error` column + NaN metrics; top-5 NaN guard at end raises `SummaryError` so broken configs cannot silently become winners. Guard fires AFTER CSV is written so debugging material survives failure.
- First-run sweep: 36/36 configs completed cleanly in 128s (~3.6s/config). Top config `atr-k1.0-N20-m2` → Sharpe_rf3=0.76, CAGR=14.14%, MaxDD=-16.69% (beats v6.0 baseline CAGR 11.5%). All 36 configs pass MaxDD ≤ −30% constraint → Plan 40-02 selection guaranteed non-empty.

### Phase 40 Plan 01 Metrics

| Plan | Duration | Tasks | Files | Commits |
| :--- | :---: | :---: | :---: | :--- |
| 40-01 | ~4 min | 1 | 1 (created) | `19bd6ad` |

### Phase 40 Plan 03 Decisions (shipped 2026-04-16)

- `analysis/sweep_v9_dd.py` mirrors the plan-40-01 skeleton but adds (a) `load_locked_atr()` which reads `output/v9_atr_best.json` at startup and raises FileNotFoundError with the exact remediation command (`Run \`uv run python analysis/select_v9_best.py --stage atr\` first`) if the JSON is absent — enforces D-13 ordered execution without process-level orchestration, (b) extended 18-column CSV schema with locked ATR metadata (`atr_buffer_k/period/consecutive_days` duplicated per row) so Phase 41 readers get full config context from a single `pd.read_csv`, (c) `refined_dd_enabled=True` + `atr_buffer_enabled=True` per cell per D-06.
- Full Phase 40 pipeline executed in sequence (all exit 0): sweep_v9_atr (108s, 36 rows) → select --stage atr → sweep_v9_dd (107s, 54 rows) → select --stage dd. All six artifacts schema-verified.
- **Stage-1 winner:** `atr-k1.0-N20-m2` → Sharpe_rf3=**0.7596**, CAGR=14.14%, MaxDD=-16.69%, transitions=125.
- **Stage-2 winner:** `dd-L-0.007-S-0.003-P3` → Sharpe_rf3=**0.7160**, CAGR=13.55%, MaxDD=-16.69%, transitions=121. DD winner UNDERPERFORMS the ATR-only stage-1 winner by 5.8% Sharpe — top 9 DD configs tied at 0.7160 (pandas stable-sort picked lexicographic-first `dd-L-0.007-S-0.003-P3`). **Refined DD provides no alpha over ATR-only on VN30 train window 2015-2021.**
- **Implication for Phase 41:** A/B must test four scenarios (baseline / +ATR-only / +DD-only / +both); based on in-sample evidence the production v9.0 candidate is likely **ATR-only** not ATR+DD. If OOS 2022-2026 confirms ATR-only ≥ ATR+DD, Phase 42 docs ship ATR-only.
- D-02 self-contained stage scripts: `compute_metrics` copied verbatim from `sweep_v9_atr.py` rather than imported — stage-2 re-run never triggers stage-1 code path as an import side effect.
- Task 2 is a runtime-execution task whose products (`output/v9_{atr,dd}_{sweep,best}.*`) are gitignored by design; captured as a `--allow-empty` chore commit with full provenance in the message.

### Phase 40 Plan 03 Metrics

| Plan | Duration | Tasks | Files | Commits |
| :--- | :---: | :---: | :---: | :--- |
| 40-03 | ~7 min | 2 | 1 (created) + 6 gitignored runtime artifacts | `23807f8`, `abd900b` |

### Phase 41 Plan 01 Decisions (shipped 2026-04-21)

- `analysis/validate_v9.py` scaffold split into two atomic tasks: Task 1 ships skeleton (imports, 7 module constants, `load_locked_params`, `run_engine`); Task 2 appends `compute_metrics`, `build_scenario_configs`, and stub `main()`. Plan 41-02 inherits a running end-to-end pipeline rather than starting from import-error recovery — frees Plan 02 context budget for report-shaping + CSV writing + production candidate decision logic.
- `compute_metrics` extends Phase 40 `sweep_v9_atr.py::compute_metrics` with one new key: `total_return_pct`. Preserves Phase 40 schema for CSV-readers while adding A/B table readability (pairwise +ATR vs baseline total-return deltas).
- `load_locked_params` returns a **tuple of two dicts** (atr_params, dd_params) rather than a merged single dict. Rationale: `v9_dd_best.json` echoes `atr_buffer_*` params for provenance (since DD sweep ran under locked ATR=True), and the +ATR-only scenario MUST be driven from the atr_params dict — not from the dd_params provenance echo. Separate dicts prevent accidental single-source-of-truth collapse.
- Both `raise FileNotFoundError` messages carry the exact Phase 40 remediation command — downstream failures self-document the fix path.
- D-06 compliance: `refined_dd_large_vol_rule` and `refined_dd_small_vol_lookback` stay at VN30_PRESET defaults (`'vol_ma20'` and 50) in ALL 4 scenarios. Never overridden in any `dataclasses.replace` call. Acceptance-criteria grep confirmed `0` matches for both field names.
- Runtime data-coverage assert uses `>= pd.Timestamp('2025-12-01')` — lets the loader return any 2025 or 2026 cutoff without failing while catching truncated-data regressions before VAL-01 runs blind.
- Stub `main()` runs end-to-end with exit 0; `output/v9_ab_comparison.txt` produced with locked-params echo + scenario list; VN30 data confirmed at 2803 rows spanning 2015-01-05 -> 2026-03-31.

### Phase 41 Plan 01 Metrics

| Plan | Duration | Tasks | Files | Commits |
| :--- | :---: | :---: | :---: | :--- |
| 41-01 | ~8 min | 2 | 1 created (validate_v9.py) + 1 stub artifact (v9_ab_comparison.txt) | `7648e71`, `481d587` |

### Phase 41 Plan 02 Decisions (shipped 2026-04-21)

- **All 3 v9 scenarios FAIL VAL-03 on VN30 2015-2026 full period.** CAGR gaps +1.47pp (+DD), +2.57pp (+both), +2.72pp (+ATR) below the 11.5% gate. Sharpe_rf3 all below baseline 0.461 (0.369-0.417). MaxDD all worse than -25% (-29% to -33%). Failure-mode analysis triggers D-21 fallback: **Production Candidate = v6.0 HybridEngine + fail-safe retention.** Phase 42 docs/dashboard describe v6.0 as production; v9 modules stay as feature-flagged-off research code.
- **Walk-forward degradation +67% to +96%** on all v9 scenarios — in-sample Phase 40 winners do not generalize to 2022-2026. +ATR CAGR collapses 14.14% train → 0.51% test (+96.4% degradation). Baseline at +35.4% is the only scenario within the 50% threshold. Indicates Phase 40 grid search overfit 2015-2021 badly.
- **+DD is closest-to-criterion (CAGR 10.03%, 1.47pp below gate), not +ATR (CAGR 8.78%, 2.72pp below).** This INVERTS Phase 40 Stage-2 zero-alpha finding where DD provided no advantage over ATR-only on 2015-2021 train window. Full-period evidence: DD beats ATR-only by +1.25pp CAGR and +0.048 Sharpe. Hypothesis: 2022-2026 OOS regime is hostile to ATR buffer widening, which increased CASH% from 38.8% (baseline) to 46.5% (+ATR), starving the book of exposure during Vietnam's 2023-2024 recovery.
- **Whipsaw reduction confirmed but costly.** ATR Buffer cuts SELL count from 105 (baseline) to 59 (-43.8%) or 57 (+both, -45.7%), validating the whipsaw-reduction hypothesis. But whipsaw reduction shifted capital from BUY to CASH (not BUY to fewer-SELLs-in-BUY), costing ~2pp absolute CAGR. DD alone (+DD) makes essentially no whipsaw change (SELL 106 vs 105, +1.0%) — Refined DD rule as configured does not meaningfully gate the MA50-breakdown path.
- **MA50-breakdown share is 100% in all scenarios on current engine**, vs baseline v6.0 reference of 84%. Engine/signal-log labels may have drifted since v6.0 — or the Phase 38 ATR buffer zone emits the same "SELL signal: ATR buffer zone" label which Plan 41-01 compute_metrics counts as MA50-breakdown (baseline uses neither ATR buffer nor refined DD yet still shows 100%, so this is engine drift not mislabeling).
- **Baseline Sharpe_rf3 = 0.461 on current engine** vs project_best_model.md memory "v6.0 CAGR 11.5%, MaxDD -28.2%" (baseline CAGR here is 10.70%, 0.8pp gap). Current engine may have drifted from shipped v6.0 — v10.0 should reconcile before declaring a new production candidate. For Phase 41 verdict, current-engine baseline is the pairwise reference (D-15 fidelity).
- **One minor spec-compliance fix during execution:** Plan embedded text had "UPPER-BOUND estimate" (caps) but acceptance criterion grep and D-07 CONTEXT.md spec used lowercase. Adjusted to "upper-bound estimate" to match — Rule 1 bug fix. Committed in Task 2 (`92afd4f`).
- **Phase 42 inputs ready:** `output/v9_ab_comparison.txt` (committed recommendation literal) + `output/v9_ab_scenarios.csv` (17-column machine-readable metrics table including walk-forward train/test CAGR + degradation + whipsaw deltas). Phase 42 DOC-01/02/03 (rules doc, dashboard JSON, audit report) can consume these directly without re-running engine unless signal_log emission is needed.

### Phase 41 Plan 02 Metrics

| Plan | Duration | Tasks | Files | Commits |
| :--- | :---: | :---: | :---: | :--- |
| 41-02 | ~6 min | 2 | 1 modified (validate_v9.py) + 2 created (v9_ab_comparison.txt, v9_ab_scenarios.csv, both gitignored) | `e2eaafa`, `92afd4f` |

### Blockers/Concerns

None for Phase 42. Concerns feed into v10.0 planning: (1) walk-forward degradation indicates Phase 40 in-sample overfitting — v10.0 should widen train window or use walk-forward CV in the grid search itself, (2) current engine baseline (CAGR 10.70%, Sharpe 0.461) drifted from shipped v6.0 memory (CAGR 11.5%, MaxDD -28.2%) — reconcile before declaring any new production candidate.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260421-lb4 | Build VN30 liquidity proxy dataset and test correlation (GO verdict) | 2026-04-21 | 3a80ce1 | [260421-lb4-build-vn30-liquidity-proxy-dataset-and-t](./quick/260421-lb4-build-vn30-liquidity-proxy-dataset-and-t/) |

## Session Continuity

Last session: 2026-04-21T04:03:59.879Z
Stopped at: Completed 41-02-PLAN.md
Resume file: None
Next command: Phase 40 complete (all 3 plans shipped) — run `/gsd:verify-phase 40` to validate, then `/gsd:transition` to start Phase 41 (A/B + walk-forward validation) consuming the 4 best-artifact files
