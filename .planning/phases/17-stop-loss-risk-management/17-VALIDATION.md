---
phase: 17
slug: stop-loss-risk-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_stop_loss.py -x -q` |
| **Full suite command** | `uv run pytest tests/test_stop_loss.py tests/test_short_position.py tests/test_hybrid_engine.py -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_stop_loss.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/test_stop_loss.py tests/test_short_position.py tests/test_hybrid_engine.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | RISK-01 | unit | `uv run pytest tests/test_stop_loss.py -k "long_default"` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | RISK-02 | unit | `uv run pytest tests/test_stop_loss.py -k "atr_adaptive"` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 2 | SHORT-03 | unit | `uv run pytest tests/test_stop_loss.py -k "short_dd5"` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 2 | RISK-03 | integration | `uv run pytest tests/test_stop_loss.py -k "backtest_volatile"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_stop_loss.py` — stubs for RISK-01, RISK-02, RISK-03, SHORT-03
- [ ] Test fixtures for ATR data and DD5 high scenarios

*Existing test infrastructure (pytest, conftest) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Volatile period spot-check | RISK-03 | Requires visual inspection of known market events | Run backtest, compare stop loss triggers at 2008 crash, 2020 COVID, 2022 bear market |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
