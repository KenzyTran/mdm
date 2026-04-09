---
phase: 32
slug: vn100-backtest-in-sample-sweep
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (none — Wave 0 adds tests/ if missing) |
| **Quick run command** | `uv run pytest tests/phase32 -x -q` |
| **Full suite command** | `uv run pytest tests/phase32` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/phase32 -x -q`
- **After every plan wave:** Run `uv run pytest tests/phase32`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 32-00-01 | 00 | 0 | BT-01 | unit | `uv run pytest tests/phase32/test_scaffold.py` | ❌ W0 | ⬜ pending |
| 32-01-xx | 01 | 1 | BT-01 | unit | `uv run pytest tests/phase32/test_pipeline.py` | ❌ W0 | ⬜ pending |
| 32-02-xx | 02 | 2 | BT-02 | unit | `uv run pytest tests/phase32/test_sweep.py` | ❌ W0 | ⬜ pending |
| 32-03-xx | 03 | 3 | BT-02 | unit | `uv run pytest tests/phase32/test_top3.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase32/__init__.py`
- [ ] `tests/phase32/conftest.py` — shared fixtures (tiny synthetic OHLC + universe)
- [ ] `tests/phase32/test_scaffold.py` — env check (pyarrow, tqdm, multiprocessing)
- [ ] Verify `pyarrow` and `tqdm` available (add to pyproject.toml if missing)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Top-3 equity curve PNGs visual sanity | BT-02 | Chart aesthetics | Open `docs/audits/phase32/top3_equity.png`, confirm no gaps/spikes |
| Full 1,536-config sweep runtime | BT-02 | Long-running (>minutes) | Run `python analysis/sweep_vn100_2014_2018.py`; confirm completes and writes `sweep_results.parquet` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
