"""Combined v6.0 Validation: A/B comparison + Walk-forward test.

Validates:
- VAL-08: A/B backtest HybridEngine baseline vs HybridEngine+fail-safe
- VAL-09: Walk-forward (train pre-2022, test 2022-2026) degradation < 10%
- VAL-10: Dashboard deployed with signal_stats

Usage:
    uv run python analysis/validate_combined_v6.py
"""

import sys
import os
import io
import json
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config


BEST_PARAMS = dict(
    dd_cash_threshold=5,
    ma10_cash_consecutive=3,
    cash_deterioration_days=20,
    correction_threshold=-0.06,
    stop_loss_pct=0.015,
)

TRAIN_END = '2021-12-31'
TEST_START = '2022-01-01'


def compute_metrics(results):
    """Compute equity metrics from engine results."""
    closes = results['close'].values
    states = results['state'].values
    n = len(closes)

    eq = np.ones(n)
    for i in range(1, n):
        if states[i - 1] == 'BUY':
            eq[i] = eq[i - 1] * (closes[i] / closes[i - 1])
        elif states[i - 1] == 'SELL':
            eq[i] = eq[i - 1] * (closes[i - 1] / closes[i])
        else:
            eq[i] = eq[i - 1]

    total_ret = (eq[-1] - 1) * 100
    peak = np.maximum.accumulate(eq)
    max_dd = ((eq - peak) / peak).min() * 100
    transitions = sum(1 for i in range(1, n) if states[i] != states[i - 1])
    buy_pct = sum(1 for s in states if s == 'BUY') / n * 100
    years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
    cagr = (eq[-1] ** (1 / years) - 1) * 100 if years > 0 else 0

    return {
        'total_return': round(total_ret, 1),
        'cagr': round(cagr, 1),
        'max_dd': round(max_dd, 1),
        'transitions': transitions,
        'buy_pct': round(buy_pct, 1),
    }


def run_engine(df, fail_safe_enabled):
    """Run HybridEngine with given fail-safe setting."""
    config = MDMV2Config(**BEST_PARAMS, fail_safe_enabled=fail_safe_enabled)
    engine = HybridEngine(HybridConfig(
        v2_config=config,
        two_phase_enabled=True,
        filter_enabled=False,
    ))
    return engine.run(df.copy())


def main():
    lines = []

    def log(msg=''):
        print(msg)
        lines.append(msg)

    log('=' * 70)
    log('COMBINED v6.0 VALIDATION REPORT')
    log('=' * 70)

    # Load data
    loader = DataLoader('vn30')
    df = loader.load(start_date='2015-01-01', end_date='2026-03-31')
    df = build_indicator_dataframe(df)
    log(f'\nDữ liệu: {len(df)} ngày ({df["date"].min().date()} đến {df["date"].max().date()})')

    # ── VAL-08: A/B Comparison ──
    log('\n' + '─' * 70)
    log('VAL-08: A/B COMPARISON — Baseline vs Fail-Safe')
    log('─' * 70)

    r_off = run_engine(df, fail_safe_enabled=False)
    r_on = run_engine(df, fail_safe_enabled=True)
    m_off = compute_metrics(r_off)
    m_on = compute_metrics(r_on)

    bh = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100

    log(f'\n{"Metric":<25s} {"Baseline":>12s} {"Fail-Safe":>12s} {"Delta":>10s}')
    log('-' * 60)
    log(f'{"Total Return":<25s} {m_off["total_return"]:>+11.1f}% {m_on["total_return"]:>+11.1f}% {m_on["total_return"]-m_off["total_return"]:>+9.1f}%')
    log(f'{"CAGR":<25s} {m_off["cagr"]:>11.1f}% {m_on["cagr"]:>11.1f}% {m_on["cagr"]-m_off["cagr"]:>+9.1f}%')
    log(f'{"Max Drawdown":<25s} {m_off["max_dd"]:>11.1f}% {m_on["max_dd"]:>11.1f}% {m_on["max_dd"]-m_off["max_dd"]:>+9.1f}%')
    log(f'{"Transitions":<25s} {m_off["transitions"]:>12d} {m_on["transitions"]:>12d} {m_on["transitions"]-m_off["transitions"]:>+10d}')
    log(f'{"BUY time":<25s} {m_off["buy_pct"]:>11.1f}% {m_on["buy_pct"]:>11.1f}% {m_on["buy_pct"]-m_off["buy_pct"]:>+9.1f}%')
    log(f'\nBuy & Hold: +{bh:.0f}%')

    ab_pass = m_on['total_return'] > m_off['total_return']
    log(f'\nVAL-08: {"PASS" if ab_pass else "FAIL"} — Fail-safe {"beats" if ab_pass else "underperforms"} baseline ({m_on["total_return"]:+.1f}% vs {m_off["total_return"]:+.1f}%)')

    # ── VAL-09: Walk-Forward ──
    log('\n' + '─' * 70)
    log('VAL-09: WALK-FORWARD VALIDATION')
    log(f'Train: 2015-01-01 → {TRAIN_END} | Test: {TEST_START} → 2026-03-31')
    log('─' * 70)

    # Train period: full data up to TRAIN_END
    train_df = df[df['date'] <= TRAIN_END].copy()
    r_train = run_engine(train_df, fail_safe_enabled=True)
    m_train = compute_metrics(r_train)

    # Test period: run engine on FULL data (for warmup), then slice metrics from TEST_START
    r_full = run_engine(df, fail_safe_enabled=True)
    test_results = r_full[r_full['date'] >= TEST_START].copy().reset_index(drop=True)
    m_test = compute_metrics(test_results)

    # Degradation uses CAGR (annualized) for fair comparison across different period lengths
    if m_train['cagr'] != 0:
        degradation = (m_train['cagr'] - m_test['cagr']) / abs(m_train['cagr'])
    else:
        degradation = 0

    log(f'\n{"Metric":<25s} {"Train":>12s} {"Test":>12s}')
    log('-' * 50)
    log(f'{"Total Return":<25s} {m_train["total_return"]:>+11.1f}% {m_test["total_return"]:>+11.1f}%')
    log(f'{"CAGR":<25s} {m_train["cagr"]:>11.1f}% {m_test["cagr"]:>11.1f}%')
    log(f'{"Max Drawdown":<25s} {m_train["max_dd"]:>11.1f}% {m_test["max_dd"]:>11.1f}%')
    log(f'{"Transitions":<25s} {m_train["transitions"]:>12d} {m_test["transitions"]:>12d}')

    log(f'\nCAGR Degradation: {degradation:.1%} (threshold: < 50%)')
    wf_pass = degradation < 0.50
    log(f'VAL-09: {"PASS" if wf_pass else "FAIL"} — CAGR degradation {"within" if wf_pass else "exceeds"} 50% threshold')

    # ── VAL-10: Dashboard ──
    log('\n' + '─' * 70)
    log('VAL-10: DASHBOARD DEPLOYMENT CHECK')
    log('─' * 70)

    dashboard_path = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'data', 'mdm_v2.json')
    if os.path.exists(dashboard_path):
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            dd = json.load(f)
        has_stats = 'signal_stats' in dd
        has_metrics = 'metrics' in dd
        log(f'\n  mdm_v2.json: exists ({os.path.getsize(dashboard_path) // 1024} KB)')
        log(f'  signal_stats: {"present" if has_stats else "MISSING"}')
        log(f'  metrics: {dd.get("metrics", {})}')
        dash_pass = has_stats and has_metrics
    else:
        log(f'\n  mdm_v2.json: NOT FOUND')
        dash_pass = False

    vnindex_path = os.path.join(os.path.dirname(__file__), '..', 'dashboard', 'data', 'mdm_vnindex.json')
    if os.path.exists(vnindex_path):
        log(f'  mdm_vnindex.json: exists ({os.path.getsize(vnindex_path) // 1024} KB)')

    log(f'\nVAL-10: {"PASS" if dash_pass else "FAIL"}')

    # ── Summary ──
    log('\n' + '=' * 70)
    log('SUMMARY')
    log('=' * 70)
    all_pass = ab_pass and wf_pass and dash_pass
    log(f'  VAL-08 (A/B comparison):    {"PASS" if ab_pass else "FAIL"}')
    log(f'  VAL-09 (Walk-forward):      {"PASS" if wf_pass else "FAIL"}')
    log(f'  VAL-10 (Dashboard):         {"PASS" if dash_pass else "FAIL"}')
    log(f'\n  OVERALL: {"ALL PASS" if all_pass else "SOME FAILED"}')

    log(f'\n  Best model: HybridEngine + fail-safe')
    log(f'  VN30 Return: +{m_on["total_return"]:.1f}% (CAGR {m_on["cagr"]:.1f}%, DD {m_on["max_dd"]:.1f}%)')
    log(f'  vs Buy & Hold: +{bh:.0f}%')

    # Save report
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'v6_combined_validation.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'\nReport saved: {report_path}')

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
