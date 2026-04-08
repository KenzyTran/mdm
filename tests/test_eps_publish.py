"""Tests for connectors.eps.resolve_eps_publish_date — DATA-04."""
import numpy as np
import pandas as pd
import pytest

from connectors.eps import resolve_eps_publish_date


def _row(year, length, **extra):
    base = {"stockcode": "VNM", "yearreport": year, "lengthreport": length, "eps": 1.0}
    base.update(extra)
    return base


def test_impute_q1_plus_45d():
    df = pd.DataFrame([_row(2023, 3)])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2023-05-15")


def test_impute_q2_plus_45d():
    df = pd.DataFrame([_row(2023, 6)])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2023-08-14")


def test_impute_q3_plus_45d():
    df = pd.DataFrame([_row(2023, 9)])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2023-11-14")


def test_impute_q4_plus_90d():
    df = pd.DataFrame([_row(2023, 12)])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2024-03-30")


def test_impute_annual_when_lengthreport_nan():
    df = pd.DataFrame([_row(2023, np.nan)])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2024-03-30")


def test_real_publish_date_column_wins():
    df = pd.DataFrame([_row(2023, 3, publish_date="2023-04-20")])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-20")


def test_announce_date_used_when_no_publish_date():
    df = pd.DataFrame([_row(2023, 3, announce_date="2023-04-22")])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-22")


def test_updated_at_used_as_last_resort():
    df = pd.DataFrame([_row(2023, 3, updated_at="2023-04-25")])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-25")


def test_mixed_real_and_imputed():
    df = pd.DataFrame([
        _row(2023, 3, publish_date="2023-04-20"),
        _row(2023, 6),
    ])
    out = resolve_eps_publish_date(df)
    assert out.loc[0, "publish_date"] == pd.Timestamp("2023-04-20")
    assert out.loc[1, "publish_date"] == pd.Timestamp("2023-08-14")


def test_missing_yearreport_raises():
    df = pd.DataFrame([{"stockcode": "VNM", "eps": 1.0}])
    with pytest.raises(ValueError, match="yearreport"):
        resolve_eps_publish_date(df)
