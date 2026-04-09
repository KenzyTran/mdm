---
phase: 31-multi-stock-portfolio-engine
plan: 05
type: execute
wave: 5
depends_on: [31-04]
files_modified:
  - strategies/portfolio/ab_report.py
  - docs/rules_canslim_mdm.md
  - docs/audits/phase31-portfolio-engine.md
  - tests/strategies/portfolio/test_ab_report.py
autonomous: true
requirements: [PORT-10]
must_haves:
  truths:
    - "ab_report.py writes trades.csv / positions.csv / nav.csv / unfilled.csv from a PortfolioResult"
    - "docs/audits/phase31-portfolio-engine.md exists and references all 4 CSVs"
    - "docs/rules_canslim_mdm.md contains a Portfolio Engine section (per Code-Docs Sync Rule)"
  artifacts:
    - path: strategies/portfolio/ab_report.py
      provides: "write_trades_csv, write_positions_csv, write_nav_csv, write_unfilled_csv, write_all"
      contains: "def write_all"
    - path: docs/audits/phase31-portfolio-engine.md
      provides: "Phase 31 audit report"
      contains: "Portfolio Engine"
    - path: docs/rules_canslim_mdm.md
      provides: "CANSLIM+MDM portfolio engine rule documentation"
      contains: "Portfolio Engine"
  key_links:
    - from: strategies/portfolio/ab_report.py
      to: strategies/portfolio/engine.py
      via: import
      pattern: "from .engine import PortfolioResult"
---

<objective>
Serialize `PortfolioResult` to the canonical CSV set under `docs/audits/phase31/`, write the phase audit report, and ship the portfolio-engine section in `docs/rules_canslim_mdm.md` (per Code-Docs Sync Rule, CLAUDE.md).

Purpose: Closes Phase 31 by producing the audit artifacts Phase 32 will consume for parameter sweeps, and satisfies the docs-in-same-commit requirement.

Output: 4 CSV writers, a markdown audit report, a Portfolio Engine docs section, and a round-trip test.
</objective>

<execution_context>
@C:/Users/trant/projects/mdm/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/trant/projects/mdm/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md
@strategies/portfolio/engine.py
@strategies/entry/ab_report.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: ab_report.py writers + round-trip test</name>
  <files>strategies/portfolio/ab_report.py, tests/strategies/portfolio/test_ab_report.py</files>
  <read_first>strategies/entry/ab_report.py (prior writer convention), .planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-27)</read_first>
  <behavior>
    - write_trades_csv(result:PortfolioResult, path:Path). Columns exactly: ticker, buy_date, buy_price, buy_cost_vnd, sell_date, sell_price, sell_cost_vnd, pnl_vnd, pnl_pct, exit_reason. Sorted by sell_date.
    - write_positions_csv(result, path). Columns: date, ticker, shares, mark_price, mark_value. Sorted by date, ticker.
    - write_nav_csv(result, path). Columns: date, nav, cash, deployed_pct, open_slots. Sorted by date.
    - write_unfilled_csv(result, path). Columns: date, ticker, reason, detail. Reason in {ceiling_lock, liquidity_gate, cooldown, no_free_slot, canslim_score_missing, shares_zero, cash_dropped}.
    - write_all(result, out_dir:Path) → dict of written paths. Creates out_dir if missing.
    - Tests:
      - test_round_trip: build a minimal PortfolioResult with 1 trade, 2 positions_daily rows, 2 nav_daily rows, 1 unfilled; call write_all to a tmp_path; re-read each CSV and assert column sets match exactly and row counts match.
      - test_empty_result: empty trades/positions/nav/unfilled → CSVs still created with just headers.
  </behavior>
  <action>
    Create `strategies/portfolio/ab_report.py`. Import `from pathlib import Path; import pandas as pd; from .engine import PortfolioResult`. Each writer: build DataFrame with enforced column order, call `.to_csv(path, index=False)`. `write_all` creates dir via `out_dir.mkdir(parents=True, exist_ok=True)` and returns `{"trades":..., "positions":..., "nav":..., "unfilled":...}`.

    Create `tests/strategies/portfolio/test_ab_report.py` with the 2 tests. Build a synthetic PortfolioResult manually (not via engine) to isolate the writer layer. Use `tmp_path` pytest fixture. Assert column sets with `set(pd.read_csv(p).columns) == {"ticker","buy_date",...}`.
  </action>
  <verify>
    <automated>uv run pytest tests/strategies/portfolio/test_ab_report.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep "def write_trades_csv" strategies/portfolio/ab_report.py matches
    - grep "def write_positions_csv" strategies/portfolio/ab_report.py matches
    - grep "def write_nav_csv" strategies/portfolio/ab_report.py matches
    - grep "def write_unfilled_csv" strategies/portfolio/ab_report.py matches
    - grep "def write_all" strategies/portfolio/ab_report.py matches
    - grep "def test_round_trip" tests/strategies/portfolio/test_ab_report.py matches
    - pytest exits 0 with ≥2 tests passed
  </acceptance_criteria>
  <done>4 writers + write_all importable; round-trip test green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Audit report + rules_canslim_mdm.md Portfolio Engine section</name>
  <files>docs/audits/phase31-portfolio-engine.md, docs/rules_canslim_mdm.md</files>
  <read_first>.planning/phases/31-multi-stock-portfolio-engine/31-CONTEXT.md (D-27, D-28), CLAUDE.md (Code-Docs Sync Rule)</read_first>
  <behavior>
    - docs/audits/phase31-portfolio-engine.md: describes engine scope, references the 4 CSVs, states SC1-SC8 status, notes that end-to-end VN100 sweep is deferred to Phase 32.
    - docs/rules_canslim_mdm.md: new file (or append if exists) with sections: Overview, MDM Gate (Policy A), Entry Feed (A∪C union), Slot Allocation, Exit Priority Chain, Cooldown, Costs, Liquidity Gate, NAV Rule (state[i-1]), T+2 & Ceiling/Floor Locks. Each section cites the decision IDs (D-04..D-28) and requirement IDs (GATE-01..04, PORT-01..10).
  </behavior>
  <action>
    Check if `docs/rules_canslim_mdm.md` exists; if not, create it with a top-level heading and the sections listed in &lt;behavior&gt;. If it exists, append a "## Portfolio Engine (Phase 31)" section covering all 10 subsections. Each subsection ≤ 6 lines; cite D-XX IDs inline.

    Create `docs/audits/phase31-portfolio-engine.md` with frontmatter (phase: 31, status: complete, date: current), sections: Scope, Test Coverage (list the test files and pass counts), SC1-SC8 Status table (mark SC8 MANDATORY with a bold callout), CSV Output Paths (list trades.csv, positions.csv, nav.csv, unfilled.csv under docs/audits/phase31/), Deferred to Phase 32 (end-to-end VN100 sweep).

    No VN100 run yet — this plan is engine-only. The report explicitly states "no production backtest run in this phase; see Phase 32 for VN100 sweep".
  </action>
  <verify>
    <automated>uv run python -c "from pathlib import Path; assert Path('docs/audits/phase31-portfolio-engine.md').exists(); assert 'Portfolio Engine' in Path('docs/rules_canslim_mdm.md').read_text(encoding='utf-8'); print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - test -f docs/audits/phase31-portfolio-engine.md (file exists)
    - test -f docs/rules_canslim_mdm.md (file exists)
    - grep "Portfolio Engine" docs/rules_canslim_mdm.md matches
    - grep "SC8" docs/audits/phase31-portfolio-engine.md matches
    - grep "state\[i-1\]" docs/rules_canslim_mdm.md matches
    - verify command above prints "ok" and exits 0
  </acceptance_criteria>
  <done>Audit report committed; rules doc has a Portfolio Engine section citing all decisions.</done>
</task>

</tasks>

<verification>
uv run pytest tests/strategies/portfolio/ -x -q
</verification>

<success_criteria>
- 4 CSV writers work and round-trip
- Audit markdown exists and references all CSVs
- docs/rules_canslim_mdm.md contains Portfolio Engine section (Code-Docs Sync Rule satisfied)
- Full tests/strategies/portfolio/ suite green
</success_criteria>

<output>
After completion, create `.planning/phases/31-multi-stock-portfolio-engine/31-05-SUMMARY.md`
</output>
