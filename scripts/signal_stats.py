"""Signal statistics and 2024 deep analysis."""
import sys, os, io, numpy as np, pandas as pd
from itertools import groupby

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config

loader = DataLoader('vn30')
df = loader.load(start_date='2015-01-01', end_date='2026-03-31')
df = build_indicator_dataframe(df)

best = dict(dd_cash_threshold=5, ma10_cash_consecutive=3, cash_deterioration_days=20,
            correction_threshold=-0.06, stop_loss_pct=0.015, fail_safe_enabled=True)
config = MDMV2Config(**best)
engine = HybridEngine(HybridConfig(v2_config=config, two_phase_enabled=True, filter_enabled=False))
result = engine.run(df.copy())
trades = engine.get_trades()

# === TONG THE ===
print('=' * 80)
print('THỐNG KÊ TÍN HIỆU - TOÀN BỘ (2015-2026)')
print('=' * 80)

states = result['state'].values
transitions = []
for i in range(1, len(states)):
    if states[i] != states[i - 1]:
        transitions.append({
            'date': result['date'].iloc[i],
            'from': states[i - 1],
            'to': states[i],
            'close': result['close'].iloc[i],
        })
trans_df = pd.DataFrame(transitions)

buy_entries = trans_df[trans_df['to'] == 'BUY']
sell_entries = trans_df[trans_df['to'] == 'SELL']
cash_entries = trans_df[trans_df['to'] == 'CASH']

print(f'\nTổng số chuyển trạng thái: {len(trans_df)}')
print(f'  -> BUY:  {len(buy_entries)}')
print(f'  -> SELL: {len(sell_entries)}')
print(f'  -> CASH: {len(cash_entries)}')

# Trade types
trade_types = {}
for t in trades:
    tt = t.get('type', 'unknown')
    trade_types[tt] = trade_types.get(tt, 0) + 1
print(f'\nLoại trade:')
for tt, count in sorted(trade_types.items(), key=lambda x: -x[1]):
    print(f'  {tt}: {count}')

# BUY signal reasons
buy_signals = [t for t in trades if t.get('type') == 'BUY']
ftd_count = sum(1 for t in buy_signals if t.get('signal_type', '') == 'FTD')
ma50_count = sum(1 for t in buy_signals if 'MA50' in str(t.get('signal_type', '')))
w52_count = sum(1 for t in buy_signals if '52' in str(t.get('signal_type', '')))
other_buy = len(buy_signals) - ftd_count - ma50_count - w52_count

print(f'\nBUY signal breakdown ({len(buy_signals)} tổng):')
print(f'  FTD classic:    {ftd_count} ({ftd_count / max(len(buy_signals), 1) * 100:.0f}%)')
print(f'  MA50 breakout:  {ma50_count} ({ma50_count / max(len(buy_signals), 1) * 100:.0f}%)')
print(f'  52-week break:  {w52_count} ({w52_count / max(len(buy_signals), 1) * 100:.0f}%)')
if other_buy:
    print(f'  Khác:           {other_buy}')

# SELL trigger reasons
sell_trades = [t for t in trades if t.get('type') == 'SELL_SIGNAL']
ma50_sell = sum(1 for t in sell_trades if 'MA50' in t.get('reason', ''))
cash_det = sum(1 for t in sell_trades if 'deterioration' in t.get('reason', ''))

print(f'\nSELL trigger breakdown ({len(sell_trades)} tổng):')
print(f'  MA50 breakdown:     {ma50_sell} ({ma50_sell / max(len(sell_trades), 1) * 100:.0f}%)')
print(f'  Cash deterioration: {cash_det} ({cash_det / max(len(sell_trades), 1) * 100:.0f}%)')

# EXIT reasons (BUY->CASH)
exit_trades = [t for t in trades if t.get('type') in ('CASH_EXIT', 'EXIT_TO_CASH')]
sl_exits = sum(1 for t in exit_trades if 'stop' in t.get('reason', '').lower())
dd_exits = sum(1 for t in exit_trades if 'DD' in t.get('reason', '') or 'distribution' in t.get('reason', '').lower())
ma10_exits = sum(1 for t in exit_trades if 'MA10' in t.get('reason', ''))

print(f'\nEXIT BUY->CASH breakdown ({len(exit_trades)} tổng):')
print(f'  Stop loss:    {sl_exits}')
print(f'  DD threshold: {dd_exits}')
print(f'  MA10 below:   {ma10_exits}')
print(f'  Khác:         {len(exit_trades) - sl_exits - dd_exits - ma10_exits}')

# SELL exit reasons
cover_trades = [t for t in trades if t.get('type') in ('SHORT_COVER', 'FAIL_SAFE_EXIT')]
fs_exits = sum(1 for t in cover_trades if t.get('type') == 'FAIL_SAFE_EXIT')
ftd_covers = sum(1 for t in cover_trades if 'FTD' in t.get('reason', ''))
ma50_covers = sum(1 for t in cover_trades if 'MA50' in t.get('reason', ''))
dd5_covers = sum(1 for t in cover_trades if 'DD5' in t.get('reason', '').upper() or 'short stop' in t.get('reason', '').lower())

print(f'\nSELL EXIT breakdown ({len(cover_trades)} tổng):')
print(f'  Fail-safe:      {fs_exits} ({fs_exits / max(len(cover_trades), 1) * 100:.0f}%)')
print(f'  FTD cover:      {ftd_covers} ({ftd_covers / max(len(cover_trades), 1) * 100:.0f}%)')
print(f'  MA50 cover:     {ma50_covers} ({ma50_covers / max(len(cover_trades), 1) * 100:.0f}%)')
print(f'  DD5 short stop: {dd5_covers} ({dd5_covers / max(len(cover_trades), 1) * 100:.0f}%)')

# Time in each state
total_days = len(result)
buy_days = (result['state'] == 'BUY').sum()
sell_days = (result['state'] == 'SELL').sum()
cash_days = (result['state'] == 'CASH').sum()
print(f'\nThời gian ở mỗi trạng thái ({total_days} ngày):')
print(f'  BUY:  {buy_days} ngày ({buy_days / total_days * 100:.1f}%)')
print(f'  SELL: {sell_days} ngày ({sell_days / total_days * 100:.1f}%)')
print(f'  CASH: {cash_days} ngày ({cash_days / total_days * 100:.1f}%)')

# Avg duration per state
state_runs = [(k, sum(1 for _ in g)) for k, g in groupby(states)]
buy_runs = [d for s, d in state_runs if s == 'BUY']
sell_runs = [d for s, d in state_runs if s == 'SELL']
cash_runs = [d for s, d in state_runs if s == 'CASH']
print(f'\nThời gian trung bình mỗi lần:')
print(f'  BUY:  {np.mean(buy_runs):.1f} ngày (min {min(buy_runs)}, max {max(buy_runs)})')
print(f'  SELL: {np.mean(sell_runs):.1f} ngày (min {min(sell_runs)}, max {max(sell_runs)})')
print(f'  CASH: {np.mean(cash_runs):.1f} ngày (min {min(cash_runs)}, max {max(cash_runs)})')

# Win rate by signal type
print(f'\nWin rate theo loại tín hiệu BUY:')
for sig_type in ['FTD', 'MA50', '52WEEK']:
    entries = [t for t in buy_signals if sig_type in str(t.get('signal_type', ''))]
    if not entries:
        continue
    # Find corresponding exits
    wins = 0
    losses = 0
    for entry in entries:
        entry_date = entry.get('date')
        # Find next exit after this entry
        for t in trades:
            if t.get('type') in ('CASH_EXIT', 'EXIT_TO_CASH') and t.get('date') > entry_date:
                pnl = t.get('pnl', 0)
                if pnl and pnl > 0:
                    wins += 1
                else:
                    losses += 1
                break
    total = wins + losses
    wr = wins / total * 100 if total > 0 else 0
    print(f'  {sig_type}: {wins}W/{losses}L = {wr:.0f}% win rate')

# === 2024 ===
print()
print('=' * 80)
print('PHÂN TÍCH 2024 (Thị trường khó khăn)')
print('=' * 80)

r24 = result[(result['date'] >= '2024-01-01') & (result['date'] < '2025-01-01')].copy()
trades24 = [t for t in trades if pd.Timestamp(t.get('date', '2000-01-01')).year == 2024]

print(f'\nVN30 2024: {r24["close"].iloc[0]:.0f} -> {r24["close"].iloc[-1]:.0f} '
      f'({(r24["close"].iloc[-1] / r24["close"].iloc[0] - 1) * 100:+.1f}%)')

# State in 2024
b24 = (r24['state'] == 'BUY').sum()
s24 = (r24['state'] == 'SELL').sum()
c24 = (r24['state'] == 'CASH').sum()
n24 = len(r24)
print(f'\nTrạng thái 2024 ({n24} ngày):')
print(f'  BUY:  {b24} ({b24 / n24 * 100:.1f}%)')
print(f'  SELL: {s24} ({s24 / n24 * 100:.1f}%)')
print(f'  CASH: {c24} ({c24 / n24 * 100:.1f}%)')

# Equity in 2024
closes24 = r24['close'].values
states24 = r24['state'].values
eq24 = np.ones(len(closes24))
for i in range(1, len(closes24)):
    if states24[i - 1] == 'BUY':
        eq24[i] = eq24[i - 1] * (closes24[i] / closes24[i - 1])
    elif states24[i - 1] == 'SELL':
        eq24[i] = eq24[i - 1] * (closes24[i - 1] / closes24[i])
    else:
        eq24[i] = eq24[i - 1]
ret24 = (eq24[-1] - 1) * 100
dd24 = ((eq24 - np.maximum.accumulate(eq24)) / np.maximum.accumulate(eq24)).min() * 100
print(f'\nHiệu suất 2024:')
print(f'  Strategy return: {ret24:+.1f}%')
print(f'  Buy & Hold:      {(r24["close"].iloc[-1] / r24["close"].iloc[0] - 1) * 100:+.1f}%')
print(f'  Max drawdown:    {dd24:.1f}%')

# All trades in 2024
print(f'\nChi tiết tín hiệu 2024 ({len(trades24)} trades):')
print(f'{"Ngày":<12s} {"Loại":<22s} {"Giá":>10s}  {"P&L":>8s}  Lý do')
print('-' * 90)
for t in trades24:
    d = pd.Timestamp(t.get('date', ''))
    tp = t.get('type', '')
    reason = t.get('reason', '')[:40]
    price = t.get('price', 0) or 0
    pnl = t.get('pnl', None)
    pnl_str = f'{pnl * 100:+.1f}%' if pnl is not None else ''
    print(f'{d.strftime("%Y-%m-%d"):<12s} {tp:<22s} {price:>10.2f}  {pnl_str:>8s}  {reason}')

# Monthly breakdown 2024
print(f'\nPhân tích theo tháng 2024:')
print(f'{"Tháng":<8s} {"Trạng thái chính":<20s} {"Return":>8s}  {"Ghi chú"}')
print('-' * 60)
for month in range(1, 13):
    rm = r24[r24['date'].dt.month == month]
    if len(rm) == 0:
        continue
    cm = rm['close'].values
    sm = rm['state'].values
    eqm = np.ones(len(cm))
    for i in range(1, len(cm)):
        if sm[i - 1] == 'BUY':
            eqm[i] = eqm[i - 1] * (cm[i] / cm[i - 1])
        elif sm[i - 1] == 'SELL':
            eqm[i] = eqm[i - 1] * (cm[i - 1] / cm[i])
        else:
            eqm[i] = eqm[i - 1]
    retm = (eqm[-1] - 1) * 100
    dominant = max(['BUY', 'SELL', 'CASH'], key=lambda s: (rm['state'] == s).sum())
    dom_pct = (rm['state'] == dominant).sum() / len(rm) * 100
    trans_m = sum(1 for i in range(1, len(sm)) if sm[i] != sm[i - 1])
    note = f'{trans_m} chuyển' if trans_m > 0 else 'giữ nguyên'
    print(f'T{month:<7d} {dominant} ({dom_pct:.0f}%){"":<10s} {retm:>+7.1f}%  {note}')
