---
phase: 11
slug: foundation-two-phase-commit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_hybrid_engine.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_hybrid_engine.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | HYB-01 | integration | `uv run pytest tests/test_hybrid_engine.py::test_hybrid_matches_v2_on_nasdaq -x` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | HYB-06 | unit | `uv run pytest tests/test_hybrid_engine.py::test_vetoed_ftd_does_not_reset_dd_counter -x` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | HYB-06 | unit | `uv run pytest tests/test_hybrid_engine.py::test_vetoed_ftd_does_not_reset_rally_tracker -x` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | HYB-06 | unit | `uv run pytest tests/test_hybrid_engine.py::test_snapshot_restore_isolation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hybrid_engine.py` — stubs for HYB-01 (regression) and HYB-06 (snapshot/restore, veto protection)
- [ ] `strategies/mdm_hybrid/__init__.py` — package must exist before tests can import

*Existing infrastructure covers pytest framework.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
