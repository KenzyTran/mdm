---
phase: 2
slug: codebase-organization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ORG-04 | regression | `python -m pytest tests/test_regression.py -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | ORG-01 | structure | `python -c "import core; import strategies"` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | ORG-02 | regression | `python -m pytest tests/test_mdm_regression.py -v` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | ORG-03 | regression | `python -m pytest tests/test_vsa_regression.py -v` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | ORG-01 | import | `python -m pytest tests/test_no_cross_imports.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_regression.py` — regression test stubs for MDM and VSA signal/equity comparison
- [ ] `tests/test_mdm_regression.py` — MDM-specific regression tests
- [ ] `tests/test_vsa_regression.py` — VSA-specific regression tests
- [ ] `tests/test_no_cross_imports.py` — cross-import isolation checks
- [ ] `tests/conftest.py` — shared fixtures (data paths, baseline snapshots)
- [ ] `pytest` — install if not in dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Notebook imports work | ORG-02, ORG-03 | Jupyter kernel state | Open each notebook, run import cells, verify no errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
