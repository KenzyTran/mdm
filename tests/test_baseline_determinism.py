"""
Engine Determinism Regression Tests (BASE-03).

Preset used: VN30_PRESET with atr_buffer_enabled=False, refined_dd_enabled=False,
and v60_strict_mode=True iff that field exists on MDMV2Config at test time.

The "reconciled preset" here means "whatever preset Phase 42-04 declared canonical
via the reconciliation outcome". Refer to output/v10_reconciled_baseline.json
reconciliation_outcome field for which fix-forward path was taken.

Enforces that HybridEngine on VN30 2015-2026 is deterministic via BYTE-EXACT
primary assertions (M5 tightening -- if determinism holds, spread is 0.0):
  1. 3 fresh instances -> CAGR/MaxDD/Sharpe/SELL/transitions sets all have cardinality 1
  2. 2 fresh instances -> results DataFrames byte-exact equal via pandas `.equals()`

D-17 thresholds (0.1pp CAGR/MaxDD spread, 0.005 Sharpe spread) are retained as
informative FALLBACK MESSAGES on byte-exact failure -- they describe the post-mortem
sanity band, not the passing condition.

Also guards the D-14 downstream invariant (m4, co-wave-4 tolerant):
  3. output/v10_reconciled_baseline.json loadable with schema_version=1 + 18 fields
     + correct types -- SKIPS if the JSON isn't present yet (plans 42-05 and 42-06
     both live in wave 4 and may commit in either order; once both are committed
     at HEAD, the JSON exists and this test runs fully).

Run:  `uv run pytest -m regression tests/test_baseline_determinism.py -v`

Acceptance bar (D-20): pytest passes locally on the reconciled-HEAD commit.
No CI exists; the bar is not "green-CI", it is "green-on-HEAD-when-committed".

If any determinism test fails, Phase 42 is INCOMPLETE (D-21). Non-determinism poisons:
  - Phase 44 MACRO-04 byte-exact v6.0 parity regression
  - Phase 45 walk-forward stability (median degradation < 30%)
  - Phase 46 VAL-02 HARD gate reproducibility
  - Phase 43-47 consumption of output/v10_reconciled_baseline.json (D-14)
"""

from dataclasses import replace
import json
import os

import pytest
import pandas as pd

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config, VN30_PRESET

# NOTE: `analysis.validate_v9` rewrites sys.stdout at module-import time
# (line 41: `sys.stdout = io.TextIOWrapper(...)`), which breaks pytest's stdout
# capture during collection if imported at module top. We import compute_metrics
# lazily inside the test body (see _get_compute_metrics below) where pytest's
# per-test capture is in control of the stream lifecycle. Do NOT move to
# module-level imports -- doing so will break `pytest` collection with
# `ValueError: I/O operation on closed file`.
# from analysis.validate_v9 import compute_metrics  # DELIBERATELY LAZY


DATA_START = '2015-01-05'
DATA_END = '2026-03-31'

# D-17 post-mortem thresholds -- informative fallback on byte-exact failure (M5)
CAGR_SPREAD_POSTMORTEM = 0.1       # percentage points
MAXDD_SPREAD_POSTMORTEM = 0.1      # percentage points
SHARPE_SPREAD_POSTMORTEM = 0.005

RECONCILED_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'output', 'v10_reconciled_baseline.json',
)

# D-12 field types for the downstream-JSON regression guard (m4)
EXPECTED_JSON_TYPES = {
    'schema_version': int,
    'cagr_pct': float,
    'max_dd_pct': float,
    'sharpe_rf3': float,
    'sell_count': int,
    'total_return_pct': float,
    'transitions': int,
    'buy_pct': float,
    'cash_pct': float,
    'sell_pct': float,
    'ma50_breakdown_sell_share': float,
    'buy_count': int,
    'run_start': str,
    'run_end': str,
    'engine_git_hash': str,
    'python_version': str,
    'pandas_version': str,
    'numpy_version': str,
    'reconciliation_outcome': str,
}
VALID_OUTCOMES = ('fixed_by_revert', 'fixed_by_preset', 'accepted_drift')


# ── stdout-safe lazy-import shim for analysis.validate_v9 ───────────────────
# `analysis.validate_v9` rewrites `sys.stdout` at module-import time
# (line 41: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`).
# Importing it at test-module top breaks pytest's capture machinery with
# "ValueError: I/O operation on closed file" when the orphaned TextIOWrapper is
# GC'd and closes the shared underlying buffer.
#
# Workarounds considered + rejected:
#   - Copy compute_metrics inline: duplicates canonical function; violates
#     "reuse, don't reinvent" (42-CONTEXT.md canonical_refs).
#   - subprocess call: breaks fixture-scoped DataFrame sharing (slow).
#   - Detach the wrapper: compute_metrics still works but pytest's capture
#     tempfile got substituted into the wrapper's buffer attr and closes later.
#
# Chosen fix: stdout-preserving lazy import.
#   1. Snapshot current sys.stdout BEFORE the side-effect import.
#   2. Perform the import (which installs an orphan TextIOWrapper on
#      sys.stdout AND holds a reference to the original buffer).
#   3. Restore sys.stdout to the snapshot.
#   4. Park the orphan wrapper on the function object so it isn't GC'd for the
#      rest of the process lifetime -- this is what prevents the buffer from
#      being closed in pytest's teardown.
_VALIDATE_V9_COMPUTE_METRICS = None
_ORPHAN_STDOUT_WRAPPER_HOLDER = []  # keeps the rewritten wrapper alive; prevents GC-induced buffer close


def _get_compute_metrics():
    """Lazy, stdout-safe import of `analysis.validate_v9.compute_metrics`.

    See module-level comment above for the rationale behind the wrapper-parking
    dance. Result cached in a module global so the import side-effect fires at
    most once per test process.
    """
    global _VALIDATE_V9_COMPUTE_METRICS
    if _VALIDATE_V9_COMPUTE_METRICS is not None:
        return _VALIDATE_V9_COMPUTE_METRICS
    import sys
    saved_stdout = sys.stdout
    try:
        from analysis.validate_v9 import compute_metrics  # noqa: E402
        orphan_wrapper = sys.stdout  # the freshly-installed TextIOWrapper
    finally:
        sys.stdout = saved_stdout
    _ORPHAN_STDOUT_WRAPPER_HOLDER.append(orphan_wrapper)  # pin for process lifetime
    _VALIDATE_V9_COMPUTE_METRICS = compute_metrics
    return compute_metrics


def _build_reconciled_cfg() -> MDMV2Config:
    """Reconciled v6.0-equivalent preset (matches plan 42-04 outcome, D-22).

    If `v60_strict_mode` field exists on MDMV2Config (preset path from D-07 step 2),
    set it True. Otherwise the preset is already the reconciled semantics
    (revert path or accepted-drift path).
    """
    overrides = dict(atr_buffer_enabled=False, refined_dd_enabled=False)
    if 'v60_strict_mode' in MDMV2Config.__dataclass_fields__:
        overrides['v60_strict_mode'] = True
    return replace(VN30_PRESET, **overrides)


def _run_once(df: pd.DataFrame) -> pd.DataFrame:
    """Fresh HybridEngine -> .run(df.copy()) -> results DataFrame."""
    engine = HybridEngine(HybridConfig(
        v2_config=_build_reconciled_cfg(),
        two_phase_enabled=True,
        filter_enabled=False,
    ))
    return engine.run(df.copy())


@pytest.mark.regression
class TestBaselineDeterminism:
    """BASE-03: HybridEngine determinism regression suite."""

    @pytest.fixture(scope='class')
    def prepared_df(self) -> pd.DataFrame:
        """Full-period VN30 DataFrame with indicators pre-computed (D-18).

        Shared read-only across engine-running tests. Each test takes `.copy()` before
        passing to the engine.
        """
        df = DataLoader('vn30').load(DATA_START, DATA_END)
        df = build_indicator_dataframe(df)
        return df

    def test_numeric_variance_across_3_runs(self, prepared_df):
        """3 fresh engines -> BYTE-EXACT equality across CAGR/MaxDD/Sharpe/SELL/transitions (M5).

        D-17's 0.1pp / 0.005 thresholds are informative post-mortem fallback messages
        only; the PRIMARY assertion is byte-exact equality (spread is 0.0 if
        determinism holds).
        """
        compute_metrics = _get_compute_metrics()
        cagrs, maxdds, sharpes, sells, trans = [], [], [], [], []
        for _ in range(3):
            results = _run_once(prepared_df)
            m = compute_metrics(results)
            cagrs.append(m['cagr_pct'])
            maxdds.append(m['max_dd_pct'])
            sharpes.append(m['sharpe_rf3'])
            sells.append(m['sell_count'])
            trans.append(m['transitions'])

        # PRIMARY byte-exact assertions (M5)
        assert len(set(cagrs)) == 1, (
            f"CAGR varied across 3 runs: {cagrs}. Must be byte-exact IDENTICAL. "
            f"Observed spread: {max(cagrs) - min(cagrs):.6f}pp "
            f"(D-17 post-mortem threshold: {CAGR_SPREAD_POSTMORTEM}pp)"
        )
        assert len(set(maxdds)) == 1, (
            f"MaxDD varied across 3 runs: {maxdds}. Must be byte-exact IDENTICAL. "
            f"Observed spread: {max(maxdds) - min(maxdds):.6f}pp "
            f"(D-17 post-mortem threshold: {MAXDD_SPREAD_POSTMORTEM}pp)"
        )
        assert len(set(sharpes)) == 1, (
            f"Sharpe varied across 3 runs: {sharpes}. Must be byte-exact IDENTICAL. "
            f"Observed spread: {max(sharpes) - min(sharpes):.6f} "
            f"(D-17 post-mortem threshold: {SHARPE_SPREAD_POSTMORTEM})"
        )
        assert len(set(sells)) == 1, (
            f"SELL count varied across 3 runs: {sells}. Must be IDENTICAL."
        )
        assert len(set(trans)) == 1, (
            f"Transitions varied across 3 runs: {trans}. Must be IDENTICAL."
        )

    def test_signal_log_byte_exact(self, prepared_df):
        """2 fresh engines -> results DataFrames must be byte-exact (D-17)."""
        results_1 = _run_once(prepared_df)
        results_2 = _run_once(prepared_df)
        assert results_1.equals(results_2), (
            "Signal log DataFrames differ between two fresh-engine runs. "
            "Engine is non-deterministic; Phase 42 is incomplete (D-21)."
        )

    def test_reconciled_baseline_json_loadable(self):
        """m4: D-14 downstream invariant -- JSON loadable with schema_version=1 + 18 fields + correct types.

        Makes the reconciled baseline's downstream contract a pytest regression gate.
        If a future phase accidentally mutates the JSON shape (e.g., renames a field or
        changes a dtype), this test fails before Phase 43-47 consumers break.

        Co-wave-4 tolerance: plan 42-05 produces this JSON in the same wave as this
        plan. If the JSON is not yet on disk (parallel wave-4 execution order), skip
        the test rather than fail -- the test will run fully on the next invocation
        after both wave-4 plans have committed.
        """
        if not os.path.isfile(RECONCILED_JSON):
            pytest.skip(
                f"{RECONCILED_JSON} not present yet; plan 42-05 has not committed "
                "its artifacts in this wave-4 run. Re-run the suite after wave 4 "
                "completes at HEAD for the full downstream-JSON regression check."
            )
        with open(RECONCILED_JSON, 'r', encoding='utf-8') as f:
            d = json.load(f)
        assert d.get('schema_version') == 1, (
            f"schema_version must be 1, got {d.get('schema_version')}"
        )
        missing = [k for k in EXPECTED_JSON_TYPES if k not in d]
        assert not missing, f"missing D-12 fields in reconciled-baseline JSON: {missing}"
        type_mismatches = []
        for field, expected_type in EXPECTED_JSON_TYPES.items():
            actual_val = d[field]
            if expected_type is int and not isinstance(actual_val, int):
                type_mismatches.append((field, expected_type.__name__, type(actual_val).__name__))
            elif expected_type is float and not isinstance(actual_val, float):
                type_mismatches.append((field, expected_type.__name__, type(actual_val).__name__))
            elif expected_type is str and not isinstance(actual_val, str):
                type_mismatches.append((field, expected_type.__name__, type(actual_val).__name__))
        assert not type_mismatches, (
            f"D-12 field type mismatches: {type_mismatches}"
        )
        assert d['reconciliation_outcome'] in VALID_OUTCOMES, (
            f"reconciliation_outcome must be one of {VALID_OUTCOMES}, "
            f"got {d['reconciliation_outcome']!r}"
        )
