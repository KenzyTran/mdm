---
phase: 23
slug: fail-safe-mechanism
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_fail_safe.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_fail_safe.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | SAFE-01 | unit | `uv run pytest tests/test_fail_safe.py::test_sell_records_threshold -x` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | SAFE-01 | unit | `uv run pytest tests/test_fail_safe.py::test_threshold_is_prev_day_high -x` | ❌ W0 | ⬜ pending |
| 23-01-03 | 01 | 1 | SAFE-02 | unit | `uv run pytest tests/test_fail_safe.py::test_fail_safe_triggers_cash -x` | ❌ W0 | ⬜ pending |
| 23-01-04 | 01 | 1 | SAFE-02 | unit | `uv run pytest tests/test_fail_safe.py::test_no_trigger_below_threshold -x` | ❌ W0 | ⬜ pending |
| 23-01-05 | 01 | 1 | SAFE-02 | unit | `uv run pytest tests/test_fail_safe.py::test_fail_safe_trade_annotation -x` | ❌ W0 | ⬜ pending |
| 23-01-06 | 01 | 1 | SAFE-02 | unit | `uv run pytest tests/test_fail_safe.py::test_disabled_no_trigger -x` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 2 | SAFE-03 | integration | `uv run python analysis/validate_fail_safe.py` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 2 | SC-4 | integration | `uv run python analysis/validate_fail_safe.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_fail_safe.py` — stubs for SAFE-01, SAFE-02
- [ ] `analysis/validate_fail_safe.py` — covers SAFE-03, SC-4

*Existing infrastructure covers test framework setup.*

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
