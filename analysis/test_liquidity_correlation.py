"""Test correlation of 5 liquidity proxies with VN30 same-day and 20d-forward returns; split VN30 performance by SBV policy regime; emit markdown verdict report."""

from __future__ import annotations

from math import sqrt
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd


VN30_CSV = Path('data/vn30_price.csv')
PROXY_CSV = Path('data/vn_liquidity_proxy.csv')
SBV_CSV = Path('data/sbv_policy_events.csv')
REPORT_MD = Path('docs/research/liquidity_proxy_correlation.md')
FWD_WINDOW = 20
CORR_THRESHOLD = 0.15
REGIME_CAGR_GAP_PP = 3.0
REGIME_SHARPE_GAP = 0.15
TRADING_DAYS = 252
PROXY_COLS = ['usdvnd_close', 'dxy_close', 'tnx_close', 'vnm_close', 'eem_close']
REGIME_DECAY_DAYS = 90


def load_vn30() -> pd.DataFrame:
    """Load VN30 daily closes and compute same-day + 20d-forward returns.

    Returns:
        DataFrame with columns ``[date, close, ret, ret_fwd20]`` sorted by date,
        filtered to ``>= 2015-01-01``.
    """
    df = pd.read_csv(VN30_CSV)
    df = df.rename(columns={'tradingdate': 'date', 'closeindex': 'close'})
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df = df.sort_values('date').reset_index(drop=True)
    df = df[df['date'] >= pd.Timestamp('2015-01-01')].reset_index(drop=True)
    df['ret'] = df['close'].pct_change()
    df['ret_fwd20'] = df['close'].pct_change(FWD_WINDOW).shift(-FWD_WINDOW)
    return df[['date', 'close', 'ret', 'ret_fwd20']]


def load_proxies() -> pd.DataFrame:
    """Load the liquidity proxy panel, forward-fill, and add returns + 20d z-scores.

    Returns:
        DataFrame keyed on date with price columns plus ``<col>_ret`` and ``<col>_z20``.
    """
    df = pd.read_csv(PROXY_CSV)
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df = df.sort_values('date').reset_index(drop=True)
    for col in PROXY_COLS:
        df[col] = df[col].ffill()
    for col in PROXY_COLS:
        df[f'{col}_ret'] = df[col].pct_change()
        mean20 = df[col].rolling(20, min_periods=20).mean()
        std20 = df[col].rolling(20, min_periods=20).std()
        df[f'{col}_z20'] = (df[col] - mean20) / std20
    return df


def load_sbv_regime(dates: pd.Series) -> pd.Series:
    """Map each date to an SBV policy regime using a 90-day decay on events.

    Args:
        dates: Sorted Series of pandas Timestamps to tag with regime.

    Returns:
        Series aligned to ``dates`` with values ∈ ``{'easing','tightening','neutral'}``.
    """
    events = pd.read_csv(SBV_CSV)
    events['date'] = pd.to_datetime(events['date'], format='%Y-%m-%d')
    events = events.sort_values('date').reset_index(drop=True)
    left = pd.DataFrame({'date': pd.to_datetime(dates.values)}).sort_values('date').reset_index(drop=True)
    merged = pd.merge_asof(
        left,
        events[['date', 'direction']].rename(columns={'date': 'event_date'}),
        left_on='date',
        right_on='event_date',
        direction='backward',
    )
    days_since = (merged['date'] - merged['event_date']).dt.days
    regime = merged['direction'].where(days_since <= REGIME_DECAY_DAYS, other='neutral')
    regime = regime.fillna('neutral')
    regime.index = dates.index
    regime.name = 'regime'
    return regime


def _pearson(a: pd.Series, b: pd.Series) -> float:
    """Pearson correlation after dropping rows where either input is NaN."""
    pair = pd.concat([a, b], axis=1).dropna()
    if len(pair) < 3:
        return float('nan')
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))


def compute_correlations(vn30: pd.DataFrame, proxies: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlations of proxy returns and z-scores vs VN30 same-day + 20d-fwd returns.

    Args:
        vn30: Output of :func:`load_vn30`.
        proxies: Output of :func:`load_proxies`.

    Returns:
        DataFrame indexed by proxy with columns
        ``[corr_sameday_ret, corr_fwd20_ret, corr_sameday_z, corr_fwd20_z]``.
    """
    merged = pd.merge(vn30, proxies, on='date', how='inner')
    rows = {}
    for col in PROXY_COLS:
        rows[col] = {
            'corr_sameday_ret': _pearson(merged[f'{col}_ret'], merged['ret']),
            'corr_fwd20_ret':   _pearson(merged[f'{col}_ret'], merged['ret_fwd20']),
            'corr_sameday_z':   _pearson(merged[f'{col}_z20'], merged['ret']),
            'corr_fwd20_z':     _pearson(merged[f'{col}_z20'], merged['ret_fwd20']),
        }
    return pd.DataFrame.from_dict(rows, orient='index')


def compute_regime_metrics(vn30: pd.DataFrame, regime: pd.Series) -> pd.DataFrame:
    """VN30 performance stats split by SBV policy regime.

    Args:
        vn30: Output of :func:`load_vn30`.
        regime: Output of :func:`load_sbv_regime` aligned to ``vn30.date``.

    Returns:
        DataFrame indexed by regime with columns
        ``[days, total_return_pct, cagr_pct, sharpe_rf3, max_dd_pct]``.
    """
    df = vn30.copy()
    df['regime'] = regime.values
    df = df.dropna(subset=['ret'])
    rows = {}
    for label in ['easing', 'neutral', 'tightening']:
        sub = df[df['regime'] == label]
        days = len(sub)
        if days == 0:
            rows[label] = {
                'days': 0,
                'total_return_pct': float('nan'),
                'cagr_pct': float('nan'),
                'sharpe_rf3': float('nan'),
                'max_dd_pct': float('nan'),
            }
            continue
        total_return = (1.0 + sub['ret']).prod() - 1.0
        cagr = (1.0 + total_return) ** (TRADING_DAYS / days) - 1.0
        ann_return = sub['ret'].mean() * TRADING_DAYS
        ann_std = sub['ret'].std() * sqrt(TRADING_DAYS)
        sharpe = (ann_return - 0.03) / ann_std if ann_std > 0 else float('nan')
        cum = (1.0 + sub['ret']).cumprod()
        running_max = cum.cummax()
        dd = (cum / running_max - 1.0)
        max_dd = dd.min()
        rows[label] = {
            'days': days,
            'total_return_pct': total_return * 100.0,
            'cagr_pct': cagr * 100.0,
            'sharpe_rf3': sharpe,
            'max_dd_pct': max_dd * 100.0,
        }
    return pd.DataFrame.from_dict(rows, orient='index')


def decide_verdict(corr_df: pd.DataFrame, regime_df: pd.DataFrame) -> Tuple[str, List[str]]:
    """Apply the two decision gates and return ``('GO'|'NO-GO', reasons_list)``.

    Gate A: any |corr_fwd20_ret| or |corr_fwd20_z| >= CORR_THRESHOLD.
    Gate B: regime CAGR spread >= REGIME_CAGR_GAP_PP or Sharpe spread >= REGIME_SHARPE_GAP.
    """
    reasons: List[str] = []
    gate_a = False
    abs_fwd = corr_df[['corr_fwd20_ret', 'corr_fwd20_z']].abs()
    max_abs = abs_fwd.max(axis=1)
    best_proxy = max_abs.idxmax()
    best_val = max_abs.max()
    if best_val >= CORR_THRESHOLD:
        gate_a = True
        reasons.append(
            f"Gate A PASSED: max |corr_fwd20| = {best_val:.4f} on {best_proxy} >= {CORR_THRESHOLD}."
        )
    else:
        reasons.append(
            f"Gate A FAILED: max |corr_fwd20| = {best_val:.4f} on {best_proxy} < {CORR_THRESHOLD}."
        )

    gate_b = False
    valid = regime_df.dropna(subset=['cagr_pct', 'sharpe_rf3'])
    if len(valid) >= 2:
        cagr_gap = valid['cagr_pct'].max() - valid['cagr_pct'].min()
        sharpe_gap = valid['sharpe_rf3'].max() - valid['sharpe_rf3'].min()
        if cagr_gap >= REGIME_CAGR_GAP_PP or sharpe_gap >= REGIME_SHARPE_GAP:
            gate_b = True
            reasons.append(
                f"Gate B PASSED: CAGR spread = {cagr_gap:.2f}pp, Sharpe spread = {sharpe_gap:.4f} "
                f"(thresholds {REGIME_CAGR_GAP_PP}pp / {REGIME_SHARPE_GAP})."
            )
        else:
            reasons.append(
                f"Gate B FAILED: CAGR spread = {cagr_gap:.2f}pp, Sharpe spread = {sharpe_gap:.4f} "
                f"(thresholds {REGIME_CAGR_GAP_PP}pp / {REGIME_SHARPE_GAP})."
            )
    else:
        reasons.append("Gate B SKIPPED: fewer than 2 regimes with valid metrics.")

    verdict = 'GO' if (gate_a or gate_b) else 'NO-GO'
    return verdict, reasons


def _manual_md(df: pd.DataFrame, floatfmt: str = '.4f') -> str:
    """Render a DataFrame as a GitHub-flavored markdown table without tabulate."""
    idx_name = df.index.name or ''
    header = [idx_name] + [str(c) for c in df.columns]
    align = ['|' + ' --- ' for _ in header]
    lines = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join([' --- '] * len(header)) + '|']
    for idx, row in df.iterrows():
        cells = [str(idx)]
        for v in row:
            if isinstance(v, (int, np.integer)):
                cells.append(str(int(v)))
            elif v is None or (isinstance(v, float) and np.isnan(v)):
                cells.append('NaN')
            else:
                cells.append(format(float(v), floatfmt))
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def _df_to_md(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(floatfmt='.4f')
    except ImportError:
        return _manual_md(df)


def write_report(
    corr_df: pd.DataFrame,
    regime_df: pd.DataFrame,
    verdict: str,
    reasons: List[str],
    vn30: pd.DataFrame,
) -> None:
    """Render the markdown research report at :data:`REPORT_MD`."""
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    context = (
        "Pre-v10.0 exploratory research. Phase 41 walk-forward validation showed "
        "all v9 scenarios degraded +67% to +96% when moving from Train 2015-2021 "
        "to Test 2022-2026, suggesting the post-2022 regime is hostile to pure "
        "price/volume features. This report tests whether a small basket of "
        "liquidity proxies (USDVND, DXY, US10Y, VNM ETF, EEM ETF) is correlated "
        "enough with VN30 same-day or 20-day-forward returns, or whether SBV "
        "policy regime (easing/neutral/tightening with a 90-day decay) explains "
        "enough of the CAGR/Sharpe gap to justify a v10.0 macro-regime filter."
    )
    corr_md = _df_to_md(corr_df)
    regime_md = _df_to_md(regime_df)
    reasons_md = '\n'.join(f"- {r}" for r in reasons)

    lines = [
        "# Liquidity Proxy Correlation with VN30 Returns",
        "",
        context,
        "",
        "## Correlation Table",
        "",
        "Pearson correlations of each proxy (daily returns and 20d rolling z-scores) "
        "with VN30 same-day returns and VN30 20d-forward returns. Inner-joined on VN30 "
        "trading days -- VN30 sessions with no matching proxy print (e.g. US holidays) "
        "are dropped from the correlation sample.",
        "",
        corr_md,
        "",
        "## SBV Regime Split",
        "",
        "VN30 performance partitioned by SBV policy regime. Regime tag derives from the "
        "most recent SBV easing or tightening event, decayed to `neutral` after "
        f"{REGIME_DECAY_DAYS} calendar days. Source file: `data/sbv_policy_events.csv`.",
        "",
        regime_md,
        "",
        "## Decision Gates",
        "",
        f"- **Gate A (correlation):** any proxy's |corr_fwd20_ret| or |corr_fwd20_z| "
        f">= `{CORR_THRESHOLD}`.",
        f"- **Gate B (regime dispersion):** CAGR spread across "
        f"{{easing, neutral, tightening}} >= `{REGIME_CAGR_GAP_PP}pp` OR Sharpe_rf3 "
        f"spread >= `{REGIME_SHARPE_GAP}`.",
        "",
        "Gate outcomes:",
        "",
        reasons_md,
        "",
        "## Verdict",
        "",
        f"**{verdict}**",
        "",
        "Reasoning:",
        "",
        reasons_md,
        "",
        "## Reproducibility",
        "",
        f"- Script: `analysis/test_liquidity_correlation.py`",
        f"- Inputs: `{VN30_CSV}`, `{PROXY_CSV}`, `{SBV_CSV}`",
        f"- VN30 date range used: {vn30['date'].min().strftime('%Y-%m-%d')} "
        f"-> {vn30['date'].max().strftime('%Y-%m-%d')} "
        f"({len(vn30)} rows)",
        f"- Forward-return window: {FWD_WINDOW} trading days",
        f"- Risk-free rate for Sharpe: 3% annual",
        "",
    ]
    REPORT_MD.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    """Orchestrate load -> compute -> decide -> write pipeline."""
    vn30 = load_vn30()
    proxies = load_proxies()
    regime = load_sbv_regime(vn30['date'])
    corr_df = compute_correlations(vn30, proxies)
    regime_df = compute_regime_metrics(vn30, regime)
    verdict, reasons = decide_verdict(corr_df, regime_df)
    write_report(corr_df, regime_df, verdict, reasons, vn30)
    top_corr = corr_df[['corr_fwd20_ret', 'corr_fwd20_z']].abs().max(axis=1).sort_values(ascending=False)
    print(f"Verdict: {verdict}")
    print(f"Top 3 |corr_fwd20|:")
    for name, val in top_corr.head(3).items():
        print(f"  {name}: {val:.4f}")
    print(f"Regime days: {regime_df['days'].to_dict()}")
    print(f"Report written to: {REPORT_MD}")


if __name__ == '__main__':
    main()
