---
phase: 31
slug: multi-stock-portfolio-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/strategies/portfolio -x -q` |
| **Full suite command** | `uv run pytest tests/strategies/portfolio` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command (subset for touched file)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | GATE-01..04, PORT-01..10 | unit | `uv run pytest tests/strategies/portfolio` | ❌ W0 | ⬜ pending |

*Planner to fill in per-task rows. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/strategies/portfolio/conftest.py` — shared fixtures (VN30 toy universe, fake Fills, fake stock_rs)
- [ ] `tests/strategies/portfolio/test_state_no_lookahead.py` — SC8 state[i-1] regression (MANDATORY — 707% bug)
- [ ] `tests/strategies/portfolio/test_microstructure.py` — T+2.5 settlement, 7% limit, tick rounding stubs
- [ ] `tests/strategies/portfolio/test_costs.py` — fee/tax/slippage stubs
- [ ] `tests/strategies/portfolio/test_cooldown.py` — cooldown after exit stubs
- [ ] `tests/strategies/portfolio/test_exits.py` — stop / trail / time-stop chain stubs
- [ ] `tests/strategies/portfolio/test_rs_reader.py` — stock_rs schema contract (after spike)
- [ ] `tests/strategies/portfolio/test_engine_integration.py` — end-to-end VN30 toy backtest stub
- [ ] `stock_rs` schema spike — confirm columns via `\d stock_rs` before writing reader

*Planner must expand to all PORT-* requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live VN100 audit report sanity | PORT-10 | Human eyeball of equity curve vs HybridEngine baseline | Open audit report, compare CAGR/DD vs last known HybridEngine run |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
