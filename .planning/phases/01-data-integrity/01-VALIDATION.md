---
phase: 1
slug: data-integrity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
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
| 01-01-01 | 01 | 1 | DATA-01 | unit | `python -m pytest tests/test_loader.py -k unified` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | DATA-02 | unit | `python -m pytest tests/test_loader.py -k normalize` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | DATA-03 | unit | `python -m pytest tests/test_fixtures.py -k signal` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | DATA-04 | integration | `python -m pytest tests/test_calculations.py -k percentage` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures and sample data paths
- [ ] `tests/test_loader.py` — stubs for DATA-01, DATA-02
- [ ] `tests/test_fixtures.py` — stubs for DATA-03
- [ ] `tests/test_calculations.py` — stubs for DATA-04
- [ ] `pip install pytest` — no test framework currently installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spot-check US prices against known values | DATA-02 | Requires external reference data lookup | Compare normalized close on 2020-01-02 against known NASDAQ close of ~9092.19 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
