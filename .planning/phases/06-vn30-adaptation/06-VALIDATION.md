---
phase: 6
slug: vn30-adaptation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0.2 (via uv dev-dependencies) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_vn30_filters.py tests/test_vn30_sweep.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_vn30_filters.py tests/test_vn30_sweep.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | VN30-01 | unit | `uv run pytest tests/test_vn30_filters.py::test_limit_day_detection -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | VN30-01 | unit | `uv run pytest tests/test_vn30_filters.py::test_expiry_day_computation -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | VN30-01 | unit | `uv run pytest tests/test_vn30_filters.py::test_dd_suppression_on_expiry -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | VN30-02 | unit | `uv run pytest tests/test_vn30_sweep.py::test_scoring_fn_abstraction -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | VN30-02 | integration | `uv run pytest tests/test_vn30_sweep.py::test_sharpe_sweep_runs -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | VN30-03 | integration | `uv run pytest tests/test_vn30_sweep.py::test_backtest_report_metrics -x` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | VN30-03 | integration | `uv run pytest tests/test_vn30_sweep.py::test_buy_and_hold_comparison -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vn30_filters.py` — stubs for VN30-01 (limit day, expiry day, DD suppression)
- [ ] `tests/test_vn30_sweep.py` — stubs for VN30-02, VN30-03 (Sharpe sweep, backtest report)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard chart visual quality | VN30-03 | Chart rendering is visual | Open generated PNG, verify VN30 price + equity curve + drawdown subplot |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
