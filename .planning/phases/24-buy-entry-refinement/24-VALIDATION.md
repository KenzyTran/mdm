---
phase: 24
slug: buy-entry-refinement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_buy_entry.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_buy_entry.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | GAP-01 | unit | `uv run pytest tests/test_buy_entry.py::TestGapFilter -x` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 1 | GAP-01 | unit | `uv run pytest tests/test_buy_entry.py::TestGapFilter::test_bypass_ma50 -x` | ❌ W0 | ⬜ pending |
| 24-01-03 | 01 | 1 | RALLY-01 | unit | `uv run pytest tests/test_buy_entry.py::TestRallyThreshold -x` | ❌ W0 | ⬜ pending |
| 24-01-04 | 01 | 1 | RALLY-02 | unit | `uv run pytest tests/test_buy_entry.py::TestRallyThreshold::test_deep_correction -x` | ❌ W0 | ⬜ pending |
| 24-02-01 | 02 | 2 | GAP-02 | smoke | `uv run python analysis/validate_buy_entry.py` | ❌ W0 | ⬜ pending |
| 24-02-02 | 02 | 2 | RALLY-03 | smoke | `uv run python analysis/validate_buy_entry.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_buy_entry.py` — stubs for GAP-01, RALLY-01, RALLY-02
- [ ] `analysis/validate_buy_entry.py` — A/B validation script for GAP-02, RALLY-03

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
