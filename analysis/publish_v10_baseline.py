#!/usr/bin/env python
"""Phase 42 BASE-02 closer — publish reconciled v10.0 baseline.

Runs the reconciled HybridEngine once on VN30 2015-2026, writes the canonical
18-field tuple (D-12) to `output/v10_reconciled_baseline.json` with
`schema_version=1` (D-15) using a consistent float formatter, and injects a
human-readable ## Reconciled Baseline section into
`docs/audits/v10_baseline_drift.md` where every float field's string
representation is BYTE-IDENTICAL to its JSON counterpart (M1 invariant).

Design bindings (42-CONTEXT.md):
  - D-12: canonical 18-field tuple shape + additional `schema_version`
  - D-13: both JSON + human audit-doc publication
  - D-14: downstream Phases 43-47 read the JSON (not literals in code)
  - D-15: schema_version=1 locks the tuple shape
  - D-16: audit-doc table uses literal numbers, not dynamic references

Checker issue bindings (from plan):
  - B2: parse_reconciliation_outcome() enforces three ValueError paths —
        (1) choice-expression leak, (2) multiple label-literals on Label
        lines, (3) zero strict Label lines.
  - M1: single rounding pass (FLOAT_DECIMALS=6) + single formatter
        (json.dumps) used for BOTH write paths → byte-identical floats.
        Post-write verify_byte_identical() re-reads both artifacts and
        asserts string equality for every float field.

Usage:
    uv run python analysis/publish_v10_baseline.py

Exits 0 on success; non-zero (fail-loud) on any failure (Phase 40 D-10).
"""

import io
import os
import re
import sys
import json
import subprocess
from dataclasses import replace

import numpy as np
import pandas as pd

# stdout UTF-8 + repo-root on sys.path.
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, VN30_PRESET, MDMV2Config
from analysis.validate_v9 import compute_metrics


# ── Module constants ────────────────────────────────────────────────────────
DATA_START = '2015-01-05'       # D-10: v6.0 shipped window start
DATA_END   = '2026-03-31'       # D-10: v6.0 shipped window end
SCHEMA_VERSION = 1              # D-15
FLOAT_DECIMALS = 6              # M1: consistent rounding for BOTH write paths

OUTPUT_JSON = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'output', 'v10_reconciled_baseline.json'
))
AUDIT_DOC = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'audits', 'v10_baseline_drift.md'
))

VALID_OUTCOMES = ('fixed_by_revert', 'fixed_by_preset', 'accepted_drift')
CHOICE_LEAK_STR = 'fixed_by_revert | fixed_by_preset | accepted_drift'
STRICT_LABEL_RE = re.compile(
    r'^Label: `(fixed_by_revert|fixed_by_preset|accepted_drift)`$',
    re.MULTILINE,
)

# Canonical field order for the audit-doc table (matches D-12 ordering).
# schema_version is intentionally EXCLUDED — it lives in the table prose, not
# the table rows, per plan 42-05 acceptance criteria.
AUDIT_FIELD_ORDER = [
    'cagr_pct',
    'max_dd_pct',
    'sharpe_rf3',
    'sell_count',
    'total_return_pct',
    'transitions',
    'buy_pct',
    'cash_pct',
    'sell_pct',
    'ma50_breakdown_sell_share',
    'buy_count',
    'run_start',
    'run_end',
    'engine_git_hash',
    'python_version',
    'pandas_version',
    'numpy_version',
    'reconciliation_outcome',
]


def parse_reconciliation_outcome() -> str:
    """Parse the reconciliation label from the audit doc (B2 hardened).

    Strict contract: the audit doc MUST contain EXACTLY ONE line matching
      ^Label: `(fixed_by_revert|fixed_by_preset|accepted_drift)`$

    Raises ValueError on three error paths:
      1. Choice-expression leak: the literal string
         'fixed_by_revert | fixed_by_preset | accepted_drift' appears
         anywhere (template copied verbatim without replacement).
      2. Multiple label-literals on Label lines: any Label-prefixed line
         contains more than one of the three label strings inside backticks.
      3. Zero strict Label lines: no line matches the strict regex above.

    Returns the captured label literal (one of VALID_OUTCOMES) on the
    happy path.
    """
    with open(AUDIT_DOC, 'r', encoding='utf-8') as f:
        text = f.read()

    # Error path 1: choice-expression leak
    if CHOICE_LEAK_STR in text:
        raise ValueError(
            "choice-expression leak in audit doc: the string "
            f"'{CHOICE_LEAK_STR}' must not appear (plan 42-04 should have "
            "replaced it with exactly one of the three literals)"
        )

    # Error path 2: multiple label-literals on Label lines
    label_lines = [ln for ln in text.splitlines() if ln.startswith('Label:')]
    for ln in label_lines:
        hits = sum(1 for lbl in VALID_OUTCOMES if f'`{lbl}`' in ln)
        if hits > 1:
            raise ValueError(
                f"multiple label literals on Label line: {ln!r} contains "
                f"{hits} of {VALID_OUTCOMES}; exactly one is required"
            )

    # Error path 3: zero strict Label lines
    matches = STRICT_LABEL_RE.findall(text)
    if len(matches) == 0:
        raise ValueError(
            "no strict Label line found: audit doc must contain exactly one "
            r"line matching ^Label: `(fixed_by_revert|fixed_by_preset|accepted_drift)`$"
        )
    if len(matches) > 1:
        raise ValueError(
            f"multiple strict Label lines found ({len(matches)}): exactly one required"
        )

    return matches[0]


def build_config():
    """Return the reconciled v6.0-equivalent preset.

    If `v60_strict_mode` exists on MDMV2Config (plan 42-04 STEP 2 preset-flag
    path landed), enable it. Otherwise (revert or accepted_drift path) the
    preset is already correct without the flag.
    """
    overrides = dict(atr_buffer_enabled=False, refined_dd_enabled=False)
    if (hasattr(MDMV2Config, '__dataclass_fields__')
            and 'v60_strict_mode' in MDMV2Config.__dataclass_fields__):
        overrides['v60_strict_mode'] = True
    return replace(VN30_PRESET, **overrides)


def run_reconciled_engine() -> pd.DataFrame:
    """Load VN30 2015-2026, build indicators, run HybridEngine once.

    Returns the results DataFrame (same shape consumed by
    analysis.validate_v9.compute_metrics).
    """
    loader = DataLoader('vn30')
    df = loader.load(start_date=DATA_START, end_date=DATA_END)
    df = build_indicator_dataframe(df)

    cfg = build_config()
    engine = HybridEngine(HybridConfig(
        v2_config=cfg,
        two_phase_enabled=True,
        filter_enabled=False,
    ))
    return engine.run(df.copy())


def _round_floats(d: dict) -> dict:
    """M1: round every float field to FLOAT_DECIMALS BEFORE both write paths.

    Ensures the JSON and audit-doc cells render byte-identical strings for
    floats (json.dumps is deterministic on rounded floats).
    """
    return {
        k: (round(v, FLOAT_DECIMALS) if isinstance(v, float) else v)
        for k, v in d.items()
    }


def build_tuple(results: pd.DataFrame, outcome: str) -> dict:
    """Assemble the canonical 18-field tuple + schema_version (D-12, D-15).

    Reuses analysis.validate_v9.compute_metrics for the 11 engine-derived
    fields (no re-implementation — plan truth #3). Adds the 7 meta fields
    (run_start, run_end, engine_git_hash, python_version, pandas_version,
    numpy_version, reconciliation_outcome).

    Applies M1 rounding at the end so BOTH write paths see the same floats.
    """
    m = compute_metrics(results)
    tup = {
        'schema_version': SCHEMA_VERSION,
        # 11 fields from compute_metrics (D-12 order)
        'cagr_pct': m['cagr_pct'],
        'max_dd_pct': m['max_dd_pct'],
        'sharpe_rf3': m['sharpe_rf3'],
        'sell_count': m['sell_count'],
        'total_return_pct': m['total_return_pct'],
        'transitions': m['transitions'],
        'buy_pct': m['buy_pct'],
        'cash_pct': m['cash_pct'],
        'sell_pct': m['sell_pct'],
        'ma50_breakdown_sell_share': m['ma50_breakdown_sell_share'],
        'buy_count': m['buy_count'],
        # 7 meta fields
        'run_start': DATA_START,
        'run_end': DATA_END,
        'engine_git_hash': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD']
        ).decode('ascii', errors='replace').strip(),
        'python_version': sys.version.split()[0],
        'pandas_version': pd.__version__,
        'numpy_version': np.__version__,
        'reconciliation_outcome': outcome,
    }
    # M1 pre-write rounding — applied before BOTH json.dump and markdown render.
    tup = _round_floats(tup)
    return tup


def write_json(tup: dict) -> None:
    """Write the canonical tuple to OUTPUT_JSON.

    json.dump with indent=2, sort_keys=False (preserves D-12 field order),
    ensure_ascii=False.
    """
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(tup, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write('\n')  # trailing newline for POSIX cleanliness
    print(f"JSON written: {OUTPUT_JSON}")


def _render_cell(v) -> str:
    """Render a single tuple value as a string for the audit-doc cell.

    Uses json.dumps for numbers (int/float) so the output is byte-identical
    to the JSON literal for the same field. Strings render UNQUOTED
    (outer quotes stripped) for readability in the markdown table.
    """
    if isinstance(v, str):
        return v
    return json.dumps(v)


def inject_audit_section(tup: dict) -> None:
    """Replace the ## Reconciled Baseline section in AUDIT_DOC.

    Locates the section by its exact header (`## Reconciled Baseline\\n`).
    Replaces everything from that header up to (but not including) the next
    `## ` header or EOF. Uses `_render_cell` on every value for byte-identical
    formatting (M1).
    """
    with open(AUDIT_DOC, 'r', encoding='utf-8') as f:
        text = f.read()

    section_header = '## Reconciled Baseline\n'
    header_idx = text.find(section_header)
    if header_idx == -1:
        raise ValueError(
            f"audit doc missing '## Reconciled Baseline' header — "
            "expected a section to replace (plan 42-02 seed should have created it)"
        )

    # Find where the section ends: next `## ` at start of a line, OR EOF.
    tail_search_start = header_idx + len(section_header)
    next_h2_match = re.search(r'^## ', text[tail_search_start:], re.MULTILINE)
    if next_h2_match:
        section_end = tail_search_start + next_h2_match.start()
    else:
        section_end = len(text)

    head = text[:header_idx]
    tail = text[section_end:]

    # Build the new section. Rows: one per AUDIT_FIELD_ORDER entry.
    # Wrap engine_git_hash and reconciliation_outcome in backticks for
    # readability (unquoted content = byte-identical to JSON value).
    rows = []
    for field in AUDIT_FIELD_ORDER:
        cell = _render_cell(tup[field])
        if field in ('engine_git_hash', 'reconciliation_outcome'):
            rows.append(f"| {field} | `{cell}` |")
        else:
            rows.append(f"| {field} | {cell} |")
    table = '\n'.join(rows)

    new_section = (
        "## Reconciled Baseline\n"
        "\n"
        "**Canonical tuple — literal values matching "
        "`output/v10_reconciled_baseline.json` (D-13, D-14, D-16).**\n"
        "\n"
        f"Schema version: **{SCHEMA_VERSION}** (D-15)\n"
        "\n"
        "| Field | Value |\n"
        "|-------|-------|\n"
        f"{table}\n"
        "\n"
        "**Downstream phases (43-47) MUST load from "
        "`output/v10_reconciled_baseline.json`, NOT quote this table in code "
        "(D-14). This table is for human reading only.**\n"
        "\n"
        "Generated by: `uv run python analysis/publish_v10_baseline.py`\n"
        "\n"
    )

    with open(AUDIT_DOC, 'w', encoding='utf-8') as f:
        f.write(head + new_section + tail)
    print(f"Audit doc updated: {AUDIT_DOC}")


def verify_byte_identical(tup: dict) -> None:
    """M1 post-write check: audit-doc cell values for float fields are
    byte-identical to the JSON string representations of the same fields.

    Reads both artifacts from disk (not in-memory tup) so the check reflects
    what was actually written. Fails loud (ValueError) on any mismatch.
    """
    with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
        on_disk_json = json.load(f)
    with open(AUDIT_DOC, 'r', encoding='utf-8') as f:
        audit_text = f.read()

    float_fields = [k for k, v in tup.items() if isinstance(v, float)]
    for field in float_fields:
        expected = json.dumps(on_disk_json[field])
        m = re.search(
            rf'^\| {re.escape(field)} \| (.*) \|$',
            audit_text,
            re.MULTILINE,
        )
        if not m:
            raise ValueError(
                f"M1 check: audit-doc row for '{field}' not found"
            )
        actual = m.group(1).strip()
        if actual != expected:
            raise ValueError(
                f"M1 byte-identical check FAILED for '{field}': "
                f"JSON={expected!r} vs audit-doc cell={actual!r}"
            )
    print(
        f"M1 byte-identical check PASSED for {len(float_fields)} float fields"
    )


def main() -> int:
    try:
        print("Phase 42-05: publishing reconciled v10.0 baseline...")

        # Step 1: parse the reconciliation outcome from the audit doc (B2).
        outcome = parse_reconciliation_outcome()
        print(f"Reconciliation outcome: {outcome!r}")

        # Step 2: run the reconciled engine once on VN30 2015-2026.
        print(f"Running HybridEngine on VN30 {DATA_START} → {DATA_END}...")
        results = run_reconciled_engine()
        print(f"Engine run complete: {len(results)} rows.")

        # Step 3: assemble canonical tuple (D-12 + schema_version).
        tup = build_tuple(results, outcome)
        print(
            f"Canonical tuple assembled: cagr={tup['cagr_pct']} "
            f"sell={tup['sell_count']} max_dd={tup['max_dd_pct']} "
            f"outcome={tup['reconciliation_outcome']}"
        )

        # Step 4: write JSON (D-13, D-15).
        write_json(tup)

        # Step 5: inject human-readable section (D-16) with M1 formatter.
        inject_audit_section(tup)

        # Step 6: M1 byte-identical post-write verification.
        verify_byte_identical(tup)

        print("Phase 42-05 publication complete.")
        return 0

    except Exception as exc:
        import traceback
        print(f"PUBLISH FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
