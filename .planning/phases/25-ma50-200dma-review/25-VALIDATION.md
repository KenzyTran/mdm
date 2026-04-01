---
phase: 25
slug: ma50-200dma-review
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `tests/conftest.py` (path setup only) |
| **Quick run command** | `uv run pytest tests/test_ma50_review.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_ma50_review.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 0 | MAREVIEW-01, MAREVIEW-02 | unit | `uv run pytest tests/test_ma50_review.py -x -q` | ❌ W0 | ⬜ pending |
| 25-02-01 | 02 | 1 | — | unit | `uv run pytest tests/test_ma50_review.py::test_sma200_indicator -x` | ❌ W0 | ⬜ pending |
| 25-02-02 | 02 | 1 | — | unit | `uv run pytest tests/test_ma50_review.py::test_breakout_gated -x` | ❌ W0 | ⬜ pending |
| 25-02-03 | 02 | 1 | MAREVIEW-01 | unit | `uv run pytest tests/test_ma50_review.py::test_no_sell_differs_from_baseline -x` | ❌ W0 | ⬜ pending |
| 25-02-04 | 02 | 1 | MAREVIEW-02 | unit | `uv run pytest tests/test_ma50_review.py::test_no_filter_differs_from_baseline -x` | ❌ W0 | ⬜ pending |
| 25-02-05 | 02 | 1 | — | unit | `uv run pytest tests/test_ma50_review.py::test_200dma_replacement -x` | ❌ W0 | ⬜ pending |
| 25-03-01 | 03 | 2 | MAREVIEW-03 | smoke | `uv run python analysis/validate_ma50_review.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ma50_review.py` — stubs for MAREVIEW-01, MAREVIEW-02, MAREVIEW-03, sma200, breakout gate, 200dma replacement
- Framework install: None needed (pytest 9.0.2 already available)

*Existing infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Report recommends keep/remove/replace with quantitative evidence | MAREVIEW-03 | Human judgment on report quality | Read `analysis/validate_ma50_review.py` output; verify table shows all 5 scenarios with return, DD, Sharpe, win rate; verify recommendation section exists with one of three actions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
