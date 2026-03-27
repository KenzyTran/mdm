"""
MDM Regression Tests

Verify that MDM strategy output is identical after migration.
These tests import from the NEW strategy paths (strategies.mdm_classic).
They will FAIL until Plan 02 completes the migration -- this is expected.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.mark.regression
class TestMDMRegression:
    """Verify MDM strategy output is identical after migration."""

    @pytest.fixture(scope='class')
    def mdm_results(self):
        """Run MDM engine and return (results_df, engine)."""
        from strategies.mdm_classic.data_loader import DataLoader
        from strategies.mdm_classic import MDMEngine

        loader = DataLoader('vnindex_price.csv')
        df = loader.load(start_date='2014-01-01', end_date='2026-01-16')
        engine = MDMEngine()
        results = engine.run(df)
        return results, engine

    def test_signal_sequence_matches(self, mdm_results):
        """Verify the signal sequence is identical to baseline."""
        results, _ = mdm_results
        signals = results[results['action'] != ''][['date', 'close', 'state', 'action']].copy()
        signals = signals.reset_index(drop=True)

        baseline = pd.read_csv(
            FIXTURES / 'mdm_signals_baseline.csv',
            parse_dates=['date']
        )

        # Ensure date columns match types
        signals['date'] = pd.to_datetime(signals['date'])
        baseline['date'] = pd.to_datetime(baseline['date'])

        pd.testing.assert_frame_equal(
            signals, baseline,
            check_dtype=False,
            obj='MDM signal sequence'
        )

    def test_trade_pnl_matches(self, mdm_results):
        """Verify trade P&L values are identical to baseline."""
        _, engine = mdm_results
        trades = engine.get_trade_df()
        baseline = pd.read_csv(FIXTURES / 'mdm_trades_baseline.csv')

        assert len(trades) == len(baseline), (
            f"Trade count mismatch: got {len(trades)}, expected {len(baseline)}"
        )

        # String columns exact match
        for col in trades.select_dtypes(include='object').columns:
            pd.testing.assert_series_equal(
                trades[col].reset_index(drop=True),
                baseline[col].reset_index(drop=True),
                check_names=False,
                obj=f'MDM trades column {col}'
            )

        # Float columns within tolerance (~1e-10)
        for col in trades.select_dtypes(include='number').columns:
            np.testing.assert_allclose(
                trades[col].fillna(0).values,
                baseline[col].fillna(0).values,
                atol=1e-10,
                err_msg=f'MDM trades column {col} mismatch'
            )

    def test_trade_count(self, mdm_results):
        """Verify total number of trades matches baseline."""
        _, engine = mdm_results
        trades = engine.get_trade_df()
        baseline = pd.read_csv(FIXTURES / 'mdm_trades_baseline.csv')
        assert len(trades) == len(baseline)
