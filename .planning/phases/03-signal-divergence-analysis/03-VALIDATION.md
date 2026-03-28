---
phase: 3
slug: signal-divergence-analysis
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-28
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v --tb=long` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v --tb=long`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 03-01-01 | 01 | 1 | SIG-01 | unit | `python -m pytest tests/test_signal_comparison.py -v` | pending |
| 03-01-02 | 01 | 1 | SIG-02 | integration | `python -m pytest tests/test_signal_generation.py -v` | pending |
| 03-02-01 | 02 | 2 | SIG-03 | integration | `python -m pytest tests/test_divergence_report.py -v` | pending |
| 03-02-02 | 02 | 2 | SIG-04 | integration | `python -m pytest tests/test_signal_chart.py -v` | pending |

*Status: pending / green / red / flaky*

**Wave 0 note:** No separate Wave 0 plan is needed. All test files are created inline within their respective TDD tasks. Each task creates its test file as part of the red-green-refactor cycle (Plan 01 tasks are `tdd="true"`; Plan 02 tasks create tests alongside production code). The Nyquist rule is satisfied by inline test creation.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual overlay chart readability | SIG-04 | Chart aesthetics require visual inspection | Open generated PNG, verify both signal series visible with clear legend |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Test files created inline within TDD tasks (no separate Wave 0 needed)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
