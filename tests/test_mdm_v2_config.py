"""Tests for MDMV2Config dataclass."""

import pytest
from strategies.mdm_v2.config import MDMV2Config


class TestMDMV2ConfigDefaults:
    """Test default configuration values."""

    def test_default_instance_creates(self):
        config = MDMV2Config()
        assert config is not None

    def test_dd_cash_threshold_default(self):
        config = MDMV2Config()
        assert config.dd_cash_threshold == 5

    def test_ma10_cash_enabled_default(self):
        config = MDMV2Config()
        assert config.ma10_cash_enabled is True

    def test_ma10_cash_consecutive_default(self):
        config = MDMV2Config()
        assert config.ma10_cash_consecutive == 2

    def test_ma50_sell_enabled_default(self):
        config = MDMV2Config()
        assert config.ma50_sell_enabled is True

    def test_cash_deterioration_days_default(self):
        config = MDMV2Config()
        assert config.cash_deterioration_days == 10

    def test_stop_loss_pct_default(self):
        config = MDMV2Config()
        assert config.stop_loss_pct == 0.025

    def test_name_default(self):
        config = MDMV2Config()
        assert config.name == "default"

    def test_classic_params_preserved(self):
        config = MDMV2Config()
        assert config.correction_threshold == -0.10
        assert config.ftd_min_rally_day == 3
        assert config.ftd_max_rally_day == 12
        assert config.ftd_min_price_gain == 0.01
        assert config.ma50_breakout_correction == -0.06
        assert config.dd_window_size == 20
        assert config.dd_price_drop_threshold == -0.002
        assert config.dd_price_stall_threshold == 0.001
        assert config.dd_stall_p_loc_threshold == 0.2


class TestMDMV2ConfigValidation:
    """Test configuration validation."""

    def test_positive_correction_threshold_raises(self):
        with pytest.raises(AssertionError):
            MDMV2Config(correction_threshold=0.1)

    def test_negative_stop_loss_raises(self):
        with pytest.raises(AssertionError):
            MDMV2Config(stop_loss_pct=-0.01)

    def test_zero_dd_cash_threshold_raises(self):
        with pytest.raises(AssertionError):
            MDMV2Config(dd_cash_threshold=0)


class TestMDMV2ConfigCustom:
    """Test custom configuration values."""

    def test_custom_dd_cash_threshold_and_name(self):
        config = MDMV2Config(dd_cash_threshold=4, name="aggressive")
        assert config.dd_cash_threshold == 4
        assert config.name == "aggressive"

    def test_custom_ma10_consecutive(self):
        config = MDMV2Config(ma10_cash_consecutive=3)
        assert config.ma10_cash_consecutive == 3

    def test_custom_cash_deterioration_days(self):
        config = MDMV2Config(cash_deterioration_days=15)
        assert config.cash_deterioration_days == 15
