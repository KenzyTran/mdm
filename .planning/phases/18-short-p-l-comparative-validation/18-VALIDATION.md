---
phase: 18
slug: short-p-l-comparative-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — existing pytest config |
| **Quick run command** | `python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | SHORT-02 | unit | `python -m pytest tests/ -k "short_pnl or equity" -v` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | SHORT-02 | integration | `python -m pytest tests/ -k "manual_calc" -v` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | TRANS-02 | integration | `python scripts/compare_long_short.py --market nasdaq` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 2 | TRANS-02 | integration | `python scripts/compare_long_short.py --market vn30` | ❌ W0 | ⬜ pending |
| 18-02-03 | 02 | 2 | TRANS-03 | manual | review docs/rules_mdm_v2.md and docs/rules_mdm_hybrid.md | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_short_pnl.py` — stubs for SHORT-02 equity curve verification
- [ ] Test fixtures for known short trades with manual P&L calculations

*Existing infrastructure covers test framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rule docs completeness | TRANS-03 | Content review | Verify docs/rules_mdm_v2.md and docs/rules_mdm_hybrid.md have short signal, stop loss, and SELL->CASH->BUY sections |
| Chart visual quality | TRANS-02 | Visual inspection | Run comparison script, verify 2 equity curves visible on same plot |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
