from models import MDMEngine, DataLoader
from models.performance import PerformanceAnalyzer
import sys

loader = DataLoader('vnindex_price.csv')
df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
engine = MDMEngine()
results = engine.run(df)
trades = engine.get_trades()

analyzer = PerformanceAnalyzer(results, trades)

with open('report.txt', 'w', encoding='utf-8') as f:
    sys.stdout = f
    analyzer.print_report()
    sys.stdout = sys.__stdout__

print("Report saved to report.txt")
