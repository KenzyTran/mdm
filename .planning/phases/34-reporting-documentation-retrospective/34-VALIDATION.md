---
phase: 34
slug: reporting-documentation-retrospective
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run pytest tests/phase34/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/phase34/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 34-01-01 | 01 | 1 | BT-05, BT-06, BT-07 | unit | `uv run pytest tests/phase34/test_report.py -x -q` | ❌ W0 | ⬜ pending |
| 34-02-01 | 02 | 1 | DOC-01 | smoke | `uv run pytest tests/phase34/test_docs.py::test_rules_doc_current -x` | ❌ W0 | ⬜ pending |
| 34-02-02 | 02 | 1 | DOC-02 | smoke | `uv run pytest tests/phase34/test_docs.py::test_data_dict_exists -x` | ❌ W0 | ⬜ pending |
| 34-02-03 | 02 | 1 | SC-7 | smoke | `grep -c "v7.0" .planning/STATE.md && grep -c "v7.0" .planning/MILESTONES.md` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase34/__init__.py` — package init (created by Plan 01 Task 1 or Plan 02 Task 2)
- [ ] `tests/phase34/test_report.py` — stubs for BT-05, BT-06, BT-07
- [ ] `tests/phase34/test_docs.py` — stubs for DOC-01, DOC-02

*Note: Wave 0 test stubs are TDD-first — written before implementation in Task 1 of Plan 01.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Report is readable and accurate | BT-05/BT-06/BT-07 | Human review of generated markdown report | Open `docs/audits/phase34/v7_report.md` and verify metrics match Phase 33 OOS results |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
