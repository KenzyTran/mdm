---
phase: 20
slug: sell-acceleration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual backtest validation (no pytest in project) |
| **Config file** | None — project uses script-based validation |
| **Quick run command** | `uv run python analysis/validate_sell_acceleration.py` |
| **Full suite command** | `uv run python analysis/validate_sell_acceleration.py` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Manual smoke test: run engine with acceleration enabled, verify SELL signals change
- **After every plan wave:** `uv run python analysis/validate_sell_acceleration.py`
- **Before `/gsd:verify-work`:** Full validation script must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | SELL-01 | integration | `uv run python analysis/validate_sell_acceleration.py` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | SELL-02 | integration | `uv run python analysis/validate_sell_acceleration.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `analysis/validate_sell_acceleration.py` — covers SELL-01, SELL-02 (A/B comparison, delay/drawdown thresholds)
- [ ] `strategies/mdm_v2/sell_acceleration.py` — the module itself (tested implicitly by validation script)

*Existing infrastructure covers test framework — no new framework installation needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Parameter tuning | SELL-01 | Requires human judgment on optimal thresholds | Review backtest output for ROC/DD clustering defaults |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
