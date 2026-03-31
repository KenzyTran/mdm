"""Export MDM backtest data as JSON for the static dashboard.

Runs 3 MDM models (V2, Hybrid, P15) on VN30 data and exports:
- Trades, equity curves, performance metrics, signals, price data
- Strategy documentation (markdown)

Usage:
    uv run python scripts/export_dashboard_data.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np

from core.data_loader import DataLoader
from core.indicators import build_indicator_dataframe
from strategies.mdm_hybrid.mdm_hybrid_engine import HybridEngine
from strategies.mdm_hybrid.config import HybridConfig, MDMV2Config, VN30_PRESET
from strategies.mdm_hybrid.indicator_filter import FilterConfig
from strategies.mdm_v2.config import MDMV2Config as V2StandaloneConfig
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DASHBOARD_DATA_DIR = os.path.join(PROJECT_ROOT, 'dashboard', 'data')

START_DATE = '2015-01-01'
END_DATE = '2026-03-27'

MODELS = {
    'mdm_v2': {
        'name': 'MDM V2 (VN30 Optimized)',
        'doc_file': 'rules_mdm_v2.md',
        'config': lambda: HybridConfig(
            v2_config=VN30_PRESET,
            two_phase_enabled=True,
            filter_enabled=False,
        ),
    },
    'mdm_hybrid': {
        'name': 'MDM Hybrid (3 Filters)',
        'doc_file': 'rules_mdm_hybrid.md',
        'config': lambda: HybridConfig(
            v2_config=VN30_PRESET,
            two_phase_enabled=True,
            filter_enabled=True,
            filter_config=FilterConfig(),
        ),
    },
    'mdm_p15': {
        'name': 'MDM Phase 15 (HA Smoothed)',
        'doc_file': 'rules_mdm_hybrid.md',
        'config': lambda: HybridConfig(
            v2_config=VN30_PRESET,
            two_phase_enabled=True,
            filter_enabled=True,
            filter_config=FilterConfig(ha_smooth_enabled=True),
        ),
    },
}


def compute_equity(results: pd.DataFrame) -> pd.Series:
    """Compute equity curve: long on BUY, short (inverse) on SELL."""
    closes = results['close'].values
    states = results['state'].shift().values  # prev_state drives today's return
    n = len(closes)
    equity = np.ones(n, dtype=float)
    for i in range(1, n):
        if states[i] == 'BUY':
            equity[i] = equity[i - 1] * (closes[i] / closes[i - 1])
        elif states[i] == 'SELL':
            equity[i] = equity[i - 1] * (closes[i - 1] / closes[i])
        else:
            equity[i] = equity[i - 1]
    return pd.Series(equity, index=results.index)


def compute_metrics(results: pd.DataFrame) -> dict:
    """Compute performance metrics."""
    equity = compute_equity(results)
    years = (results['date'].iloc[-1] - results['date'].iloc[0]).days / 365.25
    total_return = (equity.iloc[-1] - 1) * 100
    cagr = (equity.iloc[-1] ** (1 / years) - 1) * 100

    peak = equity.cummax()
    dd = (equity - peak) / peak
    max_dd = dd.min() * 100

    active_days = ((results['state'] == 'BUY') | (results['state'] == 'SELL')).sum()
    invested_pct = active_days / len(results) * 100
    long_trades = ((results['state'] == 'BUY') & (results['state'].shift() != 'BUY')).sum()
    short_trades = ((results['state'] == 'SELL') & (results['state'].shift() != 'SELL')).sum()
    trades = long_trades + short_trades

    return {
        'total_return': round(float(total_return), 1),
        'cagr': round(float(cagr), 1),
        'max_dd': round(float(max_dd), 1),
        'invested_pct': round(float(invested_pct), 1),
        'trades': int(trades),
    }


def compute_benchmark(df: pd.DataFrame) -> dict:
    """Compute buy-and-hold metrics."""
    bh_equity = df['close'] / df['close'].iloc[0]
    years = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
    bh_return = (bh_equity.iloc[-1] - 1) * 100
    bh_cagr = ((1 + bh_return / 100) ** (1 / years) - 1) * 100
    bh_peak = df['close'].cummax()
    bh_max_dd = ((df['close'] - bh_peak) / bh_peak).min() * 100

    return {
        'total_return': round(float(bh_return), 1),
        'cagr': round(float(bh_cagr), 1),
        'max_dd': round(float(bh_max_dd), 1),
    }


def detect_signals(results: pd.DataFrame) -> list:
    """Detect state transitions for signal markers."""
    signals = []
    states = results['state'].values
    dates = results['date'].values
    closes = results['close'].values

    for i in range(1, len(states)):
        if states[i] != states[i - 1]:
            signals.append({
                'date': pd.Timestamp(dates[i]).strftime('%Y-%m-%d'),
                'type': str(states[i]),
                'price': round(float(closes[i]), 2),
            })

    return signals


def format_trades(engine) -> list:
    """Extract and format trades from engine."""
    raw_trades = engine.get_trades()
    formatted = []
    for t in raw_trades:
        trade = {
            'type': t.get('type', ''),
            'date': pd.Timestamp(t['date']).strftime('%Y-%m-%d') if 'date' in t else '',
            'price': round(float(t['price']), 2) if 'price' in t else None,
            'pnl': round(float(t['pnl']) * 100, 2) if 'pnl' in t else None,
            'reason': t.get('reason', None),
            'signal_type': t.get('signal_type', None),
        }
        formatted.append(trade)
    return formatted


def build_equity_curve(results: pd.DataFrame) -> list:
    """Build daily equity curve with dates for JSON export."""
    equity = compute_equity(results)
    bh_equity = results['close'] / results['close'].iloc[0]
    dates = results['date']

    # Sample every 5th point to reduce JSON size
    step = max(1, len(dates) // 500)
    curve = []
    for i in range(0, len(dates), step):
        curve.append({
            'date': dates.iloc[i].strftime('%Y-%m-%d'),
            'strategy': round(float(equity.iloc[i]), 4),
            'buy_hold': round(float(bh_equity.iloc[i]), 4),
        })
    # Always include last point
    if len(dates) % step != 1:
        curve.append({
            'date': dates.iloc[-1].strftime('%Y-%m-%d'),
            'strategy': round(float(equity.iloc[-1]), 4),
            'buy_hold': round(float(bh_equity.iloc[-1]), 4),
        })
    return curve


def build_price_data(df: pd.DataFrame) -> list:
    """Build OHLCV price series for candlestick + volume chart."""
    prices = []
    for i in range(len(df)):
        prices.append({
            'date': df['date'].iloc[i].strftime('%Y-%m-%d'),
            'open': round(float(df['open'].iloc[i]), 2),
            'high': round(float(df['high'].iloc[i]), 2),
            'low': round(float(df['low'].iloc[i]), 2),
            'close': round(float(df['close'].iloc[i]), 2),
            'volume': int(df['volume'].iloc[i]),
        })
    return prices


INITIAL_CAPITAL = 100_000_000  # 100 trieu VND


def build_signal_history(results: pd.DataFrame) -> list:
    """Build chronological signal table with portfolio value.

    Similar to Dr. K's signal history table: each row is a state
    transition showing date, signal, price, portfolio value, and
    trade P&L.
    """
    equity = compute_equity(results)
    states = results['state'].values
    dates = results['date'].values
    closes = results['close'].values

    history = []
    buy_price = None

    for i in range(1, len(states)):
        if states[i] == states[i - 1]:
            continue

        new_state = str(states[i])
        date_str = pd.Timestamp(dates[i]).strftime('%Y-%m-%d')
        price = float(closes[i])
        portfolio = float(equity.iloc[i]) * INITIAL_CAPITAL
        trade_pnl = None

        if new_state == 'BUY':
            buy_price = price
        elif new_state in ('CASH', 'SELL') and buy_price is not None:
            trade_pnl = round((price - buy_price) / buy_price * 100, 2)
            buy_price = None

        history.append({
            'date': date_str,
            'signal': new_state,
            'price': round(price, 2),
            'portfolio': round(portfolio),
            'trade_pnl': trade_pnl,
            'cumulative_return': round((float(equity.iloc[i]) - 1) * 100, 2),
        })

    return history


def load_doc(filename: str) -> str:
    """Load strategy markdown doc."""
    path = os.path.join(PROJECT_ROOT, 'docs', filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


def export_model(key: str, info: dict, df: pd.DataFrame) -> dict:
    """Run one model and build export dict."""
    engine = HybridEngine(info['config']())
    results = engine.run(df.copy())

    return {
        'name': info['name'],
        'description_md': load_doc(info['doc_file']),
        'metrics': compute_metrics(results),
        'benchmark': compute_benchmark(df),
        'equity_curve': build_equity_curve(results),
        'signals': detect_signals(results),
        'trades': format_trades(engine),
        'signal_history': build_signal_history(results),
        'price_data': build_price_data(df),
    }


def export_v2_filtered_model(df: pd.DataFrame, output_data: dict):
    """Export MDM V2 with all v5.0 filters enabled (QE floor, SELL acceleration, BUY selectivity).

    Uses MDMV2Engine directly (not HybridEngine) with all filters ON.
    """
    config = V2StandaloneConfig(
        qe_floor_enabled=True,
        sell_acceleration_enabled=True,
        buy_filter_enabled=True,
        buy_confirmation_enabled=True,
        confirmation_window_days=3,
        confirmation_max_dd=1,
        name="v2_filtered",
    )
    engine = MDMV2Engine(config)
    results = engine.run(df.copy())

    model_data = {
        'name': 'MDM V2 + All Filters (v5.0)',
        'description_md': load_doc('rules_mdm_v2.md'),
        'metrics': compute_metrics(results),
        'benchmark': compute_benchmark(df),
        'equity_curve': build_equity_curve(results),
        'signals': detect_signals(results),
        'trades': format_trades(engine),
        'signal_history': build_signal_history(results),
        'price_data': build_price_data(df),
    }

    output_data['models']['mdm_v2_filtered'] = model_data
    print(f"    MDM V2 Filtered: {model_data['metrics']}")


def export_liquidity_overlay(output_data: dict):
    """Export Global Liquidity overlay data for dashboard chart.

    Reads global_liquidity.csv and extracts:
    - Line chart data (date + value)
    - QE floor active zones (start/end date pairs for shaded regions)
    """
    csv_path = os.path.join(PROJECT_ROOT, 'data', 'global_liquidity.csv')
    if not os.path.exists(csv_path):
        print(f"  WARNING: {csv_path} not found, skipping liquidity overlay")
        return

    liq_df = pd.read_csv(csv_path)
    liq_df['date'] = pd.to_datetime(liq_df['date'])

    # Build line chart data
    data_points = []
    step = max(1, len(liq_df) // 500)  # Sample to reduce JSON size
    for i in range(0, len(liq_df), step):
        row = liq_df.iloc[i]
        data_points.append({
            'date': row['date'].strftime('%Y-%m-%d'),
            'value': round(float(row['global_liquidity']), 2),
        })
    # Always include last point
    if len(liq_df) % step != 1:
        last = liq_df.iloc[-1]
        data_points.append({
            'date': last['date'].strftime('%Y-%m-%d'),
            'value': round(float(last['global_liquidity']), 2),
        })

    # Compute QE floor active zones (contiguous runs of qe_floor == 1)
    qe_zones = []
    in_zone = False
    zone_start = None
    for i in range(len(liq_df)):
        row = liq_df.iloc[i]
        qe_val = row.get('qe_floor', 0)
        if qe_val == 1 and not in_zone:
            in_zone = True
            zone_start = row['date'].strftime('%Y-%m-%d')
        elif qe_val != 1 and in_zone:
            in_zone = False
            zone_end = liq_df.iloc[i - 1]['date'].strftime('%Y-%m-%d')
            qe_zones.append({'start': zone_start, 'end': zone_end})
    # Close final zone if still active
    if in_zone:
        zone_end = liq_df.iloc[-1]['date'].strftime('%Y-%m-%d')
        qe_zones.append({'start': zone_start, 'end': zone_end})

    output_data['liquidity_overlay'] = {
        'data': data_points,
        'qe_zones': qe_zones,
    }
    print(f"  Liquidity overlay: {len(data_points)} points, {len(qe_zones)} QE zones")


def main():
    os.makedirs(DASHBOARD_DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("MDM DASHBOARD DATA EXPORT")
    print("=" * 60)

    print("\n[1/5] Loading VN30 data + indicators...")
    loader = DataLoader('vn30')
    df = loader.load(start_date=START_DATE, end_date=END_DATE)
    df = build_indicator_dataframe(df)
    print(f"  Loaded {len(df)} rows ({df['date'].min().date()} to {df['date'].max().date()})")

    print("\n[2/5] Running HybridEngine models and exporting...")
    all_model_keys = list(MODELS.keys())
    for key, info in MODELS.items():
        print(f"  Processing {info['name']}...")
        data = export_model(key, info, df)
        output_path = os.path.join(DASHBOARD_DATA_DIR, f'{key}.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"    -> {output_path} ({os.path.getsize(output_path) // 1024} KB)")

    print("\n[3/5] Running MDM V2 + All Filters model...")
    v2_filtered_data = {}
    v2_filtered_data['models'] = {}
    export_v2_filtered_model(df, v2_filtered_data)
    v2f_path = os.path.join(DASHBOARD_DATA_DIR, 'mdm_v2_filtered.json')
    with open(v2f_path, 'w', encoding='utf-8') as f:
        json.dump(v2_filtered_data['models']['mdm_v2_filtered'], f, ensure_ascii=False)
    print(f"    -> {v2f_path} ({os.path.getsize(v2f_path) // 1024} KB)")
    all_model_keys.append('mdm_v2_filtered')

    print("\n[4/5] Exporting Global Liquidity overlay...")
    liquidity_data = {}
    export_liquidity_overlay(liquidity_data)
    if 'liquidity_overlay' in liquidity_data:
        liq_path = os.path.join(DASHBOARD_DATA_DIR, 'liquidity_overlay.json')
        with open(liq_path, 'w', encoding='utf-8') as f:
            json.dump(liquidity_data['liquidity_overlay'], f, ensure_ascii=False)
        print(f"    -> {liq_path} ({os.path.getsize(liq_path) // 1024} KB)")

    print("\n[5/5] Writing metadata...")
    metadata = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'data_range': {
            'start': df['date'].min().strftime('%Y-%m-%d'),
            'end': df['date'].max().strftime('%Y-%m-%d'),
        },
        'models': all_model_keys,
        'has_liquidity_overlay': 'liquidity_overlay' in liquidity_data,
    }
    meta_path = os.path.join(DASHBOARD_DATA_DIR, 'metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Also write combined dashboard_data.json for convenience
    dashboard_data = {
        'models': {},
        'metadata': metadata,
    }
    # Include all model summaries (metrics only, not full data)
    for key in MODELS:
        model_path = os.path.join(DASHBOARD_DATA_DIR, f'{key}.json')
        with open(model_path, 'r', encoding='utf-8') as f:
            model_json = json.load(f)
        dashboard_data['models'][key] = {
            'name': model_json['name'],
            'metrics': model_json['metrics'],
        }
    # Add v2_filtered
    dashboard_data['models']['mdm_v2_filtered'] = {
        'name': v2_filtered_data['models']['mdm_v2_filtered']['name'],
        'metrics': v2_filtered_data['models']['mdm_v2_filtered']['metrics'],
    }
    if 'liquidity_overlay' in liquidity_data:
        dashboard_data['liquidity_overlay'] = liquidity_data['liquidity_overlay']

    dd_path = os.path.join(DASHBOARD_DATA_DIR, 'dashboard_data.json')
    with open(dd_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
    print(f"    -> {dd_path} ({os.path.getsize(dd_path) // 1024} KB)")

    total_models = len(all_model_keys)
    print(f"\n{'=' * 60}")
    print(f"DONE - {total_models} models exported to {DASHBOARD_DATA_DIR}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
