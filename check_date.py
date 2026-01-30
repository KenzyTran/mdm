from models import MDMEngine, DataLoader
import pandas as pd

loader = DataLoader('vnindex_price.csv')
df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
engine = MDMEngine()
results = engine.run(df)

# Check around 2015-01-06
print('=== Data around 2015-01-06 ===')
mask = (results['date'] >= '2015-01-05') & (results['date'] <= '2015-01-08')
for idx, row in results[mask].iterrows():
    print(f"Date: {row['date']}")
    print(f"  Close: {row['close']}, MA50: {row['ma50']:.2f}")
    if pd.notna(row['prev_ma50']):
        print(f"  Prev Close: {row['prev_close']}, Prev MA50: {row['prev_ma50']:.2f}")
    else:
        print(f"  Prev Close: {row['prev_close']}, Prev MA50: NaN")
    print(f"  Volume Up: {row['volume_up']}")
    print(f"  State: {row['state']}, Action: {row['action']}")
    print(f"  Drawdown: {row['drawdown_pct']*100:.2f}%")
    print()
