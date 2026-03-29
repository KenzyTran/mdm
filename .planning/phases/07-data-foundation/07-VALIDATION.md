---
phase: 7
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs if needed |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | DATA-05 | unit | `python -m pytest tests/test_data_loader.py -x -q` | ⬜ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | DATA-05 | unit | `python -m pytest tests/test_data_loader.py -x -q` | ⬜ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | DATA-06 | unit | `python -m pytest tests/test_signal_loader.py -x -q` | ⬜ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | DATA-06 | unit | `python -m pytest tests/test_signal_loader.py -x -q` | ⬜ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | DATA-05, DATA-06 | integration | `python -m pytest tests/test_date_alignment.py -x -q` | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_data_loader.py` — stubs for DATA-05 (extended spot-checks, full 1974+ loading)
- [ ] `tests/test_signal_loader.py` — stubs for DATA-06 (962-signal parsing, dollar_becomes column)
- [ ] `tests/test_date_alignment.py` — stubs for signal-to-OHLCV date alignment gap report
- [ ] `tests/conftest.py` — shared fixtures (sample OHLCV rows, sample signal rows)
- [ ] pytest install — if not already in environment

*Existing infrastructure may partially cover — verify during Wave 0.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spot-check values match real NASDAQ history | DATA-05 | External source verification | Compare 1974/2000/2008 close prices against Yahoo Finance or similar |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
