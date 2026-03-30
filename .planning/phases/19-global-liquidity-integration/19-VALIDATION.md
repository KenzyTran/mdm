---
phase: 19
slug: global-liquidity-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | None (default discovery) |
| **Quick run command** | `uv run pytest tests/test_liquidity.py tests/test_qe_floor.py -x -v` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_liquidity.py tests/test_qe_floor.py -x -v`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | LIQ-01 | unit | `uv run pytest tests/test_liquidity.py -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | LIQ-01 | unit | `uv run pytest tests/test_liquidity.py::test_pre2007_nan_handling -x` | ❌ W0 | ⬜ pending |
| 19-02-01 | 02 | 2 | LIQ-02 | integration | `uv run pytest tests/test_qe_floor.py::test_sell_suppressed_during_qe -x` | ❌ W0 | ⬜ pending |
| 19-02-02 | 02 | 2 | LIQ-02 | integration | `uv run pytest tests/test_qe_floor.py::test_other_transitions_unaffected -x` | ❌ W0 | ⬜ pending |
| 19-03-01 | 03 | 2 | LIQ-03 | regression | `uv run pytest tests/test_qe_floor.py::test_baseline_regression -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_liquidity.py` — stubs for LIQ-01 (loader, merge, lag, NaN handling)
- [ ] `tests/test_qe_floor.py` — stubs for LIQ-02 (SELL suppression), LIQ-03 (regression baseline)

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
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
