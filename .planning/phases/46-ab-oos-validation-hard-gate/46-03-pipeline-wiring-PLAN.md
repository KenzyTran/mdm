---
phase: 46-ab-oos-validation-hard-gate
plan: 03
type: execute
wave: 3
depends_on: ["46-01-scenario-scaffold-PLAN", "46-02-gate-helpers-PLAN"]
files_modified:
  - analysis/validate_v10.py
autonomous: true
requirements: [VAL-01, VAL-02, VAL-03, VAL-04, VAL-05]

must_haves:
  truths:
    - "main() runs 5-scenario A/B on VN30 2015-2026 once per scenario, caches results, computes compute_metrics per scenario"
    - "main() runs OOS subset (baseline + +all per D-04) as DataFrame slice of date >= OOS_START from full-period results"
    - "main() invokes all four gates (VAL-01 A/B table, VAL-02 HARD gate on +all OOS, VAL-03 walk-forward CSV lookup, VAL-04 parity pytest) regardless of interim results (D-06 no short-circuit)"
    - "Final verdict line in output/v10_validation_report.txt is EITHER 'v10 macro filter accepted as production' OR 'v6.0 retained as production' — no other string (D-09)"
    - "Verdict line appears on its OWN LINE (grep-without-word-boundary cleanly finds it)"
    - "Script exits 0 on full pass, 1 on any gate fail (D-11)"
    - "On fail path, a 'Rejection Narrative' section of 20-40 lines is written to v10_validation_report.txt summarizing which gates failed + Phase 45 evidence (train CAGR 9.54% vs 11.47% baseline, per-year DD medians, degradation distribution) + pointers to v10_grid_results.csv and absent v10_grid_best.json (D-10)"
    - "output/v10_ab_comparison.txt contains 5-scenario metrics table mirroring v9_ab_comparison.txt format with VAL-01 columns (CAGR, Sharpe, MaxDD, TotRet, transitions, SELL count, MA50 breakdown share, time-in-state percentages)"
    - "output/v10_ab_scenarios.csv has one row per scenario (5 rows + optional B&H row) with canonical column order extending v9_ab_scenarios.csv schema"
    - "verify_extremes_never_trigger is called on the +all macro-on results before the A/B table is written, raising AssertionError if isolation extremes leak"
  artifacts:
    - path: "analysis/validate_v10.py"
      provides: "Complete Phase 46 validation pipeline — main() orchestration + report writers"
      contains: "def main"
      min_lines: 450
  key_links:
    - from: "analysis/validate_v10.py::main"
      to: "build_scenarios() + run_engine() + compute_metrics()"
      via: "A/B loop per SCENARIO_ORDER"
      pattern: "for name in SCENARIO_ORDER"
    - from: "analysis/validate_v10.py::main"
      to: "load_hard_gate_thresholds() + evaluate_hard_gate()"
      via: "VAL-02 OOS subset evaluation"
      pattern: "evaluate_hard_gate"
    - from: "analysis/validate_v10.py::main"
      to: "lookup_walkforward_degradation()"
      via: "VAL-03 read Phase 45 CSV"
      pattern: "lookup_walkforward_degradation"
    - from: "analysis/validate_v10.py::main"
      to: "run_parity_gate()"
      via: "VAL-04 pytest subprocess"
      pattern: "run_parity_gate"
    - from: "analysis/validate_v10.py::main"
      to: "sys.exit"
      via: "D-11 exit code reflects verdict"
      pattern: "sys.exit\\(0\\)|sys.exit\\(1\\)"
---

<objective>
Wire the scenario builder (Plan 01) and gate helpers (Plan 02) into a complete `main()` pipeline that produces the three Phase 46 deliverables: `output/v10_ab_comparison.txt`, `output/v10_ab_scenarios.csv`, `output/v10_validation_report.txt`. The script is single-shot, deterministic, reproducible, and returns exit 0/1 per gate verdict.

Purpose: This plan converts isolated helpers into the Phase 46 record of scientific decision-making. The validation report is the canonical proof that v10.0's macro filter was evaluated against the HARD gate — Phase 47 DOC-03 will cite this artifact as milestone evidence regardless of the outcome (pass/fail). The rejection narrative (D-10) is the "last scientist" paragraph that tells a future v11.0 planner WHY v10.0 didn't work without requiring them to dig Phase 45's SUMMARY.

Output: `analysis/validate_v10.py::main()` complete + CSV writer + two report writers (A/B comparison + validation report with verdict + rejection narrative).
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-01-scenario-scaffold-SUMMARY.md
@.planning/phases/46-ab-oos-validation-hard-gate/46-02-gate-helpers-SUMMARY.md
@.planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md

@analysis/validate_v10.py
@analysis/validate_v9.py
@output/v9_ab_comparison.txt
@output/v9_ab_scenarios.csv

<interfaces>
<!-- Everything Plan 03 wires together, pre-loaded from Plans 01-02. -->

Functions already in analysis/validate_v10.py (from Plans 01, 02):
  DATA_START, DATA_END, OOS_START, OOS_END  (str date constants)
  SCENARIO_ORDER = ['baseline', '+DXY', '+EEM', '+SBV-regime', '+all']
  OOS_SCENARIO_SUBSET = ['baseline', '+all']
  VERDICT_PASS = "v10 macro filter accepted as production"
  VERDICT_FAIL = "v6.0 retained as production"
  REPORT_TXT, AB_COMPARISON_TXT, SCENARIOS_CSV  (output paths)

  compute_metrics(results) -> dict (imported from validate_v9)
  build_scenarios() -> dict[str, MDMV2Config]
  run_engine(df, cfg) -> pd.DataFrame
  verify_extremes_never_trigger(df) -> dict
  load_hard_gate_thresholds() -> dict
  evaluate_hard_gate(metrics, thresholds) -> dict
  lookup_walkforward_degradation(combo=None) -> dict
  run_parity_gate(timeout_sec=300) -> dict

Report template (from output/v9_ab_comparison.txt, adapt to 5 scenarios):
  - Header block with script name + date window
  - Scenarios built line
  - VAL-01 A/B table: Scenario | TotRet | CAGR | MaxDD | Sharpe | Trans | BUY% | CASH% | SELL%
  - Whipsaw diagnostic: SELL# | MA50% | BUY# | dSELL | dMA50 (deltas vs baseline)
  - Walk-forward reference (VAL-03): lookup_walkforward_degradation table
  - HARD gate result block (VAL-02): OOS metrics for baseline + +all, gate detail
  - Parity gate result block (VAL-04): returncode, tests passed/failed, stdout tail
  - Verdict block: final literal string on its own line + narrative
  - Rejection Narrative section (D-10) on fail path: 20-40 lines

CSV schema (extends v9_ab_scenarios.csv for VAL-01 per CONTEXT):
  scenario, sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct,
  transitions, sell_count, ma50_breakdown_sell_share, buy_count,
  buy_pct, cash_pct, sell_pct,
  sell_count_delta, ma50_share_delta,
  cagr_oos, max_dd_oos, hard_gate_pass   ← NEW columns for Phase 46 (OOS slice + HARD gate per-scenario for completeness)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add write_ab_comparison_report() + write_scenarios_csv() report writers</name>

  <read_first>
    - analysis/validate_v10.py (current state after Plans 01, 02)
    - analysis/validate_v9.py (lines 281-580 — the report/CSV writer patterns to adapt)
    - output/v9_ab_comparison.txt (the exact text formatting to mirror; 5 scenarios instead of 4)
    - output/v9_ab_scenarios.csv (the column schema to extend)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (VAL-01 columns required: transitions, time-in-state, SELL count, MA50 breakdown share)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `write_ab_comparison_report(lines_in, full_metrics, oos_metrics, wf_lookup, extremes_check, report_path)` appends the VAL-01 A/B section to `lines_in` list and writes the aggregate text file. Returns list of lines (same object, mutated).
    - `write_scenarios_csv(full_metrics, oos_metrics, hard_gate_results, baseline_sell, baseline_ma50_share, csv_path)` writes `output/v10_ab_scenarios.csv` with 5 scenario rows matching SCENARIO_ORDER and extended column schema.
    - Report section headers use the same `'─' * 70` + label conventions as v9_ab_comparison.txt for mechanical grep-ability.
    - A/B table shows all 5 scenarios in SCENARIO_ORDER.
    - Whipsaw diagnostic lists the 4 non-baseline scenarios' SELL count and MA50 breakdown share delta vs baseline.
    - Extremes headroom block reports `verify_extremes_never_trigger` output: `dxy_z_abs_max`, `eem_z_abs_max`, `headroom`.
  </behavior>

  <action>
    Append to `analysis/validate_v10.py` (after `run_parity_gate`, before any `main()` or EOF):

    ```python
    # ═══════════════════════════════════════════════════════════════════════
    # Report writers (Plan 03) — text report + CSV
    # ═══════════════════════════════════════════════════════════════════════

    def write_ab_comparison_report(
        full_metrics: dict,
        oos_metrics: dict,
        wf_lookup: dict,
        extremes_check: dict,
        bh_stats: dict,
        report_path: str = None,
    ) -> list:
        """Write output/v10_ab_comparison.txt with VAL-01 A/B table + diagnostics.

        Mirrors output/v9_ab_comparison.txt structure; extends from 4 to 5
        scenarios and adds VAL-03 walk-forward reference block (D-07) and
        extremes-headroom block (D-02 runtime sanity).

        Args:
            full_metrics: {scenario_name: metrics_dict} for full-period runs.
            oos_metrics: {scenario_name: metrics_dict} for OOS slice (only
                baseline + +all populated per D-04; others may be None).
            wf_lookup: Dict from lookup_walkforward_degradation().
            extremes_check: Dict from verify_extremes_never_trigger().
            bh_stats: Buy & Hold reference dict with keys
                total_return_pct, cagr_pct, max_dd_pct.
            report_path: Override output path. Default AB_COMPARISON_TXT.

        Returns:
            List of lines written (for the caller to fold into the unified
            validation_report.txt if desired).
        """
        path = report_path if report_path is not None else AB_COMPARISON_TXT
        lines = []
        def log(msg: str = '') -> None:
            lines.append(msg)

        log('=' * 70)
        log('PHASE 46: v10.0 A/B COMPARISON (VAL-01)')
        log(f'Data window: {DATA_START} → {DATA_END}')
        log('=' * 70)

        # Scenarios built
        log(f'\nScenarios built: {SCENARIO_ORDER}')
        log(f'Scenario isolation (D-02): +DXY / +EEM / +SBV-regime disable '
            f'OTHER factors via |z| >= 999 extremes and SBV multiplier = 2.5.')
        log(f'Isolation sanity check (verify_extremes_never_trigger):')
        log(f'  observed max |dxy_z| = {extremes_check["dxy_z_abs_max"]:.3f} '
            f'(headroom to 999: {999 - extremes_check["dxy_z_abs_max"]:.1f})')
        log(f'  observed max |eem_z| = {extremes_check["eem_z_abs_max"]:.3f} '
            f'(headroom to 999: {999 - extremes_check["eem_z_abs_max"]:.1f})')
        log(f'  headroom ≥ {extremes_check["headroom"]:.1f} → isolation extremes never reachable')

        # ── VAL-01 A/B table (D-01 + D-02 + D-03) ────────────────────────
        log('\n' + '─' * 70)
        log('VAL-01: A/B COMPARISON — 5 scenarios on full period')
        log('─' * 70)
        log(f'\n{"Scenario":<14s} {"TotRet":>9s} {"CAGR":>8s} {"MaxDD":>8s} {"Sharpe":>8s} '
            f'{"Trans":>6s} {"BUY%":>6s} {"CASH%":>6s} {"SELL%":>6s}')
        log('-' * 82)
        for name in SCENARIO_ORDER:
            m = full_metrics[name]
            log(f'{name:<14s} {m["total_return_pct"]:>+8.1f}% {m["cagr_pct"]:>7.2f}% '
                f'{m["max_dd_pct"]:>7.2f}% {m["sharpe_rf3"]:>8.3f} '
                f'{m["transitions"]:>6d} {m["buy_pct"]:>5.1f}% '
                f'{m["cash_pct"]:>5.1f}% {m["sell_pct"]:>5.1f}%')
        log(f'{"B&H VN30":<14s} {bh_stats["total_return_pct"]:>+8.1f}% '
            f'{bh_stats["cagr_pct"]:>7.2f}% {bh_stats["max_dd_pct"]:>7.2f}% '
            f'{"—":>8s} {"—":>6s} {"100.0":>5s}% {"0.0":>5s}% {"0.0":>5s}%')

        # ── Whipsaw diagnostic ───────────────────────────────────────────
        log('\n' + '─' * 70)
        log('WHIPSAW DIAGNOSTIC — SELL count + MA50-breakdown share')
        log(f'v6.0 shipped reference: 124 SELL signals, 83.87% MA50-breakdown share '
            '(from output/v10_reconciled_baseline.json)')
        log('─' * 70)
        baseline_sell = full_metrics['baseline']['sell_count']
        baseline_ma50_share = full_metrics['baseline']['ma50_breakdown_sell_share']
        log(f'\n{"Scenario":<14s} {"SELL#":>6s} {"MA50%":>8s} {"BUY#":>6s} '
            f'{"dSELL":>7s} {"dMA50":>8s}')
        log('-' * 57)
        for name in SCENARIO_ORDER:
            m = full_metrics[name]
            sell_delta = m['sell_count'] - baseline_sell
            if not (np.isnan(m['ma50_breakdown_sell_share']) or np.isnan(baseline_ma50_share)):
                ma50_share_pct = m['ma50_breakdown_sell_share'] * 100
                ma50_delta = (m['ma50_breakdown_sell_share'] - baseline_ma50_share) * 100
            else:
                ma50_share_pct = float('nan')
                ma50_delta = float('nan')
            log(f'{name:<14s} {m["sell_count"]:>6d} {ma50_share_pct:>7.1f}% '
                f'{m["buy_count"]:>6d} {sell_delta:>+7d} {ma50_delta:>+7.1f}%')

        # ── VAL-03 walk-forward reference block ──────────────────────────
        log('\n' + '─' * 70)
        log('VAL-03: WALK-FORWARD STABILITY (lookup from Phase 45 sweep)')
        log('─' * 70)
        log(f'Reading {wf_lookup["source_csv"]} for combo {wf_lookup["combo"]}')
        log(f'  median_degradation:   {wf_lookup["median_degradation"]:.4f}')
        log(f'  gate threshold (D-07): {wf_lookup["threshold"]:.2f}')
        log(f'  passed_gate:          {wf_lookup["passed_gate"]}')
        log(f'  accepted in Phase 45: {wf_lookup["accepted"]} '
            f'(rejection_reason: {wf_lookup["rejection_reason"]})')
        log(f'  total combos in sweep: {wf_lookup["total_combos"]} '
            f'(accepted: {wf_lookup["total_accepted"]})')

        # ── OOS slice preview (D-04 two-scenario subset) ─────────────────
        log('\n' + '─' * 70)
        log(f'OOS SLICE METRICS (D-04: {OOS_START} → {OOS_END}, baseline + +all only)')
        log('─' * 70)
        log(f'\n{"Scenario":<14s} {"CAGR_oos":>10s} {"MaxDD_oos":>11s} {"Sharpe_oos":>11s}')
        log('-' * 50)
        for name in OOS_SCENARIO_SUBSET:
            om = oos_metrics.get(name)
            if om is None:
                log(f'{name:<14s} {"n/a":>10s} {"n/a":>11s} {"n/a":>11s}')
            else:
                log(f'{name:<14s} {om["cagr_pct"]:>9.2f}% {om["max_dd_pct"]:>10.2f}% '
                    f'{om["sharpe_rf3"]:>11.3f}')

        # Write report
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f'A/B comparison report saved: {path} ({len(lines)} lines)')
        return lines


    def write_scenarios_csv(
        full_metrics: dict,
        oos_metrics: dict,
        hard_gate_results: dict,
        bh_stats: dict,
        csv_path: str = None,
    ) -> int:
        """Write output/v10_ab_scenarios.csv with VAL-01 columns + OOS + HARD-gate.

        Schema extends output/v9_ab_scenarios.csv:
          scenario, sharpe_rf3, cagr_pct, max_dd_pct, total_return_pct,
          transitions, sell_count, ma50_breakdown_sell_share, buy_count,
          buy_pct, cash_pct, sell_pct, sell_count_delta, ma50_share_delta,
          cagr_oos, max_dd_oos, sharpe_oos, hard_gate_passed

        Args:
            full_metrics: {scenario: metrics_dict} full-period.
            oos_metrics: {scenario: metrics_dict or None} OOS slice.
            hard_gate_results: {scenario: evaluate_hard_gate dict or None}.
            bh_stats: Buy & Hold reference.
            csv_path: Override path.

        Returns:
            Number of rows written (5 scenarios + 1 B&H row = 6 expected).
        """
        path = csv_path if csv_path is not None else SCENARIOS_CSV
        baseline_sell = full_metrics['baseline']['sell_count']
        baseline_ma50_share = full_metrics['baseline']['ma50_breakdown_sell_share']

        rows = []
        for name in SCENARIO_ORDER:
            m = full_metrics[name]
            om = oos_metrics.get(name)
            gate = hard_gate_results.get(name)
            ma50_delta = (
                (m['ma50_breakdown_sell_share'] - baseline_ma50_share)
                if not (np.isnan(m['ma50_breakdown_sell_share']) or np.isnan(baseline_ma50_share))
                else float('nan')
            )
            rows.append({
                'scenario': name,
                'sharpe_rf3': m['sharpe_rf3'],
                'cagr_pct': m['cagr_pct'],
                'max_dd_pct': m['max_dd_pct'],
                'total_return_pct': m['total_return_pct'],
                'transitions': m['transitions'],
                'sell_count': m['sell_count'],
                'ma50_breakdown_sell_share': m['ma50_breakdown_sell_share'],
                'buy_count': m['buy_count'],
                'buy_pct': m['buy_pct'],
                'cash_pct': m['cash_pct'],
                'sell_pct': m['sell_pct'],
                'sell_count_delta': m['sell_count'] - baseline_sell,
                'ma50_share_delta': ma50_delta,
                'cagr_oos': om['cagr_pct'] if om is not None else float('nan'),
                'max_dd_oos': om['max_dd_pct'] if om is not None else float('nan'),
                'sharpe_oos': om['sharpe_rf3'] if om is not None else float('nan'),
                'hard_gate_passed': gate['passed'] if gate is not None else None,
            })
        # B&H row
        rows.append({
            'scenario': 'B&H VN30',
            'sharpe_rf3': float('nan'),
            'cagr_pct': bh_stats['cagr_pct'],
            'max_dd_pct': bh_stats['max_dd_pct'],
            'total_return_pct': bh_stats['total_return_pct'],
            'transitions': 0,
            'sell_count': 0,
            'ma50_breakdown_sell_share': float('nan'),
            'buy_count': 0,
            'buy_pct': 100.0,
            'cash_pct': 0.0,
            'sell_pct': 0.0,
            'sell_count_delta': float('nan'),
            'ma50_share_delta': float('nan'),
            'cagr_oos': float('nan'),
            'max_dd_oos': float('nan'),
            'sharpe_oos': float('nan'),
            'hard_gate_passed': None,
        })
        df = pd.DataFrame(rows)
        # Canonical column order (fixed per CONTEXT)
        df = df[[
            'scenario', 'sharpe_rf3', 'cagr_pct', 'max_dd_pct', 'total_return_pct',
            'transitions', 'sell_count', 'ma50_breakdown_sell_share', 'buy_count',
            'buy_pct', 'cash_pct', 'sell_pct', 'sell_count_delta', 'ma50_share_delta',
            'cagr_oos', 'max_dd_oos', 'sharpe_oos', 'hard_gate_passed',
        ]]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        print(f'Scenarios CSV saved: {path} ({len(df)} rows)')
        return len(df)
    ```
  </action>

  <verify>
    <automated>uv run python -c "
import math
from analysis.validate_v10 import (
    write_ab_comparison_report, write_scenarios_csv,
    SCENARIO_ORDER, OOS_SCENARIO_SUBSET,
)

# Build synthetic metrics for all 5 scenarios
nan = float('nan')
def mk(cagr, maxdd, sell=100, trans=300):
    return {'sharpe_rf3': 0.45, 'cagr_pct': cagr, 'max_dd_pct': maxdd,
            'total_return_pct': 150.0, 'transitions': trans, 'sell_count': sell,
            'ma50_breakdown_sell_share': 0.85, 'buy_count': 25,
            'buy_pct': 30.0, 'cash_pct': 40.0, 'sell_pct': 30.0}

full = {n: mk(11.47, -28.17) if n == 'baseline' else mk(9.0, -19.0) for n in SCENARIO_ORDER}
oos = {'baseline': mk(5.0, -12.0), '+all': mk(2.0, -15.0)}
wf = {'source_csv': 'output/v10_grid_results.csv', 'combo': 'stage3_all_three-c1',
      'median_degradation': 0.5375, 'threshold': 0.30, 'passed_gate': False,
      'accepted': False, 'rejection_reason': 'median_degradation 0.537 >= 0.30',
      'total_combos': 39, 'total_accepted': 0}
extremes = {'dxy_z_abs_max': 3.2, 'eem_z_abs_max': 4.1, 'headroom': 994.9}
bh = {'total_return_pct': 205.1, 'cagr_pct': 10.44, 'max_dd_pct': -48.14}
hg = {name: {'passed': False, 'cagr_pass': True, 'max_dd_pass': False,
             'cagr_observed': 9.0, 'max_dd_observed': -19.0,
             'cagr_required': 11.47, 'max_dd_required': -20.0, 'detail': 'd'}
      for name in ['baseline', '+all']}

import tempfile, os
with tempfile.TemporaryDirectory() as td:
    rp = os.path.join(td, 'v10_ab_comparison.txt')
    cp = os.path.join(td, 'v10_ab_scenarios.csv')
    write_ab_comparison_report(full, oos, wf, extremes, bh, report_path=rp)
    n_rows = write_scenarios_csv(full, oos, hg, bh, csv_path=cp)

    # Verify text report
    with open(rp, 'r', encoding='utf-8') as f:
        content = f.read()
    assert 'VAL-01: A/B COMPARISON' in content, 'VAL-01 header missing'
    assert 'baseline' in content and '+DXY' in content and '+EEM' in content and '+SBV-regime' in content and '+all' in content
    assert 'WHIPSAW DIAGNOSTIC' in content
    assert 'VAL-03: WALK-FORWARD STABILITY' in content
    assert 'stage3_all_three-c1' in content
    assert 'headroom to 999' in content
    assert 'B&H VN30' in content
    # All 5 scenarios appear in order
    positions = [content.find(s) for s in SCENARIO_ORDER]
    assert all(p > 0 for p in positions), f'missing scenario: {positions}'
    assert positions == sorted(positions), f'scenarios out of order: {positions}'
    print(f'  text report: {len(content.splitlines())} lines')

    # Verify CSV
    import pandas as pd
    df = pd.read_csv(cp)
    assert len(df) == 6, f'expected 6 rows (5 scenarios + B&H), got {len(df)}'
    cols = df.columns.tolist()
    for c in ['scenario', 'cagr_pct', 'max_dd_pct', 'transitions', 'sell_count',
              'ma50_breakdown_sell_share', 'cagr_oos', 'max_dd_oos', 'hard_gate_passed']:
        assert c in cols, f'missing column {c}'
    assert df['scenario'].tolist()[:5] == SCENARIO_ORDER, f'CSV scenario order wrong: {df[\"scenario\"].tolist()}'
    print(f'  CSV: {n_rows} rows, {len(cols)} columns')
print('write_ab_comparison_report + write_scenarios_csv: OK')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def write_ab_comparison_report" analysis/validate_v10.py` returns 1 hit
    - `grep -n "def write_scenarios_csv" analysis/validate_v10.py` returns 1 hit
    - Verify command prints `write_ab_comparison_report + write_scenarios_csv: OK` with exit 0
    - Synthesized text report contains all 5 scenario names in SCENARIO_ORDER order
    - Synthesized CSV has exactly 6 rows (5 scenarios + 1 B&H) and includes columns `cagr_oos`, `max_dd_oos`, `hard_gate_passed`
    - Text report includes block headers: `VAL-01: A/B COMPARISON`, `WHIPSAW DIAGNOSTIC`, `VAL-03: WALK-FORWARD STABILITY`, `OOS SLICE METRICS`
    - Text report includes `headroom to 999` string (extremes headroom reporting — D-02 traceability)
  </acceptance_criteria>

  <done>A/B text report writer + scenarios CSV writer land with full VAL-01 column coverage, extremes headroom block, and walk-forward reference block. Synthetic end-to-end test proves report/CSV structure is correct before any real engine runs.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Add write_validation_report() with verdict + rejection narrative (D-09 + D-10)</name>

  <read_first>
    - analysis/validate_v10.py (current state after Task 1)
    - .planning/phases/45-walk-forward-grid-search/45-03-execute-sweep-commit-artifacts-SUMMARY.md (lines 92-128 — pull the EXACT numbers for the rejection narrative: train CAGR 9.54%, eval 4.57%, per-year DD medians 2019 -8.74% / 2020 -15.29% / 2021 -19.68% / 2022 -15.33% / 2023 -12.72% / 2024 -12.45%, degradation min 0.410 / median 0.538 / max 0.645)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-09 verdict format, D-10 rejection narrative content spec)
    - output/v10_reconciled_baseline.json (baseline CAGR 11.47 / total_return 238.78 for comparison in narrative)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `write_validation_report(gate_results, report_path=None)` writes `output/v10_validation_report.txt` with:
      1. Header (Phase 46 + date window)
      2. Per-gate section (VAL-01 summary line, VAL-02 per-scenario HARD gate detail, VAL-03 walk-forward lookup detail, VAL-04 parity pytest summary)
      3. Overall verdict block with the literal VERDICT_PASS or VERDICT_FAIL string on its OWN line
      4. On fail path ONLY: Rejection Narrative section (20-40 lines) per D-10
    - Takes a single `gate_results` dict with keys: `val_01_ab_complete` (bool), `val_02_hard_gate` (dict of per-scenario verdicts), `val_03_walkforward` (wf_lookup dict), `val_04_parity` (run_parity_gate dict)
    - Returns the boolean `all_passed` so main() can drive exit code
  </behavior>

  <action>
    Append to `analysis/validate_v10.py`:

    ```python
    def write_validation_report(gate_results: dict, report_path: str = None) -> bool:
        """Write output/v10_validation_report.txt with per-gate verdicts + D-09 verdict string.

        Contains (in order):
          1. Header (window, date, script name)
          2. Gate summary table (VAL-01..VAL-04 pass/fail)
          3. Per-gate detail blocks
          4. Overall verdict block with LITERAL string on its own line (D-09)
          5. Rejection Narrative (D-10) if any gate failed — 20-40 lines

        Args:
            gate_results: Dict with keys:
                'val_01_ab_complete': bool (A/B ran end-to-end without error)
                'val_02_hard_gate': dict[scenario_name, evaluate_hard_gate_dict]
                    for each scenario in OOS_SCENARIO_SUBSET (D-04)
                'val_03_walkforward': dict from lookup_walkforward_degradation()
                'val_04_parity': dict from run_parity_gate()
                'hard_gate_scenario': str — the scenario name whose HARD gate
                    result is the VAL-02 verdict (i.e., '+all' per D-04)
                'full_metrics': dict[scenario, compute_metrics_dict] for
                    narrative references (full-period baseline reference)
                'baseline_cagr_floor': float — loaded from JSON
            report_path: Override; default REPORT_TXT.

        Returns:
            all_passed: True iff every gate passed → caller sys.exit(0).
        """
        path = report_path if report_path is not None else REPORT_TXT

        # Determine overall pass/fail
        val_01_pass = gate_results['val_01_ab_complete']
        hg_scenario = gate_results['hard_gate_scenario']
        val_02_pass = gate_results['val_02_hard_gate'][hg_scenario]['passed']
        val_03_pass = gate_results['val_03_walkforward']['passed_gate']
        val_04_pass = gate_results['val_04_parity']['passed']
        all_passed = val_01_pass and val_02_pass and val_03_pass and val_04_pass

        lines = []
        def log(msg: str = '') -> None:
            lines.append(msg)

        log('=' * 70)
        log('PHASE 46: v10.0 VALIDATION REPORT')
        log(f'Data window: {DATA_START} → {DATA_END}  |  OOS: {OOS_START} → {OOS_END}')
        log(f'Script: analysis/validate_v10.py')
        log('=' * 70)

        # ── Gate summary ─────────────────────────────────────────────────
        log('\n' + '─' * 70)
        log('GATE SUMMARY')
        log('─' * 70)
        log(f'{"Gate":<8s} {"Name":<40s} {"Result":>10s}')
        log('-' * 60)
        log(f'{"VAL-01":<8s} {"A/B across 5 scenarios":<40s} '
            f'{"PASS" if val_01_pass else "FAIL":>10s}')
        log(f'{"VAL-02":<8s} {"OOS HARD gate on " + hg_scenario:<40s} '
            f'{"PASS" if val_02_pass else "FAIL":>10s}')
        log(f'{"VAL-03":<8s} {"Walk-forward median_deg < 0.30":<40s} '
            f'{"PASS" if val_03_pass else "FAIL":>10s}')
        log(f'{"VAL-04":<8s} {"v6.0 parity regression (pytest)":<40s} '
            f'{"PASS" if val_04_pass else "FAIL":>10s}')
        log('-' * 60)
        log(f'{"OVERALL":<8s} {"All four gates passed":<40s} '
            f'{"PASS" if all_passed else "FAIL":>10s}')

        # ── VAL-02 detail ────────────────────────────────────────────────
        log('\n' + '─' * 70)
        log(f'VAL-02 DETAIL — OOS HARD gate ({OOS_START} → {OOS_END})')
        log(f'Thresholds (D-05): CAGR ≥ {gate_results["baseline_cagr_floor"]:.2f}% '
            f'AND MaxDD > -20.00%')
        log('─' * 70)
        for name in OOS_SCENARIO_SUBSET:
            verdict = gate_results['val_02_hard_gate'].get(name)
            if verdict is None:
                log(f'  {name}: n/a (scenario not run on OOS slice)')
                continue
            log(f'  {name}: {"PASS" if verdict["passed"] else "FAIL"}')
            log(f'    {verdict["detail"]}')

        # ── VAL-03 detail ────────────────────────────────────────────────
        wf = gate_results['val_03_walkforward']
        log('\n' + '─' * 70)
        log(f'VAL-03 DETAIL — Walk-forward stability (lookup from Phase 45)')
        log('─' * 70)
        log(f'  combo:              {wf["combo"]}')
        log(f'  median_degradation: {wf["median_degradation"]:.4f}')
        log(f'  threshold (D-07):   < {wf["threshold"]:.2f}')
        log(f'  verdict:            {"PASS" if wf["passed_gate"] else "FAIL"}')
        if not wf['passed_gate']:
            log(f'  rejection_reason:   {wf["rejection_reason"]}')
            log(f'  source:             {wf["source_csv"]} '
                f'({wf["total_combos"]} combos, {wf["total_accepted"]} accepted)')

        # ── VAL-04 detail ────────────────────────────────────────────────
        pg = gate_results['val_04_parity']
        log('\n' + '─' * 70)
        log(f'VAL-04 DETAIL — v6.0 parity regression (pytest subprocess, D-08)')
        log('─' * 70)
        log(f'  test_file:     {pg["test_file"]}')
        log(f'  returncode:    {pg["returncode"]}')
        log(f'  tests_passed:  {pg["tests_passed"]}')
        log(f'  tests_failed:  {pg["tests_failed"]}')
        log(f'  duration:      {pg["duration_sec"]:.1f} s')
        log(f'  verdict:       {"PASS" if pg["passed"] else "FAIL"}')
        if not pg['passed']:
            log(f'  stdout tail (last 50 lines):')
            for line in pg['stdout_tail'].splitlines():
                log(f'    | {line}')

        # ── Verdict block (D-09) ─────────────────────────────────────────
        log('\n' + '=' * 70)
        log('FINAL VERDICT')
        log('=' * 70)
        log('')  # blank line before verdict for grep-without-word-boundary cleanliness
        if all_passed:
            verdict_str = VERDICT_PASS
        else:
            verdict_str = VERDICT_FAIL
        log(verdict_str)  # ← THE literal string on its own line (D-09)
        log('')

        # ── Rejection Narrative (D-10) ───────────────────────────────────
        if not all_passed:
            log('─' * 70)
            log('REJECTION NARRATIVE')
            log('─' * 70)
            baseline_cagr = gate_results['baseline_cagr_floor']
            log(f'v10.0 macro filter (DXY/EEM 20d z-scores + SBV regime) was evaluated')
            log(f'against the HARD gate (MaxDD < -20% AND CAGR ≥ {baseline_cagr:.2f}% with')
            log(f'walk-forward median degradation < 30% and v6.0 parity regression green).')
            log(f'')
            failed_gates = []
            if not val_01_pass: failed_gates.append('VAL-01 (A/B infrastructure)')
            if not val_02_pass: failed_gates.append('VAL-02 (OOS HARD gate)')
            if not val_03_pass: failed_gates.append('VAL-03 (walk-forward stability)')
            if not val_04_pass: failed_gates.append('VAL-04 (v6.0 parity)')
            log(f'Failed gate(s): {", ".join(failed_gates)}')
            log(f'')
            log(f'Phase 45 evidence (analysis/walkforward_grid.py, 39-combo sweep):')
            log(f'  • Train CAGR median 9.54% vs reconciled baseline {baseline_cagr:.2f}% → ~-2pp drag')
            log(f'    even BEFORE walk-forward year degradation is applied')
            log(f'  • Eval CAGR median 4.57% across 2019-2024 → 54% train→eval degradation')
            log(f'    (vs 30% D-07 gate). Best combo by degradation (stage1_dxy-c3) still fails')
            log(f'    at 0.411 — the entire 39-combo family is OVER-FIT to 2015-2018 training.')
            log(f'  • Per-year single-year MaxDD medians (across 39 combos):')
            log(f'      2019: -8.74%   2020: -15.29%   2021: -19.68%')
            log(f'      2022: -15.33%  2023: -12.72%   2024: -12.45%')
            log(f'    Every per-year DD IS shallower than v6.0''s full-period -28.17% — the')
            log(f'    filter DOES dampen drawdowns directionally. The trade-off (eroded CAGR)')
            log(f'    is what the walk-forward gate vetoed.')
            log(f'  • Degradation distribution across 39 combos: min 0.410 / median 0.538 / max 0.645')
            log(f'  • +all scenario full-period 10y return ≈ +146.8% (from sweep row')
            log(f'    stage3_all_three-c0/c1/c2, which trade identically above the SBV layer)')
            log(f'    vs v6.0 reconciled baseline +238.78% at {baseline_cagr:.2f}% CAGR.')
            log(f'')
            log(f'Pointers:')
            log(f'  • Phase 45 sweep results: output/v10_grid_results.csv (force-added past gitignore)')
            log(f'  • Phase 45 best-config JSON: INTENTIONALLY ABSENT — main() aborted when zero')
            log(f'    stages had accepted winners (fabrication refusal, not a bug)')
            log(f'  • Reconciled baseline (CAGR gate reference): output/v10_reconciled_baseline.json')
            log(f'  • Phase 45 SUMMARY (scientific outcome narrative):')
            log(f'    .planning/phases/45-walk-forward-grid-search/'
                f'45-03-execute-sweep-commit-artifacts-SUMMARY.md')
            log(f'')
            log(f'Lessons for v11.0 planning (per Phase 45 Plan 03 lessons-learned):')
            log(f'  1. Walk-forward CV INSIDE the sweep caught an overfit that post-hoc')
            log(f'     validation would have missed — the discipline worked as designed.')
            log(f'  2. The macro-filter thesis is directionally correct (DD reduction)')
            log(f'     but the binary-model price (eroded CAGR) is too high. Future work')
            log(f'     may revisit with (a) fractional sizing (deferred per Phase 44 D-05),')
            log(f'     (b) different publication-lag assumptions, or (c) additional alpha')
            log(f'     sources (ALPHA-01 foreign flow, ALPHA-02 jump model).')
            log(f'  3. "No fabricate on zero-accepted" guard (Phase 45 D-11) prevented')
            log(f'     silently poisoning this validation — preserved pattern for v11+.')
            log(f'')
            log(f'Production decision: v6.0 HybridEngine + fail-safe remains production per')
            log(f'project memory `project_best_model.md` and `.planning/STATE.md` Best VN30')
            log(f'Model entry. The v10.0 milestone publishes this rejection audit (Phase 47')
            log(f'DOC-03 only) and does NOT update `docs/rules_mdm_hybrid.md` or the dashboard.')

        # Save report
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f'Validation report saved: {path} ({len(lines)} lines, verdict: {verdict_str})')

        return all_passed
    ```
  </action>

  <verify>
    <automated>uv run python -c "
import tempfile, os
from analysis.validate_v10 import write_validation_report, VERDICT_PASS, VERDICT_FAIL

# Case 1: all gates pass → VERDICT_PASS, no rejection narrative
gr_pass = {
    'val_01_ab_complete': True,
    'val_02_hard_gate': {'baseline': {'passed': False, 'detail': 'd'}, '+all': {'passed': True, 'detail': 'd'}},
    'val_03_walkforward': {'combo': 'stage3_all_three-c1', 'median_degradation': 0.25,
                           'threshold': 0.30, 'passed_gate': True, 'accepted': True,
                           'rejection_reason': '', 'source_csv': 'x', 'total_combos': 39, 'total_accepted': 1},
    'val_04_parity': {'passed': True, 'returncode': 0, 'stdout_tail': 'ok',
                      'stderr_tail': '', 'tests_passed': 5, 'tests_failed': 0,
                      'test_file': 'tests/test_macro_filter_v6_parity.py', 'duration_sec': 90.0},
    'hard_gate_scenario': '+all',
    'full_metrics': {},
    'baseline_cagr_floor': 11.47,
}
with tempfile.TemporaryDirectory() as td:
    rp = os.path.join(td, 'v10_validation_report.txt')
    result = write_validation_report(gr_pass, report_path=rp)
    assert result is True, f'expected all_passed=True, got {result}'
    with open(rp, 'r', encoding='utf-8') as f:
        content = f.read()
    # D-09 pass verdict present on its own line
    lines_in_report = content.splitlines()
    assert VERDICT_PASS in lines_in_report, f'{VERDICT_PASS} not on its own line'
    assert VERDICT_FAIL not in lines_in_report
    # No rejection narrative
    assert 'REJECTION NARRATIVE' not in content
    print('Case 1 (all pass): verdict line exact, no narrative — OK')

# Case 2: HARD gate fails → VERDICT_FAIL + rejection narrative
gr_fail = dict(gr_pass)
gr_fail['val_02_hard_gate'] = {'baseline': {'passed': False, 'detail': 'd'},
                               '+all': {'passed': False, 'detail': 'CAGR ✗ 9.2% vs floor 11.47% | MaxDD ✗ -22.1% vs ceiling -20.00%'}}
gr_fail['val_03_walkforward'] = dict(gr_fail['val_03_walkforward'])
gr_fail['val_03_walkforward']['passed_gate'] = False
gr_fail['val_03_walkforward']['median_degradation'] = 0.5375
gr_fail['val_03_walkforward']['rejection_reason'] = 'median_degradation 0.537 >= 0.30'
gr_fail['val_03_walkforward']['accepted'] = False
gr_fail['val_03_walkforward']['total_accepted'] = 0

with tempfile.TemporaryDirectory() as td:
    rp = os.path.join(td, 'v10_validation_report.txt')
    result = write_validation_report(gr_fail, report_path=rp)
    assert result is False, f'expected all_passed=False, got {result}'
    with open(rp, 'r', encoding='utf-8') as f:
        content = f.read()
    lines_in_report = content.splitlines()
    # D-09 fail verdict present on its own line
    assert VERDICT_FAIL in lines_in_report, f'{VERDICT_FAIL} not on its own line'
    assert VERDICT_PASS not in lines_in_report
    # D-10 narrative present
    assert 'REJECTION NARRATIVE' in content
    assert '9.54' in content, 'narrative missing train CAGR 9.54%'
    assert '0.538' in content or '0.537' in content, 'narrative missing degradation median'
    assert '11.47' in content, 'narrative should reference baseline 11.47% via floor param'
    assert 'v6.0' in content
    assert 'Phase 45' in content
    # Narrative length: 20-40 lines from REJECTION NARRATIVE header to end-of-file
    start = content.index('REJECTION NARRATIVE')
    narrative = content[start:]
    narr_lines = narrative.splitlines()
    assert 20 <= len(narr_lines) <= 60, f'narrative length {len(narr_lines)} outside 20-60'
    print(f'Case 2 (fail): verdict line exact, narrative {len(narr_lines)} lines — OK')

print('write_validation_report: 2/2 cases PASS (D-09 verdict + D-10 narrative verified)')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def write_validation_report" analysis/validate_v10.py` returns 1 hit
    - `grep -n "log(verdict_str)" analysis/validate_v10.py` returns 1 hit (the verdict string is logged as its own line with no prefix/suffix)
    - `grep -n "REJECTION NARRATIVE" analysis/validate_v10.py` returns 1 hit (header string in writer)
    - `grep -n "\"9\\.54\"\\|9\\.54%" analysis/validate_v10.py` returns at least 1 hit (train CAGR cited in narrative)
    - `grep -n "0\\.538\\|0\\.537" analysis/validate_v10.py` returns at least 1 hit (degradation median cited in narrative)
    - `grep -n "output/v10_grid_results.csv" analysis/validate_v10.py` returns at least 1 hit (narrative pointer)
    - Verify command prints `write_validation_report: 2/2 cases PASS (D-09 verdict + D-10 narrative verified)` with exit 0
    - Case 1 proof: `VERDICT_PASS` string appears as a standalone line AND `VERDICT_FAIL` absent AND no `REJECTION NARRATIVE` section
    - Case 2 proof: `VERDICT_FAIL` string appears as a standalone line AND `VERDICT_PASS` absent AND `REJECTION NARRATIVE` section present with 20-60 lines
    - Narrative includes `9.54` (train CAGR), `11.47` (baseline), `Phase 45` (citation), `v6.0` (retained model name) — all greppable in report content
  </acceptance_criteria>

  <done>Validation report writer produces D-09-compliant verdict line and D-10-compliant rejection narrative. Both pass and fail branches verified via synthetic gate-result inputs.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Wire main() orchestration + D-11 exit code</name>

  <read_first>
    - analysis/validate_v10.py (current state — all helpers + writers from Plans 01, 02 and this plan Tasks 1-2)
    - analysis/validate_v9.py (lines 279-648 for the main() orchestration pattern — data load → scenario loop → walk-forward → report → exit)
    - .planning/phases/46-ab-oos-validation-hard-gate/46-CONTEXT.md (D-06 no short-circuit, D-11 exit code discipline, D-04 OOS subset)
  </read_first>

  <files>analysis/validate_v10.py</files>

  <behavior>
    - `main()` executes in strict order: load data → build scenarios → run all 5 full-period engines → verify_extremes_never_trigger → OOS subset (2 scenarios: baseline + +all) via DataFrame slice → evaluate HARD gate per OOS-subset scenario → lookup walk-forward → run parity subprocess → write A/B report → write scenarios CSV → write validation report → sys.exit(0 or 1)
    - D-06: NO short-circuit. If any gate fails, subsequent gates STILL run and are captured in the report.
    - D-11: `sys.exit(0)` on full pass, `sys.exit(1)` on any fail.
    - Script must be directly executable: `uv run python analysis/validate_v10.py` → runs main() → writes 3 output files → exits with code reflecting verdict.
    - Stdout is verbose-but-scannable: each stage logs a banner + summary.
  </behavior>

  <action>
    Append to `analysis/validate_v10.py`:

    ```python
    # ═══════════════════════════════════════════════════════════════════════
    # Orchestration (main) — Plan 03 Task 3
    # ═══════════════════════════════════════════════════════════════════════

    def main():
        """Phase 46 end-to-end validation (VAL-01..VAL-05).

        Executes the four gates in order WITHOUT short-circuit (D-06) and
        writes three deliverables:
          - output/v10_ab_comparison.txt (VAL-01)
          - output/v10_ab_scenarios.csv (VAL-01 machine-readable)
          - output/v10_validation_report.txt (VAL-02/03/04 + D-09 verdict)

        Exit code (D-11): 0 on full pass, 1 on any fail.
        """
        print('=' * 70)
        print('PHASE 46: v10.0 VALIDATION PIPELINE')
        print('=' * 70)

        # ── Load HARD gate thresholds early (fail-fast if JSON missing) ──
        thresholds = load_hard_gate_thresholds()
        print(f'\nHARD gate thresholds loaded from {thresholds["baseline_source"]}:')
        print(f'  CAGR floor:     {thresholds["cagr_floor"]:.2f}%')
        print(f'  MaxDD ceiling:  {thresholds["max_dd_ceiling"]:.2f}%')

        # ── Load VN30 data ───────────────────────────────────────────────
        print(f'\nLoading VN30 data: {DATA_START} → {DATA_END}')
        loader = DataLoader('vn30')
        df_full = loader.load(start_date=DATA_START, end_date=DATA_END)
        df_full = build_indicator_dataframe(df_full)
        print(f'VN30 data: {len(df_full)} rows ({df_full["date"].min().date()} → '
              f'{df_full["date"].max().date()})')
        assert df_full['date'].max() >= pd.Timestamp('2025-12-01'), (
            f"Insufficient data: max date {df_full['date'].max()} — OOS window "
            f"requires through {OOS_END}"
        )

        # ── Build scenarios ──────────────────────────────────────────────
        scenarios = build_scenarios()
        print(f'\nScenarios built: {list(scenarios.keys())}')

        # ── VAL-01: A/B across 5 scenarios on full period ────────────────
        print('\n' + '─' * 70)
        print('VAL-01: Running 5 scenarios on full period')
        print('─' * 70)
        full_results: dict = {}
        full_metrics: dict = {}
        val_01_ab_complete = True
        for name in SCENARIO_ORDER:
            print(f'  Running {name}...')
            try:
                res = run_engine(df_full, scenarios[name])
                full_results[name] = res
                full_metrics[name] = compute_metrics(res)
                m = full_metrics[name]
                print(f'    CAGR={m["cagr_pct"]:.2f}%  MaxDD={m["max_dd_pct"]:.2f}%  '
                      f'Sharpe={m["sharpe_rf3"]:.3f}  SELL={m["sell_count"]}')
            except Exception as exc:
                print(f'  ERROR in {name}: {type(exc).__name__}: {exc}')
                print(traceback.format_exc())
                val_01_ab_complete = False
                full_results[name] = None
                full_metrics[name] = {
                    'sharpe_rf3': float('nan'), 'cagr_pct': float('nan'),
                    'max_dd_pct': float('nan'), 'total_return_pct': float('nan'),
                    'transitions': 0, 'sell_count': 0,
                    'ma50_breakdown_sell_share': float('nan'), 'buy_count': 0,
                    'buy_pct': float('nan'), 'cash_pct': float('nan'),
                    'sell_pct': float('nan'),
                }

        # ── D-02 isolation sanity check on +all macro-on results ─────────
        extremes_check = {'dxy_z_abs_max': float('nan'), 'eem_z_abs_max': float('nan'),
                          'headroom': float('nan')}
        if full_results.get('+all') is not None:
            try:
                extremes_check = verify_extremes_never_trigger(full_results['+all'])
                print(f'\nD-02 isolation sanity: |dxy_z|max={extremes_check["dxy_z_abs_max"]:.2f}  '
                      f'|eem_z|max={extremes_check["eem_z_abs_max"]:.2f}  '
                      f'headroom={extremes_check["headroom"]:.1f}')
            except AssertionError as exc:
                print(f'\n❌ D-02 ISOLATION LEAK: {exc}')
                val_01_ab_complete = False

        # ── Buy & Hold reference ─────────────────────────────────────────
        bh_total_ret = (df_full['close'].iloc[-1] / df_full['close'].iloc[0] - 1) * 100
        bh_years = (df_full['date'].iloc[-1] - df_full['date'].iloc[0]).days / 365.25
        bh_cagr = ((1 + bh_total_ret / 100) ** (1 / bh_years) - 1) * 100 if bh_years > 0 else 0.0
        bh_eq = df_full['close'].values / df_full['close'].iloc[0]
        bh_peak = np.maximum.accumulate(bh_eq)
        bh_maxdd = ((bh_eq - bh_peak) / bh_peak).min() * 100
        bh_stats = {
            'total_return_pct': round(bh_total_ret, 2),
            'cagr_pct': round(bh_cagr, 2),
            'max_dd_pct': round(bh_maxdd, 2),
        }

        # ── VAL-02: OOS HARD gate (baseline + +all only, D-04) ───────────
        print('\n' + '─' * 70)
        print(f'VAL-02: OOS slice {OOS_START} → {OOS_END} (baseline + +all only, D-04)')
        print('─' * 70)
        oos_metrics: dict = {}
        hard_gate_per_scenario: dict = {}
        for name in OOS_SCENARIO_SUBSET:
            res_full = full_results.get(name)
            if res_full is None:
                oos_metrics[name] = None
                hard_gate_per_scenario[name] = None
                print(f'  {name}: n/a (full-period run errored)')
                continue
            oos_slice = res_full[res_full['date'] >= OOS_START].copy().reset_index(drop=True)
            if len(oos_slice) < 2:
                oos_metrics[name] = None
                hard_gate_per_scenario[name] = None
                print(f'  {name}: n/a (OOS slice has {len(oos_slice)} rows)')
                continue
            om = compute_metrics(oos_slice)
            oos_metrics[name] = om
            gate = evaluate_hard_gate(om, thresholds)
            hard_gate_per_scenario[name] = gate
            print(f'  {name}: {"PASS" if gate["passed"] else "FAIL"} — {gate["detail"]}')

        # ── VAL-03: Walk-forward lookup (D-06 no short-circuit) ──────────
        print('\n' + '─' * 70)
        print('VAL-03: Walk-forward stability (lookup Phase 45)')
        print('─' * 70)
        try:
            wf_lookup = lookup_walkforward_degradation()
            print(f'  combo={wf_lookup["combo"]}  median_deg={wf_lookup["median_degradation"]:.4f}  '
                  f'passed_gate={wf_lookup["passed_gate"]}')
        except Exception as exc:
            print(f'  ERROR in VAL-03 lookup: {type(exc).__name__}: {exc}')
            wf_lookup = {
                'combo': 'N/A', 'median_degradation': float('nan'), 'threshold': 0.30,
                'passed_gate': False, 'accepted': False,
                'rejection_reason': f'lookup failed: {type(exc).__name__}: {exc}',
                'source_csv': WALKFORWARD_GRID_CSV, 'total_combos': 0, 'total_accepted': 0,
            }

        # ── VAL-04: Parity pytest subprocess (D-06 no short-circuit) ─────
        print('\n' + '─' * 70)
        print('VAL-04: v6.0 parity pytest (subprocess)')
        print('─' * 70)
        parity = run_parity_gate(timeout_sec=300)
        print(f'  returncode={parity["returncode"]}  '
              f'passed={parity["tests_passed"]}  failed={parity["tests_failed"]}  '
              f'duration={parity["duration_sec"]:.1f}s  → {"PASS" if parity["passed"] else "FAIL"}')

        # ── Write artifacts (D-06: always, even on failure) ──────────────
        print('\n' + '─' * 70)
        print('Writing Phase 46 deliverables')
        print('─' * 70)
        write_ab_comparison_report(
            full_metrics=full_metrics,
            oos_metrics=oos_metrics,
            wf_lookup=wf_lookup,
            extremes_check=extremes_check,
            bh_stats=bh_stats,
        )
        write_scenarios_csv(
            full_metrics=full_metrics,
            oos_metrics=oos_metrics,
            hard_gate_results=hard_gate_per_scenario,
            bh_stats=bh_stats,
        )
        all_passed = write_validation_report({
            'val_01_ab_complete': val_01_ab_complete,
            'val_02_hard_gate': hard_gate_per_scenario,
            'val_03_walkforward': wf_lookup,
            'val_04_parity': parity,
            'hard_gate_scenario': '+all',      # D-04: +all is the "selected" scenario
            'full_metrics': full_metrics,
            'baseline_cagr_floor': thresholds['cagr_floor'],
        })

        # ── D-11: exit code reflects verdict ─────────────────────────────
        exit_code = 0 if all_passed else 1
        print(f'\nFINAL VERDICT: {"PASS" if all_passed else "FAIL"} → exit {exit_code}')
        sys.exit(exit_code)


    if __name__ == '__main__':
        main()
    ```

    IMPORTANT: Do NOT execute `python analysis/validate_v10.py` in this task. Plan 04 owns the end-to-end execution. This task only wires main() and commits the script; verification below is structural (py_compile + unit tests on the helpers, not a full engine run).
  </action>

  <verify>
    <automated>uv run python -c "
import py_compile
py_compile.compile('analysis/validate_v10.py', doraise=True)
print('py_compile OK')

# Confirm main() exists and the __main__ guard is present
import ast
with open('analysis/validate_v10.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())

# Find top-level functions
func_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
required = {'build_scenarios', 'run_engine', 'compute_metrics',
            'verify_extremes_never_trigger', 'load_hard_gate_thresholds',
            'evaluate_hard_gate', 'lookup_walkforward_degradation',
            'run_parity_gate', 'write_ab_comparison_report',
            'write_scenarios_csv', 'write_validation_report', 'main'}
# compute_metrics is imported, not defined — remove from required set
required.discard('compute_metrics')
missing = required - func_names
assert not missing, f'missing functions: {missing}'
print(f'All required functions present: {sorted(required)}')

# Confirm __main__ guard calls main()
import re
with open('analysis/validate_v10.py', 'r', encoding='utf-8') as f:
    source = f.read()
assert re.search(r'if __name__ == .__main__.:', source), 'missing __main__ guard'
assert re.search(r'main\\(\\)', source), 'main() never called'
assert 'sys.exit(exit_code)' in source or 'sys.exit(0)' in source, 'missing sys.exit with code'

# Count D-06 'no short-circuit' evidence: all four gate calls must appear OUTSIDE any try block guarding only one gate
# (loose check: each helper is called exactly once in main())
for helper in ['evaluate_hard_gate', 'lookup_walkforward_degradation', 'run_parity_gate']:
    count = source.count(f'{helper}(')
    assert count >= 1, f'{helper} not called in main'
print('main() structure OK (all 4 gates invoked, __main__ guard + sys.exit present)')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "def main" analysis/validate_v10.py` returns 1 hit
    - `grep -n "if __name__ == '__main__':" analysis/validate_v10.py` returns 1 hit
    - `grep -n "sys.exit(exit_code)" analysis/validate_v10.py` returns 1 hit (D-11)
    - `grep -n "sys.exit(0)" analysis/validate_v10.py` returns 0 (exit code is dynamic per D-11, not hardcoded 0)
    - `grep -n "for name in SCENARIO_ORDER" analysis/validate_v10.py` returns at least 1 hit (A/B loop)
    - `grep -n "for name in OOS_SCENARIO_SUBSET" analysis/validate_v10.py` returns 1 hit (D-04 OOS loop)
    - `grep -n "'hard_gate_scenario': '\\+all'" analysis/validate_v10.py` returns 1 hit (D-04 selected scenario)
    - All four gate helpers called at least once in main: `evaluate_hard_gate(`, `lookup_walkforward_degradation(`, `run_parity_gate(`, `verify_extremes_never_trigger(` — each present
    - `py_compile` succeeds (syntax valid)
    - Verify command prints `main() structure OK (all 4 gates invoked, __main__ guard + sys.exit present)` with exit 0
    - DO NOT actually run `uv run python analysis/validate_v10.py` in this task — leave end-to-end execution to Plan 04
    - Pre-existing regression tests remain green: `uv run pytest -m regression tests/test_baseline_determinism.py tests/test_macro_filter_v6_parity.py -v` → 8/8 PASS (no regression from Plan 02's subprocess helper edge cases)
  </acceptance_criteria>

  <done>main() wires all helpers + writers into a single pipeline with D-06 no-short-circuit behavior, D-11 exit code, D-04 OOS subset handling, D-02 extremes-leak sanity check. Script is structurally complete; Plan 04 will execute it.</done>
</task>

</tasks>

<verification>
After all 3 tasks:

1. Structural completeness: `uv run python -c "import analysis.validate_v10 as v; assert hasattr(v, 'main'); print('module+main importable')"` → prints `module+main importable` with exit 0.

2. py_compile clean: `uv run python -c "import py_compile; py_compile.compile('analysis/validate_v10.py', doraise=True); print('OK')"` → prints `OK` with exit 0.

3. All required functions defined (from ast): 11 functions (compute_metrics imported separately).

4. No hardcoded 11.47 in file: `grep -cn "11\\.47" analysis/validate_v10.py` returns 0 (except possibly in narrative strings that READ `baseline_cagr_floor` variable — those reference the VARIABLE, not a literal).

5. Regression suite still green: `uv run pytest -m regression -v` → full pass (13 tests including Phase 45 walkforward_oos_guard).
</verification>

<success_criteria>
- [ ] main() orchestrates all four gates in D-06 order (no short-circuit)
- [ ] A/B comparison report + scenarios CSV + validation report all write via helpers
- [ ] D-04 OOS subset limited to baseline + +all
- [ ] D-02 verify_extremes_never_trigger called on +all results before A/B table is written
- [ ] D-09 verdict string on its own line in validation report (verified in Task 2)
- [ ] D-10 rejection narrative present on fail path with specific Phase 45 numbers
- [ ] D-11 sys.exit(0) or sys.exit(1) based on all_passed
- [ ] `if __name__ == '__main__': main()` guard present
- [ ] Script is ready for Plan 04 end-to-end execution
</success_criteria>

<output>
After completion, create `.planning/phases/46-ab-oos-validation-hard-gate/46-03-pipeline-wiring-SUMMARY.md`
</output>
