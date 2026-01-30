"""
MDM Optimization Script
"""

import pandas as pd
import itertools
from typing import List, Dict
from models.config import MDMConfig
from models.mdm_engine import MDMEngine
from models.performance import PerformanceAnalyzer

def optimize_mdm():
    # Load data SAME AS BACKTEST
    engine = MDMEngine()
    # User uses VN30 from 2014-01-01
    df = engine.load_data(file_path='vn30_price.csv', start_date='2014-01-01', end_date='2026-01-16')
    
    # Define Parameter Grid
    # Focused on a few key parameters to keep search space reasonable
    param_grid = {
        'correction_threshold': [-0.08, -0.10, -0.12], # -8%, -10%, -12%
        'ftd_min_rally_day': [3, 4, 5],
        'stop_loss_pct': [0.015, 0.02, 0.025], # 1.5%, 2.0%, 2.5%
    }
    
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(itertools.product(*values))
    
    print(f"Total combinations to test: {len(combinations)}")
    
    results = []
    
    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        
        # Create config with these params
        config = MDMConfig(
            correction_threshold=params['correction_threshold'],
            ftd_min_rally_day=params['ftd_min_rally_day'],
            stop_loss_pct=params['stop_loss_pct'],
            # Keep others default for now
        )
        
        # Run Engine
        engine = MDMEngine(config)
        results_df_run = engine.run(df)
        trades = engine.get_trades()
        
        # Use Performance Analyzer for COMPOUND RETURN
        analyzer = PerformanceAnalyzer(results_df_run, trades)
        perf = analyzer.calculate_mdm_performance()
        
        # Collect result
        result_entry = params.copy()
        result_entry.update({
            'total_return': perf['total_return'], # Optimize for THIS (Compound Return)
            'win_rate': perf['win_rate'],
            'total_trades': perf['num_trades'],
            'max_drawdown': perf['max_drawdown']
        })
        results.append(result_entry)
        
        if (i+1) % 5 == 0:
            print(f"Processed {i+1}/{len(combinations)}...")
            
    # Create DataFrame
    results_df = pd.DataFrame(results)
    
    # Sort by total_return (Compound)
    results_df = results_df.sort_values('total_return', ascending=False)
    
    print("\nTop 5 Parameter Integers:")
    print(results_df.head(5).to_string())
    
    # Save to CSV
    results_df.to_csv('optimization_results.csv', index=False)
    print("\nFull results saved to optimization_results.csv")

if __name__ == "__main__":
    optimize_mdm()
