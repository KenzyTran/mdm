---
phase: 3
slug: signal-divergence-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SIG-01 | unit | `python -m pytest tests/test_signal_comparison.py -v` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | SIG-02 | unit | `python -m pytest tests/test_signal_generation.py -v` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | SIG-03 | integration | `python -m pytest tests/test_divergence_report.py -v` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | SIG-04 | integration | `python -m pytest tests/test_signal_chart.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_signal_comparison.py` — stubs for SIG-01 signal scoring
- [ ] `tests/test_signal_generation.py` — stubs for SIG-02 full signal generation
- [ ] `tests/test_divergence_report.py` — stubs for SIG-03 divergence classification
- [ ] `tests/test_signal_chart.py` — stubs for SIG-04 visual overlay

*Existing pytest infrastructure covers framework setup. Test files need creation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual overlay chart readability | SIG-04 | Chart aesthetics require visual inspection | Open generated PNG, verify both signal series visible with clear legend |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
