---
phase: 29
slug: vn100-universe-canslim-scorer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (reused from Phase 28) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/canslim -m "not integration" -x -q` |
| **Full suite command** | `uv run pytest tests/canslim -q` |
| **Estimated runtime** | ~15s quick / ~60s full |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Filled in by planner during plan creation. Every task must either have an `<automated>` verify command OR declare a Wave 0 dependency.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | UNIV-01..03, CANS-01..12 | unit | `uv run pytest tests/canslim -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `strategies/canslim/__init__.py` — package skeleton
- [ ] `strategies/canslim/{config,universe,sectors,scorer,baseline}.py` — module stubs
- [ ] `strategies/canslim/rules/{fundamental,technical,rs,flow,liquidity}.py` — rule stubs
- [ ] `tests/canslim/conftest.py` — shared fixtures (fake OHLCV, EPS, stock_list)
- [ ] `tests/canslim/test_universe.py` — UNIV-01..03 stubs
- [ ] `tests/canslim/test_config.py` — CanslimConfig defaults
- [ ] `tests/canslim/test_sectors.py` — sector routing (bank/non-bank/excluded)
- [ ] `tests/canslim/test_rules_fundamental.py` — C/C+/A/A+ + look-ahead guard
- [ ] `tests/canslim/test_rules_technical.py` — N (price within 15% of 52w high)
- [ ] `tests/canslim/test_rules_rs.py` — RS formula + percentile rank
- [ ] `tests/canslim/test_rules_flow.py` — I (20d foreign flow) + pre-2022 fallback
- [ ] `tests/canslim/test_rules_liquidity.py` — L (≥80 percentile)
- [ ] `tests/canslim/test_scorer.py` — end-to-end CANSLIM row per (date,ticker)
- [ ] `scripts/introspect_canslim_schema.py` — live-DB column name locker (MUST run in Wave 0)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Baseline overlap ≥4/10 vs `rank_top_stocks.diem_canslim` top-10 on N recent dates | Success Criterion 6 | Needs live DB + qualitative inspection; acceptable discrepancies must be documented | Run `scripts/canslim_baseline_compare.py --dates <N>` and record overlap + discrepancy notes in `docs/audits/phase29/baseline_comparison.md` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (including live-schema introspection)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
