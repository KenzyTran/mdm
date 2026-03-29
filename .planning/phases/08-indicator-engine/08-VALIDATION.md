---
phase: 8
slug: indicator-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_indicators_v2.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_indicators_v2.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | IND-01 | unit | `python -m pytest tests/test_indicators_v2.py::test_ema -x -q` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | IND-02 | unit | `python -m pytest tests/test_indicators_v2.py::test_macd -x -q` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | IND-03 | unit | `python -m pytest tests/test_indicators_v2.py::test_heikin_ashi -x -q` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | IND-04 | integration | `python -m pytest tests/test_feature_snapshot.py -x -q` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | IND-05 | integration | `python -m pytest tests/test_feature_snapshot.py::test_no_nan -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_indicators_v2.py` — stubs for IND-01, IND-02, IND-03
- [ ] `tests/test_feature_snapshot.py` — stubs for IND-04, IND-05
- [ ] pytest already installed — no framework install needed

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Heikin Ashi Smoothed visual smoothing | IND-03 | Visual inspection of candle chart | Generate HA Smoothed chart, verify candles are visibly smoother than standard HA |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
