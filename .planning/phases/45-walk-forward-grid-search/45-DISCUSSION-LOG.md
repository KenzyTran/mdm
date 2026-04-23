# Phase 45: Walk-Forward Grid Search - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 45-walk-forward-grid-search
**Areas discussed:** Search space sizing & strategy, Walk-forward methodology, Acceptance rule details, Top-N selection & Phase 46 handoff
**Language note:** First exchange in English, switched to Vietnamese mid-discussion at user request (per memory `user_language.md`).

---

## Search space sizing & strategy

### Q1.1 — Sweep strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Staged (DXY → EEM → SBV) | Phase 40 D-01 precedent. Stage 1 DXY (lock EEM/SBV at default) → Stage 2 EEM (lock DXY winner) → Stage 3 SBV (lock DXY+EEM). ~50-100 combos per stage. Conditional bias (Phase 41 D-07-style) acknowledged. | ✓ |
| Joint grid (single sweep) | Search 6 fields jointly with small cardinality (2-3 vals each = 64-729 combos). No staging bias. Bigger compute. Cleaner Phase 46 decomposition. | |
| Coarse-then-fine | Stage A: broad joint grid (2 vals) → Stage B: refine top-N with ±1 step. Catches non-monotonic sweet spots. More implementation complexity. | |

**User's choice:** Staged
**Notes:** Aligns with project's incremental-debug philosophy and Phase 40 precedent. Conditional bias accepted because DXY/EEM/SBV decompose naturally into 3 signal-source layers.

### Q1.2 — Which fields to search

| Option | Description | Selected |
|--------|-------------|----------|
| 6 policy fields only | Search 4 z-thresholds + 2 policy knobs. Lock 3 windows (dxy_window=20, eem_window=20, sbv_decay=90) at Phase 44 evidence-based defaults. | ✓ |
| All 9 active fields | Search 6 policy + 3 windows. Treat Phase 44 defaults as starting points only. | |

**User's choice:** 6 policy fields only
**Notes:** Quick-task 260421-lb4 already validated 20d/90d windows via correlation evidence. Re-searching them spends compute on the wrong question.

### Q1.3 — Cardinality per searched field

| Option | Description | Selected |
|--------|-------------|----------|
| 3 values per field | Default ± 1 step. Staged: ~170 combos total. ~30 min serial. | ✓ |
| 2 values per field | Binary tight/loose. Staged: ~48 combos. ~20 min. May miss sweet spots. | |
| 5 values per field | Wider exploration. Staged: ~1300 combos. 8+ hrs. Risk: more local optima exposed. | |

**User's choice:** 3 values per field
**Notes:** Practical compute budget without sacrificing resolution at the default ± 1 step granularity.

---

## Walk-forward methodology

### Q2.1 — Engine run pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Single full-period run + slice | Run engine 1× per combo on 2015-01-01..2024-12-31. Slice train (≤2018) + per-year eval (2019..2024) from signal log. Phase 41 D-08 precedent. ~10-15 min serial. | ✓ |
| Fresh engine per eval year | 1 train run + 6 eval runs per combo. Cleaner isolation but no production-mirror behavior, warmup repeated. ~1.5 hr. | |
| Rolling window (no historic) | Engine sees only 4 yrs per eval. Pure walk-forward but breaks state continuity, wastes warmup. | |

**User's choice:** Single full-period run + slice
**Notes:** Phase 41's mistake was tuning grid params on train-only metrics, NOT the run pattern itself. Phase 45 fixes by enforcing per-year acceptance INSIDE the sweep.

### Q2.2 — Per-year metric columns

| Option | Description | Selected |
|--------|-------------|----------|
| CAGR + Sharpe_rf3 + MaxDD | Matches ROADMAP SC-3 wording. Diagnostic columns for Phase 46 sort/rank. ~30 cols. | ✓ |
| CAGR only | Minimum for WF-02 gate. Phase 46 must re-run engine for Sharpe/MaxDD. | |
| Full whipsaw schema | CAGR + Sharpe + MaxDD + transitions + sell_count + ma50_share + buy/cash/sell pct. ~50+ cols. | |

**User's choice:** CAGR + Sharpe_rf3 + MaxDD
**Notes:** ROADMAP-aligned, diagnostics rich enough for Phase 46 ranking without re-runs.

---

## Acceptance rule details

### Q3.1 — Degradation formula

| Option | Description | Selected |
|--------|-------------|----------|
| Per-year ratio + median | `degradation_y = (cagr_train - cagr_eval_y) / abs(cagr_train)` for each y; `median_degradation = median([6 vals])`. Robust to 1-2 outliers. ROADMAP-aligned. | ✓ |
| Mean-based | Single ratio with `mean(eval_year_cagr)`. Sensitive to outlier years (e.g., 2020 covid). | |
| Sharpe degradation | Uses Sharpe_rf3 instead of CAGR. Stricter on vol shifts. Off-spec wording. | |

**User's choice:** Per-year ratio + median
**Notes:** Matches ROADMAP "median_degradation" wording verbatim. Phase 41 D-10 formula applied per-year then aggregated.

### Q3.2 — NaN/error handling

| Option | Description | Selected |
|--------|-------------|----------|
| Reject combo entirely | Any NaN year → mark `accepted=False`, reason=engine_error_year_y. Fail-loud. | |
| Skip year, median over rest | Drop NaN year, continue. Cap min coverage ≥ 5/6 years; ≥2 NaN reject. | ✓ |
| Treat NaN as max-degradation (1.0) | Conservative — NaN → 100% degradation, drives median up. Hides root cause. | |

**User's choice:** Skip year, median over rest
**Notes:** Robust to single-year flake while still failing combos with widespread errors. CSV records `eval_years_count` so reviewers can see when this happened.

### Q3.3 — Extra acceptance gates

| Option | Description | Selected |
|--------|-------------|----------|
| Degradation only | Pure ROADMAP. Combo can pass via low-but-positive train CAGR (e.g., train 2%, eval 1.5% — degradation 25% but absolute return weak). | |
| + Min eval CAGR > 0% | Sanity floor: median(eval_year_cagr) > 0. Combo must beat cash on median. | ✓ |
| + Min eval CAGR + max eval MaxDD > -30% | Adds drawdown ceiling per-year. Strict. May reject combos that meet HARD gate (-20% OOS). | |

**User's choice:** + Min eval CAGR > 0%
**Notes:** Soft sanity floor without overlapping with Phase 46 HARD gate (which is on full-period OOS, not per-year).

---

## Top-N selection & Phase 46 handoff

### Q4.1 — Top-N count + JSON shape

| Option | Description | Selected |
|--------|-------------|----------|
| 3 stage winners + 3 runners-up per stage | JSON has 3 top-level entries (stage1_dxy, stage2_eem, stage3_all_three), each with winner + runners. Phase 46 has full ammunition for 5-scenario decomposition. | ✓ |
| 1 grand best (Stage 3) + 5 runners-up | Single winner only. Phase 46 builds +DXY/+EEM/+SBV via threshold extremes. Smaller schema but Phase 46 may need to re-sweep for per-signal-only winners. | |
| 1 grand best, no runners-up | Minimum. Reviewer loses winner-vs-runners gap visibility. | |

**User's choice:** 3 stage winners + 3 runners-up per stage
**Notes:** Single-file JSON with maximum information density for Phase 46. ~2-3 KB total, reproducible from CSV.

### Q4.2 — Ranking metric

| Option | Description | Selected |
|--------|-------------|----------|
| Median eval CAGR | Primary spec metric. Tiebreak: median Sharpe_rf3 → parsimony (config closest to defaults). Phase 41 D-18 precedent. | ✓ |
| Median eval Sharpe_rf3 | Risk-adjusted. May pick low-CAGR low-vol combo, missing alpha. | |
| Composite: CAGR × (1 - degradation) | Penalizes instability directly. No project precedent, harder to explain. | |

**User's choice:** Median eval CAGR
**Notes:** ROADMAP-aligned (CAGR-centric). Parsimony tiebreak inherits Phase 41 D-18 — simpler params generalize better.

### Q4.3 — Phase 46 handoff format

| Option | Description | Selected |
|--------|-------------|----------|
| Stage winners only (Phase 46 builds scenarios) | Phase 45 outputs config tuples per stage. Phase 46 mutates VN30_PRESET via dataclasses.replace + threshold extremes for non-target signals. Separation of concerns. | ✓ |
| Phase 45 ships 5 ready-to-run scenario configs | JSON contains pre-baked baseline/+DXY/+EEM/+SBV/+all entries. Tight coupling between Phase 45 and Phase 46 scenario count. | |

**User's choice:** Stage winners only
**Notes:** Cleaner separation; Phase 46 owns scenario design, can change count without forcing Phase 45 changes.

---

## Claude's Discretion (areas user said "you decide" or deferred to planner)

- Exact CSV column ordering (suggested order documented in CONTEXT.md D-claude-1)
- Helper function decomposition inside walkforward_grid.py
- tqdm verbosity / description string format
- Whether to also write per-stage human-readable .txt siblings (Phase 40 D-21 precedent; ROADMAP only mandates JSON)
- Whether to add `analysis/inspect_grid_results.py` reviewer helper
- Whether to commit a snapshot of v10_grid_results.csv (full 39+ rows) to git or only the JSON winners
- Implementation route for compute_metrics per-year slicing (in-place kwarg add to validate_v9.py vs wrapper function)

## Deferred Ideas

- Joint full grid (rejected per D-01 — staged preferred)
- Coarse-then-fine grid (rejected per D-01 — implementation complexity)
- Search the 3 window fields (rejected per D-02 — quick-task evidence locks them)
- 5 values per field (rejected per D-03 — diminishing returns at default ± 1 step granularity)
- Whipsaw diagnostic per year (rejected per D-07 — Phase 46 VAL-04 owns full-period whipsaw)
- Composite ranking score (rejected per D-12 — no project precedent)
- Phase 46 scenario configs pre-baked into Phase 45 JSON (rejected per D-13 — separation of concerns)
- Multiprocessing per-combo (rejected per D-17 — 39 combos × ~15s = ~10 min serial)
- Per-stage .txt output siblings (planner discretion — bonus, not mandated)
- "Tune until OOS passes" loop (rejected — OOS holdout is sacred per `project_v9_whipsaw.md`)
- Adding per-signal enable flags to MDMV2Config (rejected per D-13 — Phase 44 territory, retroactive add anti-pattern)
- Joint 3-stage cross-validation (rejected — Stage 3 SBV alone has minimal sensitivity, linear staging sufficient)
- Reading reconciled baseline JSON for combo acceptance (rejected per D-09 — sanity floor uses median eval CAGR > 0%, baseline informs Phase 46 only)

