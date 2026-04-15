"""
Phase 38 backward-compatibility regression test.

Asserts that HybridEngine with atr_buffer_enabled=False produces a signal log
byte-identical to the committed v6.0 baseline on VN30 2015-2026.

This test guards ATR-04: the invariant that disabling the ATR buffer feature
does not alter any signal or state transition from the v6.0 baseline.

Per D-13: this test MUST run in CI every PR. The VN30 CSV is a repo-committed
asset for Phase 38 regression and must exist. If DATA_PATH is absent, the test
fails with a clear message — a SKIP is not a pass of ATR-04.
Fixture regeneration is explicitly a developer task (D-12).
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

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "phase38_v6_baseline_signal_log.parquet"
DATA_PATH = ROOT / "data" / "vn30.csv"
COLS = ['date', 'state', 'transition', 'ma50', 'close']


def test_atr_buffer_disabled_matches_baseline():
    """HybridEngine(atr_buffer_enabled=False) must match v6.0 baseline byte-for-byte.

    Fails (not skips) if VN30 data file is absent — the CSV is a required repo
    asset for Phase 38 CI. See D-12/D-13 in 38-CONTEXT.md.
    """
    if not DATA_PATH.exists():
        pytest.fail(
            f"VN30 data file missing: {DATA_PATH}\n"
            "This file is a required repo asset for Phase 38 regression (D-12/D-13). "
            "Commit the CSV or update DATA_PATH before running CI."
        )

    assert FIXTURE_PATH.exists(), f"Baseline fixture missing: {FIXTURE_PATH}"

    from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
    from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
    from core.data_loader import DataLoader

    expected = pd.read_parquet(FIXTURE_PATH)

    loader = DataLoader('vn30')
    loader.data_dir = ROOT
    df = loader.load(start_date="2015-01-01", end_date="2026-12-31")

    cfg = HybridConfig(v2_config=MDMV2Config(atr_buffer_enabled=False))
    engine = HybridEngine(cfg)
    result = engine.run(df)
    result['transition'] = result['state'].shift(1).fillna('CASH') + '->' + result['state']
    actual = result[COLS].reset_index(drop=True)
    expected_aligned = expected[COLS].reset_index(drop=True)

    # Exact equality for categorical string columns — float tolerance would silently
    # permit label regressions (e.g. 'SELL' vs 'CASH') to pass.
    assert (actual['state'] == expected_aligned['state']).all(), \
        f"state column mismatch at rows: {(actual['state'] != expected_aligned['state']).nonzero()[0]}"
    assert (actual['transition'] == expected_aligned['transition']).all(), \
        f"transition column mismatch at rows: {(actual['transition'] != expected_aligned['transition']).nonzero()[0]}"

    # Float tolerance for numeric columns only
    pd.testing.assert_frame_equal(
        actual[['ma50', 'close']].reset_index(drop=True),
        expected_aligned[['ma50', 'close']].reset_index(drop=True),
        check_dtype=False,
        rtol=1e-5,
        atol=1e-5,
    )


def test_atr_buffer_fixture_schema():
    """Fixture file exists and has required columns."""
    assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"
    df = pd.read_parquet(FIXTURE_PATH)
    for col in COLS:
        assert col in df.columns, f"Missing column: {col}"
    assert len(df) > 100, "Fixture suspiciously short"
