"""Generate Phase 39 v6.0 DD baseline fixture.

Run once: uv run python scripts/generate_phase39_fixture.py

Produces: tests/fixtures/phase39_v6_baseline_dd_sequence.parquet
Contains: DD columns (date, is_dd, dd_type, dd_count) from HybridEngine
with refined_dd_enabled=False on VN30 2015-2026.

Note on column naming: the HybridEngine result DataFrame exposes DD counts as
`dd_count` (not `dd_count_20d`). D-11/plan language uses the `_20d` suffix
conceptually, but the engine's actual output column is `dd_count`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from core.data_loader import DataLoader

COLS = ['date', 'is_dd', 'dd_type', 'dd_count']
OUT_DIR = ROOT / "tests" / "fixtures"
OUT_PATH = OUT_DIR / "phase39_v6_baseline_dd_sequence.parquet"


def main():
    loader = DataLoader('vn30')
    loader.data_dir = ROOT
    df = loader.load(start_date="2015-01-01", end_date="2026-12-31")
    print(f"Loaded VN30 data: {len(df)} rows, {df['date'].min()} to {df['date'].max()}")

    cfg = HybridConfig(v2_config=MDMV2Config(refined_dd_enabled=False))
    engine = HybridEngine(cfg)
    result = engine.run(df)
    print(f"Engine result: {len(result)} rows, DD columns present: "
          f"{[c for c in COLS if c in result.columns]}")

    fixture = result[COLS].reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fixture.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(fixture)} rows to {OUT_PATH}")
    print(f"DD days: {int(fixture['is_dd'].sum())}")
    print(f"DD type breakdown: {fixture['dd_type'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
