"""
Phase 39 backward-compatibility regression test.

Asserts that HybridEngine with refined_dd_enabled=False produces DD columns
identical to the committed v6.0 baseline on VN30 2015-2026.

This test guards DD-04: the invariant that disabling the refined DD feature
does not alter any DD detection from the v6.0 baseline.

Per D-10/D-11: fixture committed as parquet, test FAILS (not skips) if missing.
The VN30 CSV is a repo-committed asset for Phase 39 regression and must exist.
Fixture regeneration is a developer task via scripts/generate_phase39_fixture.py.
"""
import sys
from pathlib import Path
import pytest
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
# Handle git worktree paths
if '.claude' in str(ROOT) and 'worktrees' in str(ROOT):
    parts = ROOT.parts
    for i, part in enumerate(parts):
        if part == '.claude' and i + 1 < len(parts) and parts[i + 1] == 'worktrees':
            ROOT = Path(*parts[:i])
            break
sys.path.insert(0, str(ROOT))

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase39_v6_baseline_dd_sequence.parquet"
DATA_PATH = ROOT / "data" / "vn30.csv"
COLS = ['date', 'is_dd', 'dd_type', 'dd_count']


def test_refined_dd_disabled_matches_baseline():
    """HybridEngine(refined_dd_enabled=False) must match v6.0 DD baseline.

    Fails (not skips) if VN30 data or fixture is absent -- both are required
    repo assets for Phase 39 regression (D-10/D-11).
    """
    if not DATA_PATH.exists():
        pytest.fail(
            f"VN30 data file missing: {DATA_PATH}\n"
            "Required repo asset for Phase 39 regression (D-10/D-11). "
            "Commit the CSV or update DATA_PATH before running CI."
        )
    assert FIXTURE_PATH.exists(), f"DD baseline fixture missing: {FIXTURE_PATH}"

    from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
    from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
    from core.data_loader import DataLoader

    expected = pd.read_parquet(FIXTURE_PATH)

    loader = DataLoader('vn30')
    loader.data_dir = ROOT
    df = loader.load(start_date="2015-01-01", end_date="2026-12-31")

    cfg = HybridConfig(v2_config=MDMV2Config(refined_dd_enabled=False))
    engine = HybridEngine(cfg)
    result = engine.run(df)
    actual = result[COLS].reset_index(drop=True)
    expected_aligned = expected[COLS].reset_index(drop=True)

    # Row-count invariant: same number of trading days processed
    assert len(actual) == len(expected_aligned), \
        f"Row count mismatch: actual={len(actual)}, expected={len(expected_aligned)}"

    # Exact equality for boolean is_dd column
    is_dd_mismatches = (actual['is_dd'] != expected_aligned['is_dd']).to_numpy().nonzero()[0]
    assert len(is_dd_mismatches) == 0, \
        f"is_dd mismatch at rows: {list(is_dd_mismatches[:10])}"

    # Exact equality for integer dd_type column
    dd_type_mismatches = (actual['dd_type'] != expected_aligned['dd_type']).to_numpy().nonzero()[0]
    assert len(dd_type_mismatches) == 0, \
        f"dd_type mismatch at rows: {list(dd_type_mismatches[:10])}"

    # Exact equality for integer dd_count column
    dd_count_mismatches = (actual['dd_count'] != expected_aligned['dd_count']).to_numpy().nonzero()[0]
    assert len(dd_count_mismatches) == 0, \
        f"dd_count mismatch at rows: {list(dd_count_mismatches[:10])}"


def test_phase39_fixture_schema():
    """Fixture file exists and has required columns."""
    assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"
    df = pd.read_parquet(FIXTURE_PATH)
    for col in COLS:
        assert col in df.columns, f"Missing column: {col}"
    assert len(df) > 100, "Fixture suspiciously short"
    assert df['is_dd'].sum() > 0, "No DD days in fixture -- suspicious"
