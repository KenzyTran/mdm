---
phase: 4
slug: mdm-v2-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/test_mdm_v2.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_mdm_v2.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | MDM-01 | unit | `python -m pytest tests/test_mdm_v2.py::test_state_machine -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | MDM-02 | unit | `python -m pytest tests/test_mdm_v2.py::test_config -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | MDM-03 | integration | `python -m pytest tests/test_hypothesis.py -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | MDM-04 | integration | `python -m pytest tests/test_sweep.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mdm_v2.py` — stubs for MDM-01, MDM-02 (state machine, config)
- [ ] `tests/test_hypothesis.py` — stubs for MDM-03 (hypothesis framework)
- [ ] `tests/test_sweep.py` — stubs for MDM-04 (parameter sweep)
- [ ] `tests/conftest.py` — shared fixtures (training data, signal fixtures)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Match rate improvement | MDM-04 | Depends on actual signal data quality | Run sweep, verify top config beats classic baseline |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
