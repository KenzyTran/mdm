---
phase: 13
slug: hybrid-engine-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | HYB-03 | unit | `uv run pytest tests/test_hybrid_engine.py -k "test_pipeline"` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | HYB-03 | unit | `uv run pytest tests/test_hybrid_engine.py -k "test_confirm_mode"` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | HYB-04 | unit | `uv run pytest tests/test_hybrid_engine.py -k "test_override"` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 1 | HYB-05 | unit | `uv run pytest tests/test_hybrid_engine.py -k "test_cash_insert"` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | HYB-03 | integration | `uv run pytest tests/test_hybrid_engine.py -k "test_backtest_e2e"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hybrid_engine.py` — stubs for HYB-03, HYB-04, HYB-05
- [ ] Fixtures for sample NASDAQ OHLCV data with indicator columns

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Signal log CSV readability | HYB-03 | Visual inspection of output format | Open output CSV, verify columns match v2 signal format |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
