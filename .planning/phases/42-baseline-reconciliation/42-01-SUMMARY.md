---
phase: 42-baseline-reconciliation
plan: 01
subsystem: analysis
tags: [git-bisect, cagr, drift-forensics, hybrid-engine, vn30, baseline-reconciliation]

# Dependency graph
requires:
  - phase: 41-ab-walk-forward-validation
    provides: analysis/validate_v9.py::compute_metrics (the canonical CAGR/SELL/MaxDD metric function reused by the bisect gate)
  - phase: 27-combined-v6-validation
    provides: output/v6_combined_validation.txt (the v6.0 shipped truth-of-record CAGR 11.5% that anchors the bisect good side)
  - phase: 38-atr-buffer-zone-module
    provides: MDMV2Config.atr_buffer_enabled feature gate (forced OFF in the bisect script to match v6.0-equivalent behavior)
  - phase: 39-refined-distribution-day-module
    provides: MDMV2Config.refined_dd_enabled feature gate (forced OFF in the bisect script to match v6.0-equivalent behavior)
provides:
  - analysis/bisect_v10_baseline.py — git-bisect-compatible CAGR gate runner (exit 0/1/125)
  - BISECT_RESULT stdout contract (cagr=<float>|NA sell=<int>|NA max_dd=<float>|NA, exactly one line per invocation)
  - Inline design-note documenting the bisect gate (11.4) vs D-09 parity band (11.2–11.8) distinction
  - D-04 skip-untestable path that correctly handles pre-Phase-11 commits lacking strategies.mdm_hybrid
affects: [42-03-run-bisect, 42-04-reconciliation-decision, baseline-drift-audit]

# Tech tracking
tech-stack:
  added: []  # Pure-Python script, no new dependencies
  patterns:
    - "Per-commit gate script: single file at analysis/ emits one machine-parseable stdout line, exit code encodes gate verdict, stderr carries forensic narrative"
    - "NA-invariant stdout contract: every invocation (success AND skip) emits exactly one parseable result line so downstream parsers can correlate with bisect's [<hash>] headers one-to-one even across consecutive SKIPs"
    - "Import-error fallback for git-bisect history traversal: dedicated try/except ImportError block handles pre-feature-introduction commits, returning exit 125 (skip-untestable)"
    - "sys.stdout.reconfigure(encoding='utf-8') replacing io.TextIOWrapper(sys.stdout.buffer) wrapping — safer on Windows when engine internals emit unicode"

key-files:
  created:
    - analysis/bisect_v10_baseline.py
  modified: []

key-decisions:
  - "CAGR-only gate (not SELL + MaxDD composite): per D-03, multi-metric gates can split a single drift across two commits; bisect converges fastest on the earliest drift with a single metric"
  - "Gate threshold 11.4% (tight) vs D-09 parity band 11.2–11.8% (wide): inline comment block explicitly documents the rationale — tight gate finds earliest drift, wide band is HEAD acceptance tolerance — do NOT widen the gate"
  - "Exit 125 for pre-Phase-11 ImportError: fallback to legacy models/ path was explicitly rejected per D-04; skip-untestable is the correct bisect semantic for history before strategies/mdm_hybrid existed"
  - "sys.stdout.reconfigure() over io.TextIOWrapper(sys.stdout.buffer) wrapping: wrapper pattern (inherited from validate_v9.py:41-42) triggered 'I/O operation on closed file' on Windows mid-engine-run; reconfigure() is the documented safe encoding-change path for an already-open stream"

patterns-established:
  - "BISECT_RESULT stdout contract: `^BISECT_RESULT: cagr=(<float>|NA) sell=(<int>|NA) max_dd=(<float>|NA)$` — one line per invocation, NA-valued on skip path, parseable by downstream plan 42-03 grep/awk"
  - "Forensic stderr log: BISECT_HEAD: <short-hash> at <ISO-timestamp> printed to stderr for every invocation, so `git bisect log` readers can cross-reference SKIP entries against wall-clock and git-HEAD"
  - "Dual-layer exception handling: (1) outer import try/except for pre-feature commits, (2) inner runtime try/except for data/engine failures — both paths emit the NA stdout line to preserve the one-line invariant"

requirements-completed: [BASE-01]

# Metrics
duration: 3min
completed: 2026-04-21
---

# Phase 42 Plan 01: Bisect Runner Scaffold Summary

**Git-bisect-compatible CAGR gate (`analysis/bisect_v10_baseline.py`) that reuses `analysis.validate_v9.compute_metrics`, exits 0/1/125 on v6.0-equivalent HybridEngine runs against VN30 2015-2026, and emits exactly one parseable BISECT_RESULT line per invocation including the skip path.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-21T10:19:26Z
- **Completed:** 2026-04-21T10:22:36Z
- **Tasks:** 1 / 1
- **Files modified:** 1 (created: `analysis/bisect_v10_baseline.py`)

## Accomplishments

- Created `analysis/bisect_v10_baseline.py` — a 181-line, zero-arg, deterministic CAGR gate for `git bisect run`, wiring VN30 DataLoader → build_indicator_dataframe → HybridEngine(v6.0-equivalent preset) → compute_metrics.
- Encoded the D-03 / D-09 gate-vs-parity-band distinction as an inline comment block in the source (11.4 tight gate finds earliest drift; 11.2–11.8 wide band is HEAD acceptance tolerance) so future reviewers reading the script understand why the gate number is asymmetric with the band.
- Implemented the NA-invariant stdout contract: every invocation — success, import-error skip, or runtime-error skip — emits exactly one `BISECT_RESULT: cagr=... sell=... max_dd=...` line, so plan 42-03's per-commit parser can correlate with bisect's `[<hash>]` headers without off-by-one errors across consecutive SKIPs.
- Verified at HEAD: script runs in ~8 seconds, prints `BISECT_RESULT: cagr=10.7000 sell=105 max_dd=-28.6300` to stdout, exits code 1 (below 11.4 gate — exactly matching the measured drift reported in `output/v9_ab_comparison.txt` lines 22: baseline +213.4% / CAGR 10.70% / MaxDD -28.63% / 105 SELL).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create analysis/bisect_v10_baseline.py** — `c857a8e` (feat)

## Files Created/Modified

- `analysis/bisect_v10_baseline.py` (new, 181 lines) — Standalone git-bisect-compatible CAGR gate script. Loads VN30 via `DataLoader('vn30').load('2015-01-05', '2026-03-31')`, builds indicators, runs `HybridEngine(HybridConfig(v2_config=replace(VN30_PRESET, atr_buffer_enabled=False, refined_dd_enabled=False), two_phase_enabled=True, filter_enabled=False))`, computes metrics via `analysis.validate_v9.compute_metrics`, emits one `BISECT_RESULT:` stdout line, exits 0 if CAGR ≥ 11.4 else 1, exits 125 on ImportError or any other uncaught exception. Forensic `BISECT_HEAD:` line + tracebacks go to stderr.

## Decisions Made

All binding decisions were already fixed in the plan and 42-CONTEXT.md (D-01, D-03, D-04, D-09, D-10). Executor made one small implementation decision outside the plan's explicit direction:

- **Stdout encoding mechanism:** Plan suggested mirroring `validate_v9.py:41-42`'s `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` wrapping. Testing revealed this breaks on Windows when engine internals print during processing — `ValueError: I/O operation on closed file` interrupts the BISECT_RESULT print. Switched to `sys.stdout.reconfigure(encoding='utf-8')` (Python 3.7+, documented safe way to change encoding on an already-open stream, pyproject.toml requires >= 3.10 so always available). Kept the TextIOWrapper branch as a Python < 3.7 fallback, guarded by `hasattr(sys.stdout, 'reconfigure')`. Functionally equivalent for UTF-8 stdout; more robust on Windows.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced `io.TextIOWrapper(sys.stdout.buffer)` wrapping with `sys.stdout.reconfigure()`**
- **Found during:** Task 1 (Create analysis/bisect_v10_baseline.py) — end-to-end verification run
- **Issue:** The plan's step-2 instruction to mirror `validate_v9.py:41-42` stdout-wrapping pattern (`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`) reproducibly crashed mid-engine-run on Windows with `ValueError: I/O operation on closed file` during the final `print("BISECT_RESULT: ...")` statement. Root cause: HybridEngine internals print diagnostic lines, the fresh TextIOWrapper does not hold a strong reference to the original stream, and stdout-buffer lifetime becomes non-deterministic under Python's GC on Windows. The BISECT_RESULT line is the core output — losing it means every bisect invocation would SKIP, making the entire BASE-01 evidence producer useless.
- **Fix:** Replaced the wrapper assignment with `sys.stdout.reconfigure(encoding='utf-8')` (Python 3.7+) guarded by `hasattr(sys.stdout, 'reconfigure')` with a TextIOWrapper fallback for older Pythons. This is the documented safe way to change encoding on an already-open stream without creating a second wrapper whose lifetime Python can collect. pyproject.toml requires Python ≥ 3.10, so the reconfigure() branch always fires in practice.
- **Files modified:** `analysis/bisect_v10_baseline.py` (lines 26-40)
- **Verification:** Re-ran `uv run python analysis/bisect_v10_baseline.py` — now emits exactly one `BISECT_RESULT: cagr=10.7000 sell=105 max_dd=-28.6300` line to stdout, exits 1. Plan's automated verify block (`grep -cE "^BISECT_RESULT: "` returns 1, exit code check returns 1, inline design-note check, NA-path check) prints `PASS: bisect script exits 1 at HEAD, emits exactly 1 BISECT_RESULT line, design-note present, NA-path present`.
- **Committed in:** `c857a8e` (Task 1 commit — the fix was part of getting the script working; no separate fix-up commit needed).

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The auto-fix was necessary for correctness (without it the script cannot emit its contract line and would SKIP every bisect iteration). No scope creep — the fix is a drop-in replacement for the stdout-encoding line. Plan intent (UTF-8 stdout, one BISECT_RESULT line per invocation) fully preserved.

## Issues Encountered

- **Windows stdout-wrapping fragility:** See deviation #1 above. Flagged for awareness — if other Phase 42 plans copy the `io.TextIOWrapper(sys.stdout.buffer, ...)` idiom from `validate_v9.py`, they should consider the `sys.stdout.reconfigure()` alternative to avoid the same failure mode.

## User Setup Required

None — script has no external service or credential dependencies. Runs with only the existing repo + `uv run python` environment.

## Next Phase Readiness

**Ready for plan 42-03 (Wave 2 bisect run):**
- `analysis/bisect_v10_baseline.py` is the BASE-01 evidence producer. Plan 42-03 invokes it via `git bisect run uv run python analysis/bisect_v10_baseline.py` across ~253 commits from v6.0 ship → HEAD.
- BISECT_RESULT stdout contract is grep-parseable: `^BISECT_RESULT: cagr=(\d+\.\d+|NA) sell=(\d+|NA) max_dd=(-?\d+\.\d+|NA)$`. Plan 42-03 can pair each commit's `[<hash>]` bisect-header line with the next BISECT_RESULT line without off-by-one risk across SKIPs.
- Measured-today anchor (HEAD) confirmed: CAGR 10.7000 exits code 1 (bad). Shipped v6.0 anchor (CAGR 11.5%) is above the 11.4 gate → code 0 (good) by construction. Bisect has a well-posed good/bad bracket.

**Concerns passed forward:**
- If an old commit has a _different_ `VN30_PRESET` (e.g., fail_safe_enabled was False, or different threshold constants), the bisect script will still run it with its contemporaneous preset — this is correct, because we are hunting the drift, not force-normalizing it. Plan 42-03 reviewers should remember this when interpreting bisect log rows.
- Stdout encoding hiccup (deviation #1) was Windows-specific — if plan 42-03 runs on a Linux/CI box the original wrapper would have worked. Kept the reconfigure() path for cross-platform safety.

## Self-Check: PASSED

Artifact and commit existence verified:
- FOUND: `analysis/bisect_v10_baseline.py` (181 lines, > 60-line min from plan)
- FOUND: commit `c857a8e` in `git log --oneline --all`

Runtime behavior verified at HEAD:
- Exit code: 1 (expected — CAGR 10.70 < 11.4 gate)
- Exactly 1 `BISECT_RESULT` line on stdout (NA-invariant preserved)
- Stdout line parseable by plan 42-03 regex: `BISECT_RESULT: cagr=10.7000 sell=105 max_dd=-28.6300`
- Plan's full automated verify block: `PASS: bisect script exits 1 at HEAD, emits exactly 1 BISECT_RESULT line, design-note present, NA-path present`

---
*Phase: 42-baseline-reconciliation*
*Completed: 2026-04-21*
