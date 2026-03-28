"""
Hypothesis Testing Framework for MDM v2

Each hypothesis is a named MDMV2Config. The runner executes the v2 engine
with that config, scores against published signals, and returns match rate.
"""
import sys
import os
import pandas as pd
from typing import List, Tuple, Dict, Any

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from strategies.mdm_v2.config import MDMV2Config
from strategies.mdm_v2.mdm_v2_engine import MDMV2Engine
from core.signal_comparator import extract_model_signals, compare_signals


def run_hypothesis(
    name: str,
    config: MDMV2Config,
    df: pd.DataFrame,
    published_signals: pd.DataFrame
) -> Dict[str, Any]:
    """Run a single hypothesis and return scored result.

    Args:
        name: Hypothesis name for identification
        config: MDMV2Config with parameter values to test
        df: NASDAQ OHLCV DataFrame (should include warm-up period from 2017+)
        published_signals: Published signal DataFrame (training set, 2019-2022)

    Returns:
        Dict with keys: hypothesis, match_rate, total_published, total_matched,
        buy_rate, sell_rate, cash_rate
    """
    config.name = name
    engine = MDMV2Engine(config)
    results = engine.run(df)
    model_signals = extract_model_signals(results)
    score = compare_signals(model_signals, published_signals)

    return {
        'hypothesis': name,
        'match_rate': score['match_rate'],
        'total_published': score['total_published'],
        'total_matched': score['total_matched'],
        'buy_rate': score['per_type']['Buy']['rate'],
        'sell_rate': score['per_type']['Sell']['rate'],
        'cash_rate': score['per_type']['Cash']['rate'],
    }


def run_batch(
    hypotheses: List[Tuple[str, MDMV2Config]],
    df: pd.DataFrame,
    published_signals: pd.DataFrame,
    top_n: int = None
) -> List[Dict[str, Any]]:
    """Run multiple hypotheses and return results sorted by match_rate descending.

    Args:
        hypotheses: List of (name, config) tuples
        df: NASDAQ OHLCV DataFrame
        published_signals: Published signal DataFrame
        top_n: If set, return only top N results

    Returns:
        List of result dicts sorted by match_rate descending
    """
    results = []
    for name, config in hypotheses:
        result = run_hypothesis(name, config, df, published_signals)
        results.append(result)

    results.sort(key=lambda r: r['match_rate'], reverse=True)

    if top_n is not None:
        results = results[:top_n]

    return results
