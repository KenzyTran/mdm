"""Generate phase38 v6.0 baseline fixture. Run once, commit result."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from core.data_loader import DataLoader

# Load VN30 data 2015-2026 using the standard DataLoader
loader = DataLoader('vn30')
loader.data_dir = ROOT
df = loader.load(start_date="2015-01-01", end_date="2026-12-31")
print(f"Loaded VN30 data: {len(df)} rows, {df['date'].min()} to {df['date'].max()}")

# Run with atr_buffer_enabled=False (v6.0 behavior)
cfg = HybridConfig(v2_config=MDMV2Config(atr_buffer_enabled=False))
engine = HybridEngine(cfg)
result = engine.run(df)
print(f"Engine result: {len(result)} rows, columns: {list(result.columns)}")

# Add transition column
result['transition'] = result['state'].shift(1).fillna('CASH') + '->' + result['state']

# Save core columns only
cols = ['date', 'state', 'transition', 'ma50', 'close']
fixture = result[cols].reset_index(drop=True)

# Ensure tests/fixtures directory exists
out_dir = ROOT / "tests" / "fixtures"
out_dir.mkdir(parents=True, exist_ok=True)

out_path = out_dir / "phase38_v6_baseline_signal_log.parquet"
fixture.to_parquet(out_path, index=False)
print(f"Fixture saved: {out_path} ({len(fixture)} rows)")
print(f"Columns: {list(fixture.columns)}")
print(f"State distribution:\n{fixture['state'].value_counts()}")
