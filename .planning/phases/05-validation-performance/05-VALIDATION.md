---
phase: 5
slug: validation-performance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/test_v2_performance.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_v2_performance.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | PERF-01 | unit | `python -m pytest tests/test_v2_performance.py -k test_equity_curve` | :x: W0 | :white_large_square: pending |
| 05-01-02 | 01 | 1 | PERF-01 | unit | `python -m pytest tests/test_v2_performance.py -k test_sharpe_ratio` | :x: W0 | :white_large_square: pending |
| 05-01-03 | 01 | 1 | PERF-01 | unit | `python -m pytest tests/test_v2_performance.py -k test_max_drawdown` | :x: W0 | :white_large_square: pending |
| 05-01-04 | 01 | 1 | PERF-03 | unit | `python -m pytest tests/test_v2_performance.py -k test_validate_match_rates` | :x: W0 | :white_large_square: pending |
| 05-01-05 | 01 | 1 | PERF-03 | unit | `python -m pytest tests/test_v2_performance.py -k test_train_heldout_validation` | :x: W0 | :white_large_square: pending |
| 05-02-01 | 02 | 2 | PERF-02 | integration | `python -m pytest tests/test_v2_performance.py -k test_comparison_table` | :x: W0 | :white_large_square: pending |

*Status: :white_large_square: pending / :white_check_mark: green / :x: red / :warning: flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_v2_performance.py` — stubs for PERF-01 metrics and PERF-03 held-out validation
- [ ] `tests/conftest.py` — shared fixtures (sample DataFrames, mock configs)
- [ ] pytest install — if not already present

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-panel chart visual quality | PERF-01 | Visual inspection of PNG output | Run `python analysis/validate_v2.py`, open output PNG, verify 3 panels (equity, drawdown, signals) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
