---
phase: 14
slug: hybrid-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run python -m pytest tests/test_hybrid_engine.py -x -q` |
| **Full suite command** | `uv run python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~636 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_hybrid_engine.py -x -q`
- **After every plan wave:** Run `uv run python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | VAL-04 | integration | `uv run python -m pytest tests/test_hybrid_validation.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | VAL-04 | integration | `uv run python scripts/validate_hybrid.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hybrid_validation.py` — stubs for VAL-04 validation tests
- [ ] Existing test infrastructure covers framework needs

*Existing pytest infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Held-out set selection review | VAL-04 | Human judgment on signal selection fairness | Review held-out set composition for temporal bias |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
