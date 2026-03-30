---
phase: 16
slug: short-position-state-transitions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_short_position.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_short_position.py -x`
- **After every plan wave:** Run `uv run pytest tests/test_hybrid_engine.py tests/test_short_position.py -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | SHORT-01 | unit | `uv run pytest tests/test_short_position.py::test_enter_sell_records_short_fields -x` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | SHORT-01 | unit | `uv run pytest tests/test_short_position.py::test_short_mode_config -x` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 1 | SHORT-04 | unit | `uv run pytest tests/test_short_position.py::test_ftd_covers_short -x` | ❌ W0 | ⬜ pending |
| 16-01-04 | 01 | 1 | SHORT-04 | unit | `uv run pytest tests/test_short_position.py::test_ma50_covers_short -x` | ❌ W0 | ⬜ pending |
| 16-01-05 | 01 | 1 | SHORT-04 | unit | `uv run pytest tests/test_short_position.py::test_indicator_override_covers_short -x` | ❌ W0 | ⬜ pending |
| 16-01-06 | 01 | 1 | SHORT-04 | unit | `uv run pytest tests/test_short_position.py::test_short_pnl_calculation -x` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | TRANS-01 | unit | `uv run pytest tests/test_short_position.py::test_enter_buy_guard -x` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 1 | TRANS-01 | integration | `uv run pytest tests/test_short_position.py::test_sell_cash_buy_transition -x` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 1 | TRANS-01 | integration | `uv run pytest tests/test_short_position.py::test_nasdaq_no_sell_to_buy -x` | ❌ W0 | ⬜ pending |
| 16-REG | - | - | - | regression | `uv run pytest tests/test_hybrid_engine.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_short_position.py` — stubs for SHORT-01, SHORT-04, TRANS-01

*Existing infrastructure covers regression requirements.*

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
