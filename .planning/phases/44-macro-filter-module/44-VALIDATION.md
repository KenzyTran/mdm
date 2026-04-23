---
phase: 44
slug: macro-filter-module
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.2 |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]` — markers `regression`, `slow`) |
| **Quick run command** | `uv run pytest tests/test_macro_filter.py -x -q` |
| **Full suite command** | `uv run pytest tests/test_macro_filter.py tests/test_macro_filter_v6_parity.py -x` |
| **Estimated runtime** | ~60 seconds (unit tests fast; parity test ~45s for full VN30 2015-2026 load) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_macro_filter.py -x -q` (unit tests, ~5s)
- **After every plan wave:** Run full suite command (parity included)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | MACRO-01 | unit | `uv run pytest tests/test_macro_filter.py::test_dxy_zscore_known_date -x` | ❌ W0 | ⬜ pending |
| 44-01-02 | 01 | 1 | MACRO-02 | unit | `uv run pytest tests/test_macro_filter.py::test_eem_zscore_known_date -x` | ❌ W0 | ⬜ pending |
| 44-01-03 | 01 | 1 | MACRO-03 | unit | `uv run pytest tests/test_macro_filter.py::test_sbv_regime_transitions -x` | ❌ W0 | ⬜ pending |
| 44-01-04 | 01 | 1 | MACRO-03 | unit | `uv run pytest tests/test_macro_filter.py::test_sbv_decay_to_neutral -x` | ❌ W0 | ⬜ pending |
| 44-02-01 | 02 | 2 | MACRO-04 | unit | `uv run pytest tests/test_macro_filter.py::test_macro_verdict_pass_through -x` | ❌ W0 | ⬜ pending |
| 44-02-02 | 02 | 2 | MACRO-04 | unit | `uv run pytest tests/test_macro_filter.py::test_short_circuit_when_disabled -x` | ❌ W0 | ⬜ pending |
| 44-02-03 | 02 | 2 | MACRO-05 | unit | `uv run pytest tests/test_macro_filter.py::test_dxy_easing_vetoes_sell -x` | ❌ W0 | ⬜ pending |
| 44-02-04 | 02 | 2 | MACRO-05 | unit | `uv run pytest tests/test_macro_filter.py::test_dxy_tightening_lowers_dd -x` | ❌ W0 | ⬜ pending |
| 44-02-05 | 02 | 2 | MACRO-05 | unit | `uv run pytest tests/test_macro_filter.py::test_sbv_tightening_shrinks_stop_loss -x` | ❌ W0 | ⬜ pending |
| 44-02-06 | 02 | 2 | MACRO-05 | unit | `uv run pytest tests/test_macro_filter.py::test_most_restrictive_combiner -x` | ❌ W0 | ⬜ pending |
| 44-03-01 | 03 | 3 | MACRO-04 | regression | `uv run pytest tests/test_macro_filter_v6_parity.py -x -m regression` | ❌ W0 | ⬜ pending |
| 44-03-02 | 03 | 3 | MACRO-04 | regression | `uv run pytest tests/test_macro_filter_v6_parity.py::test_signal_log_byte_exact -x -m regression` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Wave numbers/plan IDs above are PLACEHOLDERS — gsd-planner refines them when generating PLAN.md files. Validation contract (which assertions cover which REQ-ID) is what's load-bearing.*

---

## Wave 0 Requirements

- [ ] `tests/test_macro_filter.py` — NEW; stubs for MACRO-01, MACRO-02, MACRO-03, MACRO-05 (DXY/EEM z-score on known date, SBV regime transitions + decay, policy verbs, combiner logic)
- [ ] `tests/test_macro_filter_v6_parity.py` — NEW; stubs for MACRO-04 byte-exact signal-log parity vs `output/v10_reconciled_baseline.json` with `macro_filter_enabled=False` AND `v60_strict_mode=True` (Phase 42 D-04 contract)
- [ ] `tests/conftest.py` — verify existing fixtures (no new shared fixtures needed; macro_filter tests use synthetic mini-fixtures inline per Phase 42 D-18 precedent)
- [ ] pytest >= 9.0.2 already installed (verified via `pyproject.toml`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ROADMAP.md SC-5 text rewrite (D-05) | MACRO-05 | Doc-text edit, not behavior | `grep -n "dxy_easing_z_threshold" .planning/ROADMAP.md` returns line 852 area; old text "forces half-position or full CASH" must be absent |
| REQUIREMENTS.md MACRO-05 text rewrite (D-05) | MACRO-05 | Doc-text edit, not behavior | `grep -n "dxy_easing_z_threshold" .planning/REQUIREMENTS.md` returns line 26 area; old text "sbv_tightening_position_frac" must be absent |

*Note: All MacroFilter behaviors (z-score math, regime classifier, policy verbs, combiner, parity) have automated verification. Only the doc-text rewrites are manual-grep verifications.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (tests/test_macro_filter.py, tests/test_macro_filter_v6_parity.py)
- [ ] No watch-mode flags (all `-x` short-circuit on first fail)
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
