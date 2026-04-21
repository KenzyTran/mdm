#!/usr/bin/env python
"""Phase 42 BASE-01 — git-bisect-compatible CAGR gate.

Exit codes (per git-bisect semantics):
  0   — CAGR >= CAGR_GATE (commit is "good", i.e. above the drift threshold)
  1   — CAGR <  CAGR_GATE (commit is "bad", i.e. drifted baseline)
  125 — Untestable: ImportError, data-load failure, or any uncaught exception
        (git-bisect marks the commit as "skip"). See D-04 of 42-CONTEXT.md —
        pre-Phase-11 commits predate `strategies/mdm_hybrid/` and must skip.

Usage:
    # Drive a bisect run with this script as the per-commit gate:
    git bisect start
    git bisect bad  HEAD
    git bisect good <v6.0-ship-hash>
    git bisect run uv run python analysis/bisect_v10_baseline.py

    # Or invoke directly to probe a single commit:
    uv run python analysis/bisect_v10_baseline.py; echo $?

Design references (binding for this script):
  - D-01 (42-CONTEXT.md): git-bisect is the audit methodology for BASE-01
  - D-03 (42-CONTEXT.md): CAGR is the SOLE gate metric (not SELL or MaxDD)
  - D-04 (42-CONTEXT.md): Exit 125 on untestable commits (skip-untestable path)
  - D-10 (42-CONTEXT.md): Data window is 2015-01-05 → 2026-03-31 (truth-of-record)

Every invocation (success AND skip) emits EXACTLY ONE stdout line matching:
    ^BISECT_RESULT: cagr=(\\d+\\.\\d+|NA) sell=(\\d+|NA) max_dd=(-?\\d+\\.\\d+|NA)$

Plan 42-03 parses this line per-commit; the NA-invariant guarantees one-to-one
correlation between bisect's `[<hash>]` header lines and BISECT_RESULT lines,
even across consecutive SKIPs.
"""

import io
import os
import sys

# stdout UTF-8 reconfiguration + repo-root on sys.path.
# Use reconfigure() (Python 3.7+) instead of wrapping sys.stdout.buffer with a
# fresh TextIOWrapper — the wrapper pattern (from validate_v9.py:41-42) breaks
# on Windows when downstream imports/engine code hold references to the
# original sys.stdout and the GC closes the buffer mid-run. reconfigure() is
# the documented safe way to change encoding on the already-open stream.
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        # Non-fatal — fall back to default encoding. Forensic continuity is
        # more important than a clean UTF-8 stream at this layer.
        pass
else:
    # Python < 3.7 (shouldn't hit this path — pyproject.toml requires >= 3.10)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ── Module constants ────────────────────────────────────────────────────────
DATA_START = '2015-01-05'   # v6.0 shipped window start (D-10)
DATA_END = '2026-03-31'     # v6.0 shipped window end (D-10)

# -----------------------------------------------------------------------------
# CAGR_GATE design note (D-03 vs D-09 — both bind, they serve different jobs):
#   - CAGR_GATE = 11.4 is INTENTIONALLY TIGHTER than the D-09 parity acceptance
#     band (11.2–11.8, i.e. ±0.3pp of 11.5). The gate's job is to find the
#     EARLIEST drift commit via git bisect; the parity band is the ACCEPTANCE
#     tolerance at HEAD after fix-forward.
#   - A bisect hit inside [11.2, 11.4] means: "an earliest drift commit was
#     found, but HEAD may already be inside the D-09 parity band" — this is a
#     sub-spec drift finding, worth documenting but not necessarily a fix-
#     forward target. Plan 42-04 handles this case via the `accepted_drift`
#     label (optionally annotated "sub-spec drift").
#   - Do NOT widen the gate to the parity band; doing so would make bisect
#     miss the earliest drift.
# -----------------------------------------------------------------------------
CAGR_GATE = 11.4       # D-03: tight bisect gate — finds earliest drift
EXIT_GOOD = 0
EXIT_BAD = 1
EXIT_SKIP = 125        # git bisect "untestable, skip"

NA_LINE = "BISECT_RESULT: cagr=NA sell=NA max_dd=NA"


def _emit_na_and_skip(reason: str) -> int:
    """Emit the NA-valued BISECT_RESULT line (stdout) + a human reason (stderr),
    then return EXIT_SKIP. Preserves the one-line-per-invocation invariant
    that plan 42-03's parser relies on.
    """
    print(NA_LINE)
    print(f"BISECT_SKIP: {reason}", file=sys.stderr)
    return EXIT_SKIP


def main() -> int:
    import traceback
    from datetime import datetime, timezone
    import subprocess

    # Forensic header — a future reviewer reading a `git bisect log` with SKIPs
    # needs to see which commit + wall-clock this invocation corresponds to.
    try:
        head_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL,
        ).decode('ascii', errors='replace').strip()
    except Exception:
        head_hash = 'unknown'
    start_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"BISECT_HEAD: {head_hash} at {start_iso}", file=sys.stderr)

    # -------------------------------------------------------------------------
    # D-04 import-error fallback: strategies.mdm_hybrid did not exist before
    # Phase 11 (see 42-CONTEXT.md). On older commits this import will fail;
    # we must emit the NA line + return EXIT_SKIP so bisect marks it untestable.
    # We do NOT fall back to the legacy models/ path — D-04 explicitly accepts
    # skip-untestable as the correct behavior for pre-Phase-11 history.
    # -------------------------------------------------------------------------
    try:
        from dataclasses import replace
        from core.data_loader import DataLoader
        from core.indicators import build_indicator_dataframe
        from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
        from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET
        from analysis.validate_v9 import compute_metrics
    except ImportError as exc:
        return _emit_na_and_skip(
            f"import failed at commit {head_hash}: {type(exc).__name__}: {exc} "
            f"(pre-Phase-11 commits lack strategies.mdm_hybrid — D-04)"
        )

    # -------------------------------------------------------------------------
    # Outer try/except: any other failure (data file missing, engine crash,
    # metric NaN, etc.) also emits the NA line so plan 42-03's per-commit
    # parser sees exactly one BISECT_RESULT line. Traceback goes to stderr
    # for forensic debuggability (Phase 40 D-10 fail-loud convention).
    # -------------------------------------------------------------------------
    try:
        # D-04: v6.0-equivalent preset. VN30_PRESET already has atr_buffer=False
        # and refined_dd=False, but we restate explicitly via dataclasses.replace
        # — bisect runs across commits where VN30_PRESET defaults MAY differ.
        cfg = replace(
            VN30_PRESET,
            atr_buffer_enabled=False,
            refined_dd_enabled=False,
        )

        # Load data + precompute indicators (matches validate_v9.py:301-303).
        loader = DataLoader('vn30')
        df = loader.load(start_date=DATA_START, end_date=DATA_END)
        df = build_indicator_dataframe(df)

        # Engine construction mirrors validate_v9.py::run_engine (two_phase=True,
        # filter=False — the v6.0/v9 canonical shape).
        engine = HybridEngine(HybridConfig(
            v2_config=cfg,
            two_phase_enabled=True,
            filter_enabled=False,
        ))
        results = engine.run(df.copy())

        # Reuse compute_metrics verbatim — do NOT reimplement (plan truth #3).
        metrics = compute_metrics(results)
        cagr = metrics['cagr_pct']
        sell = metrics['sell_count']
        dd = metrics['max_dd_pct']

        # Machine-parseable line — plan 42-03 greps this.
        print(f"BISECT_RESULT: cagr={cagr:.4f} sell={sell} max_dd={dd:.4f}")

        return EXIT_GOOD if cagr >= CAGR_GATE else EXIT_BAD

    except Exception:
        # Any runtime failure (FileNotFoundError, AttributeError from engine
        # API drift, KeyError on metric dict, etc.) → NA line + EXIT_SKIP.
        print(NA_LINE)
        print(traceback.format_exc(), file=sys.stderr)
        return EXIT_SKIP


if __name__ == '__main__':
    sys.exit(main())
