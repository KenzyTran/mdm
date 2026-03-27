"""
VSA Regression Tests

Verify that VSA strategy output is identical after migration.
These tests import from the NEW strategy paths (strategies.vsa).
They will FAIL until Plan 02 completes the migration -- this is expected.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'

# VSA requires VN30_STOCKS_PRICE.csv which may not be available in all environments
VSA_DATA_FILE = Path(__file__).resolve().parent.parent / 'VN30_STOCKS_PRICE.csv'


@pytest.mark.regression
@pytest.mark.skipif(
    not VSA_DATA_FILE.exists(),
    reason='VN30_STOCKS_PRICE.csv not found -- VSA baselines require this data file'
)
class TestVSARegression:
    """Verify VSA strategy output is identical after migration."""

    @pytest.fixture(scope='class')
    def vsa_results(self):
        """Run VSA engine and return (nav_df, trades_df)."""
        from strategies.vsa.vsa_engine import VSAEngine

        engine = VSAEngine()
        engine.load_data(str(VSA_DATA_FILE))
        nav_df = engine.run()
        trades_df = engine.get_trades()
        return nav_df, trades_df

    def test_nav_history_matches(self, vsa_results):
        """Verify the NAV history is identical to baseline."""
        nav_df, _ = vsa_results
        baseline = pd.read_csv(
            FIXTURES / 'vsa_nav_baseline.csv',
            parse_dates=['date']
        )

        # Ensure date columns match types
        nav_df['date'] = pd.to_datetime(nav_df['date'])
        baseline['date'] = pd.to_datetime(baseline['date'])

        assert len(nav_df) == len(baseline), (
            f"NAV row count mismatch: got {len(nav_df)}, expected {len(baseline)}"
        )

        # Compare NAV values within tolerance
        np.testing.assert_allclose(
            nav_df['nav'].values,
            baseline['nav'].values,
            rtol=1e-10,
            err_msg='VSA NAV history mismatch'
        )

    def test_trade_count_matches(self, vsa_results):
        """Verify total number of trades matches baseline."""
        _, trades_df = vsa_results
        baseline = pd.read_csv(FIXTURES / 'vsa_trades_baseline.csv')
        assert len(trades_df) == len(baseline), (
            f"Trade count mismatch: got {len(trades_df)}, expected {len(baseline)}"
        )

    def test_trade_pnl_matches(self, vsa_results):
        """Verify trade P&L values are identical to baseline."""
        _, trades_df = vsa_results
        baseline = pd.read_csv(FIXTURES / 'vsa_trades_baseline.csv')

        # String columns exact match
        for col in trades_df.select_dtypes(include='object').columns:
            pd.testing.assert_series_equal(
                trades_df[col].reset_index(drop=True),
                baseline[col].reset_index(drop=True),
                check_names=False,
                obj=f'VSA trades column {col}'
            )

        # Float columns within tolerance
        for col in trades_df.select_dtypes(include='number').columns:
            np.testing.assert_allclose(
                trades_df[col].fillna(0).values,
                baseline[col].fillna(0).values,
                atol=1e-10,
                err_msg=f'VSA trades column {col} mismatch'
            )

    def test_exit_reasons_match(self, vsa_results):
        """Verify exit reasons are identical to baseline."""
        _, trades_df = vsa_results
        baseline = pd.read_csv(FIXTURES / 'vsa_trades_baseline.csv')

        pd.testing.assert_series_equal(
            trades_df['exit_reason'].reset_index(drop=True),
            baseline['exit_reason'].reset_index(drop=True),
            check_names=False,
            obj='VSA exit reasons'
        )
