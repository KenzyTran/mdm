# Phase 41: A/B & Walk-Forward Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 41-ab-walk-forward-validation
**Areas discussed:** Script structure & outputs, DD-only scenario params, Pass/fail enforcement, Production candidate conclusion

---

## Gray-Area Selection

| Area | Description | Selected |
|------|-------------|----------|
| Script structure & outputs | Layout, config loading, artifact set, whipsaw location | ✓ |
| DD-only scenario params | Stage-2 winner vs defaults vs re-sweep | ✓ |
| Walk-forward execution style | Full-period-slice vs train/test-only | (Claude's discretion — v6 precedent) |
| Whipsaw diagnostic granularity | Minimum vs extended vs full | (Claude's discretion — v6 precedent) |
| Pass/fail enforcement | Exit code, VAL coverage, failure writeup | ✓ |
| Production candidate conclusion | Decision rule, location, decisiveness, fallback | ✓ |

---

## Area 1: Script Structure & Outputs

### Q1: How should Phase 41 validation code be laid out?

| Option | Description | Selected |
|--------|-------------|----------|
| Single unified script (Recommended) | analysis/validate_v9.py mirrors validate_combined_v6.py pattern | ✓ |
| Split by concern | ab_compare_v9.py + walk_forward_v9.py + whipsaw_diagnostic_v9.py | |
| Two scripts | validate_v9.py (A/B+WF) + diagnose_v9_whipsaw.py | |

**User's choice:** Single unified script
**Notes:** Matches v6 precedent; one entry point; no orchestration glue

### Q2: How should ATR/DD winning params be loaded for the 4 scenarios?

| Option | Description | Selected |
|--------|-------------|----------|
| Load from Phase 40 JSON at startup (Recommended) | Read output/v9_{atr,dd}_best.json at script start | ✓ |
| Hard-code params as constants | Embed values directly in script | |
| Hybrid: hard-code + assert match | Embed + assert equality with JSON | |

**User's choice:** Load from Phase 40 JSON at startup
**Notes:** Single source of truth; Phase 40 reruns propagate; fails loud if JSONs missing

### Q3: What output artifacts beyond v9_ab_comparison.txt should be produced?

| Option | Description | Selected |
|--------|-------------|----------|
| TXT + scenarios CSV (Recommended) | v9_ab_comparison.txt + v9_ab_scenarios.csv | ✓ |
| TXT only (spec minimum) | Just v9_ab_comparison.txt | |
| TXT + CSV + per-scenario signal_log parquets | Above + per-scenario parquets | |

**User's choice:** TXT + scenarios CSV
**Notes:** CSV feeds Phase 42 dashboard without re-parsing text; parquet deferred to Phase 42

### Q4: Where should the whipsaw diagnostic (VAL-04) live?

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded section in v9_ab_comparison.txt (Recommended) | Add 'Whipsaw Reduction' section to main report | ✓ |
| Separate v9_whipsaw_diagnostic.txt | Dedicated file | |
| Both TXT section + CSV column | Redundant but chart-friendly | |

**User's choice:** Embedded section in v9_ab_comparison.txt
**Notes:** Single-file audit trail; scenarios.csv also carries whipsaw columns per D-13

---

## Area 2: DD-only Scenario Params

### Q1: Which DD params should the +DD only scenario use?

| Option | Description | Selected |
|--------|-------------|----------|
| Stage-2 winner as-is (Recommended) | -0.7%/-0.3%/3% from v9_dd_best.json despite ATR-locked-sweep bias | ✓ |
| Phase 39 defaults | -0.7%/-0.4%/5%/50 shipped defaults | |
| Both: run twice + compare | Winner AND defaults as sub-scenarios | |

**User's choice:** Stage-2 winner as-is
**Notes:** Only DD config with sweep evidence; 9-way tie means alternatives are equivalent; document bias in report

### Q2: How should the bias disclosure appear in the final report?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated caveat paragraph (Recommended) | 'Methodological note' section | ✓ |
| One-line footnote | Terse footnote on scenario row | |
| No disclosure needed | Skip caveat | |

**User's choice:** Dedicated caveat paragraph
**Notes:** Readers must understand DD-only is upper-bound estimate

### Q3: Should the +both scenario use same DD params as +DD only?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — use v9_dd_best.json params (Recommended) | Consistent; Stage-2 IS canonical +both config | ✓ |
| No — use Phase 39 defaults for +both | Parallel only if Q1 picked defaults | |

**User's choice:** Yes — use v9_dd_best.json params
**Notes:** Stage-2 winner IS the intended full-stack v9.0 config

### Q4: How to handle refined_dd_large_vol_rule + small_vol_lookback?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep Phase 39 fixed values (Recommended) | vol_ma20 + 50-lookback | ✓ |
| Vary for sensitivity check | Mini-sweep on lookback | |

**User's choice:** Keep Phase 39 fixed values
**Notes:** Out of grid per Phase 40 deferred; no creep

---

## Area 3: Pass/Fail Enforcement

### Q1: What exit code behavior should the validation script have?

| Option | Description | Selected |
|--------|-------------|----------|
| Exit 0 always, report pass/fail in text (Recommended) | Documented-failure allowed per spec | ✓ |
| Exit 1 if VAL-03 fails (strict) | Block auto-advance pipeline | |
| Exit 1 only if ALL scenarios fail | Allow pass if one v9 variant meets criterion | |

**User's choice:** Exit 0 always, report pass/fail in text
**Notes:** Spec explicitly allows failure-mode writeup; reviewer decides next step

### Q2: Which VALs should contribute to the pass/fail determination?

| Option | Description | Selected |
|--------|-------------|----------|
| VAL-03 only (Recommended) | Only milestone success criterion gates | ✓ |
| VAL-02 + VAL-03 | Walk-forward degradation also gates | |
| All of VAL-01..04 | Including whipsaw target | |

**User's choice:** VAL-03 only
**Notes:** VAL-01/02/04 are evidence; only CAGR + Sharpe/MaxDD criterion gates

### Q3: If VAL-03 fails, what does the failure-mode writeup include?

| Option | Description | Selected |
|--------|-------------|----------|
| Diagnostic table + hypothesis (Recommended) | Metric gaps + closest scenario + hypothesized reasons | ✓ |
| Metric gap only | Terse one-line FAIL | |
| Full autopsy | Per-year + drawdown overlay + signal diff | |

**User's choice:** Diagnostic table + hypothesis
**Notes:** Actionable for v10.0 planning; not as heavy as Phase 42 audit

### Q4: Should the script compare v9 scenarios to B&H VN30?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include B&H row (Recommended) | Matches v6 precedent + passive benchmark | ✓ |
| No — only 4 scenarios + v6 baseline | Strict to spec | |

**User's choice:** Yes — include B&H row
**Notes:** B&H +205% / MaxDD -48.1% stays in table for context

---

## Area 4: Production Candidate Conclusion

### Q1: What decision rule picks the production candidate?

| Option | Description | Selected |
|--------|-------------|----------|
| OOS Test period Sharpe (Recommended) | 2022-2026 Sharpe_rf3 + parsimony tiebreak (5% margin) | ✓ |
| Full-period Sharpe | 2015-2026 Sharpe (mixes train + test) | |
| Multi-metric vote | Rank on Sharpe + CAGR + MaxDD | |

**User's choice:** OOS Test period Sharpe
**Notes:** DD must earn its slot — Phase 40 showed zero in-sample alpha

### Q2: Where should the production candidate recommendation live?

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded in v9_ab_comparison.txt (Recommended) | Final section with pick + rule + justification | ✓ |
| Separate docs/audits/v9_production_candidate.md | Dedicated markdown | |
| Defer to Phase 42 audit | Phase 41 data-only | |

**User's choice:** Embedded in v9_ab_comparison.txt
**Notes:** Single audit trail; Phase 42 can quote/link

### Q3: How decisive should the recommendation be?

| Option | Description | Selected |
|--------|-------------|----------|
| Clear recommendation + justification (Recommended) | Committed pick with 2-3 sentence justification | ✓ |
| Data-driven finalist only | State winner without 'ship this' language | |
| Ranked top-2 with trade-offs | Defer the call | |

**User's choice:** Clear recommendation + justification
**Notes:** Phase 42 can override but Phase 41 default is committed

### Q4: If all v9 scenarios fail VAL-03, what does the production candidate section say?

| Option | Description | Selected |
|--------|-------------|----------|
| Recommend v6.0 remains best model (Recommended) | Explicit v9.0 rejection | ✓ |
| Still name a v9 finalist | Closest-to-criterion as 'best of v9 family' | |
| Defer decision to Phase 42 review | Phase 41 reports failure only | |

**User's choice:** Recommend v6.0 remains best model
**Notes:** Matches best-model doc discipline; Phase 42 rolls docs/dashboard accordingly

---

## Claude's Discretion

Areas deferred to Claude during planning/implementation per Phase 41 CONTEXT.md:

- Walk-forward execution style (chose full-period-slice per v6 precedent / D-08/D-09)
- Whipsaw diagnostic granularity (chose extended: SELL/BUY counts + shares + time-in-state per D-11/D-12/D-13)
- Exact report formatting (table widths, separator styles)
- Signal-log action-string label verification (Plan must confirm labels match Phase 40 D-20 expectations)
- CSV column order (follow Phase 40 sweep conventions)
- Fail-loud behavior per scenario (follow Phase 40 D-10)

## Deferred Ideas

See CONTEXT.md `<deferred>` section. No new deferrals emerged during discussion beyond what's noted there.
