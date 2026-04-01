---
phase: 26
slug: banding-volatility-filter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | tests/conftest.py |
| **Quick run command** | `uv run pytest tests/test_volatility_filter.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_volatility_filter.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | BAND-01 | unit | `uv run pytest tests/test_volatility_filter.py::test_atr_computation -x` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | BAND-01 | unit | `uv run pytest tests/test_volatility_filter.py::test_regime_classification -x` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 1 | BAND-02 | unit | `uv run pytest tests/test_volatility_filter.py::test_signal_suppression -x` | ❌ W0 | ⬜ pending |
| 26-02-02 | 02 | 1 | BAND-02 | unit | `uv run pytest tests/test_volatility_filter.py::test_protective_exits_not_suppressed -x` | ❌ W0 | ⬜ pending |
| 26-03-01 | 03 | 2 | BAND-03 | integration | `uv run python analysis/validate_volatility_filter.py` | ❌ W0 | ⬜ pending |
| 26-03-02 | 03 | 2 | BAND-03 | integration | `uv run python analysis/validate_volatility_filter.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_volatility_filter.py` — stubs for BAND-01, BAND-02
- [ ] `analysis/validate_volatility_filter.py` — A/B backtest validation for BAND-03
- [ ] No framework install needed (pytest already in project)

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 2020 crash exit timing unchanged | BAND-03 | Requires visual signal timeline comparison | Run A/B validation script, compare 2020 Feb-Apr signal dates between baseline and filtered |
| 2021 rally entry timing unchanged | BAND-03 | Requires visual signal timeline comparison | Run A/B validation script, compare 2021 Jan-Jun signal dates between baseline and filtered |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
